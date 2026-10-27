import httpx
import pytest

from quality_engine.litellm_client import LiteLLMClient, LiteLLMError


def test_litellm_real_http_contract_mock_transport():
    seen = []
    def handler(request):
        seen.append((request.url.path, request.headers.get("Authorization")))
        return httpx.Response(200, json={
            "model": "local-allowed", "choices": [{"message": {"content": "matched"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3},
            "response_cost": 0.001,
        })
    gateway = LiteLLMClient(base_url="https://gateway.example",
                            api_key="test-not-real", allowed_models={"local-allowed"},
                            transport=httpx.MockTransport(handler))
    answer = gateway.complete(model="local-allowed",
                              messages=[{"role": "user", "content": "test"}])
    assert (answer.output_text, answer.prompt_tokens, answer.response_cost_usd) == ("matched", 10, 0.001)
    assert seen == [("/v1/chat/completions", "Bearer test-not-real")]
    gateway.close()


def test_model_allowlist_denies_without_network():
    gateway = LiteLLMClient(base_url="https://gateway.example",
                            api_key="placeholder", allowed_models={"allowed"},
                            transport=httpx.MockTransport(lambda req: pytest.fail("unexpected call")))
    with pytest.raises(LiteLLMError, match="MODEL_NOT_ALLOWED"):
        gateway.complete(model="disallowed", messages=[{"role": "user", "content": "x"}])
    gateway.close()


def test_gateway_failure_is_fail_closed_and_scrubbed():
    gateway = LiteLLMClient(base_url="https://gateway.example", api_key="private-key",
                            allowed_models={"allowed"},
                            transport=httpx.MockTransport(lambda req: httpx.Response(503)))
    with pytest.raises(LiteLLMError, match="GATEWAY_CALL_FAILED") as error:
        gateway.complete(model="allowed", messages=[{"role": "user", "content": "x"}])
    assert "private-key" not in str(error.value)
    gateway.close()


def test_external_plain_http_denied():
    with pytest.raises(ValueError):
        LiteLLMClient(base_url="http://external.example", api_key="placeholder",
                      allowed_models={"allowed"})


@pytest.mark.parametrize("wrong", [
    {"model": "unauthorized-fallback"},
    {"usage": {"prompt_tokens": -1, "completion_tokens": 1}},
    {"usage": {"prompt_tokens": True, "completion_tokens": 1}},
    {"response_cost": float("nan")},
    {"response_cost": -0.0001},
])
def test_misreported_proxy_model_or_usage_is_rejected(wrong):
    payload = {"model": "allowed", "choices": [{"message": {"content": "ok"}}],
               "usage": {"prompt_tokens": 10, "completion_tokens": 2},
               "response_cost": 0.03}
    payload.update(wrong)
    client = LiteLLMClient(base_url="https://gateway.example", api_key="placeholder",
                            allowed_models={"allowed"},
                            transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload)))
    try:
        with pytest.raises(LiteLLMError, match="GATEWAY_CALL_FAILED"):
            client.complete(model="allowed", messages=[{"role": "user", "content": "ok"}])
    finally:
        client.close()
