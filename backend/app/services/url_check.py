"""URL-only model analysis plus a bounded, SSRF-safe live reachability probe."""
from __future__ import annotations

import ipaddress
import re
import socket
import ssl
import time
from threading import BoundedSemaphore
from urllib.parse import urljoin, urlsplit, urlunsplit

from fastapi import HTTPException

from app.services.url_model import url_model
from app.services.url_probe import MAX_REDIRECTS, ProbeFailure, REDIRECT_STATUSES, UnsafeDestination, _public_addresses, _head_once

_SLOTS = BoundedSemaphore(4)
_MAX_URL_LENGTH = 2048


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value or len(value) > _MAX_URL_LENGTH or any(ord(char) < 32 or char.isspace() for char in value) or "\\" in value:
        raise HTTPException(422, detail="Enter a valid public http:// or https:// website URL.")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        port = parsed.port
        if parsed.scheme.lower() not in {"http", "https"} or not host or parsed.username or parsed.password:
            raise ValueError("scheme, host, or credentials")
        if port not in {None, 80, 443}:
            raise ValueError("port")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            ascii_host = host.encode("idna").decode("ascii").lower().rstrip(".")
            labels = ascii_host.split(".")
            if len(ascii_host) > 253 or any(not label or len(label) > 63 or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label) for label in labels):
                raise ValueError("hostname")
            host = ascii_host
        else:
            if not address.is_global:
                raise ValueError("private IP")
            host = address.compressed
        netloc = f"[{host}]" if ":" in host else host
        if port is not None and port not in (80 if parsed.scheme.lower() == "http" else 443,):
            raise ValueError("scheme/port")
        path = "" if parsed.path in {"", "/"} else parsed.path
        return urlunsplit((parsed.scheme.lower(), netloc, path, parsed.query, ""))
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, detail="Enter a valid public http:// or https:// website URL.") from exc


def _probe(url: str) -> dict:
    redirects = []
    dns_count = 0
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        parsed = urlsplit(current)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = _public_addresses(host, port)
        dns_count += len(addresses)
        try:
            status, location = _head_once(current, addresses)
        except ProbeFailure:
            return {"status": "unreachable", "http_status": None, "final_host": host,
                    "dns_address_count": dns_count, "redirects": redirects}
        if status not in REDIRECT_STATUSES or not location:
            return {"status": "reachable", "http_status": status, "final_host": host, "dns_address_count": dns_count, "redirects": redirects}
        if len(redirects) >= MAX_REDIRECTS:
            return {"status": "redirect_limit", "http_status": status, "final_host": host, "dns_address_count": dns_count, "redirects": redirects}
        try:
            next_url = normalize_url(urljoin(current, location))
        except HTTPException as exc:
            raise UnsafeDestination("unsafe_or_invalid_redirect") from exc
        next_host = urlsplit(next_url).hostname or ""
        redirects.append({"status": status, "from_host": host, "to_host": next_host, "cross_host": host.lower() != next_host.lower()})
        current = next_url
    raise AssertionError("redirect loop bounds failed")


def check_url(value: str) -> dict:
    if not _SLOTS.acquire(blocking=False):
        raise HTTPException(429, detail="URL checks are busy. Please try again shortly.")
    try:
        stages = []
        started = time.perf_counter()
        url = normalize_url(value)
        host = urlsplit(url).hostname or ""
        stages.append({"name": "URL validation", "duration_ms": round((time.perf_counter() - started) * 1000, 1), "status": "complete"})

        started = time.perf_counter()
        try:
            prediction = url_model.predict(url)
        except RuntimeError as exc:
            raise HTTPException(503, detail="The trained URL analysis model is unavailable.") from exc
        stages.append({"name": "URL feature extraction and ML", "duration_ms": round((time.perf_counter() - started) * 1000, 1), "status": "complete"})

        started = time.perf_counter()
        try:
            probe = _probe(url)
            probe_error = None
            probe_status = "complete" if probe["status"] == "reachable" else "unavailable"
        except UnsafeDestination as exc:
            probe = {"status": "blocked", "http_status": None, "final_host": host, "dns_address_count": 0, "redirects": []}
            probe_error = "A hostname resolved to a private or reserved network address; the connection was blocked."
            probe_status = "blocked"
        except (ProbeFailure, OSError, ssl.SSLError, HTTPException) as exc:
            probe = {"status": "unreachable", "http_status": None, "final_host": host, "dns_address_count": 0, "redirects": []}
            probe_error = "The public DNS or HTTP check could not complete. This does not change the model result."
            probe_status = "unavailable"
        stages.append({"name": "Public DNS and HTTP check", "duration_ms": round((time.perf_counter() - started) * 1000, 1), "status": probe_status})

        findings = []
        if prediction["label"] == "phishing_signal":
            findings.append("The URL-only model found structural patterns associated with phishing in its training dataset.")
        else:
            findings.append("The URL-only model found no strong phishing pattern; this is not proof that the site is safe.")
        if urlsplit(url).scheme == "http":
            findings.append("The URL uses unencrypted HTTP.")
        if probe.get("redirects"):
            findings.append(f"The website redirected {len(probe['redirects'])} time(s); review the recorded host changes.")
        if probe_error:
            findings.append(probe_error)

        started = time.perf_counter()
        stages.append({"name": "Evidence summary", "duration_ms": round((time.perf_counter() - started) * 1000, 1), "status": "complete"})
        return {
            "url": url, "host": host, "model": prediction, "probe": probe,
            "findings": findings, "stages": stages,
            "limitations": ["URL model output is an investigation signal trained on the PhiUSIIL dataset, not a confirmed verdict.", "DNS and HTTP checks show current reachability and redirects only; they cannot establish that a site is safe.", "This check analyzes URL structure, not packet captures or network-flow data."],
        }
    finally:
        _SLOTS.release()
