"""Conversation-level analyzer for recent WeChat chat history."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import json
import re
from typing import Any, Mapping, Sequence, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator

from emotion_agent.analyzers.base import BaseAnalyzer
from emotion_agent.utils.types import AgentContext, LLMResponse, Message, SenderRole


ChatHistoryItem: TypeAlias = "str | Mapping[str, Any] | Message | ChatMessage"
ChatHistory: TypeAlias = "Sequence[ChatHistoryItem]"


class ChatMessage(BaseModel):
    """Normalized chat record used by the conversation analyzer."""

    model_config = ConfigDict(extra="ignore")

    role: str = Field(default=SenderRole.USER.value, description="Message role or sender name.")
    content: str = Field(default="", description="Message text content.")

    @field_validator("role", "content", mode="before")
    @classmethod
    def coerce_text(cls, value: object) -> str:
        """Convert parsed values to stripped strings."""
        if value is None:
            return ""
        return str(value).strip()


class ConversationAnalysis(BaseModel):
    """Structured JSON-compatible result for recent conversation analysis."""

    model_config = ConfigDict(extra="ignore")

    emotion: str = Field(default="", description="Current emotional signal.")
    intent: str = Field(default="", description="Main user intent.")
    interest_score: int = Field(default=0, ge=0, le=100, description="Interest score from 0 to 100.")
    relationship_stage: str = Field(default="L1", description="Estimated relationship stage (L1-L6).")
    risk_level: str = Field(default="low", description="Risk level: low, medium, or high.")
    user_raw_text: str = Field(default="", description="Latest user message for downstream strategy use.")

    @field_validator("emotion", "intent", "relationship_stage", "risk_level", "user_raw_text", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> str:
        """Normalize text-like fields."""
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("interest_score", mode="before")
    @classmethod
    def normalize_score(cls, value: object) -> int:
        """Clamp score-like values into the supported 0-100 range."""
        try:
            score = int(float(str(value)))
        except (TypeError, ValueError):
            score = 0
        return max(0, min(100, score))


class ConversationAnalysisPromptTemplate:
    """Builds prompt templates for structured conversation analysis."""

    SUPPORTED_INTENTS: tuple[str, ...] = (
        "分享生活",
        "调侃",
        "测试",
        "冷淡",
        "吃醋",
        "抱怨",
        "邀约",
        "求安慰",
        "分享情绪",
        "工作压力",
    )

    INTENT_PROMPTS: Mapping[str, str] = {
        "分享生活": "识别对方是否在主动讲日常、行程、吃喝、见闻或生活碎片。",
        "调侃": "识别玩笑、逗趣、反话、轻松打趣和带笑意的互动。",
        "测试": "识别试探态度、确认在意程度、故意抛问题或观察反应。",
        "冷淡": "识别回复短、敷衍、降温、回避、低投入或结束话题倾向。",
        "吃醋": "识别对第三方关系的敏感、占有欲、不满或在意。",
        "抱怨": "识别吐槽、不满、委屈、烦躁和对人事物的负面评价。",
        "邀约": "识别见面、吃饭、看电影、一起活动或确认时间地点。",
        "求安慰": "识别希望被陪伴、被哄、被理解、被安抚的表达。",
        "分享情绪": "识别主动表达开心、难过、焦虑、生气、委屈等感受。",
        "工作压力": "识别加班、老板、项目、同事、绩效、汇报等职场压力。",
    }

    STAGE_DESC: Mapping[str, str] = {
        "L1": "刚认识/开场陌生期",
        "L2": "破冰互动/初级熟悉期",
        "L3": "高频互动/深度熟悉期",
        "L4": "好感试探/暧昧模糊期",
        "L5": "线下建立纽带/稳定推进期",
        "L6": "高度同频/亲密关系期",
    }

    def build(self, chat_history: Sequence[ChatMessage]) -> str:
        """Build a complete structured-analysis prompt for an LLM provider."""
        formatted_history = self._format_history(chat_history)
        intent_definitions = "\n".join(
            f"- {intent}: {description}" for intent, description in self.INTENT_PROMPTS.items()
        )
        stage_definitions = "\n".join(
            f"- {stage}: {desc}" for stage, desc in self.STAGE_DESC.items()
        )
        supported_intents = "、".join(self.SUPPORTED_INTENTS)

        return (
            "你是一个微信情感聊天分析器。请只分析最近聊天记录，不要编造不存在的信息。\n\n"
            "任务：\n"
            "1. 判断主要情绪 emotion。\n"
            f"2. 从这些意图中选择一个最主要的 intent：{supported_intents}。\n"
            "3. 给出 interest_score，范围 0-100，越高代表对方越愿意继续互动。\n"
            f"4. 判断 relationship_stage（关系阶段），必须且只能选择以下标签：\n{stage_definitions}\n"
            "5. 判断 risk_level，只能使用 low、medium、high。\n\n"
            "意图识别说明：\n"
            f"{intent_definitions}\n\n"
            "输出要求：\n"
            "- 只输出 JSON，不要 Markdown（不要用 ```json 包裹），不要解释。\n"
            "- 必须包含且只包含以下字段。\n"
            "{\n"
            '  "emotion": "",\n'
            '  "intent": "",\n'
            '  "interest_score": 0,\n'
            '  "relationship_stage": "",\n'
            '  "risk_level": ""\n'
            "}\n\n"
            "最近聊天记录：\n"
            f"{formatted_history}"
        )

    @staticmethod
    def _format_history(chat_history: Sequence[ChatMessage]) -> str:
        """Format normalized chat records for prompt insertion."""
        if not chat_history:
            return "(empty)"
        result = []
        for index, message in enumerate(chat_history, start=1):
            role = message.role
            if role in ("assistant", "boy", "me", "我"):
                role = "男主"
            elif role in ("user", "girl", "her", "她"):
                role = "女生"
            result.append(f"{index}. {role}: {message.content}")
        return "\n".join(result)


class ConversationAnalyzer(BaseAnalyzer):
    """Analyzes the latest 20 chat records and returns structured JSON data."""

    # 💡 融入更贴合现代网感和真实语境的局部规则关键词
    KEYWORDS: Mapping[str, tuple[str, ...]] = {
        "分享生活": ("今天", "刚刚", "刚才", "吃了", "去了", "看到", "路上", "回家", "睡醒", "日常", "安利", "搞笑的"),
        "调侃": ("哈哈", "hhh", "笑死", "逗你", "开玩笑", "别装", "你猜", "离谱", "夺笋", "太损了"),
        "测试": ("试试", "考考", "你觉得我", "你会不会", "如果我", "是不是不", "海王", "套路", "交代"),
        "冷淡": ("嗯", "哦", "好吧", "随便", "再说", "忙", "算了", "没事", "标点"),
        "吃醋": ("她是谁", "他是谁", "别人", "不理我", "你和", "还聊", "关系很好", "吃醋", "别的妹子"),
        "抱怨": ("烦", "无语", "服了", "为什么", "老是", "真累", "吐槽", "受不了", "破防", "下雨"),
        "邀约": ("一起", "见面", "吃饭", "看电影", "有空", "周末", "出来", "面基", "约个时间"),
        "求安慰": ("安慰", "抱抱", "陪我", "哄我", "难受", "想哭", "撑不住", "需要你", "呜呜"),
        "分享情绪": ("开心", "难过", "委屈", "生气", "焦虑", "失落", "期待", "害怕", "emo"),
        "工作压力": ("工作", "加班", "老板", "项目", "同事", "绩效", "汇报", "压力", "KPI", "deadline", "对线", "硬撑"),
    }

    HIGH_RISK_KEYWORDS: tuple[str, ...] = ("自杀", "轻生", "不想活", "活不下去", "伤害自己", "结束生命")
    MEDIUM_RISK_KEYWORDS: tuple[str, ...] = ("崩溃", "绝望", "抑郁", "失眠", "喝酒", "撑不住", "真的够呛")
    GREETING_TEXTS: tuple[str, ...] = ("你好", "嗨", "哈喽", "hello", "hi", "nihao")

    def __init__(
        self,
        llm: Any | None = None,
        *,
        max_history: int = 20,
        prompt_template: ConversationAnalysisPromptTemplate | None = None,
    ) -> None:
        """Create a conversation analyzer with optional LLM-assisted analysis."""
        self.llm = llm
        self.max_history = max_history
        self.prompt_template = prompt_template or ConversationAnalysisPromptTemplate()

    @property
    def name(self) -> str:
        """Return the stable analyzer name."""
        return "conversation"

    def analyze(self, chat_history: ChatHistory | AgentContext) -> ConversationAnalysis:
        """Analyze recent chat history and return a Pydantic structured result."""
        messages = self._normalize_history(chat_history)[-self.max_history :]

        if self.llm is not None:
            llm_result = self._analyze_with_llm(messages)
            if llm_result is not None:
                return llm_result

        return self._analyze_with_rules(messages)

    def build_prompt(self, chat_history: ChatHistory | AgentContext) -> str:
        """Build the LLM prompt for the latest chat history."""
        messages = self._normalize_history(chat_history)[-self.max_history :]
        return self.prompt_template.build(messages)

    def _analyze_with_llm(self, chat_history: Sequence[ChatMessage]) -> ConversationAnalysis | None:
        """Ask an optional LLM provider for structured JSON and validate it."""
        system_prompt = (
            "你是一个微信聊天分析器。"
            "你的任务不是安慰，也不是回复，而是读懂最近对话。"
            "请只输出 JSON。不要解释，不要 markdown，不要补充字段。"
        )
        response = self.llm.analyze(
            messages=self._llm_messages(chat_history),
            system_prompt=system_prompt,
            temperature=0.0,
            max_tokens=320,
        )
        if not isinstance(response, LLMResponse) or not response.success:
            return None
        parsed = self._parse_analysis_json(response.content)
        if parsed is None:
            return None
        latest_user = self._latest_user_text(chat_history)
        return parsed.model_copy(update={"user_raw_text": latest_user})

    def _parse_analysis_json(self, content: str) -> ConversationAnalysis | None:
        """Parse and validate JSON emitted by an LLM provider."""
        text = self._strip_json_fence(content)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if match is None:
                return None
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        if not isinstance(data, dict):
            return None
        return ConversationAnalysis.model_validate(data)

    @staticmethod
    def _strip_json_fence(content: str) -> str:
        """Remove common Markdown JSON fences and non-JSON wrappers safely."""
        if not content:
            return ""
            
        text = content.strip()
        
        # 1. 强力清除可能存在的 Markdown 标记 (不管它带不带换行、大写还是小写)
        # 匹配 ``` 后面跟着可选的 json/JSON 以及换行符
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        # 匹配结尾的 ```
        text = re.sub(r"\s*```$", "", text)
        
        text = text.strip()
        
        # 2. 如果大模型不听话，在JSON前后加了“以下是分析结果：”等废话
        # 我们直接使用非贪婪正则，精准提取最外层的 { 和 } 及其内部所有内容
        match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if match:
            return match.group(1).strip()
            
        return text

    def _analyze_with_rules(self, chat_history: Sequence[ChatMessage]) -> ConversationAnalysis:
        """Produce a deterministic local analysis when no LLM result is available."""
        user_messages = self._user_messages(chat_history) or list(chat_history)
        joined_text = "\n".join(message.content for message in user_messages)
        latest_user = self._latest_user_text(chat_history)
        if self._is_greeting(latest_user):
            return ConversationAnalysis(
                emotion="友好",
                intent="分享生活",
                interest_score=30,
                relationship_stage="L1" if len(chat_history) <= 2 else "L2",
                risk_level="low",
                user_raw_text=latest_user,
            )
        intent_scores = self._score_intents(joined_text, user_messages)
        intent = max(intent_scores, key=intent_scores.get) if intent_scores else "分享生活"

        if intent_scores and intent_scores[intent] <= 0:
            intent = "冷淡" if self._coldness_score(user_messages) >= 2 else "分享生活"

        interest_score = self._interest_score(chat_history=user_messages, intent=intent)
        return ConversationAnalysis(
            emotion=self._emotion(joined_text=joined_text, intent=intent),
            intent=intent,
            interest_score=interest_score,
            relationship_stage=self._relationship_stage(user_messages, intent, interest_score),
            risk_level=self._risk_level(joined_text),
            user_raw_text=latest_user,
        )

    @classmethod
    def _is_greeting(cls, text: str) -> bool:
        """Return whether a short message is just a greeting."""
        normalized = re.sub(r"\s+", "", text.lower().strip())
        return normalized in cls.GREETING_TEXTS

    def _llm_messages(self, chat_history: Sequence[ChatMessage]) -> list[dict[str, str]]:
        """Build structured messages for LLM-first analysis."""
        schema = (
            "请阅读最近聊天，并返回 JSON："
            '{"emotion":"","intent":"","interest_score":0,"relationship_stage":"","risk_level":""}。'
            "intent 只能从这些值里选一个：分享生活、调侃、测试、冷淡、吃醋、抱怨、邀约、求安慰、分享情绪、工作压力。"
            "relationship_stage 只能填 L1-L6。risk_level 只能填 low、medium、high。"
            "判断时优先看最近 5 条，不要被很久以前的话带偏。"
        )
        messages: list[dict[str, str]] = [{"role": "user", "content": schema}]
        for message in chat_history:
            role = "assistant" if message.role in {"assistant", "me", "boy", "我"} else "user"
            speaker = "我" if role == "assistant" else "她"
            messages.append({"role": role, "content": f"{speaker}：{message.content}"})
        return messages

    @staticmethod
    def _latest_user_text(chat_history: Sequence[ChatMessage]) -> str:
        """Return the latest user-side message for downstream components."""
        for message in reversed(chat_history):
            if message.role not in {"assistant", "me", "boy", "我"}:
                return message.content
        return chat_history[-1].content if chat_history else ""

    @staticmethod
    def _user_messages(chat_history: Sequence[ChatMessage]) -> list[ChatMessage]:
        """Return only user-side messages for intent-heavy rule analysis."""
        return [message for message in chat_history if message.role not in {"assistant", "me", "boy", "我"}]

    def _score_intents(
        self,
        joined_text: str,
        chat_history: Sequence[ChatMessage],
    ) -> dict[str, int]:
        """Score supported intents with transparent keyword rules."""
        lowered_text = joined_text.lower()
        latest_user = self._latest_user_text(chat_history).lower()
        scores: dict[str, int] = {}
        for intent, keywords in self.KEYWORDS.items():
            scores[intent] = sum(2 for keyword in keywords if keyword.lower() in lowered_text)
            scores[intent] += sum(3 for keyword in keywords if keyword.lower() in latest_user)

        coldness = self._coldness_score(chat_history)
        scores["冷淡"] = scores.get("冷淡", 0) + coldness * 3

        if any(word in latest_user for word in ("一起", "吃饭", "电影", "见面", "出来", "周末", "有空")):
            scores["邀约"] = scores.get("邀约", 0) + 8
        if "一起" in joined_text and any(word in joined_text for word in ("吃饭", "电影", "见面", "出来", "面基")):
            scores["邀约"] = scores.get("邀约", 0) + 5
        if any(word in latest_user for word in ("别的女生", "她是谁", "他是谁", "还聊", "和别人", "不理我")):
            scores["吃醋"] = scores.get("吃醋", 0) + 10
            scores["测试"] = scores.get("测试", 0) + 3
        if any(word in latest_user for word in ("压力", "加班", "老板", "项目", "对线", "硬撑")):
            scores["工作压力"] = scores.get("工作压力", 0) + 4
        elif any(word in joined_text for word in ("压力", "加班", "老板", "项目", "对线", "硬撑")):
            scores["工作压力"] = scores.get("工作压力", 0) + 4
        return scores

    @staticmethod
    def _coldness_score(chat_history: Sequence[ChatMessage]) -> int:
        """Estimate low-engagement signals from the latest short replies."""
        recent = chat_history[-5:]
        cold_words = {"嗯", "哦", "好", "好吧", "行", "随便", "再说", "忙", "...", "。", "—"}
        score = 0
        for message in recent:
            content = message.content.strip()
            if content in cold_words or len(content) <= 2:
                score += 1
        return score

    def _interest_score(self, chat_history: Sequence[ChatMessage], intent: str) -> int:
        """Estimate willingness to continue the conversation on a 0-100 scale."""
        if not chat_history:
            return 0

        contents = [message.content for message in chat_history]
        joined_text = "\n".join(contents)
        question_count = sum(content.count("?") + content.count("？") for content in contents)
        average_length = sum(len(content) for content in contents) / len(contents)

        score = 45
        score += min(len(chat_history) * 2, 20)
        score += min(question_count * 4, 12)
        score += 8 if average_length >= 12 else 0
        score += 10 if intent in {"邀约", "分享生活", "分享情绪", "求安慰"} else 0
        score += 6 if any(word in joined_text for word in ("哈哈", "想你", "晚安", "早安", "一起", "😂", "笑死")) else 0
        score -= self._coldness_score(chat_history) * 10
        score -= 15 if intent == "冷淡" else 0
        return max(0, min(100, int(score)))

    @staticmethod
    def _emotion(joined_text: str, intent: str) -> str:
        """Infer a coarse emotional label from text and intent."""
        if intent == "吃醋":
            return "吃醋"
        emotion_rules: Mapping[str, tuple[str, ...]] = {
            "开心": ("开心", "哈哈", "期待", "高兴", "笑死", "😂"),
            "难过": ("难过", "想哭", "失落", "不开心", "呜呜", "emo"),
            "委屈": ("委屈", "没人懂", "不公平", "太惨了"),
            "焦虑": ("焦虑", "慌", "压力", "deadline", "来不及", "死线"),
            "生气": ("生气", "烦", "无语", "受不了", "破防"),
            "疲惫": ("累", "疲惫", "困", "加班", "硬撑"),
        }
        lowered_text = joined_text.lower()
        for emotion, keywords in emotion_rules.items():
            if any(keyword.lower() in lowered_text for keyword in keywords):
                return emotion
        return "平静"

    def _risk_level(self, joined_text: str) -> str:
        """Infer risk level from explicit risk keywords."""
        if any(keyword in joined_text for keyword in self.HIGH_RISK_KEYWORDS):
            return "high"
        if any(keyword in joined_text for keyword in self.MEDIUM_RISK_KEYWORDS):
            return "medium"
        return "low"

    @staticmethod
    def _relationship_stage(
        chat_history: Sequence[ChatMessage],
        intent: str,
        interest_score: int,
    ) -> str:
        """💡 核心修复：将底层兜底阶段映射无缝对齐至上游的 L1~L6 规范"""
        joined_text = "\n".join(message.content for message in chat_history)
        warm_markers = ("想你", "晚安", "早安", "抱抱", "一起", "哈哈", "😂", "笑死")
        
        if intent == "冷淡" and interest_score < 40:
            return "L1"
        if intent in {"吃醋", "邀约"} or any(marker in joined_text for marker in warm_markers):
            return "L4" if interest_score >= 65 else "L3"
        if len(chat_history) >= 14 and interest_score >= 70:
            return "L5"
        if len(chat_history) >= 6 and interest_score >= 50:
            return "L3"
        return "L2" if len(chat_history) >= 3 else "L1"

    def _normalize_history(self, chat_history: ChatHistory | AgentContext) -> list[ChatMessage]:
        """Normalize supported chat history inputs into Pydantic chat records."""
        if isinstance(chat_history, AgentContext):
            items: Sequence[ChatHistoryItem] = [*chat_history.recent_messages, chat_history.current_message]
        else:
            items = chat_history
        return [self._normalize_item(item) for item in items]

    @staticmethod
    def _normalize_item(item: ChatHistoryItem) -> ChatMessage:
        """Normalize one raw chat item into ``ChatMessage``."""
        if isinstance(item, ChatMessage):
            return item
        if isinstance(item, Message):
            return ChatMessage(role=item.role.value, content=item.content)
        if isinstance(item, str):
            return ChatMessage(role=SenderRole.USER.value, content=item)
        role = item.get("role", item.get("sender", SenderRole.USER.value))
        content = item.get("content", item.get("text", item.get("message", "")))
        return ChatMessage(role=role, content=content)


def _demo() -> None:
    """Run a small module smoke test."""
    analyzer = ConversationAnalyzer()
    analysis = analyzer.analyze(["今天跟大老板强行对线了半小时，被骂惨了，真的顶不住，破防了。"])
    print(analysis.model_dump_json(indent=2))


if __name__ == "__main__":
    _demo()
