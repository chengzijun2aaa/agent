"""Generate emotionally intelligent WeChat reply candidates."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import hashlib
import re
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.strategy.strategy_planner import ReplyPlan


class ReplyCandidate(BaseModel):
    """One generated reply candidate."""

    model_config = ConfigDict(extra="ignore")

    text: str
    source: str = "rules"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplyGenerator:
    """Generates varied replies that optimize empathy, authenticity, and attraction."""

    STAGE_DESC: Mapping[str, str] = {
        "L1": "刚认识/陌生：礼貌、低压，不要装熟",
        "L2": "刚认识：友好、轻松，适度打开话题",
        "L3": "熟悉：能接住细节，可以主动延展",
        "L4": "暧昧：俏皮、有在意感，但不过界",
        "L5": "约会后：亲近、有回忆感和下次期待",
        "L6": "恋爱：明确偏爱、安心陪伴",
    }

    def __init__(self, llm: Any | None = None) -> None:
        """Create a reply generator."""
        self.llm = llm

    def generate(
        self,
        chat_history: Sequence[Mapping[str, Any] | str],
        plan: ReplyPlan,
        relationship_state: Mapping[str, Any],
        memory: Mapping[str, Any],
    ) -> list[ReplyCandidate]:
        """Generate reply candidates, preferring LLM output with rule fallback."""
        candidates: list[ReplyCandidate] = []
        if self.llm is not None:
            candidates = self._generate_with_llm(chat_history, plan, relationship_state, memory)
        if not candidates:
            candidates = self._generate_with_rules(chat_history, plan, relationship_state, memory)
        return self._dedupe(candidates)[: plan.candidate_count]

    def _generate_with_llm(
        self,
        chat_history: Sequence[Mapping[str, Any] | str],
        plan: ReplyPlan,
        relationship_state: Mapping[str, Any],
        memory: Mapping[str, Any],
    ) -> list[ReplyCandidate]:
        """Generate replies using an optional LLM provider."""
        prompt = self._build_prompt(chat_history, plan, relationship_state, memory)
        response = self.llm.generate(prompt, temperature=0.85, max_tokens=420)
        if not getattr(response, "success", False) or not getattr(response, "content", ""):
            return []

        candidates: list[ReplyCandidate] = []
        for line in response.content.splitlines():
            text = self._clean_line(line)
            if text:
                candidates.append(ReplyCandidate(text=text, source="llm"))
        return candidates

    def _build_prompt(
        self,
        chat_history: Sequence[Mapping[str, Any] | str],
        plan: ReplyPlan,
        relationship_state: Mapping[str, Any],
        memory: Mapping[str, Any],
    ) -> str:
        """Build a generation prompt that favors natural human chat over polished advice."""
        stage = str(relationship_state.get("stage", "L1"))
        history = self._format_history(chat_history[-12:])
        memory_text = self._memory_summary(memory, self._latest_text(chat_history))
        tactics = "\n".join(f"- {item}" for item in plan.tactics[:4])
        avoid = "\n".join(f"- {item}" for item in plan.avoid[:6])

        return f"""
你在帮人回微信，但最终效果必须像真人自己发的，不像情感导师，不像高情商教程，也不像客服。

请直接生成 6 条候选回复，每条一行，只输出回复本身。

关系阶段：{stage} - {self.STAGE_DESC.get(stage, "自然真诚")}
当前方向：{plan.objective}
整体感觉：{plan.tone}
可用记忆：{memory_text or "无"}

聊天记录：
{history}

只把这些当隐性参考，不要复述：
{tactics}

必须避免：
{avoid}
- 不要像咨询师：少用“先”“你可以”“你值得”“我理解你的情绪”。
- 不要像教程：少用“接住”“提供情绪价值”“建立舒适感”这类词。
- 不要像公关话术：少用完整闭环句和太工整的排比。
- 不要油，不要端着，不要查岗，不要拿腔拿调。

输出要求：
1. 像真实微信，允许不完整句，允许口语，允许留白。
2. 优先短句，长度尽量 4 到 20 个字，最多不要超过 26 个字。
3. 候选要有区别，但都要像同一个人会说的话。
4. 不要每句都很会聊，允许一点自然、随口、甚至轻微笨拙。
5. 不要编号，不要解释。
""".strip()

    @staticmethod
    def _generate_with_rules(
        chat_history: Sequence[Mapping[str, Any] | str],
        plan: ReplyPlan,
        relationship_state: Mapping[str, Any],
        memory: Mapping[str, Any],
    ) -> list[ReplyCandidate]:
        """Generate varied deterministic fallback replies."""
        latest = ReplyGenerator._latest_text(chat_history)
        stage = str(relationship_state.get("stage", "L1"))
        memory_hint = ReplyGenerator._memory_hint(memory, latest)
        lower = latest.lower()

        if ReplyGenerator._is_greeting(lower):
            base = ReplyGenerator._greeting_pool(stage)
        elif "你在干嘛" in latest or "在干嘛" in latest:
            base = ReplyGenerator._what_doing_pool(stage)
        elif any(word in latest for word in ("累", "压力", "加班", "烦", "崩溃", "难受")):
            base = [
                "听着就挺耗你的，先缓一口气",
                "辛苦了，今天别硬撑太久",
                "这事确实烦，先让我站你这边",
                "你先说，我听着呢",
                "今天这波对你不太友好啊",
                "抱抱，先把这口气顺下来",
            ]
        elif any(word in latest for word in ("猫", "狗", "宠物", "拆家")):
            pet = memory_hint or "小家伙"
            base = [
                f"{pet}今天又开始营业了是吧",
                "它这是把家当游乐场了吧",
                "听着又气又想笑",
                "你现在是铲屎官受害者现场吗",
                "它拆家，你负责善后，太辛苦了",
                "给我看看案发现场我判断一下",
            ]
        elif any(word in latest for word in ("出来", "见面", "吃饭", "电影", "周末", "有空")):
            base = [
                "可以啊，周末哪天",
                "行啊，吃什么",
                "这个我可以赴约",
                "你都开口了，那就去",
                "可以，地点你挑",
                "那别光说说，定一下",
            ]
        elif any(word in latest for word in ("别的女生", "她是谁", "他是谁", "还聊", "和别人")):
            base = [
                "你这句怎么有点酸",
                "没有，别乱想",
                "你这是在吃味吗",
                "真没有你想的那样",
                "我主要还是在回你",
                "这锅我先不认",
            ]
        elif any(word in latest for word in ("是不是", "你会不会", "你是不是", "在不在意")):
            base = [
                "你这是在试探我吗",
                "在意啊，只是不想说太满",
                "你问这么认真，我也认真点",
                "我没敷衍你，这个你放心",
                "你想听真话还是漂亮话",
                "这题答不好要扣分是吧",
            ]
        elif plan.emotional_need == "空间感和低压力":
            base = [
                "行，那你先忙，不吵你",
                "没事，你方便了再回我",
                "我不催你，先把你的事处理好",
                "收到，我先安静一会儿",
                "好，你先缓缓",
                "不用急着回，我在",
            ]
        else:
            base = ReplyGenerator._general_pool(stage)

        offset = ReplyGenerator._stable_offset(latest + stage)
        rotated = base[offset:] + base[:offset]
        return [ReplyCandidate(text=text, source="rules", metadata={"objective": plan.objective}) for text in rotated]

    @staticmethod
    def _greeting_pool(stage: str) -> list[str]:
        """Return greeting replies by stage."""
        if stage in {"L4", "L5", "L6"}:
            return [
                "你来得刚好",
                "终于出现了啊",
                "嗨，今天想我没",
                "刚好想找你来着",
                "你这一声我收到了",
                "在呢，今天过得怎么样",
            ]
        return [
            "你好呀",
            "嗨，刚看到",
            "在呢，你好",
            "你好，今天怎么样",
            "来了，怎么说",
            "嗨，找我聊会儿吗",
        ]

    @staticmethod
    def _what_doing_pool(stage: str) -> list[str]:
        """Return replies for 'what are you doing' by stage."""
        if stage in {"L4", "L5", "L6"}:
            return [
                "在想怎么回你才不明显",
                "刚忙完，正好等到你",
                "在被你这句话叫出来",
                "本来在忙，现在注意力跑你那了",
                "在想你怎么突然查岗",
                "在呢，你是不是想我了",
            ]
        if stage == "L3":
            return [
                "刚忙完，准备歇会儿",
                "在处理点事，你呢",
                "刚看手机，你那边呢",
                "在摸鱼，你别举报我",
                "刚停下来，怎么啦",
                "在呢，说说你那边",
            ]
        return [
            "刚忙完，准备歇会儿",
            "在处理点事，你呢",
            "刚看到消息，怎么啦",
            "在呢，你那边忙完了吗",
            "刚停下来，你呢",
            "没干嘛，正好可以聊两句",
        ]

    @staticmethod
    def _general_pool(stage: str) -> list[str]:
        """Return general replies by stage."""
        if stage in {"L4", "L5", "L6"}:
            return [
                "你这句还挺会挑时候",
                "你怎么突然冒出来了",
                "这话我得想两秒",
                "行，你继续",
                "你这样说我会多想",
                "那我听你往下说",
            ]
        return [
            "然后呢",
            "你继续",
            "有点意思",
            "那后来呢",
            "你这句展开说说",
            "原来是这样",
        ]

    @staticmethod
    def _is_greeting(text: str) -> bool:
        """Return whether latest text is a greeting."""
        normalized = re.sub(r"\s+", "", text.lower())
        return normalized in {"你好", "nihao", "hello", "hi", "嗨", "哈喽"}

    @staticmethod
    def _format_history(chat_history: Sequence[Mapping[str, Any] | str]) -> str:
        """Format recent chat history for prompting."""
        lines: list[str] = []
        for item in chat_history:
            if isinstance(item, str):
                lines.append(f"她：{item}")
            else:
                role = str(item.get("role", "user"))
                speaker = "我" if role in {"assistant", "boy", "me"} else "她"
                content = str(item.get("content", item.get("text", item.get("message", ""))))
                lines.append(f"{speaker}：{content}")
        return "\n".join(lines)

    @staticmethod
    def _memory_summary(memory: Mapping[str, Any], latest: str) -> str:
        """Summarize memory only when it is contextually useful."""
        parts: list[str] = []
        pets = memory.get("pets", [])
        if pets and any(word in latest for word in ("猫", "狗", "宠物", "拆家")) and isinstance(pets[0], Mapping):
            pet = pets[0]
            parts.append(f"她养了{pet.get('breed') or pet.get('species') or '宠物'}")
        interests = memory.get("interests", [])
        if interests:
            parts.append("兴趣：" + "、".join(str(item) for item in interests[:2]))
        return "；".join(parts) if parts else "无"

    @staticmethod
    def _memory_hint(memory: Mapping[str, Any], latest: str) -> str:
        """Return a short memory hint for rule replies."""
        pets = memory.get("pets", [])
        if pets and any(word in latest for word in ("猫", "狗", "宠物", "拆家")) and isinstance(pets[0], Mapping):
            return str(pets[0].get("breed") or pets[0].get("species") or "")
        return ""

    @staticmethod
    def _clean_line(line: str) -> str:
        """Clean one LLM output line."""
        text = re.sub(r"^\s*[-*\d.、）)]+\s*", "", line).strip()
        text = text.strip("\"'“”")
        text = text.replace("您", "你")
        text = re.sub(r"\s+", " ", text)
        return text[:48].rstrip("，,。 ")

    @staticmethod
    def _dedupe(candidates: Sequence[ReplyCandidate]) -> list[ReplyCandidate]:
        """Deduplicate candidates by normalized text."""
        seen: set[str] = set()
        result: list[ReplyCandidate] = []
        for candidate in candidates:
            text = candidate.text.strip()
            key = re.sub(r"\W+", "", text.lower())
            if not text or key in seen:
                continue
            seen.add(key)
            result.append(candidate.model_copy(update={"text": text}))
        return result

    @staticmethod
    def _stable_offset(value: str) -> int:
        """Return a deterministic rotation offset for fallback variety."""
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
        return int(digest[:2], 16) % 6

    @staticmethod
    def _latest_text(chat_history: Sequence[Mapping[str, Any] | str]) -> str:
        """Return latest chat content."""
        if not chat_history:
            return ""
        latest = chat_history[-1]
        if isinstance(latest, str):
            return latest
        return str(latest.get("content", latest.get("text", latest.get("message", ""))))


def _demo() -> None:
    """Run a small module smoke test."""
    plan = ReplyPlan(objective="自然回复", tone="轻松")
    replies = ReplyGenerator().generate(["你在干嘛"], plan, {"stage": "L4"}, {})
    print([reply.text for reply in replies])


if __name__ == "__main__":
    _demo()
