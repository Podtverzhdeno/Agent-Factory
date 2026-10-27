#!/usr/bin/env bash
# Strict local acceptance: intentionally fails if Java, Maven, or PostgreSQL-in-Docker is unavailable.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT"

for command in java javac mvn docker python3; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "ACCEPTANCE BLOCKED: missing $command" >&2
    exit 3
  fi
done
if ! docker info >/dev/null 2>&1; then
  echo "ACCEPTANCE BLOCKED: Docker daemon unavailable (PostgreSQL test cannot run)" >&2
  exit 4
fi

if [[ -n "${EXPECTED_HEAD_SHA:-}" ]]; then
  actual_sha="$(git rev-parse HEAD)"
  if [[ "$actual_sha" != "$EXPECTED_HEAD_SHA" ]]; then
    echo "ACCEPTANCE FAILED: expected commit $EXPECTED_HEAD_SHA, found $actual_sha" >&2
    exit 7
  fi
fi
echo "Checking acceptance report verifier against known passing and failing fixtures"
python3 -m unittest discover -s "$HERE" -p "test_verify_surefire.py" -v

echo "Checking pure JDK domain/control-plane tests"
bash "$HERE/run-core-tests.sh"

echo "Running Maven/Spring/JWT/PostgreSQL Testcontainers tests"
mvn -B -ntp -f "$ROOT/services/factory-orchestrator/pom.xml" clean verify

# Validate every required JUnit class and reject skipped, missing or failed tests.
REPORTS="$ROOT/services/factory-orchestrator/target/surefire-reports"
python3 "$HERE/verify-surefire.py" "$REPORTS"
echo "CONTROL PLANE ACCEPTANCE PASSED"
