import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, List

import config
from config.settings import settings
from database.supabase_client import connect_prisma, prisma_client
from db.retry import retry_with_backoff
from prisma import Json

logger = logging.getLogger(__name__)


def run_sync(coro):
    """Run an async coroutine synchronously from a worker thread."""
    try:
        from database import supabase_client

        owner_loop = supabase_client.prisma_main_loop
        if owner_loop is not None and owner_loop.is_running():
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None
            if running is not owner_loop:
                return asyncio.run_coroutine_threadsafe(coro, owner_loop).result()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # ``run_until_complete`` on Uvicorn's loop (even after applying
            # nest_asyncio) corrupts AnyIO task scheduling and eventually
            # resets active HTTP connections.  Callers from the API already
            # run these blocking store methods in a worker thread.
            raise RuntimeError("Parent store synchronous access must run outside the event-loop thread")
        return loop.run_until_complete(coro)
    except Exception:
        if asyncio.iscoroutine(coro):
            coro.close()
        raise



def _parse_metadata(metadata) -> Dict:
    if not metadata:
        return {}
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        try:
            return json.loads(metadata)
        except Exception:
            return {}
    return {}


async def _save_async(parent_id: str, content: str, metadata: Dict) -> None:
    await connect_prisma()
    existing = await prisma_client.parentchunk.find_unique(where={"id": parent_id})
    data = {"content": content, "metadata": Json(metadata) if metadata else None}
    if existing:
        await prisma_client.parentchunk.update(where={"id": parent_id}, data=data)
    else:
        await prisma_client.parentchunk.create(data={"id": parent_id, **data})


async def _save_many_async(parents: List) -> None:
    await connect_prisma()
    batch_size = 500
    for i in range(0, len(parents), batch_size):
        batch = parents[i : i + batch_size]
        data = [
            {
                "id": parent_id,
                "content": doc.page_content if hasattr(doc, "page_content") else str(doc),
                "metadata": Json(doc.metadata) if hasattr(doc, "metadata") and doc.metadata else None,
            }
            for parent_id, doc in batch
        ]
        await prisma_client.parentchunk.create_many(data=data, skip_duplicates=True)


async def _delete_many_async(parent_ids: List[str]) -> None:
    await connect_prisma()
    # Batch deletes in groups of 500 to avoid giant SQL expressions
    batch_size = 500
    for i in range(0, len(parent_ids), batch_size):
        batch = parent_ids[i : i + batch_size]
        await prisma_client.parentchunk.delete_many(where={"id": {"in": batch}})


async def _load_async(parent_id: str) -> Dict:
    await connect_prisma()
    clean_id = parent_id[:-5] if parent_id.lower().endswith(".json") else parent_id
    record = await prisma_client.parentchunk.find_unique(where={"id": clean_id})
    if not record:
        raise FileNotFoundError(f"Parent chunk not found: {parent_id}")
    return {"page_content": record.content, "metadata": _parse_metadata(record.metadata)}


async def _list_sources_async() -> List[str]:
    await connect_prisma()
    # Projected in SQL: find_many() would stream every parent chunk's full
    # content (tens of MB) across the pooler just to read one metadata key.
    rows = await prisma_client.query_raw(
        "SELECT DISTINCT metadata->>'source' AS source FROM parent_chunks "
        "WHERE metadata->>'source' IS NOT NULL AND metadata->>'source' != ''"
    )
    return sorted(row["source"] for row in rows)


async def _list_ids_for_source_async(source_name: str) -> List[str]:
    await connect_prisma()
    # Prisma's JSON-path filter is unsupported by prisma-client-py and raised
    # FieldNotFoundError, so the old fallback fetched the entire table.
    rows = await prisma_client.query_raw(
        "SELECT id FROM parent_chunks WHERE metadata->>'source' = $1", source_name
    )
    return [row["id"] for row in rows]


async def _clear_store_async() -> None:
    await connect_prisma()
    await prisma_client.parentchunk.delete_many()


class ParentStoreManager:
    """Parent-chunk storage backed by Postgres with strict cloud mode.

    When CLOUD_BACKEND_ENABLED=true, state is written strictly to Postgres with zero
    local file creation and no silent local fallbacks.
    """

    _degraded = False
    _degradation_reason = None

    def __init__(self, store_path=None):
        self.store_path = Path(store_path or config.PARENT_STORE_PATH)
        # Only create parent_store/ directory when cloud mode is NOT enabled
        if not self.use_database:
            self.store_path.mkdir(parents=True, exist_ok=True)

    @property
    def use_database(self) -> bool:
        return bool(
            settings.CLOUD_BACKEND_ENABLED
            and settings.DATABASE_URL
            and not (not settings.CLOUD_BACKEND_ENABLED and ParentStoreManager._degraded)
        )

    @classmethod
    def degradation_reason(cls):
        """Why the store fell back to local JSON, or None while healthy."""
        if settings.CLOUD_BACKEND_ENABLED:
            return None
        return cls._degradation_reason

    def _path_for(self, parent_id: str) -> Path:
        clean_id = parent_id[:-5] if parent_id.lower().endswith(".json") else parent_id
        safe_id = clean_id.replace("/", "_").replace("\\", "_")
        return self.store_path / f"{safe_id}.json"

    def _save_local(self, parent_id: str, content: str, metadata: Dict) -> None:
        payload = {"page_content": content, "metadata": metadata or {}}
        self.store_path.mkdir(parents=True, exist_ok=True)
        self._path_for(parent_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_local(self, parent_id: str) -> Dict:
        path = self._path_for(parent_id)
        if not path.exists():
            raise FileNotFoundError(f"Parent chunk not found: {parent_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _database_failed(self, operation: str, exc: Exception) -> None:
        """Handle database failure strictly based on cloud mode setting."""
        if settings.CLOUD_BACKEND_ENABLED:
            logger.error(
                "Database parent store unavailable during '%s' in strict cloud mode: %s",
                operation,
                exc,
            )
            raise RuntimeError(
                f"Database parent store failed during '{operation}' in strict cloud mode: {exc}"
            ) from exc

        if not ParentStoreManager._degraded:
            ParentStoreManager._degraded = True
            ParentStoreManager._degradation_reason = f"{operation}: {exc}"
            logger.error(
                "Database parent store unavailable during %s; falling back to local store: %s",
                operation,
                exc,
            )

    def save(self, parent_id: str, content: str, metadata: Dict) -> None:
        if not self.use_database:
            self._save_local(parent_id, content, metadata)
            return
        try:
            retry_with_backoff(lambda: run_sync(_save_async(parent_id, content, metadata)))
        except Exception as exc:
            self._database_failed("save", exc)
            if not settings.CLOUD_BACKEND_ENABLED:
                self._save_local(parent_id, content, metadata)

    def save_many(self, parents: List) -> None:
        if not parents:
            return
        if not self.use_database:
            for parent_id, doc in parents:
                content = doc.page_content if hasattr(doc, "page_content") else str(doc)
                metadata = doc.metadata if hasattr(doc, "metadata") else {}
                self._save_local(parent_id, content, metadata)
            return
        try:
            retry_with_backoff(lambda: run_sync(_save_many_async(parents)))
        except Exception as exc:
            self._database_failed("save_many", exc)
            if not settings.CLOUD_BACKEND_ENABLED:
                for parent_id, doc in parents:
                    content = doc.page_content if hasattr(doc, "page_content") else str(doc)
                    metadata = doc.metadata if hasattr(doc, "metadata") else {}
                    self._save_local(parent_id, content, metadata)

    def delete_many(self, parent_ids: List[str]) -> None:
        if not parent_ids:
            return
        if not self.use_database:
            for parent_id in parent_ids:
                self._path_for(parent_id).unlink(missing_ok=True)
            return
        try:
            retry_with_backoff(lambda: run_sync(_delete_many_async(parent_ids)))
        except Exception as exc:
            self._database_failed("delete_many", exc)
            if not settings.CLOUD_BACKEND_ENABLED:
                for parent_id in parent_ids:
                    self._path_for(parent_id).unlink(missing_ok=True)

    def load(self, parent_id: str) -> Dict:
        if not self.use_database:
            return self._load_local(parent_id)
        try:
            return run_sync(_load_async(parent_id))
        except FileNotFoundError:
            raise
        except Exception as exc:
            self._database_failed("load", exc)
            return self._load_local(parent_id)

    def load_content(self, parent_id: str) -> Dict:
        data = self.load(parent_id)
        clean_id = parent_id[:-5] if parent_id.lower().endswith(".json") else parent_id
        return {
            "content": data["page_content"],
            "parent_id": clean_id,
            "metadata": data.get("metadata", {}),
        }

    def load_content_many(self, parent_ids: List[str]) -> List[Dict]:
        def sort_key(id_str):
            match = re.search(r"_(?:parent_|p)(\d+)$", id_str)
            return int(match.group(1)) if match else 0

        return [self.load_content(pid) for pid in sorted(set(parent_ids), key=sort_key)]

    def list_sources(self) -> List[str]:
        if not self.use_database:
            sources = set()
            if self.store_path.exists():
                for path in self.store_path.glob("*.json"):
                    try:
                        source = (
                            json.loads(path.read_text(encoding="utf-8"))
                            .get("metadata", {})
                            .get("source")
                        )
                        if source:
                            sources.add(source)
                    except Exception:
                        continue
            return sorted(sources)
        try:
            return retry_with_backoff(lambda: run_sync(_list_sources_async()))
        except Exception as exc:
            self._database_failed("list_sources", exc)
            return self.list_sources()

    def list_ids_for_source(self, source_name: str) -> List[str]:
        if not self.use_database:
            ids = []
            if self.store_path.exists():
                for path in self.store_path.glob("*.json"):
                    try:
                        payload = json.loads(path.read_text(encoding="utf-8"))
                        if payload.get("metadata", {}).get("source") == source_name:
                            ids.append(path.stem)
                    except Exception:
                        continue
            return ids
        try:
            return retry_with_backoff(lambda: run_sync(_list_ids_for_source_async(source_name)))
        except Exception as exc:
            self._database_failed("list_ids_for_source", exc)
            return self.list_ids_for_source(source_name)

    def clear_store(self) -> None:
        if not self.use_database:
            if self.store_path.exists():
                for path in self.store_path.glob("*.json"):
                    path.unlink()
            return
        try:
            retry_with_backoff(lambda: run_sync(_clear_store_async()))
        except Exception as exc:
            self._database_failed("clear_store", exc)
            if not settings.CLOUD_BACKEND_ENABLED:
                self.clear_store()
