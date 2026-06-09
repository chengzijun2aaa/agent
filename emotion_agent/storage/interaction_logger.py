"""Interaction logging for reply selection, edits, feedback, and follow-ups."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field


class InteractionEvent(BaseModel):
    """One JSONL interaction event for product learning."""

    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str
    user_id: str
    turn_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)


class InteractionLogger:
    """File-backed logger for the product feedback loop.

    The logger records generation outputs, copy/selection feedback, edited
    sent text, and the next message received from the other person. This gives
    the project the data needed to improve naturalness and ranking over time.
    """

    def __init__(self, log_dir: str | Path = "data/interaction_logs") -> None:
        """Create a logger rooted at ``log_dir``."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_generation(
        self,
        *,
        user_id: str,
        user_message: str,
        reply: str,
        candidates: list[Mapping[str, Any]],
        diagnostics: Mapping[str, Any],
    ) -> str:
        """Record one generated reply turn and return its turn id."""
        turn_id = uuid.uuid4().hex
        self.log_event(
            InteractionEvent(
                event_type="generation",
                user_id=user_id,
                turn_id=turn_id,
                payload={
                    "user_message": user_message,
                    "reply": reply,
                    "candidates": [dict(candidate) for candidate in candidates],
                    "diagnostics": dict(diagnostics),
                },
            )
        )
        return turn_id

    def log_feedback(
        self,
        *,
        user_id: str,
        turn_id: str | None,
        action: str,
        rating: str | None = None,
        selected_reply: str = "",
        selected_index: int | None = None,
        edited_reply: str = "",
    ) -> str:
        """Record a copy, explicit selection, or good/bad feedback event."""
        was_edited = bool(edited_reply.strip()) and edited_reply.strip() != selected_reply.strip()
        event = InteractionEvent(
            event_type="feedback",
            user_id=user_id,
            turn_id=turn_id,
            payload={
                "action": action,
                "rating": rating or "",
                "selected_reply": selected_reply,
                "selected_index": selected_index,
                "edited_reply": edited_reply,
                "was_edited": was_edited,
            },
        )
        self.log_event(event)
        return event.event_id

    def log_follow_up(self, *, user_id: str, previous_turn_id: str | None, follow_up_message: str) -> str:
        """Record how the other person replied after a generated turn."""
        event = InteractionEvent(
            event_type="follow_up",
            user_id=user_id,
            turn_id=previous_turn_id,
            payload={"follow_up_message": follow_up_message},
        )
        self.log_event(event)
        return event.event_id

    def log_event(self, event: InteractionEvent) -> None:
        """Append one event to the session JSONL log."""
        path = self._path_for(event.user_id)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json())
            handle.write("\n")

    def read_events(self, user_id: str, *, limit: int | None = None) -> list[InteractionEvent]:
        """Read recent events for one user id."""
        path = self._path_for(user_id)
        if not path.exists():
            return []
        rows = [
            InteractionEvent.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return rows[-limit:] if limit is not None else rows

    def _path_for(self, user_id: str) -> Path:
        """Return the JSONL path for one safe user id."""
        safe_id = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fa5]+", "_", user_id.strip() or "default")
        return self.log_dir / f"{safe_id[:64] or 'default'}.jsonl"


def _demo() -> None:
    """Run a small module smoke test."""
    logger = InteractionLogger("data/interaction_demo")
    turn_id = logger.log_generation(
        user_id="demo",
        user_message="你好",
        reply="你好呀",
        candidates=[],
        diagnostics={"intent": "分享生活"},
    )
    logger.log_feedback(user_id="demo", turn_id=turn_id, action="copy", selected_reply="你好呀")
    print(turn_id)


if __name__ == "__main__":
    _demo()
