#!/usr/bin/env bash
set -euo pipefail
# Private, disposable PostgreSQL is *inside* this integration-test container.
# Discard a preconfigured Railway shared DATABASE_URL before any database
# connection or test process starts. No external PostgreSQL hosts are used.
unset AGENT_ENGINE_TEST_PG_DSN DATABASE_URL PGHOST PGPASSWORD PGUSER PGDATABASE
export AGENT_ENGINE_REQUIRE_INTEGRATIONS=1
export LANGGRAPH_STRICT_MSGPACK=true
export AGENT_ENGINE_TEST_PG_MODE=local-ephemeral

PG_BIN_DIR="$(find /usr/lib/postgresql -mindepth 2 -maxdepth 2 -type d -name bin | sort -V | tail -n 1)"
if [[ -z "$PG_BIN_DIR" || ! -x "$PG_BIN_DIR/initdb" ]]; then
  echo "Agent 04: PostgreSQL binaries missing (fail closed)" >&2
  exit 2
fi
export PATH="$PG_BIN_DIR:$PATH"
PG_CLUSTER_DIR="$(mktemp -d /tmp/agent04-test-pg.XXXXXXXX)"
# Trust auth is restricted to the disposable container's loopback interface;
# this is NOT a production DB or a network-exposed database.
initdb -D "$PG_CLUSTER_DIR" --auth-local=trust --auth-host=trust \
    --encoding=UTF8 --no-instructions >/dev/null
pg_ctl -D "$PG_CLUSTER_DIR" \
    -o "-c listen_addresses=127.0.0.1 -c port=55432 -c unix_socket_directories=/tmp" \
    -l "$PG_CLUSTER_DIR/server.log" -w start >/dev/null
cleanup_pg() {
  pg_ctl -D "$PG_CLUSTER_DIR" -m immediate -w stop >/dev/null 2>&1 || true
}
trap cleanup_pg EXIT
psql -h 127.0.0.1 -p 55432 -U postgres -d postgres \
    -v ON_ERROR_STOP=1 \
    -c "CREATE ROLE agent04_test LOGIN PASSWORD 'ephemeral-only-agent04';" >/dev/null
createdb -h 127.0.0.1 -p 55432 -U postgres -O agent04_test agent04_test
export AGENT_ENGINE_TEST_PG_DSN="postgresql://agent04_test:ephemeral-only-agent04@127.0.0.1:55432/agent04_test"
# Fail if any binary/linter/real SDK/Postgres test fails; no health on failures.
bash tests/agent-engine/run_integration_gates.sh
cleanup_pg
trap - EXIT
# Health indicates an isolated integration appliance only, never live readiness.
exec python tests/agent-engine/railway_gate_health.py
