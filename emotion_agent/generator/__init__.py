"""Generation components for creating draft responses."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.generator.base import BaseGenerator
from emotion_agent.generator.reply_generator import ReplyCandidate, ReplyGenerator
from emotion_agent.generator.response_generator import ResponseGenerator

__all__ = ["BaseGenerator", "ReplyCandidate", "ReplyGenerator", "ResponseGenerator"]


def _demo() -> None:
    """Run a small package smoke test."""
    print("Generator package ready")


if __name__ == "__main__":
    _demo()
