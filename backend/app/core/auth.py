"""Verify Supabase access tokens before exposing analyst data."""
from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: str
    access_token: str


async def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in to use this workspace.", headers={"WWW-Authenticate": "Bearer"})
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Supabase authentication is not configured on this API.")

    client: httpx.AsyncClient | None = getattr(request.app.state, "supabase_auth_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable.")
    try:
        response = await client.get(
            "/auth/v1/user",
            headers={
                "apikey": settings.supabase_publishable_key,
                "Authorization": f"Bearer {credentials.credentials}",
            },
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable.") from exc

    if response.status_code in (401, 403):
        raise HTTPException(status_code=401, detail="Your session is invalid or expired. Sign in again.", headers={"WWW-Authenticate": "Bearer"})
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable.")
    try:
        user_id = str(UUID(response.json()["id"]))
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Authentication service returned an invalid identity.") from None
    return Principal(user_id=user_id, access_token=credentials.credentials)
