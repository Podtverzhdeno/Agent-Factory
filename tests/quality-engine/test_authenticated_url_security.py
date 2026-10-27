"""Regression coverage for authenticated Runtime and LiteLLM endpoint URL parsing.

The configured base URL is trusted configuration, but it must never silently
reinterpret a loopback-looking string as a remote authority and leak a bearer
service token to it.
"""
from __future__ import annotations

import httpx
import pytest

from quality_engine.litellm_client import LiteLLMClient
from quality_engine.runtime_http import RuntimeEvidenceHTTPCollector


def _client(kind: str, base_url: str):
    forbidden = httpx.MockTransport(
        lambda request: pytest.fail("No network call is expected during URL validation")
    )
    if kind == "runtime":
        return RuntimeEvidenceHTTPCollector(
            base_url=base_url, service_token="sensitive-test-bearer", transport=forbidden)
    return LiteLLMClient(
        base_url=base_url, api_key="sensitive-test-bearer",
        allowed_models={"approved-model"}, transport=forbidden)


@pytest.mark.parametrize("kind", ["runtime", "litellm"])
@pytest.mark.parametrize("malicious_url", [
    "http://127.0.0.1:8000@attacker.example",
    "http://127.0.0.1:8080@attacker.example/path",
    "https://trusted.example@attacker.example",
    "https://user:password@trusted.example",
    "https://user@trusted.example",
    "https://trusted.example?token=leak",
    "https://trusted.example#fragment",
    "https://trusted.example:invalid",
    "https://trusted.example:70000",
    "https://trusted.example:0",
    "http://127.0.0.1:70000",
    "http://127.0.0.1:0",
    "http://127.0.0.1:8080?redirect=evil",
    "http://127.0.0.1:8080#fragment",
    "http://localhost:8000",
    "http://[::1]:8000",
    "http://attacker.example",
    "ftp://trusted.example",
    "https://",
    " https://trusted.example",
    "https://trusted.example\n",
    "https://trusted.example:443@attacker.example",
])
def test_authenticated_clients_reject_unsafe_url_authorities(kind, malicious_url):
    with pytest.raises(ValueError, match="HTTPS"):
        _client(kind, malicious_url)


@pytest.mark.parametrize("kind", ["runtime", "litellm"])
@pytest.mark.parametrize("safe_url", [
    "https://trusted.example",
    "https://trusted.example:8443",
    "https://trusted.example:443/v1",
    "http://127.0.0.1:9000",
    "http://127.0.0.1:80",
    "http://127.0.0.1",
])
def test_authenticated_clients_accept_tls_and_exact_ipv4_loopback(kind, safe_url):
    client = _client(kind, safe_url)
    client.close()
