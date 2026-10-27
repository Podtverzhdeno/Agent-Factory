#!/usr/bin/env python3
"""Validate twin-agent-harness SDD requirement coverage (not application E2E)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "openspec/changes/twin-agent-harness"
files = ["proposal.md", "design.md", "tasks.md"]
errors = [f"missing {name}" for name in files if not (root / name).exists()]
specs = sorted((root / "specs").glob("*/spec.md"))
if len(specs) != 3:
    errors.append("expected exactly three capability specs")
expected = {f"AF-REQ-{i:03d}" for i in range(38, 49)}
seen = {}
for path in specs:
    content = path.read_text(encoding="utf-8")
    if "## ADDED Requirements" not in content:
        errors.append(f"missing requirements header {path}")
    for block in re.split(r"(?=^### Requirement: )", content, flags=re.MULTILINE):
        match = re.match(r"### Requirement: (AF-REQ-\d{3})", block)
        if not match:
            continue
        req = match.group(1)
        seen[req] = seen.get(req, 0) + 1
        if "#### Scenario:" not in block or "- **WHEN**" not in block or "- **THEN**" not in block:
            errors.append(f"missing WHEN/THEN for {req}")
if set(seen) != expected or any(count != 1 for count in seen.values()):
    errors.append(f"requirement mismatch: missing={sorted(expected-set(seen))}, extra={sorted(set(seen)-expected)}, duplicates={[k for k,v in seen.items() if v != 1]}")
taskpath = root / "tasks.md"
if taskpath.exists():
    tasks = taskpath.read_text(encoding="utf-8")
    if not expected.issubset(set(re.findall(r"AF-REQ-\d{3}", tasks))):
        errors.append("not all requirements mapped to tasks")
    if re.search(r"^- \[x\]", tasks, flags=re.MULTILINE):
        errors.append("unexecuted implementation tasks already marked complete")
for error in errors:
    print("FAIL:", error)
if errors:
    sys.exit(1)
print(f"Twin-agent SDD OK: {len(seen)} requirements mapped with scenarios, no implementation claims.")
