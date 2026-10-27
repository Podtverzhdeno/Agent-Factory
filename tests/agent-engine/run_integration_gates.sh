#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
: "${AGENT_ENGINE_TEST_PG_DSN:?Provide an isolated PostgreSQL DSN; NEVER production}"
# Restrict persisted graph checkpoint deserialization to built-in safe types.
export LANGGRAPH_STRICT_MSGPACK=true
python -m compileall -q services/agent-builder services/agent-runtime services/litellm-adapter tests/agent-engine
python tests/agent-engine/ruff_report.py
python -m pyright services/agent-builder services/agent-runtime services/litellm-adapter tests/agent-engine
# Exercise real SDK adapters and all non-DB tests without ever exposing a
# production/shared database connection to the pytest process. Optional
# PostgreSQL cases may SKIP in this phase but may NOT do so in acceptance.
env -u AGENT_ENGINE_TEST_PG_DSN -u DATABASE_URL -u PGHOST -u PGPASSWORD \
    -u PGUSER -u PGDATABASE AGENT_ENGINE_REQUIRE_INTEGRATIONS=0 \
    python -m pytest -q tests/agent-engine -ra
# The PG guard must run immediately before DB-touching tests, not before lint.
python tests/agent-engine/verify_test_database.py
AGENT_ENGINE_REQUIRE_INTEGRATIONS=1 python -m pytest -q tests/agent-engine -ra
