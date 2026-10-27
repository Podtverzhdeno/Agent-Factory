import sys
from types import SimpleNamespace
import pytest

from gepard_optimizer import DspyGepaBackend, GepaUnavailableError


def _kwargs():
    return dict(student=object(), metric=lambda e, p: 1.0,
                trainset=[object()], valset=[object()], reflection_lm=object(),
                train_ref="artifact://train-v1", validation_ref="artifact://val-v1")


def test_backend_checks_dataset_boundaries_before_import():
    runner = DspyGepaBackend()
    for changed in ({"train_ref": "artifact://holdout"},
                    {"validation_ref": "artifact://train-v1"},
                    {"valset": []}, {"max_metric_calls": 1000},
                    {"reflection_lm": None}):
        with pytest.raises(ValueError):
            runner.compile(**(_kwargs() | changed))


def test_backend_real_library_not_installed_is_explicit():
    # DSPy is optional; if present, the separate integration would need a configured LM.
    if 'dspy' not in sys.modules:
        import importlib.util
        if importlib.util.find_spec('dspy') is None:
            with pytest.raises(GepaUnavailableError):
                DspyGepaBackend().compile(**_kwargs())


def test_backend_calls_dspy_gepa_contract_but_does_not_release(monkeypatch):
    calls = {}
    class FakeGepa:
        def __init__(self, **options):
            calls['options'] = options
        def compile(self, student, **sets):
            calls['sets'] = sets
            return "optimized-program"
    monkeypatch.setitem(sys.modules, "dspy", SimpleNamespace(GEPA=FakeGepa))
    result = DspyGepaBackend().compile(**(_kwargs() | {"optimize_tool_descriptions": True}))
    assert result.candidate_program == "optimized-program"
    assert result.status == "REQUIRES_INDEPENDENT_EVALUATION"
    assert calls['options']['enable_tool_optimization'] is True
    assert calls['sets']['trainset'] and calls['sets']['valset']
