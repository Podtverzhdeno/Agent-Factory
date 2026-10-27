"""Dependency-free tests for the acceptance report validator."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from verify_acceptance_reports import REQUIRED, validate


class ReportValidatorTests(unittest.TestCase):
    def write(self, directory: Path, name: str, count: int, *, skipped: int = 0,
              failed: int = 0, missing_cases: bool = False) -> None:
        cases = "".join(
            f'<testcase name="case{i}">{"<skipped/>" if i < skipped else "<failure/>" if i < skipped + failed else ""}</testcase>'
            for i in range(count - int(missing_cases))
        )
        xml = f'<testsuite name="{name}" tests="{count}" skipped="{skipped}" failures="{failed}" errors="0">{cases}</testsuite>'
        (directory / f"TEST-com.agentfactory.api.{name}.xml").write_text(xml)

    def test_green_complete_suite(self) -> None:
        with TemporaryDirectory() as location:
            directory = Path(location)
            for name, count in REQUIRED.items():
                self.write(directory, name, count)
            self.assertEqual([], validate(directory))

    def test_missing_critical_suite_is_error(self) -> None:
        with TemporaryDirectory() as location:
            directory = Path(location)
            for name, count in REQUIRED.items():
                if name != "JdbcPersistenceIntegrationTest":
                    self.write(directory, name, count)
            self.assertTrue(any("JdbcPersistenceIntegrationTest" in err for err in validate(directory)))

    def test_skipped_tests_are_error(self) -> None:
        with TemporaryDirectory() as location:
            directory = Path(location)
            for name, count in REQUIRED.items():
                self.write(directory, name, count, skipped=1 if name == "JdbcPersistenceIntegrationTest" else 0)
            self.assertTrue(any("skipped=1" in err for err in validate(directory)))

    def test_false_success_with_incomplete_xml_is_error(self) -> None:
        with TemporaryDirectory() as location:
            directory = Path(location)
            for name, count in REQUIRED.items():
                self.write(directory, name, count, missing_cases=name == "ControlPlaneSecurityTest")
            self.assertTrue(any("exact count" in err for err in validate(directory)))

    def test_test_failure_is_error(self) -> None:
        with TemporaryDirectory() as location:
            directory = Path(location)
            for name, count in REQUIRED.items():
                self.write(directory, name, count, failed=1 if name == "RemoteHttpIntegrationTest" else 0)
            self.assertTrue(any("failures=1" in err for err in validate(directory)))


if __name__ == "__main__":
    unittest.main()
