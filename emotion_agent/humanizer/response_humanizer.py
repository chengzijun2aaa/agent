"""Response Humanizer - 真实微信去AI味"""

from __future__ import annotations

import random
import re

from emotion_agent.humanizer.base import BaseHumanizer
from emotion_agent.utils.types import AgentContext, GenerationResult


class ResponseHumanizer(BaseHumanizer):
    """把AI回复变成真实男人随手发的微信"""

    def humanize(self, context: AgentContext, draft: GenerationResult) -> GenerationResult:
        text = (draft.text or "").strip()
        if not text:
            text = "嗯？"

        text = self._remove_ai_tone(text)
        text = self._add_rhythm(text)
        text = self._add_imperfection(text)
        text = self._shorten(text)

        draft.text = text.strip()
        return draft

    def _remove_ai_tone(self, text: str) -> str:
        replacements = [
            ("我理解", "懂"),
            ("你的情绪", ""),
            ("先缓一口气", "喘口气"),
            ("你可以", "你就"),
            ("我听着呢", "说"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    def _add_rhythm(self, text: str) -> str:
        if random.random() > 0.6 and len(text) > 18:
            text = text.replace("，", "，", 1)
        if random.random() > 0.7 and not any(text.endswith(c) for c in "？！…哈嗯"):
            text += random.choice(["，嗯", "，哈", ""])
        return text

    def _add_imperfection(self, text: str) -> str:
        if random.random() > 0.7:
            text = text.rstrip("。！？") + "…"
        return text

    def _shorten(self, text: str) -> str:
        if len(text) > 40:
            text = text[:38].rstrip("，。 ") + "…"
        return text


if __name__ == "__main__":
    print("Humanizer loaded successfully")
