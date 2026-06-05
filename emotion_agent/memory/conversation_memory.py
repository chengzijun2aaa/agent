"""Conversation memory implementation."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from collections import deque
from typing import Deque, Sequence

from emotion_agent.memory.base import BaseMemory
from emotion_agent.utils.types import Message


class ConversationMemory(BaseMemory):
    """In-memory bounded message store for recent conversation turns."""

    def __init__(self, max_messages: int = 50) -> None:
        """Create a conversation memory with a maximum message count."""
        self._messages: Deque[Message] = deque(maxlen=max_messages)

    def append(self, message: Message) -> None:
        """Append one message to memory."""
        self._messages.append(message)

    def get_recent(self, limit: int | None = None) -> Sequence[Message]:
        """Return recent messages, optionally capped by a caller-provided limit."""
        messages = list(self._messages)
        if limit is None:
            return messages
        return messages[-limit:]

    def clear(self) -> None:
        """Clear all remembered messages."""
        self._messages.clear()


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{ConversationMemory().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
