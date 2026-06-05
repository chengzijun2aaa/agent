"""Base memory interfaces."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from abc import ABC, abstractmethod
from typing import Sequence

from emotion_agent.utils.types import Message


class BaseMemory(ABC):
    """Abstract interface for agent memory implementations."""

    @abstractmethod
    def append(self, message: Message) -> None:
        """Append one message to memory."""

    @abstractmethod
    def get_recent(self, limit: int | None = None) -> Sequence[Message]:
        """Return recent messages from memory."""

    @abstractmethod
    def clear(self) -> None:
        """Clear memory contents."""


def _demo() -> None:
    """Run a small module smoke test."""
    print("BaseMemory interface ready")


if __name__ == "__main__":
    _demo()
