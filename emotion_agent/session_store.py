"""Persistent session orchestration for chat history, relationship state, and memory paths."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from emotion_agent.state.relationship_state_machine import RelationshipStateMachine
from emotion_agent.storage.file_storage import FileStorage
from emotion_agent.utils.types import Message, SenderRole


@dataclass(slots=True)
class SessionBundle:
    """Runtime session bundle used by the chat server."""

    conversation_id: str
    memory_path: Path
    relationship_machine: RelationshipStateMachine
    chat_history: list[dict[str, Any]]


class SessionStore:
    """Coordinates persistent chat history, state snapshots, and memory files."""

    def __init__(
        self,
        *,
        storage: FileStorage | None = None,
        memory_dir: str | Path = "data/memory",
    ) -> None:
        """Create a persistent session store."""
        self.storage = storage or FileStorage()
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def load(self, conversation_id: str) -> SessionBundle:
        """Load one conversation's persisted history and relationship state."""
        history_messages = self.storage.load_messages(conversation_id)
        state_payload = self.storage.load_state(conversation_id) or {}
        relationship_machine = RelationshipStateMachine(state_payload or None)
        chat_history = [self._message_dict(message) for message in history_messages]
        return SessionBundle(
            conversation_id=conversation_id,
            memory_path=self.memory_dir / f"{conversation_id}.json",
            relationship_machine=relationship_machine,
            chat_history=chat_history,
        )

    def save_history(self, conversation_id: str, chat_history: list[dict[str, Any]]) -> None:
        """Persist the full current history for one conversation."""
        messages = [
            Message(
                role=SenderRole.ASSISTANT if item.get("role") == "assistant" else SenderRole.USER,
                content=str(item.get("content", "")),
                metadata=item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {},
            )
            for item in chat_history
            if str(item.get("content", "")).strip()
        ]
        self.storage.replace_messages(conversation_id, messages)

    def save_state(self, conversation_id: str, state: dict[str, Any]) -> None:
        """Persist the current relationship state snapshot."""
        self.storage.save_state(conversation_id, state)

    def clear_history(self, conversation_id: str) -> None:
        """Clear persisted message history for one conversation."""
        self.storage.clear_messages(conversation_id)

    @staticmethod
    def _message_dict(message: Message) -> dict[str, Any]:
        """Convert a typed message back into the server's history shape."""
        payload: dict[str, Any] = {"role": message.role.value, "content": message.content}
        if message.metadata:
            payload["metadata"] = dict(message.metadata)
        return payload


def _demo() -> None:
    """Run a small module smoke test."""
    store = SessionStore()
    bundle = store.load("demo")
    print(bundle.memory_path.as_posix())


if __name__ == "__main__":
    _demo()
