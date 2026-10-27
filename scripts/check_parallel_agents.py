#!/usr/bin/env python3
"""Structural checks for five independent coding agent task packs, not implementation acceptance."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs" / "parallel"
NAMES = [
    "01-control-plane", "02-business-task", "03-tool-registry",
    "04-agent-engine", "05-quality-engine",
]
OWNED = {
    "01-control-plane": ["services/factory-orchestrator/", "services/agent-store/", "tests/control-plane/"],
    "02-business-task": ["services/business-task/", "services/document-ingestion/", "tests/business-task/"],
    "03-tool-registry": ["services/tool-mcp-registry/", "tests/tool-registry/"],
    "04-agent-engine": ["services/agent-builder/", "services/agent-runtime/", "services/litellm-adapter/", "tests/agent-engine/"],
    "05-quality-engine": ["services/evaluation/", "services/gepard-optimizer/", "tests/quality-engine/"],
}
errors = []
for file in ["README.md", "CONTRACTS_V0.md", "INTEGRATION_GATE.md"]:
    if not (BASE / file).is_file():
        errors.append(f"missing shared file {file}")
seen_paths = {}
for slug in NAMES:
    file = BASE / "agents" / f"{slug}.md"
    if not file.is_file():
        errors.append(f"missing work packet {slug}")
        continue
    body = file.read_text(encoding="utf-8")
    for phrase in ["Branch:", "You own only:", "Copy/paste launch prompt", "Acceptance", "Exclusions"]:
        if phrase not in body:
            errors.append(f"{slug}: missing {phrase}")
    if not re.search(r"AF-REQ-\d{3}", body):
        errors.append(f"{slug}: no references to requirements")
    for owned in OWNED[slug]:
        if owned not in body:
            errors.append(f"{slug}: missing ownership claim {owned}")
        if owned in seen_paths:
            errors.append(f"overlapping path {owned}: {slug}, {seen_paths[owned]}")
        seen_paths[owned] = slug
for left, lpaths in OWNED.items():
    for right, rpaths in OWNED.items():
        if left >= right:
            continue
        for a in lpaths:
            for b in rpaths:
                if a.startswith(b) or b.startswith(a):
                    errors.append(f"overlapping workstreams: {left}/{right}: {a} vs {b}")
if errors:
    for error in errors:
        print("FAIL:", error)
    sys.exit(1)
print("Five parallel work packets structurally valid: unique path ownership, briefs and shared contracts.")
print("Note: code, deployments and the owner architecture ADR still need independent review.")
