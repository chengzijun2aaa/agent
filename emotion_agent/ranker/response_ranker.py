"""Default response ranker placeholder."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Sequence

from emotion_agent.ranker.base import BaseRanker
from emotion_agent.utils.types import AgentContext, GenerationResult, RankedResponse


class ResponseRanker(BaseRanker):
    """Selects a final response candidate behind a ranker boundary."""

    def rank(self, context: AgentContext, candidates: Sequence[GenerationResult]) -> RankedResponse:
        """Return the first candidate as a placeholder ranking result."""
        _ = context
        selected = candidates[0] if candidates else GenerationResult.empty()
        return RankedResponse(result=selected, score=0.0, reason="placeholder")


def _demo() -> None:
    """Run a small module smoke test."""
    print(f"{ResponseRanker().__class__.__name__} ready")


if __name__ == "__main__":
    _demo()
