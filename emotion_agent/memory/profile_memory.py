"""User profile memory implementation."""

from __future__ import annotations

from typing import Any, Mapping


class ProfileMemory:
    """Stores long-lived user profile attributes behind a small object boundary."""

    def __init__(self) -> None:
        """Create an empty profile memory."""
        self._profile: dict[str, Any] = {}

    def update(self, values: Mapping[str, Any]) -> None:
        """Merge profile attributes into memory."""
        self._profile.update(values)

    def get(self, key: str, default: Any | None = None) -> Any:
        """Read one profile attribute by key."""
        return self._profile.get(key, default)

    def snapshot(self) -> dict[str, Any]:
        """Return a shallow copy of the current profile."""
        return dict(self._profile)

    def clear(self) -> None:
        """Clear all stored profile attributes."""
        self._profile.clear()


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{ProfileMemory().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
