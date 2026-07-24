"""Ingestion job registry with disk persistence and resumption state.

Wraps the existing DocumentManager pipeline in a worker thread, reports progress,
and persists job state to uploads/jobs_registry.json so restarts do not lose track
of running or interrupted jobs.
"""
import asyncio
import json
import logging
import shutil
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from backend.bootstrap import PROJECT_DIR

logger = logging.getLogger(__name__)
REGISTRY_PATH = PROJECT_DIR / "uploads" / "jobs_registry.json"


@dataclass
class UploadJob:
    id: str
    kind: str  # "upload" | "reindex"
    status: str = "pending"  # pending | running | completed | completed_with_errors | failed | interrupted
    progress: float = 0.0
    current_file: str = ""
    added: int = 0
    skipped: int = 0
    error: str | None = None
    cleanup_dir: Path | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("cleanup_dir", None)
        return d


class UploadService:

    def __init__(self):
        self._jobs: dict[str, UploadJob] = {}
        self._load_registry()

    def _save_registry(self) -> None:
        try:
            REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {job_id: job.to_dict() for job_id, job in self._jobs.items()}
            REGISTRY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to persist upload jobs registry: %s", e)

    def _load_registry(self) -> None:
        if not REGISTRY_PATH.exists():
            return
        try:
            content = REGISTRY_PATH.read_text(encoding="utf-8")
            data = json.loads(content)
            for job_id, d in data.items():
                # Any job left in 'running' or 'pending' state during startup was interrupted by restart
                if d.get("status") in ("running", "pending"):
                    d["status"] = "interrupted"
                    d["error"] = "Backend restarted while job was in progress."
                job = UploadJob(**d)
                self._jobs[job_id] = job
        except Exception as e:
            logger.warning("Failed to load upload jobs registry: %s", e)

    def get(self, job_id: str) -> UploadJob | None:
        return self._jobs.get(job_id)

    def start_ingest(
        self,
        doc_manager,
        paths: list[Path],
        lock: threading.Lock,
        cleanup_dir: Path | None = None,
        uploaded_by: str = "Unknown",
        version: str = "1.0",
    ) -> UploadJob:
        job = UploadJob(id=uuid.uuid4().hex, kind="upload", cleanup_dir=cleanup_dir)
        self._jobs[job.id] = job
        self._save_registry()
        asyncio.get_running_loop().create_task(
            self._run_ingest(job, doc_manager, paths, lock, uploaded_by, version)
        )
        return job

    def start_reindex(self, doc_manager, lock: threading.Lock) -> UploadJob:
        job = UploadJob(id=uuid.uuid4().hex, kind="reindex")
        self._jobs[job.id] = job
        self._save_registry()
        asyncio.get_running_loop().create_task(self._run_reindex(job, doc_manager, lock))
        return job

    async def _run_ingest(
        self,
        job: UploadJob,
        doc_manager,
        paths: list[Path],
        lock: threading.Lock,
        uploaded_by: str,
        version: str,
    ) -> None:
        job.status = "running"
        self._save_registry()
        try:
            job.added, job.skipped, errors = await asyncio.to_thread(
                self._ingest, job, doc_manager, paths, lock, uploaded_by, version
            )
            job.progress = 1.0
            if errors:
                job.status = "completed_with_errors"
                job.error = "; ".join(errors)
            else:
                job.status = "completed"
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
        finally:
            self._save_registry()
            self._cleanup(job)

    async def _run_reindex(self, job: UploadJob, doc_manager, lock: threading.Lock) -> None:
        job.status = "running"
        self._save_registry()
        try:
            await asyncio.to_thread(self._reindex, job, doc_manager, lock)
            job.progress = 1.0
            job.status = "completed"
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
        finally:
            self._save_registry()

    def _ingest(
        self,
        job: UploadJob,
        doc_manager,
        paths: list[Path],
        lock: threading.Lock,
        uploaded_by: str,
        version: str,
    ) -> tuple[int, int, list[str]]:
        def progress_callback(fraction: float, desc: str = "") -> None:
            job.progress = float(fraction)
            job.current_file = desc
            self._save_registry()

        with lock:
            return doc_manager.add_documents(
                [str(p) for p in paths],
                progress_callback=progress_callback,
                uploaded_by=uploaded_by,
                version=version,
            )

    def _reindex(self, job: UploadJob, doc_manager, lock: threading.Lock) -> None:
        def progress_callback(fraction: float, desc: str = "") -> None:
            job.progress = float(fraction)
            job.current_file = desc
            self._save_registry()

        with lock:
            job.progress = 0.1
            job.current_file = "Clearing Pinecone vector collection"
            self._save_registry()

            doc_manager.rag_system.vector_db.delete_collection(doc_manager.rag_system.collection_name)
            doc_manager.rag_system.vector_db.create_collection(doc_manager.rag_system.collection_name)

            job.progress = 0.2
            job.current_file = "Re-embedding vectors from database parent store"
            self._save_registry()

            added, skipped = doc_manager.reembed_from_parent_store(
                progress_callback=progress_callback
            )

            job.added = added
            job.skipped = skipped
            job.progress = 1.0
            job.current_file = "Re-indexing complete"
            self._save_registry()


    @staticmethod
    def _cleanup(job: UploadJob) -> None:
        if job.cleanup_dir is not None:
            shutil.rmtree(job.cleanup_dir, ignore_errors=True)
