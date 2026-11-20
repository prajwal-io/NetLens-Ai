"""Bounded HTTP HEAD checks with DNS pinning and private-network blocking."""
from __future__ import annotations

import ipaddress
import re
import socket
import ssl
from urllib.parse import quote, urlsplit, urlunsplit

MAX_HEADER_BYTES = 16 * 1024
MAX_REDIRECTS = 4
TIMEOUT_SECONDS = 3.0
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class UnsafeDestination(Exception):
    pass


class ProbeFailure(Exception):
    pass


def _public_addresses(host: str, port: int) -> list[str]:
    try:
        # shortcut: OS resolver timeout is platform-controlled; use async DNS for high-concurrency hosting.
        answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ProbeFailure("dns_failed") from exc
    addresses = list(dict.fromkeys(answer[4][0].split("%", 1)[0] for answer in answers))
    if not addresses:
        raise ProbeFailure("dns_empty")
    try:
        parsed = [ipaddress.ip_address(address) for address in addresses]
    except ValueError as exc:
        raise ProbeFailure("dns_invalid") from exc
    if any(not address.is_global for address in parsed):
        raise UnsafeDestination("private_or_reserved_address")
    return addresses[:4]


def _head_once(url: str, addresses: list[str]) -> tuple[int, str | None]:
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    target = urlunsplit(("", "", quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~"), quote(parsed.query, safe="/?%:@!$&'()*+,;=-._~"), ""))
    host_header = parsed.netloc
    last_error: OSError | ssl.SSLError | None = None
    for address in addresses:
        sock = None
        try:
            sock = socket.create_connection((address, port), timeout=TIMEOUT_SECONDS)
            sock.settimeout(TIMEOUT_SECONDS)
            if parsed.scheme == "https":
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
            request = (
                f"HEAD {target} HTTP/1.1\r\nHost: {host_header}\r\n"
                "User-Agent: NetLensAI-URLCheck/1.0\r\nAccept: */*\r\nConnection: close\r\n\r\n"
            ).encode("ascii", "strict")
            sock.sendall(request)
            data = bytearray()
            while b"\r\n\r\n" not in data and len(data) <= MAX_HEADER_BYTES:
                chunk = sock.recv(min(2048, MAX_HEADER_BYTES + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
            if len(data) > MAX_HEADER_BYTES or b"\r\n\r\n" not in data:
                raise ProbeFailure("response_headers_too_large_or_incomplete")
            lines = bytes(data).split(b"\r\n\r\n", 1)[0].split(b"\r\n")
            match = re.fullmatch(rb"HTTP/\d(?:\.\d)?\s+(\d{3})(?:\s+.*)?", lines[0])
            if not match:
                raise ProbeFailure("invalid_http_response")
            location = None
            for line in lines[1:]:
                if b":" not in line:
                    continue
                name, value = line.split(b":", 1)
                if name.strip().lower() == b"location":
                    location = value.strip().decode("latin-1")
            return int(match.group(1)), location
        except (OSError, ssl.SSLError) as exc:
            last_error = exc
        finally:
            if sock:
                sock.close()
    raise ProbeFailure("connection_failed") from last_error
