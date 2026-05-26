"""Runtime bootstrap helpers for direct execution of example scripts."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root_on_path() -> Path:
    """Insert the free-edition root directory onto `sys.path` when needed.

    Args:
        None.

    Returns:
        The resolved free-edition root directory.

    Raises:
        None.
    """
    project_root = Path(__file__).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    return project_root
