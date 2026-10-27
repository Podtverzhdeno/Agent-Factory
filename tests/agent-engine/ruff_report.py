"""Bound Ruff output without dropping diagnostics or weakening exit status."""

from __future__ import annotations

import collections
import json
import subprocess
import sys
from pathlib import Path


TARGETS = (
    "services/agent-builder",
    "services/agent-runtime",
    "services/litellm-adapter",
    "tests/agent-engine",
)


def summarize_ruff(diagnostics: list[dict]) -> list[str]:
    """Print bounded grouped evidence; *every* violation still fails."""
    grouped = collections.Counter(str(d.get("code") or "UNKNOWN") for d in diagnostics)
    files = collections.Counter(str(d.get("filename") or "unknown") for d in diagnostics)
    lines = [f"Ruff: {len(diagnostics)} total violations across {len(files)} files"]
    lines.extend(f"  {code}: {count}" for code, count in grouped.most_common(30))
    lines.append("Files with the most violations:")
    for name, count in files.most_common(20):
        lines.append(f"  {Path(name).as_posix()}: {count}")
    lines.append("First 25 individual violations:")
    for item in diagnostics[:25]:
        loc = item.get("location") or {}
        lines.append(f"  {item.get('filename')}:{loc.get('row')} "
                     f"{item.get('code')}: {item.get('message')}")
    if len(diagnostics) > 25:
        lines.append(f"  ... {len(diagnostics) - 25} other violations retained in failure count")
    return lines


def main() -> int:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--output-format", "json", *TARGETS],
            capture_output=True, text=True, check=False, timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Ruff unavailable or timeout: {type(exc).__name__}", file=sys.stderr)
        return 2
    try:
        diagnostics = json.loads(result.stdout)
        if not isinstance(diagnostics, list):
            raise ValueError("Expected JSON diagnostic array")
    except (json.JSONDecodeError, ValueError):
        print("Ruff produced non-JSON diagnostics (aborting closed)", file=sys.stderr)
        print(result.stderr[:1500], file=sys.stderr)
        return result.returncode or 2
    for line in summarize_ruff(diagnostics):
        print(line)
    if result.stderr:
        print(result.stderr[:2000], file=sys.stderr)
    return result.returncode if result.returncode else int(bool(diagnostics))


if __name__ == "__main__":
    sys.exit(main())
