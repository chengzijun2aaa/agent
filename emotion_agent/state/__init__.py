"""State objects for sessions, emotions, and conversations."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.state.conversation_state import ConversationState
from emotion_agent.state.emotional_state import EmotionalState
from emotion_agent.state.relationship_state_machine import (
    RelationshipStage,
    RelationshipState,
    RelationshipStateMachine,
)
from emotion_agent.state.session_state import SessionState

__all__ = [
    "ConversationState",
    "EmotionalState",
    "RelationshipStage",
    "RelationshipState",
    "RelationshipStateMachine",
    "SessionState",
]


def _demo() -> None:
    """Run a small package smoke test."""
    print("State package ready")


if __name__ == "__main__":
    _demo()
