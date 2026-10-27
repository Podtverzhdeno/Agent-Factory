"""Opt-in live DSPy GEPA via approved LiteLLM Proxy. No live calls by default."""
import os
import pytest
from gepard_optimizer import DspyGepaBackend


def test_real_gepa_compile_with_litellm_proxy():
    if os.environ.get("AF_QUALITY_ALLOW_PAID_INFERENCE") != "YES":
        pytest.skip("explicit budget authorization for paid inference not provided")
    url = os.environ.get("AGENT_FACTORY_LITELLM_PROXY_URL")
    key = os.environ.get("AGENT_FACTORY_LITELLM_API_KEY")
    model = os.environ.get("AGENT_FACTORY_LITELLM_TEST_MODEL")
    if not all((url, key, model)):
        pytest.skip("real proxy endpoint, key and approved model required")
    dspy = pytest.importorskip("dspy")
    lm = dspy.LM("openai/" + model, api_base=url, api_key=key,
                 max_tokens=256, temperature=0)
    dspy.configure(lm=lm)
    student = dspy.Predict("question -> answer")
    train = [dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
             dspy.Example(question="What is 3+1?", answer="4").with_inputs("question")]
    validation = [dspy.Example(question="What is 1+2?", answer="3").with_inputs("question")]

    def feedback(gold, pred, trace=None, pred_name=None, pred_trace=None):
        return 1.0 if str(getattr(pred, "answer", "")).strip() == gold.answer else 0.0

    result = DspyGepaBackend().compile(
        student=student, metric=feedback, trainset=train, valset=validation,
        reflection_lm=lm, max_metric_calls=8,
        train_ref="artifact://synthetic-gepa-train-v1",
        validation_ref="artifact://synthetic-gepa-validation-v1",
    )
    assert result.status == "REQUIRES_INDEPENDENT_EVALUATION"
    assert result.candidate_program is not None
