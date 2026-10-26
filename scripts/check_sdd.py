#!/usr/bin/env python3
"""Offline SDD structure check; OpenSpec CLI and functional tests still required."""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGE = ROOT / "openspec/changes/bootstrap-factory-mvp"
REQUIRED = [
    "README.md", "AGENTS.md", ".specify/memory/constitution.md", "openspec/config.yaml",
    "docs/product/MVP.md", "docs/architecture/architecture.md", "docs/architecture/OWNER_QUESTIONNAIRE.md", "docs/architecture/adr/0002-microservices.md", "docs/process/SDD.md",
    "docs/quality/gates.md", "docs/quality/traceability.md",
    "openspec/changes/bootstrap-factory-mvp/proposal.md",
    "openspec/changes/bootstrap-factory-mvp/design.md",
    "openspec/changes/bootstrap-factory-mvp/tasks.md",
]

def main() -> int:
    errors = [f"missing file: {p}" for p in REQUIRED if not (ROOT / p).is_file()]
    files = sorted((CHANGE / "specs").glob("*/spec.md"))
    if len(files) < 4:
        errors.append("expected 4+ delta specs")
    found: dict[str, str] = {}
    for file in files:
        txt = file.read_text(encoding="utf-8")
        if "## ADDED Requirements" not in txt:
            errors.append(f"missing ADDED Requirements: {file}")
        blocks = re.split(r"(?=^### Requirement: )", txt, flags=re.MULTILINE)
        for b in blocks:
            m = re.match(r"### Requirement: (AF-REQ-\d{3})\b", b)
            if not m:
                continue
            req = m.group(1)
            if req in found:
                errors.append(f"duplicate {req}: {file}")
            found[req] = str(file)
            if "#### Scenario:" not in b or "- **WHEN**" not in b or "- **THEN**" not in b:
                errors.append(f"missing scenario WHEN/THEN: {req}")
    expected = {f"AF-REQ-{i:03d}" for i in range(1, 24)}
    if set(found) != expected:
        errors.append(f"requirement mismatch: missing={sorted(expected-set(found))}, extra={sorted(set(found)-expected)}")
    task = CHANGE / "tasks.md"
    if task.is_file():
        content = task.read_text(encoding="utf-8")
        unlinked = expected - set(re.findall(r"AF-REQ-\d{3}", content))
        if unlinked:
            errors.append(f"not mapped to tasks: {sorted(unlinked)}")
        if re.search(r"^- \[x\]", content, flags=re.MULTILINE):
            errors.append("spec-only bootstrap cannot claim implementation tasks are complete")
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print(f"SDD structure OK: {len(found)} requirements; {len(files)} capability specs; all mapped to tasks.")
    print("Note: independent OpenSpec CLI, code, and E2E tests remain necessary.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
