#!/usr/bin/env bash
set -euo pipefail
# Sandbox integration gate: do not become healthy unless REAL SDK+PG tests pass.
: "${AGENT_ENGINE_TEST_PG_DSN:?An isolated PostgreSQL test database DSN is required}"
export AGENT_ENGINE_REQUIRE_INTEGRATIONS=1
export LANGGRAPH_STRICT_MSGPACK=true
python tests/agent-engine/verify_test_database.py
bash tests/agent-engine/run_integration_gates.sh
# This private probe has no agent execution or user/business routes.
exec python tests/agent-engine/railway_gate_health.py
