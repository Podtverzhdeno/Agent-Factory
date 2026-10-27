#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
mapfile -t SOURCES < <(find "$ROOT/services/agent-store/src/main/java" "$ROOT/services/factory-orchestrator/src/main/java/com/agentfactory/control" "$HERE/src/test/java" -name '*.java' ! -name 'ControlPlaneApplication.java' ! -name 'ControlPlaneRestController.java' ! -name 'Spring*.java' ! -name 'Kafka*.java' | sort)
# Pure-JDK strict Evaluation DTO; the rest of the REST adapter requires Spring.
SOURCES+=("$ROOT/services/factory-orchestrator/src/main/java/com/agentfactory/api/EvaluationHttpPayload.java")
javac -Xlint:all -Werror -encoding UTF-8 -d "$OUT" "${SOURCES[@]}"
java -ea -cp "$OUT" com.agentfactory.control.ControlPlaneComponentTests
java -ea -cp "$OUT" com.agentfactory.control.JdbcTransactionScopeTests
java -ea -cp "$OUT" com.agentfactory.control.EventIdentityTests
java -ea -cp "$OUT" com.agentfactory.control.OutboxRaceTests
java -ea -cp "$OUT" com.agentfactory.control.EvaluationHttpPayloadTests
java -ea -cp "$OUT" com.agentfactory.control.ControlPlaneTelemetryTests
