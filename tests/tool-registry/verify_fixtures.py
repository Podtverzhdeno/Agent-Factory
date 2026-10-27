#!/usr/bin/env python3
"""Independent stdlib contract verification of the Builder/Registry RFQ JSON fixtures.

This is deliberately not a substitute for running the Spring REST or production MCP stack.
The Java digest algorithm is independently reimplemented and cross-checked here.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent


def fail(detail: str) -> None:
    raise AssertionError(detail)


def check(condition: bool, detail: str) -> None:
    if not condition:
        fail(detail)


def length_prefixed(value: str) -> str:
    # Mirrors String.length() from the Java canonicalizer, not UTF-8 byte count.
    utf16_length = len(value.encode("utf-16-le")) // 2
    return f"{utf16_length}:{value}"


def canonical_digest(manifest: dict) -> str:
    def as_sorted(values: list[str]) -> str:
        return "".join(length_prefixed(value) for value in sorted(values))

    data = [
        manifest["schema_version"],
        manifest["tool_id"],
        manifest["version"],
        manifest["operation"],
        manifest["transport"],
        as_sorted(manifest["capabilities"]),
        manifest["input_schema_ref"],
        manifest["output_schema_ref"],
        as_sorted([effect.upper() for effect in manifest["side_effects"]]),
        as_sorted(manifest["required_scopes"]),
        manifest["risk_level"].upper(),
        as_sorted(manifest["tenant_availability"]),
        manifest["endpoint_ref"],
        manifest["health"],
        manifest["provenance"],
        manifest["description"],
    ]
    raw = "".join(length_prefixed(value) for value in data).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def main() -> None:
    source = json.loads((ROOT / "fixtures/synthetic-tool-manifests.json").read_text(encoding="utf-8"))
    request = json.loads((ROOT / "fixtures/rfq-selection-request.json").read_text(encoding="utf-8"))
    expected = json.loads((ROOT / "fixtures/rfq-expected-selection.json").read_text(encoding="utf-8"))
    check(source.get("fixtures_only") is True, "Fixtures must not claim production approval")
    check(expected["decision"] == "SELECTED", "Unexpected synthetic RFQ decision")
    manifests = source["manifests"]
    check(len(manifests) == 4, "Exactly four synthetic operation fixtures expected")

    required_fields = {
        "schema_version", "tool_id", "version", "operation", "transport",
        "capabilities", "input_schema_ref", "output_schema_ref", "side_effects",
        "required_scopes", "risk_level", "tenant_availability", "endpoint_ref",
        "health", "provenance", "description", "manifest_digest",
    }
    risk = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    permitted = set(request["allowed_effects"])
    required = set(request["required_capabilities"])
    authorized_scopes = {"registry:lookup", "xlsx:read", "catalog:read", "xlsx:draft"}
    compatible = []
    checks = 0

    for manifest in manifests:
        check(set(manifest) == required_fields, "Manifest contains unexpected or missing keys")
        check(manifest["schema_version"] == "0.1", "Wrong manifest contract version")
        check(bool(re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", manifest["version"])), "Invalid semantic version")
        check(manifest["transport"] == "MCP", "Fixture transport changed")
        check(manifest["tenant_availability"] == ["tenant-a"], "Fixture tenant leakage")
        check(manifest["endpoint_ref"].startswith("artifact://approved/endpoints/"), "Raw MCP URL in fixture")
        check(manifest["provenance"] == "trusted:synthetic-fixture", "Fixture provenance changed")
        check(manifest["health"] == "HEALTHY", "Fixture health changed")
        check(manifest["manifest_digest"] == canonical_digest(manifest), "Stored fixture digest disagrees with Java canonicalizer")
        checks += 1

        changed = copy.deepcopy(manifest)
        changed["description"] += " changed"
        check(changed["manifest_digest"] != canonical_digest(changed), "Digest did not bind changed description")
        changed = copy.deepcopy(manifest)
        changed["required_scopes"].append("admin:root")
        check(changed["manifest_digest"] != canonical_digest(changed), "Digest did not bind scopes")
        changed = copy.deepcopy(manifest)
        changed["tenant_availability"].append("tenant-b")
        check(changed["manifest_digest"] != canonical_digest(changed), "Digest did not bind tenants")
        checks += 3

        if (set(manifest["side_effects"]) <= permitted
            and risk[manifest["risk_level"]] <= risk[request["max_risk"]]
            and set(manifest["required_scopes"]) <= authorized_scopes):
            compatible.append(manifest)

    options = []
    for amount in range(1, len(compatible) + 1):
        for subset in itertools.combinations(compatible, amount):
            covered = set().union(*(set(m["capabilities"]) for m in subset))
            if required <= covered:
                options.append(subset)
        if options:
            break
    check(bool(options), "RFQ capabilities are not covered")
    selected = min(options, key=lambda items: (
        len(items),
        sum(risk[m["risk_level"]] for m in items),
        len(set().union(*(set(m["required_scopes"]) for m in items))),
        sum(len(m["side_effects"]) for m in items),
        "|".join(sorted(f'{m["tool_id"]}@{m["version"]}/{m["operation"]}' for m in items)),
    ))
    tool_ids = sorted(m["tool_id"] for m in selected)
    check(tool_ids == expected["selected_tool_ids"], f"Expected RFQ selection drift: {tool_ids}")
    check(set(expected["excluded_tool_ids"]).isdisjoint(tool_ids), "Unsafe tool included in selection")
    check("payments.charge" in expected["excluded_tool_ids"], "Payment fixture must be excluded")
    check(set().union(*(set(m["capabilities"]) for m in selected)) == required,
          "Builder selection includes unrelated capabilities")
    check(len(tool_ids) == 3, "Incorrect minimum operation count")
    print(f"PASS: RFQ JSON fixture verification ({len(manifests)} SHA-256 digests, {checks} integrity checks, minimum authorized cover)")


if __name__ == "__main__":
    main()
