from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.dependencies import get_current_user
from backend.schemas.auth import LoginRequest, TokenResponse, UserProfile
from backend.schemas.common import StatusResponse
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    from repositories.user_repository import UserRepository

    try:
        result = await AuthService.login(body.email, body.password)
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    try:
        await UserRepository.create_user(result["user_id"], result["email"])
    except Exception:
        pass

    return TokenResponse(
        access_token=result["access_token"],
        user=UserProfile(
            user_id=result["user_id"],
            email=result["email"],
            is_guest=False,
            is_admin=(result["user_id"] == "mock-admin-id" or result["email"] == "admin@example.com")
        ),
    )


@router.post("/guest", response_model=TokenResponse)
async def guest_login():
    from repositories.user_repository import UserRepository

    token, user = AuthService.mint_guest_token()
    try:
        await UserRepository.create_user(user["user_id"], user["email"], "Guest")
    except Exception:
        pass
    return TokenResponse(
        access_token=token,
        user=UserProfile(user_id=user["user_id"], email=user["email"], is_guest=True, is_admin=False),
    )


@router.post("/logout", response_model=StatusResponse)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    if credentials is not None:
        await AuthService.logout(credentials.credentials)
    return StatusResponse(status="ok")


@router.get("/profile", response_model=UserProfile)
async def profile(user: dict = Depends(get_current_user)):
    from repositories.user_repository import UserRepository

    record = None
    try:
        record = await UserRepository.get_user(user["user_id"])
    except Exception:
        pass

    # Prioritize verified token claims
    email = user.get("email") or (record.email if record else "")
    name = (record.name if record else None) or ("Admin" if user["user_id"] == "mock-admin-id" else None)

    is_admin = False
    if user["user_id"] == "mock-admin-id" or email == "admin@example.com":
        is_admin = True
    elif record and (getattr(record, "isAdmin", False) or getattr(record, "is_admin", False)):
        is_admin = True

    return UserProfile(
        user_id=user["user_id"],
        email=email,
        name=name,
        is_guest=user.get("is_guest", False),
        is_admin=is_admin,
    )
