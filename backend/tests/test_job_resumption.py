import json
import pytest
from pathlib import Path
from backend.services.upload_service import UploadService, UploadJob, REGISTRY_PATH

def test_job_persistence_and_interruption(tmp_path: Path, monkeypatch):
    test_registry = tmp_path / "jobs_registry.json"
    import backend.services.upload_service as service_module
    monkeypatch.setattr(service_module, "REGISTRY_PATH", test_registry)

    service1 = UploadService()
    job = UploadJob(id="job_test_123", kind="upload", status="running", progress=0.45, current_file="medquad.csv")
    service1._jobs[job.id] = job
    service1._save_registry()

    assert test_registry.exists()

    # Simulate backend restart by initializing a new service instance
    service2 = UploadService()
    reloaded_job = service2.get("job_test_123")

    assert reloaded_job is not None
    assert reloaded_job.status == "interrupted"
    assert "restarted" in reloaded_job.error.lower()
    assert reloaded_job.progress == 0.45
