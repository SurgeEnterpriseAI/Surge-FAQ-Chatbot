import pytest
from fastapi.testclient import TestClient
from backend.services.auth_service import AuthService
from repositories.chat_repository import ChatRepository
from backend.app import create_app

@pytest.mark.asyncio
async def test_auth_service_mock_login():
    # Test valid credentials
    result = await AuthService.login("admin@example.com", "admin")
    assert result["user_id"] == "mock-admin-id"
    assert result["email"] == "admin@example.com"
    assert "access_token" in result

    # Test verify token
    token = result["access_token"]
    claims = AuthService.verify_token(token)
    assert claims is not None
    assert claims["user_id"] == "mock-admin-id"
    assert claims["is_guest"] is False

    # Test invalid credentials
    with pytest.raises(PermissionError):
        await AuthService.login("admin@example.com", "wrong")


def test_login_api_endpoint(client):
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["user_id"] == "mock-admin-id"
    assert data["user"]["is_guest"] is False


def test_login_api_endpoint_failure(client):
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_guest_login_api_endpoint(client):
    response = client.post("/api/auth/guest")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["is_guest"] is True
    assert data["user"]["user_id"].startswith("guest-")


def test_profile_api_endpoint():
    app = create_app(init_resources=False)
    with TestClient(app) as test_client:
        # Log in as admin to get token
        login_resp = test_client.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin"})
        token = login_resp.json()["access_token"]

        # Call profile endpoint with token
        profile_resp = test_client.get("/api/auth/profile", headers={"Authorization": f"Bearer {token}"})
        assert profile_resp.status_code == 200
        profile_data = profile_resp.json()
        assert profile_data["user_id"] == "mock-admin-id"
        assert profile_data["email"] == "admin@example.com"
        assert profile_data["is_guest"] is False


def test_conversation_isolation(monkeypatch):
    # Setup two mock chats in the DB with different owners
    class MockChat:
        def __init__(self, id, userId):
            self.id = id
            self.userId = userId

    chats_db = {
        "chat1": MockChat("chat1", "mock-admin-id"),
        "chat2": MockChat("chat2", "guest-user-1")
    }

    async def mock_get_chat(chat_id):
        return chats_db.get(chat_id)

    async def mock_get_messages(chat_id):
        return []

    async def mock_get_conversation_summary(chat_id):
        return None

    monkeypatch.setattr(ChatRepository, "get_chat", mock_get_chat)
    monkeypatch.setattr(ChatRepository, "get_messages", mock_get_messages)
    monkeypatch.setattr(ChatRepository, "get_conversation_summary", mock_get_conversation_summary)
    
    app = create_app(init_resources=False)
    with TestClient(app) as test_client:
        # Generate tokens manually
        import time
        import jwt
        from backend.services.auth_service import GUEST_ISSUER, _guest_secret
        
        now = int(time.time())
        admin_jwt = jwt.encode({"sub": "mock-admin-id", "email": "admin@example.com", "iss": GUEST_ISSUER, "iat": now, "exp": now + 3600, "role": "admin"}, _guest_secret(), algorithm="HS256")
        guest_jwt = jwt.encode({"sub": "guest-user-1", "email": "guest-user-1@guest.local", "iss": GUEST_ISSUER, "iat": now, "exp": now + 3600, "role": "guest"}, _guest_secret(), algorithm="HS256")

        # Admin requests chat1 (authorized)
        resp1 = test_client.get("/api/history/chat1", headers={"Authorization": f"Bearer {admin_jwt}"})
        assert resp1.status_code == 200

        # Admin requests chat2 (unauthorized - belongs to guest-user-1)
        resp2 = test_client.get("/api/history/chat2", headers={"Authorization": f"Bearer {admin_jwt}"})
        assert resp2.status_code == 403

        # Guest requests chat2 (authorized)
        resp3 = test_client.get("/api/history/chat2", headers={"Authorization": f"Bearer {guest_jwt}"})
        assert resp3.status_code == 200

        # Guest requests chat1 (unauthorized - belongs to admin)
        resp4 = test_client.get("/api/history/chat1", headers={"Authorization": f"Bearer {guest_jwt}"})
        assert resp4.status_code == 403
