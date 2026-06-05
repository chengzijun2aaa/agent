"""Conversation state aggregate."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from dataclasses import dataclass, field
from typing import Any

from emotion_agent.state.emotional_state import EmotionalState
from emotion_agent.state.session_state import SessionState


@dataclass(slots=True)
class ConversationState:
    """Aggregates session, emotional, and workflow state for one conversation."""

    session: SessionState
    emotion: EmotionalState
    attributes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, user_id: str | None = None) -> "ConversationState":
        """Create a new conversation state aggregate."""
        return cls(session=SessionState.new(user_id=user_id), emotion=EmotionalState.empty())

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable state snapshot for storage boundaries."""
        return {
            "session_id": self.session.session_id,
            "user_id": self.session.user_id,
            "message_count": self.session.message_count,
            "emotion": self.emotion.label.value,
            "attributes": dict(self.attributes),
        }


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{ConversationState.new().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
