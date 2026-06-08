"""File-backed storage adapter for chat messages and state snapshots."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from emotion_agent.storage.base import BaseStorage
from emotion_agent.utils.exceptions import StorageError
from emotion_agent.utils.types import Message, SenderRole


class FileStorage(BaseStorage):
    """Persist session messages and state snapshots as JSON files."""

    def __init__(self, data_dir: str | Path = "data/sessions") -> None:
        """Create a file-backed storage rooted at ``data_dir``."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save_message(self, conversation_id: str, message: Message) -> None:
        """Append one message to the persisted conversation record."""
        payload = self._load_payload(conversation_id)
        messages = payload.setdefault("messages", [])
        messages.append(self._message_to_dict(message))
        self._save_payload(conversation_id, payload)

    def load_messages(self, conversation_id: str, limit: int | None = None) -> Sequence[Message]:
        """Load persisted messages for one conversation."""
        payload = self._load_payload(conversation_id)
        items = payload.get("messages", [])
        messages = [self._message_from_dict(item) for item in items if isinstance(item, dict)]
        return messages[-limit:] if limit is not None else messages

    def save_state(self, conversation_id: str, state: dict[str, Any]) -> None:
        """Persist a serializable state snapshot."""
        payload = self._load_payload(conversation_id)
        payload["state"] = dict(state)
        self._save_payload(conversation_id, payload)

    def load_state(self, conversation_id: str) -> dict[str, Any] | None:
        """Load a previously persisted state snapshot."""
        payload = self._load_payload(conversation_id)
        state = payload.get("state")
        return dict(state) if isinstance(state, dict) else None

    def replace_messages(self, conversation_id: str, messages: Sequence[Message]) -> None:
        """Replace the full persisted message list for one conversation."""
        payload = self._load_payload(conversation_id)
        payload["messages"] = [self._message_to_dict(message) for message in messages]
        self._save_payload(conversation_id, payload)

    def clear_messages(self, conversation_id: str) -> None:
        """Remove persisted chat history while preserving state snapshots."""
        payload = self._load_payload(conversation_id)
        payload["messages"] = []
        self._save_payload(conversation_id, payload)

    def _path_for(self, conversation_id: str) -> Path:
        """Resolve the on-disk JSON file path for one conversation."""
        safe_id = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fa5]+", "_", conversation_id.strip() or "default")
        return self.data_dir / f"{safe_id[:64] or 'default'}.json"

    def _load_payload(self, conversation_id: str) -> dict[str, Any]:
        """Read one conversation payload from disk."""
        path = self._path_for(conversation_id)
        if not path.exists():
            return {"messages": [], "state": {}}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Failed to load session file: {path}") from exc
        if not isinstance(raw, dict):
            return {"messages": [], "state": {}}
        raw.setdefault("messages", [])
        raw.setdefault("state", {})
        return raw

    def _save_payload(self, conversation_id: str, payload: dict[str, Any]) -> None:
        """Write one conversation payload to disk."""
        path = self._path_for(conversation_id)
        try:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Failed to save session file: {path}") from exc

    @staticmethod
    def _message_to_dict(message: Message) -> dict[str, Any]:
        """Serialize a ``Message`` dataclass into JSON-friendly data."""
        payload = asdict(message)
        payload["role"] = message.role.value
        payload["timestamp"] = message.timestamp.isoformat()
        return payload

    @staticmethod
    def _message_from_dict(payload: dict[str, Any]) -> Message:
        """Deserialize one stored message payload."""
        timestamp = payload.get("timestamp")
        parsed_timestamp = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else datetime.now()
        return Message(
            role=SenderRole(str(payload.get("role", SenderRole.USER.value))),
            content=str(payload.get("content", "")),
            timestamp=parsed_timestamp,
            metadata=payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {},
        )


def _demo() -> None:
    """Run a small module smoke test."""
    storage = FileStorage("data/session_demo")
    storage.clear_messages("demo")
    storage.save_state("demo", {"stage": "L1"})
    print(storage.load_state("demo"))


if __name__ == "__main__":
    _demo()
