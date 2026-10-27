#!/usr/bin/env bash
# Strict local acceptance: intentionally fails if Java, Maven, or PostgreSQL-in-Docker is unavailable.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT"

for command in java javac mvn docker; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "ACCEPTANCE BLOCKED: missing $command" >&2
    exit 3
  fi
done
if ! docker info >/dev/null 2>&1; then
  echo "ACCEPTANCE BLOCKED: Docker daemon unavailable (PostgreSQL test cannot run)" >&2
  exit 4
fi

echo "Checking pure JDK domain/control-plane tests"
bash "$HERE/run-core-tests.sh"

echo "Running Maven/Spring/JWT/PostgreSQL Testcontainers tests"
mvn -B -ntp -f "$ROOT/services/factory-orchestrator/pom.xml" clean verify

# A green run must not consist of skipped PostgreSQL integration tests.
REPORTS="$ROOT/services/factory-orchestrator/target/surefire-reports"
if ! find "$REPORTS" -maxdepth 1 -name '*JdbcPersistenceIntegrationTest*.xml' | grep -q .; then
  echo "ACCEPTANCE FAILED: PostgreSQL integration report missing" >&2
  exit 5
fi
if grep -E '<testsuite[^>]+skipped="[1-9][0-9]*"' "$REPORTS"/*JdbcPersistenceIntegrationTest*.xml; then
  echo "ACCEPTANCE FAILED: PostgreSQL test was skipped" >&2
  exit 6
fi
echo "CONTROL PLANE ACCEPTANCE PASSED"
