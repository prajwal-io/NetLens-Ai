from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from app.core.config import settings


async def lookup_url(value: str) -> dict:
    try:
        parsed = urlsplit(value.strip())
        if (parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password
                or any(char.isspace() or ord(char) < 32 for char in parsed.netloc) or parsed.port == 0):
            raise ValueError
    except ValueError:
        raise HTTPException(422, detail="Enter a valid http:// or https:// URL without embedded credentials.")

    if not settings.webrisk_api_key:
        raise HTTPException(503, detail="Live URL reputation is not configured. Set NETSIGHT_WEBRISK_API_KEY on the backend.")

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), follow_redirects=False) as client:
            response = await client.get(
                "https://webrisk.googleapis.com/v1/uris:search",
                params=[("threatTypes", kind) for kind in ("SOCIAL_ENGINEERING", "MALWARE", "UNWANTED_SOFTWARE")] + [
                    ("uri", value.strip()), ("key", settings.webrisk_api_key)
                ],
            )
            if response.status_code == 403:
                raise HTTPException(
                    503,
                    detail="Google Web Risk rejected this project or API key. Check that Web Risk is enabled, billing is active, and the key is restricted to Web Risk API.",
                )
            if response.status_code == 429:
                raise HTTPException(503, detail="Google Web Risk quota or rate limit was reached. Check the project's Web Risk quota.")
            response.raise_for_status()
            body = response.json()
    except (httpx.TimeoutException, httpx.HTTPError, ValueError):
        raise HTTPException(502, detail="The URL reputation provider could not complete this check. Retry shortly.")

    threat = body.get("threat") if isinstance(body, dict) else None
    types = threat.get("threatTypes", []) if isinstance(threat, dict) else []
    expires_at = threat.get("expireTime") if isinstance(threat, dict) else None
    if not isinstance(types, list) or not all(item in {"SOCIAL_ENGINEERING", "MALWARE", "UNWANTED_SOFTWARE"} for item in types):
        raise HTTPException(502, detail="The URL reputation provider returned an invalid response.")
    return {"provider": "Google Web Risk", "matched": bool(types), "threat_types": types,
            "expires_at": expires_at if isinstance(expires_at, str) else None}
