#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT="$(mktemp -d)"
trap 'rm -rf "$OUTPUT"' EXIT
javac -d "$OUTPUT" "$ROOT/services/tool-mcp-registry/src/main/java/com/agentfactory/registry/ToolRegistry.java" "$ROOT/tests/tool-registry/RegistrySelfTest.java"
java -ea -cp "$OUTPUT" com.agentfactory.registry.RegistrySelfTest
