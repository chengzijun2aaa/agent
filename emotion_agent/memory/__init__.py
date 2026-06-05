"""Memory components for conversation and user profile state."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.memory.base import BaseMemory
from emotion_agent.memory.conversation_memory import ConversationMemory
from emotion_agent.memory.memory_manager import (
    MemoryExtraction,
    MemoryFact,
    MemoryManager,
    MemorySearchResult,
    MemoryStore,
    PetMemory,
    UserMemory,
)
from emotion_agent.memory.profile_memory import ProfileMemory

__all__ = [
    "BaseMemory",
    "ConversationMemory",
    "MemoryExtraction",
    "MemoryFact",
    "MemoryManager",
    "MemorySearchResult",
    "MemoryStore",
    "PetMemory",
    "ProfileMemory",
    "UserMemory",
]


def _demo() -> None:
    """Run a small package smoke test."""
    print("Memory package ready")


if __name__ == "__main__":
    _demo()
