"""Script execution bootstrap for direct humanizer module runs."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root_on_path() -> None:
    """Add the project root to ``sys.path`` when a package file is run directly."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "emotion_agent").is_dir():
            root = str(parent)
            if root not in sys.path:
                sys.path.insert(0, root)
            return


ensure_project_root_on_path()


def _demo() -> None:
    """Run a small module smoke test."""
    print("Humanizer script bootstrap ready")


if __name__ == "__main__":
    _demo()
