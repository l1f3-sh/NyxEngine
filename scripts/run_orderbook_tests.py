"""Utility entry-point to run only the order book focussed unit tests."""

# pathlib helps compute the repository root relative to this script's location.
from pathlib import Path
# subprocess allows delegating to pytest without reimplementing test discovery.
import subprocess
# sys exposes the active interpreter so we can invoke pytest consistently.
import sys


def main() -> int:
    """Execute pytest for the order book tests and return its exit code."""

    project_root = Path(__file__).resolve().parent.parent
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/test_orderbook.py"], cwd=project_root)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
