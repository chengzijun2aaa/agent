"""Storage boundaries for persistence adapters."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.storage.base import BaseStorage
from emotion_agent.storage.memory_storage import InMemoryStorage

__all__ = ["BaseStorage", "InMemoryStorage"]


def _demo() -> None:
    """Run a small package smoke test."""
    print("Storage package ready")


if __name__ == "__main__":
    _demo()
