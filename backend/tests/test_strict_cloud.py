from unittest.mock import MagicMock, patch
import pytest

from db.retry import retry_with_backoff
from db.parent_store_manager import ParentStoreManager


def test_retry_with_backoff_success():
    calls = []

    def flaky_func():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("Temporary disconnect")
        return "success"

    result = retry_with_backoff(flaky_func, attempts=5, base_delay=0.01)
    assert result == "success"
    assert len(calls) == 3


def test_retry_with_backoff_auth_error_no_retry():
    calls = []

    def auth_failing_func():
        calls.append(1)
        err = Exception("Unauthorized")
        err.status_code = 401
        raise err

    with pytest.raises(Exception, match="Unauthorized"):
        retry_with_backoff(auth_failing_func, attempts=5, base_delay=0.01)

    # Must fail on the first attempt without retrying
    assert len(calls) == 1


def test_parent_store_manager_raises_in_strict_cloud():
    with patch("config.settings.settings.CLOUD_BACKEND_ENABLED", True), patch(
        "config.settings.settings.DATABASE_URL", "postgresql://fake:fake@localhost:5432/fake"
    ):
        manager = ParentStoreManager()
        assert manager.use_database is True

        with patch("db.parent_store_manager.run_sync", side_effect=RuntimeError("Postgres down")):
            with pytest.raises(RuntimeError, match="Database parent store failed during 'save'"):
                manager.save("p1", "test content", {"source": "test.txt"})

