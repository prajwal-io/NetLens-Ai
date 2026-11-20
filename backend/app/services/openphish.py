"""In-memory cache for the OpenPhish community phishing feed."""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

import httpx

logger = logging.getLogger(__name__)
FEED_URL = "https://openphish.com/feed.txt"
FEED_TTL_SECONDS = 12 * 60 * 60
MAX_FEED_BYTES = 16 * 1024 * 1024


class FeedUnavailable(Exception):
    pass


def normalize_url(value: str) -> str | None:
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        host = parsed.hostname.lower().rstrip(".")
        if ":" in host:
            host = f"[{host}]"
        port = parsed.port
        default_port = (parsed.scheme.lower() == "http" and port == 80) or (parsed.scheme.lower() == "https" and port == 443)
        netloc = host if port is None or default_port else f"{host}:{port}"
        return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))
    except ValueError:
        return None


class OpenPhishFeed:
    def __init__(self):
        self._urls: frozenset[str] | None = None
        self._fetched_at: datetime | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def _download(self) -> frozenset[str]:
        chunks = []
        size = 0
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0), follow_redirects=True) as client:
            async with client.stream("GET", FEED_URL) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_FEED_BYTES:
                        raise ValueError("OpenPhish feed exceeds its size limit.")
                    chunks.append(chunk)
        text = b"".join(chunks).decode("utf-8")
        urls = frozenset(
            normalized for line in text.splitlines()
            if (normalized := normalize_url(line)) is not None
        )
        if not urls:
            raise ValueError("OpenPhish feed contains no valid URLs.")
        return urls

    async def lookup(self, value: str) -> tuple[bool, datetime, bool]:
        now = time.monotonic()
        if self._urls is None or now >= self._expires_at:
            async with self._lock:
                now = time.monotonic()
                if self._urls is None or now >= self._expires_at:
                    try:
                        self._urls = await self._download()
                        self._fetched_at = datetime.now(timezone.utc)
                        self._expires_at = time.monotonic() + FEED_TTL_SECONDS
                    except (httpx.HTTPError, UnicodeError, ValueError) as exc:
                        logger.warning("Could not refresh OpenPhish community feed: %s", exc)
                        if self._urls is None or self._fetched_at is None:
                            raise FeedUnavailable from exc

        if self._urls is None or self._fetched_at is None:
            raise FeedUnavailable
        stale = time.monotonic() >= self._expires_at
        normalized = normalize_url(value)
        return bool(normalized and normalized in self._urls), self._fetched_at, stale


openphish_feed = OpenPhishFeed()
