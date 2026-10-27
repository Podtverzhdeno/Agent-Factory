"""Contract tests for the fail-closed Maven Surefire acceptance verifier."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree

SCRIPT = Path(__file__).with_name("verify-surefire.py")
SPEC = importlib.util.spec_from_file_location("control_plane_surefire_gate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def emit_report(path: Path, suite: str, tests: int, skipped: int = 0,
                errors: int = 0, failures: int = 0) -> None:
    name = f"com.agentfactory.api.{suite}"
    root = Element("testsuite", {
        "name": name, "tests": str(tests), "skipped": str(skipped),
        "errors": str(errors), "failures": str(failures),
    })
    ElementTree(root).write(path / f"TEST-{name}.xml", encoding="utf-8")


class SurefireEvidenceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name)
        for name, minimum in gate.REQUIRED.items():
            emit_report(self.path, name, minimum)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_complete_suite_passes(self) -> None:
        success, problems = gate.verify(self.path)
        self.assertTrue(success, problems)

    def test_missing_class_fails(self) -> None:
        (self.path / "TEST-com.agentfactory.api.JdbcPersistenceIntegrationTest.xml").unlink()
        success, problems = gate.verify(self.path)
        self.assertFalse(success)
        self.assertTrue(any("JdbcPersistenceIntegrationTest" in p for p in problems))

    def test_skipped_postgres_fails(self) -> None:
        emit_report(self.path, "JdbcPersistenceIntegrationTest", 15, skipped=15)
        self.assertFalse(gate.verify(self.path)[0])

    def test_reduced_suite_fails(self) -> None:
        emit_report(self.path, "ControlPlaneSecurityTest", 2)
        self.assertFalse(gate.verify(self.path)[0])

    def test_junit_failure_fails(self) -> None:
        emit_report(self.path, "RemoteHttpIntegrationTest", 8, failures=1)
        self.assertFalse(gate.verify(self.path)[0])

    def test_corrupted_xml_fails(self) -> None:
        file = self.path / "TEST-com.agentfactory.api.RemoteHttpIntegrationTest.xml"
        file.write_text("<testsuite", encoding="utf-8")
        self.assertFalse(gate.verify(self.path)[0])

    def test_duplicate_report_fails(self) -> None:
        emit_report(self.path, "ControlPlaneSecurityTest", 6)
        extra = self.path / "TEST-copy.xml"
        extra.write_text((self.path / "TEST-com.agentfactory.api.ControlPlaneSecurityTest.xml")
                         .read_text(encoding="utf-8"), encoding="utf-8")
        self.assertFalse(gate.verify(self.path)[0])


if __name__ == "__main__":
    unittest.main()
