import logging
import uuid
from typing import Dict, List, Optional

from database.supabase_client import connect_prisma, prisma_client
from prisma import Json

logger = logging.getLogger(__name__)


class DocumentRepository:

    @staticmethod
    async def create_document(
        filename: str, metadata: Optional[Dict] = None, status: str = "pending"
    ):
        """Create or update a document record in Postgres."""
        await connect_prisma()
        try:
            existing = await prisma_client.document.find_unique(where={"filename": filename})
            data = {
                "filename": filename,
                "status": status,
                "metadata": Json(metadata) if metadata else None,
            }
            if existing:
                return await prisma_client.document.update(
                    where={"filename": filename}, data=data
                )
            else:
                data["id"] = str(uuid.uuid4())
                return await prisma_client.document.create(data=data)
        except Exception as e:
            logger.error("Error creating document record '%s': %s", filename, e)
            raise RuntimeError(f"Database error during document record creation: {e}") from e

    @staticmethod
    async def mark_indexing(document_id: str):
        """Mark document status as indexing."""
        await connect_prisma()
        try:
            return await prisma_client.document.update(
                where={"id": document_id}, data={"status": "indexing"}
            )
        except Exception as e:
            logger.error("Error marking document '%s' as indexing: %s", document_id, e)

    @staticmethod
    async def mark_indexed(document_id: str, chunk_count: int):
        """Mark document status as indexed with total chunk count."""
        await connect_prisma()
        try:
            return await prisma_client.document.update(
                where={"id": document_id},
                data={"status": "indexed", "chunkCount": chunk_count},
            )
        except Exception as e:
            logger.error("Error marking document '%s' as indexed: %s", document_id, e)

    @staticmethod
    async def mark_failed(document_id: str, error: Optional[str] = None):
        """Mark document status as failed."""
        await connect_prisma()
        try:
            meta = {}
            if error:
                meta["error"] = str(error)
            return await prisma_client.document.update(
                where={"id": document_id},
                data={"status": "failed", "metadata": Json(meta) if meta else None},
            )
        except Exception as e:
            logger.error("Error marking document '%s' as failed: %s", document_id, e)

    @staticmethod
    async def get_by_filename(filename: str):
        """Find document by exact filename."""
        await connect_prisma()
        try:
            return await prisma_client.document.find_unique(where={"filename": filename})
        except Exception as e:
            logger.error("Error fetching document by filename '%s': %s", filename, e)
            return None

    @staticmethod
    async def list_documents() -> List:
        """Retrieve all document records ordered by creation date descending."""
        await connect_prisma()
        try:
            return await prisma_client.document.find_many(order={"createdAt": "desc"})
        except Exception as e:
            logger.error("Error listing documents: %s", e)
            return []

    @staticmethod
    async def delete_document(filename_or_id: str) -> bool:
        """Delete a document record by filename or ID."""
        await connect_prisma()
        try:
            doc = await prisma_client.document.find_unique(where={"filename": filename_or_id})
            if doc:
                await prisma_client.document.delete(where={"filename": filename_or_id})
                return True
            doc_by_id = await prisma_client.document.find_unique(where={"id": filename_or_id})
            if doc_by_id:
                await prisma_client.document.delete(where={"id": filename_or_id})
                return True
            return False
        except Exception as e:
            logger.error("Error deleting document record '%s': %s", filename_or_id, e)
            return False

    @staticmethod
    async def clear_all_documents() -> None:
        """Delete all document records."""
        await connect_prisma()
        try:
            await prisma_client.document.delete_many()
        except Exception as e:
            logger.error("Error clearing document records: %s", e)
