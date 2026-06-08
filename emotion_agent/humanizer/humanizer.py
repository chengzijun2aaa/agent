"""Response Humanizer - concise, natural WeChat wording."""

from __future__ import annotations

import random
import re

from typing import Any, Sequence

from emotion_agent.generator.reply_generator import ReplyCandidate
from emotion_agent.humanizer.base import BaseHumanizer
from emotion_agent.utils.types import AgentContext, GenerationResult


class ResponseHumanizer(BaseHumanizer):
    """Turn generated drafts into short, natural WeChat-style replies."""

    def humanize(self, context: AgentContext, draft: GenerationResult) -> GenerationResult:
        text = draft.text.strip()
        if not text:
            text = "嗯？"
        serious = self._is_serious_reply(text)

        text = self._remove_therapist_tone(text)
        serious = serious or self._is_serious_reply(text)
        text = self._add_colloquial_rhythm(text, serious=serious)
        text = self._add_imperfection(text, serious=serious)
        text = self._shorten_if_needed(text)

        return GenerationResult(text=text.strip(), provider=draft.provider, metadata=draft.metadata)

    def _remove_therapist_tone(self, text: str) -> str:
        """Remove common therapist/assistant phrasing."""
        replacements = [
            ("我理解", "懂"),
            ("你的情绪", ""),
            ("先缓一口气", "先喘口气"),
            ("你可以", "你就"),
            ("辛苦了", "辛苦"),
            ("我听着呢", "说"),
            ("我懂你", "懂"),
            ("提供支持", ""),
            ("情绪价值", ""),
            ("慢慢说", "继续"),
            ("别太难过", "别想太多"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    def _add_colloquial_rhythm(self, text: str, *, serious: bool = False) -> str:
        """Add light colloquial rhythm without changing meaning."""
        if len(text) > 35 and random.random() > 0.6:
            # 随机断句
            if "，" in text:
                parts = text.split("，", 1)
                filler = "" if serious else random.choice(["", "哈，"])
                text = parts[0] + "，" + filler + parts[1]
        
        return text

    def _add_imperfection(self, text: str, *, serious: bool = False) -> str:
        """Add small imperfections while avoiding semantic corruption."""
        tricks = [
            lambda t: t.rstrip("。！？") + "…" if random.random() > 0.75 else t,
            lambda t: t if serious and len(t) < 30 else t,
            lambda t: t.replace("真的", "真") if "真的" in t else t,
        ]
        
        for trick in tricks:
            if random.random() > 0.65:
                text = trick(text)
        
        return text

    def _shorten_if_needed(self, text: str) -> str:
        """强制短 + 松"""
        if len(text) > 38:
            text = text[:38].rstrip("，。、 ") + random.choice(["…", "", ""])
        return text.strip()

    @staticmethod
    def _is_serious_reply(text: str) -> bool:
        """Return whether a reply is handling stress, sadness, or support."""
        serious_words = (
            "累",
            "难受",
            "委屈",
            "压力",
            "烦",
            "硬撑",
            "喘口气",
            "站你",
            "我听着",
            "别自己扛",
            "这时候",
            "吃醋",
            "放心",
            "查我岗",
            "别的女生",
            "别的女人",
            "哄你",
            "带你缓缓",
            "去缓缓",
            "补回来",
            "记着",
            "靠我",
            "先说",
        )
        return any(word in text for word in serious_words)


class Humanizer:
    """Compatibility adapter used by the reply pipeline.

    The newer ``ResponseHumanizer`` works on one ``GenerationResult`` inside
    the legacy agent path. The web reply pipeline still passes a list of
    ``ReplyCandidate`` objects, so this adapter keeps that path startable.
    """

    def __init__(self) -> None:
        self.response_humanizer = ResponseHumanizer()

    def humanize(self, candidates: Sequence[ReplyCandidate]) -> list[ReplyCandidate]:
        """Humanize reply candidates while preserving their metadata."""
        return [self._humanize_candidate(candidate) for candidate in candidates]

    def _humanize_candidate(self, candidate: ReplyCandidate) -> ReplyCandidate:
        """Humanize one reply candidate."""
        draft = GenerationResult(text=candidate.text, metadata=candidate.metadata)
        context = AgentContext(
            user_id="pipeline",
            current_message=ReplyCandidateCompatibility.message(candidate.text),
            recent_messages=[],
            state={},
        )
        result = self.response_humanizer.humanize(context=context, draft=draft)
        return candidate.model_copy(update={"text": result.text})


class ReplyCandidateCompatibility:
    """Small helper to avoid importing extra pipeline context objects elsewhere."""

    @staticmethod
    def message(text: str) -> Any:
        """Create the minimal message object required by ``AgentContext``."""
        from emotion_agent.utils.types import Message, SenderRole

        return Message(role=SenderRole.ASSISTANT, content=text)


def _demo() -> None:
    from emotion_agent.utils.types import Message, SenderRole, GenerationResult, AgentContext
    humanizer = ResponseHumanizer()
    
    draft = GenerationResult(text="我理解你现在很难受，先缓一口气，我会一直陪着你的。")
    context = AgentContext(
        user_id="test",
        current_message=Message(role=SenderRole.USER, content="今天好累想哭"),
        recent_messages=[],
        state={}
    )
    
    result = humanizer.humanize(context, draft)
    print(result.text)


if __name__ == "__main__":
    _demo()
