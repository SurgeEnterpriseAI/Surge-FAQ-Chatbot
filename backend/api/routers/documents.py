import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.bootstrap import PROJECT_DIR
from backend.dependencies import (
    get_current_user,
    get_doc_manager,
    get_ingest_lock,
    get_upload_service,
)
from backend.schemas.documents import (
    DocumentListResponse,
    DocumentOut,
    UploadJobStatus,
    UploadResponse,
)

router = APIRouter(tags=["documents"])

ALLOWED_SUFFIXES = {".pdf", ".docx", ".pptx", ".txt", ".md", ".csv", ".xlsx", ".xls"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
API_UPLOAD_DIR = PROJECT_DIR / "uploads" / "api"


def _job_status(job) -> UploadJobStatus:
    return UploadJobStatus(
        job_id=job.id,
        kind=job.kind,
        status=job.status,
        progress=job.progress,
        current_file=job.current_file,
        added=job.added,
        skipped=job.skipped,
        error=job.error,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload(
    files: list[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
    doc_manager=Depends(get_doc_manager),
    lock=Depends(get_ingest_lock),
    upload_service=Depends(get_upload_service),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # One directory per job so original filenames are preserved (the ingest
    # pipeline dedupes by file name) without cross-upload collisions.
    job_dir = API_UPLOAD_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []
    for f in files:
        name = Path(f.filename or "").name
        if not name or Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {name or 'unknown'}. Allowed: {', '.join(sorted(ALLOWED_SUFFIXES))}",
            )
        content = await f.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"{name} exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit",
            )
        dest = job_dir / name
        dest.write_bytes(content)
        saved_paths.append(dest)

    # Originals are retained by DocumentManager once a file ingests successfully,
    # so a failed upload does not leave an orphan copy behind.
    job = upload_service.start_ingest(
        doc_manager,
        saved_paths,
        lock,
        cleanup_dir=job_dir,
        uploaded_by=user.get("email") or user.get("user_id") or "Unknown",
        version="1.0"
    )
    return UploadResponse(job_id=job.id)


@router.get("/upload/{job_id}", response_model=UploadJobStatus)
async def upload_status(
    job_id: str,
    user: dict = Depends(get_current_user),
    upload_service=Depends(get_upload_service),
):
    job = upload_service.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Upload job not found")
    return _job_status(job)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(user: dict = Depends(get_current_user), doc_manager=Depends(get_doc_manager)):
    from repositories.document_repository import DocumentRepository

    db_docs = await DocumentRepository.list_documents()
    out_docs = []

    if db_docs:
        for doc in db_docs:
            searchable = (doc.status == "indexed")
            pct = 100.0 if doc.status == "indexed" else 0.0
            out_docs.append(
                DocumentOut(
                    source=doc.filename,
                    markdown_file=Path(doc.filename).with_suffix(".md").name,
                    searchable=searchable,
                    status=doc.status,
                    vectors_indexed=doc.chunkCount or 0,
                    expected_chunks=doc.chunkCount or 0,
                    progress_pct=pct,
                )
            )
    else:
        sources = await asyncio.to_thread(doc_manager.rag_system.parent_store.list_sources)
        for s in sources:
            parent_ids = doc_manager.rag_system.parent_store.list_ids_for_source(s)
            count = len(parent_ids)
            out_docs.append(
                DocumentOut(
                    source=s,
                    markdown_file=Path(s).with_suffix(".md").name,
                    searchable=True,
                    status="indexed",
                    vectors_indexed=count,
                    expected_chunks=count,
                    progress_pct=100.0,
                )
            )

    return DocumentListResponse(documents=out_docs)



@router.delete("/document/{source_name}")
async def delete_document(
    source_name: str,
    user: dict = Depends(get_current_user),
    doc_manager=Depends(get_doc_manager),
    lock=Depends(get_ingest_lock),
):
    def _delete():
        with lock:
            return doc_manager.delete_document(source_name)

    try:
        result = await asyncio.to_thread(_delete)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No indexed document named {source_name}")

    if not result["vector_deleted"]:
        raise HTTPException(
            status_code=501,
            detail=(
                "Document removed from the parent store and markdown cache, but this "
                "Pinecone tier does not support metadata-filter deletes. Run POST "
                "/api/reindex to rebuild the vector index."
            ),
        )
    return {"status": "deleted", "source": source_name, **result}


@router.post("/reindex", response_model=UploadResponse)
async def reindex(
    user: dict = Depends(get_current_user),
    doc_manager=Depends(get_doc_manager),
    lock=Depends(get_ingest_lock),
    upload_service=Depends(get_upload_service),
):
    job = upload_service.start_reindex(doc_manager, lock)
    return UploadResponse(job_id=job.id)
