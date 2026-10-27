"""Real HTTP adapter for an approved LiteLLM proxy, behind typed transport.

This adapter only executes authorized benchmark inference; independent business
evaluators still decide correctness. Never treats response prose as success.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

import httpx


@dataclass(frozen=True)
class CompletionUsage:
    model_id: str
    output_text: str
    prompt_tokens: int
    completion_tokens: int
    response_cost_usd: float | None


class LiteLLMError(RuntimeError):
    pass


class LiteLLMClient:
    def __init__(self, *, base_url: str, api_key: str, allowed_models: set[str],
                 transport: httpx.BaseTransport | None = None, timeout_seconds: float = 30):
        if not base_url.startswith("https://") and not base_url.startswith("http://127.0.0.1:"):
            raise ValueError("LiteLLM proxy URL must use TLS (except localhost)")
        if not api_key or not allowed_models or timeout_seconds <= 0:
            raise ValueError("gateway credentials, models and timeout required")
        self._models = frozenset(allowed_models)
        self._client = httpx.Client(base_url=base_url.rstrip("/"), transport=transport,
                                    timeout=timeout_seconds,
                                    headers={"Authorization": f"Bearer {api_key}"})

    def complete(self, *, model: str, messages: list[dict[str, str]],
                 max_tokens: int = 256) -> CompletionUsage:
        if model not in self._models:
            raise LiteLLMError("MODEL_NOT_ALLOWED")
        if max_tokens < 1 or not messages:
            raise ValueError("messages/max_tokens are required")
        try:
            response = self._client.post(
                "/v1/chat/completions",
                json={"model": model, "messages": messages, "max_tokens": max_tokens},
            )
            response.raise_for_status()
            content: dict[str, Any] = response.json()
            usage = content["usage"]
            text = content["choices"][0]["message"]["content"]
            if not isinstance(text, str):
                raise ValueError("invalid completion content")
            reported_model = str(content.get("model") or model)
            if reported_model != model:
                raise ValueError("unexpected proxy model substitution")
            prompt_tokens, completion_tokens = usage["prompt_tokens"], usage["completion_tokens"]
            if (type(prompt_tokens) is not int or type(completion_tokens) is not int
                    or prompt_tokens < 0 or completion_tokens < 0):
                raise ValueError("invalid token usage")
            raw_cost = content.get("response_cost")
            reported_cost = float(raw_cost) if raw_cost is not None else None
            if reported_cost is not None and (not isfinite(reported_cost) or reported_cost < 0):
                raise ValueError("invalid response cost")
            return CompletionUsage(reported_model, text, prompt_tokens, completion_tokens, reported_cost)
        except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError) as exc:
            raise LiteLLMError("GATEWAY_CALL_FAILED") from exc

    def close(self) -> None:
        self._client.close()
