import pytest
from fastapi.testclient import TestClient
from backend.app import create_app

def test_analytics_endpoints_require_auth():
    app = create_app(init_resources=False)
    with TestClient(app) as test_client:
        response = test_client.get("/api/analytics/ai-performance")
        assert response.status_code == 401

def test_analytics_endpoints_require_admin():
    app = create_app(init_resources=False)
    with TestClient(app) as test_client:
        # Login as a regular guest user first to get a guest token
        login_resp = test_client.post("/api/auth/guest")
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        
        # Access analytics with guest token should be forbidden (403)
        headers = {"Authorization": f"Bearer {token}"}
        response = test_client.get("/api/analytics/ai-performance", headers=headers)
        assert response.status_code == 403

def test_analytics_endpoints_succeed_for_admin():
    app = create_app(init_resources=False)
    with TestClient(app) as test_client:
        # Login as admin to get admin token
        login_resp = test_client.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin"})
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        
        # Call endpoint with admin token
        headers = {"Authorization": f"Bearer {token}"}
        response = test_client.get("/api/analytics/ai-performance", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "totalRequests" in data
        assert "successfulResponses" in data
        assert "trends" in data

        # Test other metrics
        response = test_client.get("/api/analytics/system", headers=headers)
        assert response.status_code == 200
        assert "cpuUsage" in response.json()

        response = test_client.get("/api/analytics/users", headers=headers)
        assert response.status_code == 200
        assert "registeredUsers" in response.json()

        # Without a database there is no history, so predictions must decline to
        # project rather than inventing a series.
        response = test_client.get("/api/analytics/predictions", headers=headers)
        assert response.status_code == 200
        predictions = response.json()
        assert predictions["available"] is False
        assert predictions["reason"] == "insufficient history"


def test_analytics_reports_no_data_without_database(monkeypatch):
    """Every metric must read as empty, never as fabricated activity."""
    from backend.services.analytics_service import AnalyticsService

    async def _unavailable():
        return False

    monkeypatch.setattr(AnalyticsService, "_database_available", staticmethod(_unavailable))

    app = create_app(init_resources=False)
    with TestClient(app) as test_client:
        login_resp = test_client.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        ai = test_client.get("/api/analytics/ai-performance", headers=headers).json()
        assert ai["hasData"] is False
        assert ai["totalRequests"] == 0
        assert all(point["requests"] == 0 for point in ai["trends"])

        agents = test_client.get("/api/analytics/agent-performance", headers=headers).json()
        assert agents["hasData"] is False
        assert agents["metrics"] == []

        security = test_client.get("/api/analytics/security", headers=headers).json()
        assert security["hasData"] is False
        assert security["recentSecurityEvents"] == []
        assert security["adminLoginHistory"] == []

        business = test_client.get("/api/analytics/business-metrics", headers=headers).json()
        assert business["hasData"] is False
        assert business["openTickets"] == 0
