"""Validate authenticated internal HTTP client endpoints before sending secrets.

Uses HTTPX's URL parser (the same parser used to send requests), rather than
string-prefix tests that can misidentify a URL's authority before an @ sign.
"""
from __future__ import annotations

import httpx


def validated_service_url(base_url: str, *, label: str) -> str:
    """Require HTTPS or explicit IPv4 loopback HTTP, without URL credentials.

    Return the URL normalized by HTTPX so validation and request construction
    agree on the authority. For production, TLS still needs trusted DNS,
    certificates and egress restrictions enforced by infrastructure.
    """
    if (not isinstance(base_url, str) or not base_url or len(base_url) > 2048
            or any(char.isspace() or ord(char) < 32 or ord(char) == 127
                   for char in base_url)):
        raise ValueError(f"{label} requires HTTPS (except explicit IPv4 loopback)")
    try:
        endpoint = httpx.URL(base_url)
        port = endpoint.port
        valid = (
            endpoint.is_absolute_url
            and bool(endpoint.host)
            and not endpoint.userinfo
            and not endpoint.query
            and not endpoint.fragment
            and (port is None or 1 <= port <= 65535)
            and (
                endpoint.scheme == "https"
                or (endpoint.scheme == "http" and endpoint.host == "127.0.0.1")
            )
        )
    except (httpx.InvalidURL, TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError(f"{label} requires HTTPS (except explicit IPv4 loopback)")
    return str(endpoint)
