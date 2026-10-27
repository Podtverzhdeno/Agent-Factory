#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT="$(mktemp -d)"
trap 'rm -rf "$OUTPUT"' EXIT
javac -Xlint:all -Werror -d "$OUTPUT" "$ROOT/services/tool-mcp-registry/src/main/java/com/agentfactory/registry/ToolRegistry.java" "$ROOT/services/tool-mcp-registry/src/main/java/com/agentfactory/registry/PayloadShapeValidator.java" "$ROOT/services/tool-mcp-registry/src/main/java/com/agentfactory/registry/MinimumCapabilityCover.java" "$ROOT/services/tool-mcp-registry/src/main/java/com/agentfactory/registry/BuilderManifestProjection.java" "$ROOT/tests/tool-registry/RegistrySelfTest.java" "$ROOT/tests/tool-registry/RegistryRegressionTest.java" "$ROOT/tests/tool-registry/RegistryCoverPropertyTest.java" "$ROOT/tests/tool-registry/RegistryConcurrencyTest.java" "$ROOT/tests/tool-registry/RegistryBuilderProjectionTest.java"
java -ea -cp "$OUTPUT" com.agentfactory.registry.RegistrySelfTest
java -ea -cp "$OUTPUT" com.agentfactory.registry.RegistryRegressionTest
java -ea -cp "$OUTPUT" com.agentfactory.registry.RegistryCoverPropertyTest
java -ea -cp "$OUTPUT" com.agentfactory.registry.RegistryConcurrencyTest
java -ea -cp "$OUTPUT" com.agentfactory.registry.RegistryBuilderProjectionTest

python3 "$ROOT/tests/tool-registry/verify_fixtures.py"
python3 "$ROOT/tests/tool-registry/verify_architecture.py"
python3 "$ROOT/tests/tool-registry/verify_container_recipe.py"
