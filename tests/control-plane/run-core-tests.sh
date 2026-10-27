#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
mapfile -t SOURCES < <(find "$ROOT/services/agent-store/src/main/java" "$ROOT/services/factory-orchestrator/src/main/java/com/agentfactory/control" "$HERE/src/test/java" -name '*.java' ! -name 'Jdbc*.java' ! -name 'ControlPlaneApplication.java' ! -name 'ControlPlaneRestController.java' ! -name 'Spring*.java' ! -name 'Kafka*.java' | sort)
javac -Xlint:all -Werror -encoding UTF-8 -d "$OUT" "${SOURCES[@]}"
java -ea -cp "$OUT" com.agentfactory.control.ControlPlaneComponentTests
