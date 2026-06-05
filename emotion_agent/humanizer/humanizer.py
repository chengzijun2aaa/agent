"""Humanize generated replies into WeChat-like text."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import re
from typing import Sequence

from emotion_agent.generator.reply_generator import ReplyCandidate


class Humanizer:
    """Makes candidate replies shorter, warmer, and more WeChat-like."""

    def humanize(self, candidates: Sequence[ReplyCandidate]) -> list[ReplyCandidate]:
        """Humanize a sequence of candidates."""
        return [candidate.model_copy(update={"text": self._humanize_text(candidate.text)}) for candidate in candidates]

    def _humanize_text(self, text: str) -> str:
        """Humanize one reply string."""
        cleaned = re.sub(r"\s+", " ", text).strip()
        cleaned = cleaned.replace("您", "你")
        cleaned = cleaned.replace("请你", "你可以")
        cleaned = cleaned.rstrip("。")
        if len(cleaned) > 42:
            cleaned = cleaned[:42].rstrip("，,、 ") + "..."
        return cleaned


def _demo() -> None:
    """Run a small module smoke test."""
    print(Humanizer().humanize([ReplyCandidate(text="您好，请你不要太难过。")])[0].text)


if __name__ == "__main__":
    _demo()
