#!/usr/bin/env python3
"""Check the bilateral A2A SDD change structure; not a functional A2A test."""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGE = ROOT / "openspec/changes/a2a-bilateral-evaluation"
required = ["proposal.md", "design.md", "tasks.md", "specs/bilateral-a2a-evaluation/spec.md"]
failures = [f"missing {p}" for p in required if not (CHANGE / p).is_file()]
req_expected = {f"AF-REQ-{n:03d}" for n in range(31, 38)}
spec_file = CHANGE / "specs/bilateral-a2a-evaluation/spec.md"
found: dict[str, int] = {}
if spec_file.is_file():
    text = spec_file.read_text(encoding="utf-8")
    if "## ADDED Requirements" not in text:
        failures.append("ADDED Requirements section missing")
    for block in re.split(r"(?=^### Requirement: )", text, flags=re.MULTILINE):
        match = re.match(r"### Requirement: (AF-REQ-\d{3})", block)
        if not match:
            continue
        req = match.group(1)
        found[req] = found.get(req, 0) + 1
        if "#### Scenario:" not in block or "- **WHEN**" not in block or "- **THEN**" not in block:
            failures.append(f"missing scenario for {req}")
if set(found) != req_expected:
    failures.append(f"requirements mismatch: missing {sorted(req_expected-set(found))}, extra {sorted(set(found)-req_expected)}")
if any(n != 1 for n in found.values()):
    failures.append("duplicate requirements")
task_path = CHANGE / "tasks.md"
if task_path.is_file():
    tasks = task_path.read_text(encoding="utf-8")
    if not req_expected.issubset(set(re.findall(r"AF-REQ-\d{3}", tasks))):
        failures.append("not all requirements mapped to implementation tasks")
    if re.search(r"^- \[x\]", tasks, flags=re.MULTILINE):
        failures.append("cannot mark unimplemented A2A features complete")
if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print(f"Bilateral A2A SDD structure OK: {len(found)} scenario-backed requirements; tasks mapped.")
print("Note: strict OpenSpec CLI, implementation and adversarial A2A end-to-end tests remain separate.")
