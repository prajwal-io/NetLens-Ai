import ipaddress
import re
from urllib.parse import urlsplit

from fastapi import HTTPException

from app.services.openphish import FeedUnavailable, openphish_feed


async def lookup_url(value: str) -> dict:
    try:
        candidate = value.strip()
        parsed = urlsplit(candidate)
        host = parsed.hostname
        if (parsed.scheme.lower() not in {"http", "https"} or not host or parsed.username is not None or parsed.password is not None
                or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in candidate)
                or "\\" in parsed.netloc or "%" in parsed.netloc):
            raise ValueError
        port = parsed.port
        if port is not None and not 1 <= port <= 65535:
            raise ValueError
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if host.endswith(".."):
                raise ValueError
            ascii_host = host.rstrip(".").encode("idna").decode("ascii")
            labels = ascii_host.split(".")
            if (len(ascii_host) > 253 or not labels or any(
                not label or len(label) > 63 or not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?", label)
                for label in labels
            )):
                raise ValueError
    except ValueError:
        raise HTTPException(422, detail="Enter a valid http:// or https:// URL without embedded credentials.")

    try:
        matched, updated_at, stale = await openphish_feed.lookup(value)
    except FeedUnavailable:
        raise HTTPException(503, detail="OpenPhish feed is unavailable right now. Local URL checks are still available.") from None
    return {"provider": "OpenPhish Community Feed", "matched": matched,
            "threat_types": ["PHISHING"] if matched else [], "updated_at": updated_at,
            "stale": stale}
