"""Emotional state model."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from dataclasses import dataclass

from emotion_agent.utils.types import EmotionLabel


@dataclass(slots=True)
class EmotionalState:
    """Represents the current inferred emotional state for a conversation."""

    label: EmotionLabel = EmotionLabel.UNKNOWN
    intensity: float = 0.0
    confidence: float = 0.0

    @classmethod
    def empty(cls) -> "EmotionalState":
        """Create an empty emotional state."""
        return cls()


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{EmotionalState.empty().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
