"""Ranking components for selecting a final response."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.ranker.base import BaseRanker
from emotion_agent.ranker.reply_ranker import ReplyRanker, ReplyScore
from emotion_agent.ranker.response_ranker import ResponseRanker

__all__ = ["BaseRanker", "ReplyRanker", "ReplyScore", "ResponseRanker"]


def _demo() -> None:
    """Run a small package smoke test."""
    print("Ranker package ready")


if __name__ == "__main__":
    _demo()
