#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
: "${AGENT_ENGINE_TEST_PG_DSN:?Provide an isolated PostgreSQL DSN; NEVER production}"
python -m compileall -q services/agent-builder services/agent-runtime services/litellm-adapter tests/agent-engine
python -m ruff check services/agent-builder services/agent-runtime services/litellm-adapter tests/agent-engine
python -m pyright services/agent-builder services/agent-runtime services/litellm-adapter tests/agent-engine
AGENT_ENGINE_REQUIRE_INTEGRATIONS=1 python -m pytest -q tests/agent-engine -ra
