"""Default response humanizer placeholder."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.humanizer.base import BaseHumanizer
from emotion_agent.utils.types import AgentContext, GenerationResult


class ResponseHumanizer(BaseHumanizer):
    """Pass-through response humanizer reserved for future style logic."""

    def humanize(self, context: AgentContext, draft: GenerationResult) -> GenerationResult:
        """Return the draft unchanged as a placeholder."""
        _ = context
        return draft


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{ResponseHumanizer().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
