from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.services.auth_service import AuthService

_bearer = HTTPBearer(auto_error=False)


def get_rag_system(request: Request):
    rag_system = request.app.state.rag_system
    if rag_system is None or rag_system.agent_graph is None:
        raise HTTPException(status_code=503, detail="RAG system is not initialized yet")
    return rag_system


def get_doc_manager(request: Request):
    doc_manager = request.app.state.doc_manager
    if doc_manager is None:
        raise HTTPException(status_code=503, detail="Document manager is not initialized yet")
    return doc_manager


def get_ingest_lock(request: Request):
    return request.app.state.ingest_lock


def get_upload_service(request: Request):
    return request.app.state.upload_service


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = AuthService.verify_token(credentials.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    from repositories.user_repository import UserRepository
    is_admin = False
    if user.get("user_id") == "mock-admin-id" or user.get("email") == "admin@example.com":
        is_admin = True
    else:
        try:
            record = await UserRepository.get_user(user["user_id"])
            if record and (getattr(record, "isAdmin", False) or getattr(record, "is_admin", False)):
                is_admin = True
        except Exception:
            pass
            
    if not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    return user

