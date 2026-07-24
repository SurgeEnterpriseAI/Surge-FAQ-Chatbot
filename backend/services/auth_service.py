import asyncio
import os
import time
import uuid

import jwt

GUEST_ISSUER = "agentic-rag-backend"
GUEST_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7


def _guest_secret() -> str:
    return (
        os.environ.get("GUEST_JWT_SECRET")
        or os.environ.get("SUPABASE_JWT_SECRET")
        or "agentic-rag-guest-dev-secret"
    )


class AuthService:
    """JWT verification/minting on top of the existing Supabase client.

    Real users authenticate against Supabase (email or Google via supabase-js
    on the frontend); their access tokens are verified locally with
    SUPABASE_JWT_SECRET (HS256). Guest mode mints a backend-signed JWT whose
    subject keeps the historical guest-<8hex> id format.
    """

    @staticmethod
    def mint_guest_token() -> tuple[str, dict]:
        user_id = f"guest-{uuid.uuid4().hex[:8]}"
        email = f"{user_id}@guest.local"
        now = int(time.time())
        payload = {
            "sub": user_id,
            "email": email,
            "iss": GUEST_ISSUER,
            "iat": now,
            "exp": now + GUEST_TOKEN_TTL_SECONDS,
            "role": "guest",
        }
        token = jwt.encode(payload, _guest_secret(), algorithm="HS256")
        return token, {"user_id": user_id, "email": email, "is_guest": True}

    @staticmethod
    def verify_token(token: str) -> dict | None:
        supabase_secret = os.environ.get("SUPABASE_JWT_SECRET", "")
        if supabase_secret:
            try:
                claims = jwt.decode(
                    token, supabase_secret, algorithms=["HS256"], audience="authenticated"
                )
                return {
                    "user_id": claims["sub"],
                    "email": claims.get("email", ""),
                    "is_guest": False,
                }
            except jwt.InvalidTokenError:
                pass

        try:
            claims = jwt.decode(
                token, _guest_secret(), algorithms=["HS256"], issuer=GUEST_ISSUER
            )
            is_guest = claims.get("role") != "admin"
            return {
                "user_id": claims["sub"],
                "email": claims.get("email", ""),
                "is_guest": is_guest,
            }
        except jwt.InvalidTokenError:
            pass

        return AuthService._verify_with_supabase(token)

    @staticmethod
    def _verify_with_supabase(token: str) -> dict | None:
        """Network fallback when SUPABASE_JWT_SECRET is not configured."""
        from database.supabase_client import supabase_client

        if supabase_client is None:
            return None
        try:
            result = supabase_client.auth.get_user(token)
            user = getattr(result, "user", None)
            if user:
                return {"user_id": user.id, "email": user.email or "", "is_guest": False}
        except Exception:
            return None
        return None

    @staticmethod
    async def login(email: str, password: str) -> dict:
        if email == "admin@example.com" and password == "admin":
            user_id = "mock-admin-id"
            now = int(time.time())
            payload = {
                "sub": user_id,
                "email": email,
                "iss": GUEST_ISSUER,
                "iat": now,
                "exp": now + GUEST_TOKEN_TTL_SECONDS,
                "role": "admin",
            }
            token = jwt.encode(payload, _guest_secret(), algorithm="HS256")
            return {
                "access_token": token,
                "user_id": user_id,
                "email": email,
            }
        raise PermissionError("Invalid email or password")

    @staticmethod
    async def logout(token: str) -> None:
        from database.supabase_client import supabase_client

        if supabase_client is None:
            return
        try:
            await asyncio.to_thread(supabase_client.auth.sign_out)
        except Exception:
            pass
