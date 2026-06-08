"""Humanize generated replies into WeChat-like text."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import re
from typing import Sequence

from emotion_agent.generator.reply_generator import ReplyCandidate


class Humanizer:
    """Makes candidate replies shorter, warmer, and more WeChat-like."""

    STIFF_PATTERNS: tuple[tuple[str, str], ...] = (
        ("我理解你的情绪", "懂你这会儿的感觉"),
        ("先缓一口气", "先喘口气"),
        ("你可以", "你就"),
        ("辛苦了，今天别硬撑太久", "辛苦了，别再死撑"),
        ("我在意，只是不想说得太夸张", "在意啊，只是不想说太满"),
        ("我没有敷衍你，这点你可以放心", "我没敷衍你，这个你放心"),
    )

    def humanize(self, candidates: Sequence[ReplyCandidate]) -> list[ReplyCandidate]:
        """Humanize a sequence of candidates."""
        return [candidate.model_copy(update={"text": self._humanize_text(candidate.text)}) for candidate in candidates]

    def _humanize_text(self, text: str) -> str:
        """Humanize one reply string."""
        cleaned = re.sub(r"\s+", " ", text).strip()
        cleaned = cleaned.replace("您", "你")
        cleaned = cleaned.replace("请你", "你可以")
        for before, after in self.STIFF_PATTERNS:
            cleaned = cleaned.replace(before, after)
        cleaned = cleaned.replace("我会认真想", "我还真会多想")
        cleaned = cleaned.replace("听起来", "")
        cleaned = cleaned.replace("确实", "是挺")
        cleaned = re.sub(r"(你继续说，我在听|我在，慢慢说)", "你继续", cleaned)
        cleaned = cleaned.rstrip("。")
        if len(cleaned) > 42:
            cleaned = cleaned[:42].rstrip("，,、 ") + "..."
        cleaned = cleaned.strip("，, ")
        return cleaned


def _demo() -> None:
    """Run a small module smoke test."""
    print(Humanizer().humanize([ReplyCandidate(text="您好，请你不要太难过。")])[0].text)


if __name__ == "__main__":
    _demo()
