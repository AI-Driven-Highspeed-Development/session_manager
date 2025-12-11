"""Refresh script for session_manager."""

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))

from managers.session_manager.session_manager_cli import register_cli


def refresh() -> None:
    """Register CLI commands for session_manager."""
    register_cli()


if __name__ == "__main__":
    refresh()
