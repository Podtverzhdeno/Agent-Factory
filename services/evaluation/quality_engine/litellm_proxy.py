"""LiteLLM Proxy API adapter with provider-independent real cost accounting.

This client calls an existing trusted LiteLLM Proxy. It does NOT provision a
Proxy, create per-tenant keys or replace proxy-side enforced budgets.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable

import httpx

from .core import AccessDenied, InvalidEvidence


class LiteLLMUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Completion:
    model_id: str
    text: str | None
    tool_calls: tuple[dict, ...]
    total_tokens: int
    cost_usd: Decimal
    call_id: str
    retries: int
    fallbacks: int
    duration_ms: float


class LiteLLMProxyClient:
    """Calls only provider-approved model aliases for an authenticated tenant."""

    def __init__(self, *, client: httpx.Client,
                 key_for_tenant: Callable[[str], str],
                 allowed_models: Callable[[str], frozenset[str]]):
        if client.follow_redirects:
            raise ValueError("LiteLLM redirect handling must be disabled")
        self._client = client
        self._key_for_tenant = key_for_tenant
        self._allowed = allowed_models

    def complete(self, *, tenant_id: str, model: str,
                 messages: tuple[dict, ...], idempotency_key: str,
                 max_tokens: int = 512) -> Completion:
        if not tenant_id or not model or model not in self._allowed(tenant_id):
            raise AccessDenied("unapproved tenant model route")
        if not idempotency_key or not messages or not 1 <= max_tokens <= 16384:
            raise InvalidEvidence("invalid bounded completion command")
        for message in messages:
            if message.get("role") not in ("system", "developer", "user", "assistant", "tool"):
                raise InvalidEvidence("unsupported message role")
            if not isinstance(message.get("content"), (str, list, type(None))):
                raise InvalidEvidence("invalid message content")
        token = self._key_for_tenant(tenant_id)
        if not token or "\r" in token or "\n" in token:
            raise AccessDenied("missing tenant LiteLLM credential")
        try:
            response = self._client.post(
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {token}",
                         "X-Correlation-ID": idempotency_key},
                json={"model": model, "messages": list(messages), "max_tokens": max_tokens,
                      "stream": False, "user": tenant_id},
                timeout=90.0,
            )
            response.raise_for_status()
            content = response.json()
        except (httpx.HTTPError, ValueError, TypeError):
            raise LiteLLMUnavailable("LiteLLM completion failed") from None
        try:
            raw_cost = response.headers["x-litellm-response-cost"]
            cost = Decimal(raw_cost)
            if not cost.is_finite() or cost < 0:
                raise InvalidEvidence("invalid LiteLLM billing cost")
            message = content["choices"][0]["message"]
            used_tokens = int(content["usage"]["total_tokens"])
            if used_tokens < 0:
                raise InvalidEvidence("negative token usage")
            text = message.get("content")
            if text is not None and not isinstance(text, str):
                raise InvalidEvidence("unexpected text content")
            calls = tuple(message.get("tool_calls") or ())
            if any(not isinstance(call, dict) for call in calls):
                raise InvalidEvidence("invalid tool calls")
            retry = int(response.headers.get("x-litellm-attempted-retries", "0"))
            fallback = int(response.headers.get("x-litellm-attempted-fallbacks", "0"))
            duration = float(response.headers.get("x-litellm-response-duration-ms", "0"))
            if retry < 0 or fallback < 0 or not 0 <= duration < float("inf"):
                raise InvalidEvidence("invalid LiteLLM usage headers")
            call_id = response.headers.get("x-litellm-call-id")
            if not call_id:
                raise InvalidEvidence("missing traceable LiteLLM call ID")
            return Completion(model, text, calls, used_tokens, cost, call_id,
                              retry, fallback, duration)
        except (KeyError, IndexError, TypeError, ValueError, InvalidOperation):
            raise InvalidEvidence("incomplete LiteLLM cost/usage evidence") from None
