"""Session state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(slots=True)
class SessionState:
    """Tracks identifiers and lifecycle timestamps for a chat session."""

    session_id: str
    user_id: str | None = None
    message_count: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def new(cls, user_id: str | None = None) -> "SessionState":
        """Create a new session state with generated identifiers."""
        return cls(session_id=str(uuid4()), user_id=user_id)

    def touch(self) -> None:
        """Refresh update timestamp and increment the message counter."""
        self.message_count += 1
        self.updated_at = datetime.now(timezone.utc)


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{SessionState.new().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
