"""Base interfaces for persistence adapters."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from abc import ABC, abstractmethod
from typing import Any, Sequence

from emotion_agent.utils.types import Message


class BaseStorage(ABC):
    """Abstract storage interface for messages and state snapshots."""

    @abstractmethod
    def save_message(self, conversation_id: str, message: Message) -> None:
        """Persist a single message for a conversation."""

    @abstractmethod
    def load_messages(self, conversation_id: str, limit: int | None = None) -> Sequence[Message]:
        """Load messages for a conversation."""

    @abstractmethod
    def save_state(self, conversation_id: str, state: dict[str, Any]) -> None:
        """Persist a serializable state snapshot."""

    @abstractmethod
    def load_state(self, conversation_id: str) -> dict[str, Any] | None:
        """Load a previously persisted state snapshot."""


def _demo() -> None:
    """Run a small module smoke test."""
    print("BaseStorage interface ready")


if __name__ == "__main__":
    _demo()
