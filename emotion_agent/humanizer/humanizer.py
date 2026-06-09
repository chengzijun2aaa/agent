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
            return GenerationResult(text="嗯？", provider=draft.provider, metadata=draft.metadata)

        # 1. 基础防护：彻底洗掉大模型附带的任何 Markdown 乱码痕迹
        text = self._strip_markdown_and_junk(text)

        # 2. 判断语境严肃度
        serious = self._is_serious_reply(text)

        # 3. 去除客服/心理医生味
        text = self._remove_therapist_tone(text)
        serious = serious or self._is_serious_reply(text)

        # 4. 灵魂注入：模拟微信聊天的高级语气助词与节奏
        text = self._add_colloquial_rhythm(text, serious=serious)
        text = self._add_imperfection(text, serious=serious)

        # 5. 安全字数控制：坚决不使用硬截断，而是优雅地进行句子裁剪
        text = self._smart_length_control(text, max_len=38)

        # 6. 收尾清理：拿掉死板的句末标点，微信聊天不发句号
        text = self._strip_trailing_punctuation(text)

        return GenerationResult(text=text.strip(), provider=draft.provider, metadata=draft.metadata)

    def _strip_markdown_and_junk(self, text: str) -> str:
        """Strip markdown markers, accidental quotes, or trailing spacing tags."""
        text = re.sub(r"\*\*|\*|#|`|__", "", text)  # 去除粗体、斜体、代码块标记
        text = re.sub(r'^[“\"\'「]|[\"\'」]$', "", text)  # 去除 LLM 偶尔喜欢带上的首尾双引号
        return text.strip()

    def _remove_therapist_tone(self, text: str) -> str:
        """Remove common therapist/assistant phrasing with precise mapping."""
        replacements = [
            ("我理解你", "我懂"),
            ("我理解", "懂"),
            ("你的情绪", ""),
            ("先缓一口气", "先喘口气"),
            ("你可以", "你就"),
            ("辛苦了", "辛苦啦"),
            ("我听着呢", "说吧"),
            ("我懂你", "懂"),
            ("提供支持", ""),
            ("情绪价值", ""),
            ("慢慢说", "继续"),
            ("别太难过", "别想太多"),
            ("发生什么了", "咋啦"),
            ("怎么了", "咋啦"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    def _add_colloquial_rhythm(self, text: str, *, serious: bool = False) -> str:
        """Add light colloquial rhythm without damaging structure."""
        if serious:
            return text

        # 替换死板的“真的”为口语化的“真”，用正则确保前后是词边界或特定结构
        # 规避“你是真的皮” -> “你是真皮” 的尴尬
        if "真的" in text and not any(p in text for p in ["真的皮", "真的牛", "真的好"]):
            if random.random() > 0.5:
                text = text.replace("真的", "真", 1)

        # 太长的句子随机插入轻量口语衬字
        if len(text) > 25 and random.random() > 0.7:
            if "，" in text:
                parts = text.split("，", 1)
                filler = random.choice(["哈，", "其实 ", "感觉 "])
                text = f"{parts[0]}，{filler}{parts[1]}"
        
        return text

    def _add_imperfection(self, text: str, *, serious: bool = False) -> str:
        """Add organic human elements while strictly avoiding multi-ellipse clutter."""
        # 已经有省略号了，不要再叠 buff
        if "…" in text or "..." in text:
            return text

        # 严肃或委屈语境下，末尾极低概率加单个波浪号或者省略号模拟语气拉长
        if serious and random.random() > 0.8:
            text = text.rstrip("。！？， ") + "…"
        elif not serious and random.random() > 0.85:
            # 快乐或者闲聊语境，偶尔加哈
            if not text.endswith(("哈", "吧", "呀", "呢")):
                text = text.rstrip("。！？， ") + "哈"
                
        return text

    def _smart_length_control(self, text: str, max_len: int = 38) -> str:
        """智能长度控制：绝不硬生生截断词语，而是按标点吃掉最后半句。"""
        if len(text) <= max_len:
            return text

        # 使用常见的聊天切分标点拆分句子
        punctuations = r"[，。！？、；…\s]"
        parts = re.split(f"({punctuations})", text)
        
        current_text = ""
        for i in range(0, len(parts), 2):
            segment = parts[i]
            punc = parts[i+1] if i+1 < len(parts) else ""
            
            # 如果加上下一段会爆字数，就地斩断，放弃后续语义，确保发出去的最后一句是完整的
            if len(current_text) + len(segment) + len(punc) > max_len:
                if not current_text:
                    # 如果第一句本身就极长（罕见），被迫硬截
                    return text[:max_len].rstrip(punctuations)
                break
            current_text += segment + punc

        return current_text.strip()

    def _strip_trailing_punctuation(self, text: str) -> str:
        """微信聊天的灵魂：洗掉死板的结尾句号，保留情绪化的问号或叹号。"""
        # 拿掉尾部所有死板的 句号、逗号、分号
        text = re.sub(r"[。，,；;]\s*$", "", text)
        
        # 归一化连续的问号/叹号，防止大模型抽风喷出 “？？？？？？” 显得太具有攻击性
        text = re.sub(r"？{2,}", "？？", text)
        text = re.sub(r"！{2,}", "！！", text)
        return text.strip()

    @staticmethod
    def _is_serious_reply(text: str) -> bool:
        """Return whether a reply is handling stress, sadness, or support."""
        serious_words = (
            "累", "难受", "委屈", "压力", "烦", "硬撑", "喘口气", "站你", 
            "我听着", "别自己扛", "这时候", "吃醋", "放心", "查我岗", 
            "别的女生", "别的女人", "哄你", "带你缓缓", "去缓缓", 
            "补回来", "记着", "靠我", "先说", "抱抱", "摸头",
        )
        return any(word in text for word in serious_words)


class Humanizer:
    """Compatibility adapter used by the reply pipeline."""

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
    from emotion_agent.utils.types import AgentContext, GenerationResult, Message, SenderRole
    humanizer = ResponseHumanizer()
    
    # 测试 1：高危强力客服腔 + 句号测试
    draft_1 = GenerationResult(text="**我理解你现在很难受**，先缓一口气，我会一直提供支持并在你身边慢慢说的。")
    context_1 = AgentContext(
        user_id="test",
        current_message=Message(role=SenderRole.USER, content="今天好累想哭"),
        recent_messages=[],
        state={}
    )
    print("测试 1 (客服腔清洗) ->:", humanizer.humanize(context_1, draft_1).text)

    # 测试 2：智能字数控制（拒绝硬截断词语）
    long_text = "我也觉得这家店的环境一般般，不过隔壁新开的那家港式火锅好像还可以，我们明天晚上一起去尝尝吧！"
    draft_2 = GenerationResult(text=long_text)
    print("测试 2 (拒绝硬断句) ->:", humanizer.humanize(context_1, draft_2).text)


if __name__ == "__main__":
    _demo()