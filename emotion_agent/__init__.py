"""Top-level package for the WeChat emotion chat agent architecture."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.reply_pipeline import ReplyPipeline, ReplyPipelineResult

__all__ = ["EmotionChatAgent", "ReplyPipeline", "ReplyPipelineResult", "build_default_agent"]


def build_default_agent(*args: object, **kwargs: object) -> object:
    """Build the legacy composed agent lazily to keep package imports lightweight."""
    from emotion_agent.main import build_default_agent as _build_default_agent

    return _build_default_agent(*args, **kwargs)


def __getattr__(name: str) -> object:
    """Load legacy exports lazily so the web pipeline can import cleanly."""
    if name == "EmotionChatAgent":
        from emotion_agent.main import EmotionChatAgent

        return EmotionChatAgent
    raise AttributeError(f"module 'emotion_agent' has no attribute {name!r}")


def _demo() -> None:
    """Run a small import smoke test for the package."""
    agent = build_default_agent()
    print(f"Package ready: {agent.__class__.__name__}")


if __name__ == "__main__":
    _demo()
