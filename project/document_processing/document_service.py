import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Tuple

from document_processing.markitdown_processor import DocumentProcessor

logger = logging.getLogger("document_service")


class DocumentService:

    def __init__(self, upload_dir: str = None):
        self.processor = DocumentProcessor()

    def prepare_temp_file(self, source_path: str) -> Path:
        """Copies the uploaded file into an isolated temporary directory."""
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file does not exist: {source_path}")

        temp_dir = Path(tempfile.mkdtemp(prefix="rag_ingest_"))
        temp_path = temp_dir / source_path.name
        shutil.copy2(source_path, temp_path)
        logger.info("Copied %s to isolated temp directory: %s", source_path, temp_path)
        return temp_path

    def process_and_metadata(
        self, file_path: Path, collection_name: str
    ) -> Tuple[str, dict]:
        """Processes a document file, returns converted markdown content and metadata dict."""
        markdown_content = self.processor.process_document(file_path)

        metadata = {
            "source": file_path.name,
            "filename": file_path.name,
            "collection": collection_name,
            "document_type": file_path.suffix.lower(),
            "upload_time": datetime.utcnow().isoformat(),
        }

        return markdown_content, metadata

    def cleanup(self, file_path: Path):
        """Cleans up the temporary file and its containing isolated temporary directory."""
        try:
            self.processor.cleanup_temp_file(file_path)
        except Exception as e:
            logger.warning("Error cleaning up processor temp file: %s", e)

        if file_path and file_path.exists():
            temp_dir = file_path.parent
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info("Cleaned up temp directory: %s", temp_dir)
            except Exception as e:
                logger.warning("Error removing temp directory %s: %s", temp_dir, e)
