"""Top-level package for the WeChat emotion chat agent architecture."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.main import EmotionChatAgent, build_default_agent
from emotion_agent.reply_pipeline import ReplyPipeline, ReplyPipelineResult

__all__ = ["EmotionChatAgent", "ReplyPipeline", "ReplyPipelineResult", "build_default_agent"]


def _demo() -> None:
    """Run a small import smoke test for the package."""
    agent = build_default_agent()
    print(f"Package ready: {agent.__class__.__name__}")


if __name__ == "__main__":
    _demo()
