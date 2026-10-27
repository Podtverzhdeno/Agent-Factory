#!/usr/bin/env python3
"""Dependency-free guard for the JSON v0 contract; does not replace MockMvc/Jackson tests."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = (root / "services/tool-mcp-registry/src/main/java/com/agentfactory/registry/RegistryJsonConfig.java").read_text()
http_tests = (root / "services/tool-mcp-registry/src/test/java/com/agentfactory/registry/RegistryAuthorizedHttpTest.java").read_text()
api = (root / "services/tool-mcp-registry/openapi.yaml").read_text()
runner = (root / "tests/tool-registry/run.sh").read_text()
core = (root / "services/tool-mcp-registry/src/main/java/com/agentfactory/registry/ToolRegistry.java").read_text()

checks = {
    "Jackson3-only adapter isolated from domain": "tools.jackson.databind.JacksonModule" in source and "tools.jackson" not in core and "com.fasterxml.jackson" not in core,
    "v0 schema requires lowercase Risk": "Risk: {type: string, enum: [low, medium, high, critical]}" in api,
    "v0 schema requires lowercase Effect": "Effect: {type: string, enum: [read, draft_file, write, payment, destructive]}" in api,
    "risk serializer": "module.addSerializer(Risk.class, lowerCaseSerializer())" in source,
    "risk deserializer": "module.addDeserializer(Risk.class, strictLowerCaseDeserializer(Risk.class))" in source,
    "effects serializer": "module.addSerializer(Effect.class, lowerCaseSerializer())" in source,
    "effects deserializer": "module.addDeserializer(Effect.class, strictLowerCaseDeserializer(Effect.class))" in source,
    "strict case normalization": "value.equals(value.toLowerCase(Locale.ROOT))" in source,
    "unknown enum maps to typed Jackson bad request": "context.weirdStringException(value, enumType" in source,
    "unknown fields rejected": "FAIL_ON_UNKNOWN_PROPERTIES, true" in source,
    "snake case retained": "PropertyNamingStrategies.SNAKE_CASE" in source,
    "wire JUnit uses supported case": '"\\"max_risk\\":\\"low\\""' in http_tests,
    "wire JUnit tests lowercase effects": '"\\"allowed_effects\\":[\\"read\\"]"' in http_tests,
    "wire JUnit rejects uppercase": 'request.replace("\\"low\\"", "\\"LOW\\"")' in http_tests,
    "wire JUnit rejects unknown values": 'unknown_effect' in http_tests,
    "status enums left unchanged": "module.addSerializer(Status.class" not in source and "module.addSerializer(Decision.class" not in source,
    "manifest digest untouched": "String.valueOf(m.riskLevel())" in core,
    "duplicate JSON keys rejected before domain": "STRICT_DUPLICATE_DETECTION" in source,
    "input nesting bounded": ".maxNestingDepth(16)" in source,
    "input document size bounded": ".maxDocumentLength(1_048_576)" in source,
    "input token count bounded": ".maxTokenCount(50_000)" in source,
    "input field values bounded": ".maxStringLength(8_192)" in source,
    "input JSON name length bounded": ".maxNameLength(128)" in source,
    "parser negative JUnit included": 'testJsonParserRejectsDuplicateKeysAndExcessivePayload' in http_tests,
    "test wired into runner": 'verify_wire_contract.py' in runner,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise AssertionError("Wire-contract static guards failed: " + ", ".join(failed))
print(f"PASS: {len(checks)} Jackson3 wire-format static guards (JUnit still requires Maven)")
