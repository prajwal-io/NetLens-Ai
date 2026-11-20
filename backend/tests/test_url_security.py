import asyncio
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.services import reputation


@pytest.mark.parametrize("value", [
    "javascript:alert(1)",
    "ftp://example.com/file",
    "https://user:secret@example.com/",
    "https://bad host.example/",
    "https://example.com:70000/",
    "https://bad_host.example/",
    "https://example.com\\@evil.example/",
    "https://[:::]/",
])
def test_lookup_rejects_invalid_or_unsafe_url_syntax(value):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(reputation.lookup_url(value))
    assert exc.value.status_code == 422


def test_lookup_accepts_valid_url_and_returns_mocked_feed_match(monkeypatch):
    observed = []
    updated = datetime(2026, 11, 20, tzinfo=timezone.utc)

    async def lookup(value):
        observed.append(value)
        return True, updated, False

    monkeypatch.setattr(reputation.openphish_feed, "lookup", lookup)
    result = asyncio.run(reputation.lookup_url("https://paypal-security.example/login"))

    assert observed == ["https://paypal-security.example/login"]
    assert result["matched"] is True
    assert result["threat_types"] == ["PHISHING"]
    assert result["updated_at"] == updated


def test_feed_failure_is_reported_without_network_fallback(monkeypatch):
    async def unavailable(_value):
        raise reputation.FeedUnavailable

    monkeypatch.setattr(reputation.openphish_feed, "lookup", unavailable)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(reputation.lookup_url("https://example.com/path"))

    assert exc.value.status_code == 503
    assert "Local URL checks are still available" in exc.value.detail
