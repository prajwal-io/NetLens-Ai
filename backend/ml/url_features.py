"""URL-only lexical features shared by training and request-time inference."""
from __future__ import annotations

import math
from collections import Counter
from urllib.parse import urlsplit

import numpy as np


FEATURES = (
    "url_length", "host_length", "path_length", "query_length", "host_dot_count",
    "subdomain_count", "host_hyphen_count", "host_digit_count", "url_digit_ratio",
    "special_char_count", "special_char_ratio", "url_entropy", "host_entropy",
    "https", "ip_literal", "punycode", "path_depth", "query_param_count",
    "encoded_char_count", "at_sign_count", "suspicious_token_count", "long_host_label_count",
)
SUSPICIOUS_TOKENS = ("account", "auth", "billing", "confirm", "login", "password", "secure", "signin", "update", "verify")


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    return -sum((count / len(value)) * math.log2(count / len(value)) for count in counts.values())


def extract_url_features(value: str) -> np.ndarray:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
    if parsed.scheme.lower() not in {"http", "https"} or not host:
        raise ValueError("URL features require an absolute HTTP or HTTPS URL.")
    labels = host.split(".")
    url = value.lower()
    path = parsed.path or "/"
    query = parsed.query
    digits = sum(char.isdigit() for char in url)
    special = sum(not char.isalnum() for char in url)
    tokens = sum(url.count(token) for token in SUSPICIOUS_TOKENS)
    try:
        import ipaddress
        ipaddress.ip_address(host)
        ip_literal = 1
    except ValueError:
        ip_literal = 0
    values = (
        len(value), len(host), len(path), len(query), host.count("."), max(0, len(labels) - 2),
        host.count("-"), sum(char.isdigit() for char in host), digits / max(1, len(url)),
        special, special / max(1, len(url)), _entropy(url), _entropy(host),
        int(parsed.scheme.lower() == "https"), ip_literal, int("xn--" in host),
        len([part for part in path.split("/") if part]), len([part for part in query.split("&") if part]),
        url.count("%"), url.count("@"), tokens, sum(len(label) >= 25 for label in labels),
    )
    return np.asarray(values, dtype="float64")
