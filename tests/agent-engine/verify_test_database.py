"""Fail closed before an integration gate can touch shared or production data."""

from __future__ import annotations

import os
import sys
from urllib.parse import urlsplit

_ALLOWED_HOST = "agent04-test-postgres.railway.internal"
_ALLOWED_LOCAL_HOST = "127.0.0.1"
_ALLOWED_LOCAL_PORT = 55432
_ALLOWED_DATABASE = "agent04_test"
_ALLOWED_USER = "agent04_test"


def validate_isolated_test_database(dsn: str, *, local_ephemeral: bool = False) -> str | None:
    """Only the dedicated, explicitly named Agent 04 Railway test DB is valid."""
    if not dsn or any(ch.isspace() for ch in dsn):
        return "MISSING_TEST_DSN"
    try:
        parts = urlsplit(dsn)
        if (parts.scheme not in {"postgres", "postgresql"}
                or not (parts.hostname == _ALLOWED_HOST or
                        (local_ephemeral and parts.hostname == _ALLOWED_LOCAL_HOST
                         and parts.port == _ALLOWED_LOCAL_PORT))
                or parts.path != "/" + _ALLOWED_DATABASE
                or parts.username != _ALLOWED_USER
                or not parts.password
                or parts.query or parts.fragment
                or parts.port not in ((55432,) if local_ephemeral else (None, 5432))):
            return "TEST_DATABASE_NOT_ISOLATED"
    except (ValueError, AttributeError):
        return "INVALID_TEST_DSN"
    return None


def main() -> int:
    # Never echo database URLs or credentials to Railway logs.
    local_ephemeral = os.environ.get("AGENT_ENGINE_TEST_PG_MODE") == "local-ephemeral"
    error = validate_isolated_test_database(
        os.environ.get("AGENT_ENGINE_TEST_PG_DSN", ""),
        local_ephemeral=local_ephemeral)
    if error:
        print(f"Agent 04 integration refused: {error}", file=sys.stderr)
        return 2
    print("Dedicated Agent 04 test database identity verified (network access not proven)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
