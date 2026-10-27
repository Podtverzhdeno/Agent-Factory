"""Real LiteLLM HTTP smoke; explicitly opt in to paid inference."""
import os
import pytest

from quality_engine.litellm_client import LiteLLMClient


def test_litellm_real_proxy_smoke():
    if os.environ.get("AF_QUALITY_ALLOW_PAID_INFERENCE") != "YES":
        pytest.skip("live inference requires explicit budget authorization")
    url = os.environ.get("AGENT_FACTORY_LITELLM_PROXY_URL")
    key = os.environ.get("AGENT_FACTORY_LITELLM_API_KEY")
    model = os.environ.get("AGENT_FACTORY_LITELLM_TEST_MODEL")
    if not all((url, key, model)):
        pytest.skip("no approved live LiteLLM proxy credentials")
    client = LiteLLMClient(base_url=url, api_key=key, allowed_models={model},
                            timeout_seconds=20)
    try:
        completion = client.complete(
            model=model, messages=[{"role": "user", "content": "Respond with PONG only"}],
            max_tokens=16)
        assert completion.prompt_tokens > 0
        assert completion.completion_tokens >= 0
        assert completion.output_text
        # Provider smoke only; price-quality requires separately proven billing data.
    finally:
        client.close()
