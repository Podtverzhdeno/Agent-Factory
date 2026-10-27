#!/usr/bin/env python3
"""Fail-closed verification of Maven Surefire JUnit acceptance evidence.

The SDD validation workflow is not a substitute for these executable Java tests.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from xml.etree import ElementTree

# Class-name suffix -> lower bound of expected JUnit methods. Counts are
# deliberately conservative; a reduced test suite must trigger a review.
REQUIRED = {
    "ControlPlaneComponentSuiteTest": 4,
    "ControlPlaneSecurityTest": 6,
    "JdbcPersistenceIntegrationTest": 14,
    "JdbcSpringWiringIntegrationTest": 2,
    "RemoteHttpIntegrationTest": 9,
}


def verify(directory: Path) -> tuple[bool, list[str]]:
    problems: list[str] = []
    suites: dict[str, list[tuple[int, int, int, int]]] = {name: [] for name in REQUIRED}
    if not directory.is_dir():
        return False, [f"Surefire report directory missing: {directory}"]
    for report in directory.glob("TEST-*.xml"):
        try:
            root = ElementTree.parse(report).getroot()
        except (OSError, ElementTree.ParseError) as exc:
            problems.append(f"Invalid Surefire XML {report.name}: {exc}")
            continue
        roots = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
        if not roots:
            problems.append(f"No testsuite in {report.name}")
        for suite in roots:
            raw = suite.get("name", "")
            name = raw.rsplit(".", 1)[-1]
            if name not in REQUIRED:
                continue
            try:
                counts = tuple(int(suite.get(key, "0"))
                               for key in ("tests", "errors", "failures", "skipped"))
            except ValueError:
                problems.append(f"Noninteger counters in {report.name} ({name})")
                continue
            if any(n < 0 for n in counts):
                problems.append(f"Negative counters in {report.name} ({name})")
                continue
            cases = suite.findall("testcase")
            if len(cases) != counts[0]:
                problems.append(
                    f"{name}: reported {counts[0]} tests but XML contains {len(cases)} testcases"
                )
            child_skips=sum(case.find("skipped") is not None for case in cases)
            child_failures=sum(case.find("failure") is not None for case in cases)
            child_errors=sum(case.find("error") is not None for case in cases)
            if (child_skips,child_failures,child_errors) != (counts[3],counts[2],counts[1]):
                problems.append(
                    f"{name}: suite counters disagree with testcase-level skip/failure/error elements"
                )
            suites[name].append(counts)

    for name, minimum in REQUIRED.items():
        items = suites[name]
        if len(items) != 1:
            problems.append(f"{name}: expected exactly one report, got {len(items)}")
            continue
        tests, errors, failures, skipped = items[0]
        if tests < minimum:
            problems.append(f"{name}: {tests} tests reported, minimum {minimum}")
        if errors or failures or skipped:
            problems.append(
                f"{name}: errors={errors}, failures={failures}, skipped={skipped}"
            )
        if tests <= errors + failures + skipped:
            problems.append(f"{name}: no successful executable tests")
    return not problems, problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report_directory", type=Path)
    args = parser.parse_args()
    success, problems = verify(args.report_directory)
    if not success:
        for problem in problems:
            print(f"ACCEPTANCE FAILED: {problem}", file=sys.stderr)
        return 5
    print("SUREFIRE ACCEPTANCE PASSED: all required JUnit suites executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
