"""Generate candidate WeChat replies from a reply plan with advanced preprocessing and humanization."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Any, Mapping, Sequence
import re
from pydantic import BaseModel, ConfigDict, Field

class ReplyPlan(BaseModel):
    """Strategy input from upper planner."""
    objective: str = "自然回复"
    tone: str = "轻松"
    candidate_count: int = 6  # 提升至6条候选
    tactics: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class ReplyCandidate(BaseModel):
    """One generated reply candidate."""
    model_config = ConfigDict(extra="ignore")

    text: str
    source: str = "rules"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplyGenerator:
    """Generates six candidate replies with LLM formatting and humanized fallback."""

    STAGE_DESC = {
        "L1": "刚认识",
        "L2": "认识不久",
        "L3": "比较熟悉",
        "L4": "存在明显好感",
        "L5": "已经见过面",
        "L6": "亲密关系"
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
        """Generate candidate replies and pass through optionally-implemented Ranker."""
        candidates = []
        if self.llm is not None:
            candidates = self._generate_with_llm(chat_history, plan, relationship_state, memory)
        
        # 如果 LLM 生成失败或为空，自动降级到更自然的 Rules 兜底
        if not candidates:
            candidates = self._generate_with_rules(chat_history, plan, relationship_state, memory)

        # 💡 【防御战线 C：精排层物理切除】
        # 天王老子来了，只要不是在聊猫，带“猫”的候选直接在代码层做物理清洗！
        latest_msg = self._latest_text(chat_history)
        candidates = self._rank_candidates(candidates, latest_msg)

        return candidates[: plan.candidate_count]

    def _build_chat_history(self, chat_history: Sequence[Mapping[str, Any] | str]) -> str:
        """格式化聊天记录，截取最近20轮"""
        result = []
        for msg in chat_history[-20:]:
            if isinstance(msg, str):
                result.append(msg)
                continue

            role = msg.get("role", "unknown")
            content = (
                msg.get("content")
                or msg.get("text")
                or msg.get("message")
                or ""
            )

            if role in ["assistant", "boy", "me"]:
                role = "我"
            elif role in ["user", "girl", "her"]:
                role = "她"

            result.append(f"{role}：{content}")

        return "\n".join(result)

    def _build_memory_summary(self, memory: Mapping[str, Any], latest_msg: str) -> str:
        """💡【防御战线 A：记忆源头控制】"""
        parts = []

        city = memory.get("city")
        if city:
            parts.append(f"她在{city}")

        job = memory.get("job")
        if job:
            parts.append(f"职业是{job}")

        # 只有在最新聊天里主动提到了“猫”，或者上下文在聊宠物，才把宠物记忆开放给 LLM
        if "猫" in latest_msg or "宠物" in latest_msg:
            pets = memory.get("pets", [])
            if pets:
                pet = pets[0]
                breed = pet.get("breed") or pet.get("species") if isinstance(pet, dict) else pet
                if breed:
                    parts.append(f"养了一只{breed}")

        interests = memory.get("interests", [])
        if interests:
            parts.append(f"喜欢{','.join(interests[:3])}")

        return "；".join(parts) or "暂无"

    @staticmethod
    def humanize(text: str) -> str:
        """过滤 AI 味机制"""
        replacements = {
            "我认为": "",
            "我觉得": "",
            "确实如此": "确实",
            "非常": "挺",
            "哈哈哈哈": "哈哈",
            "真的非常": "真挺",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text.strip()

    def _generate_with_llm(
        self,
        chat_history: Sequence[Mapping[str, Any] | str],
        plan: ReplyPlan,
        relationship_state: Mapping[str, Any],
        memory: Mapping[str, Any],
    ) -> list[ReplyCandidate]:
        """Generate replies using an LLM provider with optimized structure."""
        latest_msg = self._latest_text(chat_history)
        history_text = self._build_chat_history(chat_history)
        memory_text = self._build_memory_summary(memory, latest_msg)
        stage = relationship_state.get("stage", "L1")
        stage_desc = self.STAGE_DESC.get(stage, "刚认识")

        tactics_text = "\n".join(f"- {t}" for t in getattr(plan, "tactics", []))
        avoid_text = "\n".join(f"- {a}" for a in getattr(plan, "avoid", []))

        # 💡【防御战线 B：硬核负向 Prompt 约束】
        prompt = f"""
你是微信聊天高手。请直接给出 6 条纯文本候选回复。

目标：
{plan.objective}

语气：
{plan.tone}

关系阶段：
{stage} ({stage_desc})

已知信息：
{memory_text}

战术指令：
{tactics_text}

必须避免（Avoid）：
{avoid_text}
- 严禁说教、自嗨、油腻、长篇大论。
- 严禁使用“在教猫回复”、“跟猫学吊胃口”等任何关于猫或宠物的互联网过时烂梗（当前并未在聊宠物话题）。

最近聊天：
{history_text}

要求：
1. 输出6条候选回复，每行一条。
2. 每条8~20字，长短交错，像真人发微信，多用口语。
3. 不要带有任何解释、编号（如 1. 2. 3.）、Markdown 符号或标点前缀。

直接输出回复内容。
"""
        response = self.llm.generate(prompt, temperature=0.8, max_tokens=350)
        if not getattr(response, "success", False) or not response.content:
            return []

        candidates = []
        for line in response.content.splitlines():
            clean_line = line.strip(" -1234567890.、*\"'")
            if clean_line:
                humanized_line = self.humanize(clean_line)
                candidates.append(ReplyCandidate(text=humanized_line, source="llm"))
                
        return candidates

    @staticmethod
    def _generate_with_rules(
        chat_history: Sequence[Mapping[str, Any] | str],
        plan: ReplyPlan,
        relationship_state: Mapping[str, Any],
        memory: Mapping[str, Any],
    ) -> list[ReplyCandidate]:
        """Rule 兜底更自然，废除刻意和AI味的话术"""
        latest = ReplyGenerator._latest_text(chat_history)
        stage = str(relationship_state.get("stage", "L1"))

        if any(k in latest for k in ["累", "烦", "崩溃", "压力", "加班"]):
            base = [
                "今天确实够呛😂",
                "先缓缓，别硬撑",
                "这波听着都累",
                "辛苦啦，快去瘫会儿",
                "摸鱼缓一缓，别死磕",
                "太窒息了，等会儿犒劳下自己"
            ]
        elif stage in {"L4", "L5", "L6"}:
            base = [
                "稀客啊😂",
                "哟，终于出现了",
                "刚好看到",
                "在呢，刚刚还在想事情",
                "收到，今天忙啥呢",
                "出现得正是时候[旺柴]"
            ]
        else:
            base = [
                "我在😂",
                "怎么啦",
                "突然找我有事？",
                "刚看到，你说",
                "咋啦，今天没加班？",
                "怎么突然想起抓我了"
            ]

        return [
            ReplyCandidate(text=text, source="rules", metadata={"objective": plan.objective}) 
            for text in base[: plan.candidate_count]
        ]

    def _rank_candidates(self, candidates: list[ReplyCandidate], latest_msg: str) -> list[ReplyCandidate]:
        """💡【防御战线 C 的具体实现】"""
        # 如果对方没主动聊猫，任何带“猫”的生成结果直接乱棍打死
        if "猫" not in latest_msg and "宠物" not in latest_msg:
            filtered = [c for c in candidates if "猫" not in c.text and "喵" not in c.text]
            
            # 如果被洗掉后条数不够了，用安全的兜底话术无缝补齐，绝对不破坏 6 条候选的死命令
            backup_pool = [
                "刚忙完，刚才整个人都麻了。",
                "怎么啦，突然召唤我？",
                "刚看到，今天一天都在对线。",
                "哈哈，你这句话差点没把我送走。",
                "在呢在呢，刚空下来。",
                "哟，今儿个刮的什么风。"
            ]
            idx = 0
            while len(filtered) < 6 and idx < len(backup_pool):
                if not any(b in [f.text for f in filtered] for b in [backup_pool[idx]]):
                    filtered.append(ReplyCandidate(text=backup_pool[idx], source="filter_fallback"))
                idx += 1
            return filtered
            
        return candidates

    @staticmethod
    def _latest_text(chat_history: Sequence[Mapping[str, Any] | str]) -> str:
        """Return latest chat content."""
        if not chat_history:
            return ""
        latest = chat_history[-1]
        if isinstance(latest, str):
            return latest
        return str(latest.get("content", latest.get("text", latest.get("message", ""))))