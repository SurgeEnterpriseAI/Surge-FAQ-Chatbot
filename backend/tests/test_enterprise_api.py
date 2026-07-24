import asyncio

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.api.routers import enterprise
from backend.dependencies import require_admin


def test_traces_returns_empty_list_when_telemetry_is_offline(monkeypatch):
    async def stalled_connection():
        await asyncio.sleep(10)

    monkeypatch.setattr(enterprise, "connect_prisma", stalled_connection)

    app = create_app(init_resources=False)
    app.dependency_overrides[require_admin] = lambda: {"user_id": "mock-admin-id"}
    with TestClient(app) as client:
        response = client.get("/api/enterprise/traces?limit=100")

    assert response.status_code == 200
    assert response.json() == []
