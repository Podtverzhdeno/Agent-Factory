#!/usr/bin/env bash
set -euo pipefail
cd /workspace
python -m compileall -q services/agent-builder services/agent-runtime services/evaluation services/gepard-optimizer tests/integration
python -m pytest -q tests/integration/test_signed_runtime_quality.py -ra
exec python tests/integration/health.py
