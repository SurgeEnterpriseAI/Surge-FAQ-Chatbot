import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import config
from db.parent_store_manager import run_sync
from document_processing.document_service import DocumentService
from repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


class DocumentManager:

    def __init__(self, rag_system):
        self.rag_system = rag_system
        self.markdown_dir = Path(config.MARKDOWN_DIR)
        self.knowledge_base_dir = Path(config.KNOWLEDGE_BASE_DIR)
        self.doc_service = DocumentService()

    @staticmethod
    def _reject_if_too_large(doc_name: str, child_count: int, bypass_limit: bool = False):
        """Fail fast on a document that exceeds chunk limits."""
        if bypass_limit:
            return
        limit = getattr(config, "MAX_CHILD_CHUNKS_PER_DOCUMENT", 100000)
        if not limit or child_count <= limit:
            return
        raise ValueError(
            f"{doc_name} produces {child_count:,} chunks, over the {limit:,} limit."
        )

    def add_documents(
        self,
        document_paths,
        progress_callback=None,
        uploaded_by=None,
        version=None,
    ):
        """Ingest documents into Postgres parent_store and Pinecone with zero persistent local files."""
        if not document_paths:
            return 0, 0, []

        document_paths = (
            [document_paths] if isinstance(document_paths, str) else list(document_paths)
        )
        allowed_suffixes = {
            ".pdf",
            ".docx",
            ".pptx",
            ".txt",
            ".md",
            ".csv",
            ".xlsx",
            ".xls",
        }
        rejected = [
            Path(p).name
            for p in document_paths
            if p and Path(p).suffix.lower() not in allowed_suffixes
        ]
        document_paths = [
            p for p in document_paths if p and Path(p).suffix.lower() in allowed_suffixes
        ]

        if not document_paths:
            return 0, 0, [f"Unsupported file type: {name}" for name in rejected]

        added = 0
        skipped = 0
        self.last_errors = [f"Unsupported file type: {name}" for name in rejected]

        existing_sources = set(self.rag_system.parent_store.list_sources())
        total_files = len(document_paths)

        def report(file_index, fraction_within_file, message):
            if not progress_callback:
                return
            span = 1 / total_files
            progress_callback(
                min(file_index * span + fraction_within_file * span, 1.0), message
            )

        for i, doc_path in enumerate(document_paths):
            report(i, 0.0, f"Reading {Path(doc_path).name}")

            source_path = Path(doc_path)
            doc_name = source_path.name

            if doc_name in existing_sources:
                skipped += 1
                continue

            parent_ids = []
            temp_path = None
            document_id = None
            try:
                # 1. Copy upload into an isolated temporary directory
                temp_path = self.doc_service.prepare_temp_file(source_path)
                temp_dir = temp_path.parent

                # 2. Markdown conversion inside temp directory only
                markdown_content, meta = self.doc_service.process_and_metadata(
                    temp_path, self.rag_system.collection_name
                )
                meta["uploaded_by"] = uploaded_by or "Unknown"
                meta["version"] = version or "1.0"

                temp_md_path = temp_dir / f"{source_path.stem}.md"
                temp_md_path.write_text(markdown_content, encoding="utf-8")

                # 3. Create parent & child chunks
                report(i, 0.05, f"Chunking {doc_name}")
                is_medquad_or_csv = (
                    "medquad" in doc_name.lower() or source_path.suffix.lower() == ".csv"
                )
                chunk_source = temp_path if is_medquad_or_csv else temp_md_path

                parent_chunks, child_chunks = self.rag_system.chunker.create_chunks_single(
                    chunk_source,
                    source_name=doc_name,
                )

                if not child_chunks:
                    raise ValueError("No child chunks were created.")

                self._reject_if_too_large(
                    doc_name, len(child_chunks), bypass_limit=is_medquad_or_csv
                )

                # 4. Register document in database
                doc_rec = run_sync(
                    DocumentRepository.create_document(
                        filename=doc_name, metadata=meta, status="indexing"
                    )
                )
                if doc_rec:
                    document_id = doc_rec.id
                    meta["document_id"] = document_id

                for parent_id, doc in parent_chunks:
                    doc.metadata.update(meta)

                for chunk in child_chunks:
                    chunk.metadata.update(meta)

                # 5. Save parent chunks to Postgres in batches
                report(i, 0.10, f"Saving {len(parent_chunks):,} parent chunks for {doc_name}")
                parent_ids = [parent_id for parent_id, _ in parent_chunks]
                self.rag_system.parent_store.save_many(parent_chunks)

                # 6. Embed and upsert child chunks to Pinecone
                total_children = len(child_chunks)

                def on_embedded(done, _total=total_children, _idx=i, _name=doc_name):
                    report(
                        _idx,
                        0.15 + 0.85 * (done / _total),
                        f"Embedding {_name}: {done:,}/{_total:,} chunks",
                    )

                collection = self.rag_system.vector_db.get_collection(
                    self.rag_system.collection_name
                )
                collection.add_documents(child_chunks, progress_callback=on_embedded)

                if document_id:
                    run_sync(
                        DocumentRepository.mark_indexed(
                            document_id, chunk_count=len(child_chunks)
                        )
                    )

                existing_sources.add(doc_name)
                added += 1

            except Exception as e:
                self.rag_system.parent_store.delete_many(parent_ids)
                if document_id:
                    run_sync(DocumentRepository.mark_failed(document_id, str(e)))
                err_msg = f"Error processing {doc_name}: {e}"
                logger.error(err_msg)
                self.last_errors.append(err_msg)
            finally:
                if temp_path:
                    self.doc_service.cleanup(temp_path)

        if added == 0 and self.last_errors:
            raise ValueError("; ".join(self.last_errors))

        return added, skipped, list(self.last_errors)

    def get_markdown_files(self) -> List[str]:
        """List active document source filenames from the database."""
        db_docs = run_sync(DocumentRepository.list_documents())
        if db_docs:
            return sorted([doc.filename for doc in db_docs if doc.status == "indexed"])

        sources = self.rag_system.parent_store.list_sources()
        return sorted(sources)

    def delete_document(self, source_name: str) -> Dict:
        """Remove a document from the parent store, document database table, and vector index."""
        parent_ids = self.rag_system.parent_store.list_ids_for_source(source_name)

        if parent_ids:
            self.rag_system.parent_store.delete_many(parent_ids)

        run_sync(DocumentRepository.delete_document(source_name))

        vector_deleted = True
        try:
            collection = self.rag_system.vector_db.get_collection(
                self.rag_system.collection_name
            )
            collection.delete(filter={"source": source_name})
        except Exception as e:
            vector_deleted = False
            logger.warning("Could not delete vectors for %s: %s", source_name, e)

        return {"parents_deleted": len(parent_ids), "vector_deleted": vector_deleted}

    def reembed_from_parent_store(
        self, progress_callback=None, document_id: Optional[str] = None
    ) -> Tuple[int, int]:
        """Rebuilds Pinecone vector index directly from parent chunks stored in Postgres."""
        sources = self.rag_system.parent_store.list_sources()
        if not sources:
            return 0, 0

        added = 0
        skipped = 0
        total_sources = len(sources)

        for i, source_name in enumerate(sources):
            if progress_callback:
                progress_callback(i / total_sources, f"Re-embedding {source_name}")

            parent_ids = self.rag_system.parent_store.list_ids_for_source(source_name)
            if not parent_ids:
                skipped += 1
                continue

            try:
                parent_records = self.rag_system.parent_store.load_content_many(parent_ids)
                child_docs = []

                for record in parent_records:
                    pid = record["parent_id"]
                    content = record["content"]
                    metadata = record.get("metadata", {})

                    if "medquad" in source_name.lower() or metadata.get("row") is not None:
                        focus_area = metadata.get("focus_area", "")
                        lines = content.split("\n")
                        question_line = lines[0] if lines else content
                        child_text = question_line
                        if focus_area:
                            child_text += f"\nFocus: {focus_area}"
                        if len(child_text) > 1500:
                            child_text = child_text[:1500]

                        child_meta = dict(metadata)
                        child_meta["id"] = f"{pid}_c0"
                        if hasattr(self.rag_system, "collection_name"):
                            child_meta["collection"] = self.rag_system.collection_name

                        from langchain_core.documents import Document

                        child_docs.append(Document(page_content=child_text, metadata=child_meta))
                    else:
                        from langchain_core.documents import Document

                        parent_doc = Document(page_content=content, metadata=metadata)
                        splits = self.rag_system.chunker._DocumentChunker__child_splitter.split_documents([parent_doc])
                        for idx, s in enumerate(splits):
                            s.metadata["id"] = f"{pid}_c{idx}"
                            child_docs.append(s)

                if child_docs:
                    collection = self.rag_system.vector_db.get_collection(
                        self.rag_system.collection_name
                    )
                    collection.add_documents(child_docs)
                    added += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error("Error re-embedding source %s: %s", source_name, e)
                skipped += 1

        if progress_callback:
            progress_callback(1.0, "Re-embedding complete")

        return added, skipped

    def clear_all(self):
        """Clear Pinecone vector index, Postgres parent chunks, and documents table."""
        self.rag_system.vector_db.delete_collection(self.rag_system.collection_name)
        self.rag_system.parent_store.clear_store()
        run_sync(DocumentRepository.clear_all_documents())
        self.rag_system.vector_db.create_collection(self.rag_system.collection_name)
