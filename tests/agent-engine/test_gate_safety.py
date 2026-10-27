"""No Railway integration can connect to a shared database by accident."""

from ruff_report import summarize_ruff
from verify_test_database import validate_isolated_test_database


def test_gate_accepts_only_dedicated_test_db_host_user_name():
    allowed = "postgresql://agent04_test:synthetic@agent04-test-postgres.railway.internal:5432/agent04_test"
    assert validate_isolated_test_database(allowed) is None


def test_gate_denies_shared_or_production_postgresql():
    invalid = (
        "postgresql://postgres:secret@postgres.railway.internal:5432/railway",
        "postgresql://agent04_test:secret@production.railway.internal:5432/agent04_test",
        "postgresql://agent04_test:secret@agent04-test-postgres.railway.internal/production",
        "postgresql://postgres:secret@agent04-test-postgres.railway.internal/agent04_test",
        "postgresql://agent04_test@agent04-test-postgres.railway.internal/agent04_test",
        "postgresql://agent04_test:secret@agent04-test-postgres.railway.internal/agent04_test?sslmode=disable",
        "invalid",
        "",
    )
    for dsn in invalid:
        assert validate_isolated_test_database(dsn) is not None


def test_ruff_diagnostic_summary_is_bounded_but_preserves_count():
    data = [
        {"code": "F401", "filename": "a.py", "message": "unused", "location": {"row": 1}}
        for _ in range(1001)
    ]
    lines = summarize_ruff(data)
    assert "1001 total violations" in lines[0]
    assert any("F401: 1001" in x for x in lines)
    assert any("976 other violations" in x for x in lines)
    assert len(lines) < 55


def test_integration_gate_checks_db_identity_before_pytest_but_after_lint():
    from pathlib import Path
    script = (Path(__file__).resolve().parent / "run_integration_gates.sh").read_text()
    assert script.index("ruff_report.py") < script.index("verify_test_database.py")
    assert script.index("python -m pyright") < script.index("verify_test_database.py")
    assert script.index("verify_test_database.py") < script.index("AGENT_ENGINE_REQUIRE_INTEGRATIONS=1 python -m pytest")


def test_integration_gate_exercises_tests_without_database_before_strict_acceptance():
    from pathlib import Path
    sh = (Path(__file__).resolve().parent / "run_integration_gates.sh").read_text()
    assert "env -u AGENT_ENGINE_TEST_PG_DSN -u DATABASE_URL" in sh
    assert "AGENT_ENGINE_REQUIRE_INTEGRATIONS=0" in sh
    assert sh.index("AGENT_ENGINE_REQUIRE_INTEGRATIONS=0") < sh.index("verify_test_database.py")
    assert sh.index("verify_test_database.py") < sh.index("AGENT_ENGINE_REQUIRE_INTEGRATIONS=1 python -m pytest")


def test_official_a2a_server_extra_is_installed_by_integration_gate():
    from pathlib import Path
    requirements = (Path(__file__).resolve().parent / "requirements-integration.txt").read_text()
    assert "a2a-sdk[http-server]" in requirements


def test_guard_accepts_exact_local_ephemeral_database_only_with_explicit_mode():
    dsn = "postgresql://agent04_test:ephemeral@127.0.0.1:55432/agent04_test"
    assert validate_isolated_test_database(dsn) == "TEST_DATABASE_NOT_ISOLATED"
    assert validate_isolated_test_database(dsn, local_ephemeral=True) is None
    for bad in (
        "postgresql://postgres:ephemeral@127.0.0.1:55432/agent04_test",
        "postgresql://agent04_test:ephemeral@127.0.0.1:5432/agent04_test",
        "postgresql://agent04_test:ephemeral@127.0.0.1:55432/railway",
        "postgresql://agent04_test:ephemeral@postgres.railway.internal:55432/agent04_test",
    ):
        assert validate_isolated_test_database(bad, local_ephemeral=True) is not None


def test_ephemeral_entrypoint_discards_shared_database_env_before_starting_pg():
    from pathlib import Path
    root = Path(__file__).resolve().parent
    entry = (root / "railway_gate_entrypoint.sh").read_text()
    assert "unset AGENT_ENGINE_TEST_PG_DSN DATABASE_URL" in entry
    assert entry.index("unset AGENT_ENGINE_TEST_PG_DSN") < entry.index("initdb -D")
    assert "listen_addresses=127.0.0.1" in entry
    assert "port=55432" in entry
    assert "trap cleanup_pg EXIT" in entry
    assert entry.index("bash tests/agent-engine/run_integration_gates.sh") < entry.index("exec python tests/agent-engine/railway_gate_health.py")
