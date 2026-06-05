"""In-memory storage adapter."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from collections import defaultdict
from typing import Any, DefaultDict, Sequence

from emotion_agent.storage.base import BaseStorage
from emotion_agent.utils.types import Message


class InMemoryStorage(BaseStorage):
    """Process-local storage adapter for development and tests."""

    def __init__(self) -> None:
        """Create empty message and state stores."""
        self._messages: DefaultDict[str, list[Message]] = defaultdict(list)
        self._states: dict[str, dict[str, Any]] = {}

    def save_message(self, conversation_id: str, message: Message) -> None:
        """Persist a single message for a conversation."""
        self._messages[conversation_id].append(message)

    def load_messages(self, conversation_id: str, limit: int | None = None) -> Sequence[Message]:
        """Load messages for a conversation."""
        messages = list(self._messages[conversation_id])
        if limit is None:
            return messages
        return messages[-limit:]

    def save_state(self, conversation_id: str, state: dict[str, Any]) -> None:
        """Persist a serializable state snapshot."""
        self._states[conversation_id] = dict(state)

    def load_state(self, conversation_id: str) -> dict[str, Any] | None:
        """Load a previously persisted state snapshot."""
        state = self._states.get(conversation_id)
        return dict(state) if state is not None else None


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{InMemoryStorage().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
