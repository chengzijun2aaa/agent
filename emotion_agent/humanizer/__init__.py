"""Humanization components for polishing generated responses."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.humanizer.base import BaseHumanizer
from emotion_agent.humanizer.humanizer import Humanizer
from emotion_agent.humanizer.response_humanizer import ResponseHumanizer

__all__ = ["BaseHumanizer", "Humanizer", "ResponseHumanizer"]


def _demo() -> None:
    """Run a small package smoke test."""
    print("Humanizer package ready")


if __name__ == "__main__":
    _demo()
