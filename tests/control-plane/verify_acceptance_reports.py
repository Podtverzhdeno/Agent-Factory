#!/usr/bin/env python3
"""Fail-closed Surefire acceptance: core, JWT, PostgreSQL and HTTP suites must really run."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

REQUIRED = {
    "ControlPlaneComponentSuiteTest": 1,
    "ControlPlaneSecurityTest": 4,
    "JdbcPersistenceIntegrationTest": 8,
    "RemoteHttpIntegrationTest": 5,
}


def validate(reports: Path) -> list[str]:
    errors: list[str] = []
    if not reports.is_dir():
        return [f"Surefire report directory missing: {reports}"]
    for class_name, minimum in REQUIRED.items():
        report = reports / f"TEST-com.agentfactory.api.{class_name}.xml"
        if not report.is_file():
            errors.append(f"Missing required test report: {report.name}")
            continue
        try:
            root = ET.parse(report).getroot()
        except (ET.ParseError, OSError) as exc:
            errors.append(f"Invalid XML for {class_name}: {exc}")
            continue
        if root.tag != "testsuite":
            errors.append(f"Unexpected XML document for {class_name}: {root.tag}")
            continue
        try:
            total = int(root.attrib["tests"])
            failures = int(root.attrib.get("failures", "0"))
            errors_count = int(root.attrib.get("errors", "0"))
            skipped = int(root.attrib.get("skipped", "0"))
        except (KeyError, ValueError) as exc:
            errors.append(f"Invalid test counters for {class_name}: {exc}")
            continue
        cases = root.findall("testcase")
        counted_skips = sum(case.find("skipped") is not None for case in cases)
        counted_failures = sum(case.find("failure") is not None for case in cases)
        counted_errors = sum(case.find("error") is not None for case in cases)
        if total < minimum or total != len(cases):
            errors.append(f"{class_name}: expected >= {minimum} executed cases and exact count, reported {total}, listed {len(cases)}")
        if failures or errors_count or skipped or counted_skips or counted_failures or counted_errors:
            errors.append(f"{class_name}: failures={failures}, errors={errors_count}, skipped={skipped}, listed_skipped={counted_skips}, listed_failed={counted_failures}, listed_errors={counted_errors}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, help="Maven target/surefire-reports")
    args = parser.parse_args()
    errors = validate(args.reports)
    for error in errors:
        print(f"ACCEPTANCE FAILED: {error}", file=sys.stderr)
    if errors:
        return 1
    print("REQUIRED SUREFIRE ACCEPTANCE SUITES PASSED (not skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
