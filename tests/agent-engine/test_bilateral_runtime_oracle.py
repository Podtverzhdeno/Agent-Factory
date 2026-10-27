"""A model success message cannot substitute for a verified quote artifact."""
import pytest
from agent_runtime import Decision
from agent_runtime.bilateral_oracle import evaluate_quote
from test_bilateral_quote_oracle import NOW, fixture
from test_engine import Registry, build, invoke, manifest, task


@pytest.mark.asyncio
async def test_completed_model_run_cannot_pass_quote_oracle_without_artifact():
    spec = build(task('buyer-quote', ['catalog.read'], ['read'],
                      ['catalog:read']),
                 Registry([manifest('catalog.lookup', ['catalog.read'],
                                    ['read'], ['catalog:read'])]))
    runtime, tools = invoke(spec, [
        Decision(kind='final', text='Supplier confirmed order; quote sent.')])
    result = await runtime.run(
        spec, tenant_id='buyer', run_id='false-success', thread_id='rfq',
        request='Provide a verified quotation', trace_id='test-rfq')
    assert result.status == 'COMPLETED'
    assert not tools.called
    rfq, events, _ = fixture()
    verdict = evaluate_quote(rfq, events, None, now=NOW)
    assert not verdict.passed
    assert verdict.code == 'MISSING_BUSINESS_ARTIFACT'
