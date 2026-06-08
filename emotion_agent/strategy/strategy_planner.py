"""Strategy planning with behavior profiling, risk routing, and ethical attraction constraints."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.analyzers.conversation_analyzer import ConversationAnalysis
from emotion_agent.analyzers.risk_detector import RiskReport


class BehaviorProfile(BaseModel):
    """Continuous behavioral snapshot of the other person on 0-100 scales."""

    model_config = ConfigDict(extra="ignore")

    warmth: int = Field(default=50, ge=0, le=100, description="言语温度和亲和度。")
    responsiveness: int = Field(default=50, ge=0, le=100, description="回复意愿、字数和接话程度。")
    playfulness: int = Field(default=50, ge=0, le=100, description="接梗、调侃和轻松互动接受度。")
    guardedness: int = Field(default=50, ge=0, le=100, description="防备心和对过快推进的抵触。")
    emotional_need: int = Field(default=50, ge=0, le=100, description="当前需要倾听、安慰和认同的程度。")


class BehaviorProfiler:
    """Builds continuous behavior values from analysis, relationship state, and risk."""

    @staticmethod
    def profile(
        analysis: ConversationAnalysis,
        relationship_state: Mapping[str, Any],
        risk: RiskReport | None = None,
    ) -> BehaviorProfile:
        """Calculate a behavior profile without rigid one-label branching."""
        score = analysis.interest_score
        intent = analysis.intent
        stage = str(relationship_state.get("stage", analysis.relationship_stage or "L1"))

        warmth = 50
        responsiveness = 50
        playfulness = 50
        guardedness = 50
        emotional_need = 50

        if score > 70:
            warmth = min(90, 40 + score // 2)
            responsiveness = min(95, 45 + score // 2)
            guardedness = max(20, 75 - score // 2)
        elif score < 40:
            warmth = max(15, score - 10)
            responsiveness = max(20, score)
            guardedness = min(90, 100 - score)

        if intent in {"冷淡", "敷衍"}:
            responsiveness = max(10, responsiveness - 30)
            playfulness = max(10, playfulness - 25)
            guardedness = min(95, guardedness + 25)
        elif intent == "测试":
            guardedness = min(95, guardedness + 28)
            playfulness = min(82, playfulness + 10)
        elif intent in {"抱怨", "求安慰", "分享情绪", "工作压力"}:
            emotional_need = min(95, emotional_need + 38)
            playfulness = max(15, playfulness - 22)
            warmth = min(90, warmth + 8)
        elif intent in {"分享生活", "邀约"}:
            playfulness = min(85, playfulness + 15)
            responsiveness = min(90, responsiveness + 10)
        elif intent == "调侃":
            playfulness = min(92, playfulness + 22)
            warmth = min(88, warmth + 10)
        elif intent == "吃醋":
            emotional_need = min(88, emotional_need + 25)
            guardedness = min(88, guardedness + 10)

        if stage in {"L4", "L5", "L6"}:
            warmth = min(95, warmth + 8)
            playfulness = min(92, playfulness + 8)
            guardedness = max(15, guardedness - 8)

        if risk is not None:
            emotional_need = min(100, emotional_need + risk.support // 3 + risk.crisis // 4)
            guardedness = min(100, guardedness + risk.boundary // 3 + risk.conflict // 4)
            if risk.risk_level != "low":
                playfulness = max(10, playfulness - 25)

        return BehaviorProfile(
            warmth=warmth,
            responsiveness=responsiveness,
            playfulness=playfulness,
            guardedness=guardedness,
            emotional_need=emotional_need,
        )


class ReplyPlan(BaseModel):
    """Concrete plan used by the reply generator."""

    model_config = ConfigDict(extra="ignore")

    objective: str
    tone: str
    emotional_need: str = "连接感"
    relationship_move: str = "自然接话"
    tactics: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    target_length: str = "short"
    candidate_count: int = 6
    behavior_profile: BehaviorProfile = Field(default_factory=BehaviorProfile)
    favorability_score: float = Field(default=0.0, ge=0.0, le=100.0)
    favorability_stage: str = "F0"
    favorability_label: str = "陌生观望"
    intimacy_boundary: str = "不要推进身体接触。"
    consent_note: str = "好感度只是聊天信号估计，不等于同意。"


class StrategyPlanner:
    """Plans responses using restored behavior profiling plus sincere relationship constraints."""

    def plan(
        self,
        analysis: Any,
        *args: Any,
        relationship_state: Mapping[str, Any] | None = None,
        memory: Mapping[str, Any] | None = None,
        risk: Any | None = None,
        profile: Any | None = None,
        conversation_turn_count: int = 5,
    ) -> ReplyPlan:
        """Create a balanced reply plan for downstream generation.

        The method accepts both the restored old call style
        ``plan(analysis, profile, risk, relationship_state)`` and the current
        pipeline style ``plan(analysis, relationship_state, memory, risk)``.
        """
        relationship_state, memory, risk, profile, conversation_turn_count = self._normalize_call(
            args=args,
            relationship_state=relationship_state,
            memory=memory,
            risk=risk,
            profile=profile,
            conversation_turn_count=conversation_turn_count,
        )
        analysis_obj = self._coerce_analysis(analysis)
        risk_obj = self._coerce_risk(risk)
        relationship_state = relationship_state or {}
        memory = memory or {}
        profile_obj = self._coerce_profile(profile, analysis_obj, relationship_state, risk_obj)

        user_text = str(getattr(analysis_obj, "user_raw_text", "") or "")
        intent = analysis_obj.intent or "日常互动"
        stage = str(relationship_state.get("stage", analysis_obj.relationship_stage or "L1"))
        stage_label = str(relationship_state.get("stage_label", ""))
        emotional_need = self._infer_emotional_need(analysis_obj, risk_obj, profile_obj)
        favorability_score = self._safe_float(relationship_state.get("favorability_score", 0.0))
        favorability_stage = str(relationship_state.get("favorability_stage", "F0"))
        favorability_label = str(relationship_state.get("favorability_label", "陌生观望"))
        intimacy_boundary = str(relationship_state.get("intimacy_boundary", "不要推进身体接触。"))
        consent_note = str(relationship_state.get("consent_note", "好感度只是聊天信号估计，不等于同意。"))
        relationship_move = self._relationship_move(stage, intent, risk_obj, profile_obj, favorability_score)

        tactics = [
            f"关系阶段：{stage} {stage_label}".strip(),
            f"好感度：{favorability_score:.1f}/100（{favorability_stage} {favorability_label}）",
            f"她的主要意图：{intent}",
            f"她的情绪：{analysis_obj.emotion or '未知'}",
            f"兴趣分：{analysis_obj.interest_score}",
            f"行为画像：热情{profile_obj.warmth}/响应{profile_obj.responsiveness}/接梗{profile_obj.playfulness}/防备{profile_obj.guardedness}/情绪需求{profile_obj.emotional_need}",
            f"她此刻可能需要：{emotional_need}",
            f"推进方式：{relationship_move}",
            f"亲密边界：{intimacy_boundary}",
            f"可用记忆：{self._memory_hint(memory)}",
        ]
        avoid = [
            "长篇大论的说教",
            "过度解读对方的话",
            "刻意的套路和打压话术",
            "PUA",
            "故意冷落",
            "制造嫉妒",
            "道德绑架",
            "查岗式追问",
            "油腻称呼",
            "过度暴露需求感",
            "把好感度当成对方已经同意",
            "根据分数鼓励身体接触",
        ]

        insult_keywords = ("傻卵", "傻x", "有病", "滚", "乐色", "傻逼", "弱智", "闭嘴")
        has_insult = any(word in user_text.lower() for word in insult_keywords)

        if risk_obj.crisis > 70 or risk_obj.risk_level == "high":
            return ReplyPlan(
                objective="优先安全陪伴，稳定情绪，建议现实支持，不推进暧昧。",
                tone="克制、可靠、温和",
                emotional_need="安全感和现实支持",
                relationship_move="暂停推进，先保护对方",
                tactics=[*tactics, "先承接情绪，再鼓励联系可信任的人或专业帮助。"],
                avoid=[*avoid, "暧昧挑逗", "刺激对方", "轻飘飘开玩笑", "盲目承诺"],
                candidate_count=4,
                behavior_profile=profile_obj,
                favorability_score=favorability_score,
                favorability_stage=favorability_stage,
                favorability_label=favorability_label,
                intimacy_boundary=intimacy_boundary,
                consent_note=consent_note,
            )

        if has_insult or risk_obj.conflict > 70 or risk_obj.boundary > 70:
            return ReplyPlan(
                objective="面对越界或冲突时保持稳定，不自证、不攻击，清楚但不压迫地守住边界。",
                tone="简短、平静、有边界",
                emotional_need="空间感和低压力",
                relationship_move="先降温，停止强推进",
                tactics=[
                    *tactics,
                    "用短句降低对抗，不讲大道理。",
                    "允许对方有情绪，但不承接侮辱或失控表达。",
                ],
                avoid=[
                    *avoid,
                    "教对方做人",
                    "低头讨好",
                    "阴阳怪气",
                    "反向指责",
                    "连续追问",
                ],
                candidate_count=6,
                behavior_profile=profile_obj,
                favorability_score=favorability_score,
                favorability_stage=favorability_stage,
                favorability_label=favorability_label,
                intimacy_boundary=intimacy_boundary,
                consent_note=consent_note,
            )

        objective = self._objective_for_intent(intent)
        tone = self._tone_for_stage(stage)

        if risk_obj.conflict > 50:
            objective = "不承接对立情绪，通过平和、客观的态度中和紧绷感。"
            tone = "情绪稳定、大度、温和"
            tactics.append("执行冲突缓冲：承接情绪，不急于解释和反击。")
            avoid.extend(["自证清白", "反向指责", "阴阳怪气"])
        elif risk_obj.boundary > 55:
            objective = "明确个人边界，不卑不亢地给对方空间。"
            tone = "坦诚、清爽、有原则"
            tactics.append("执行边界策略：尊重对方节奏，也保持自己的舒适边界。")
            avoid.extend(["无底线退让", "讨好式顺从", "密集追问"])
        elif risk_obj.support > 55 or profile_obj.emotional_need > 75:
            objective = "提供高质量的倾听和情绪价值，让对方感觉被理解。"
            tone = "温柔、真诚、有支撑感"
            tactics.append("执行支持共情：先站在她的情绪里，再轻轻打开表达空间。")
            avoid.extend(["开玩笑调侃", "理性分析讲道理", "转移话题"])
        elif profile_obj.guardedness > 70 or profile_obj.warmth < 40:
            objective = "降低聊天压迫感，给对方留出舒适的社交距离。"
            tone = "松弛、淡定、低压力"
            tactics.append("执行轻松低压：少问、多接、允许对方慢回。")
            avoid.extend(["高频发问", "过度热情迎合", "表白式推进"])
            if profile_obj.responsiveness < 30:
                objective = "得体自然地收尾，不消耗无谓的社交精力。"
                relationship_move = "优雅留白"
                tactics.append("执行结束话题：用无压力的结束语保留舒适感。")
                avoid.extend(["恋战式硬找话题", "询问式结尾"])
        elif profile_obj.playfulness > 60 and profile_obj.warmth >= 50:
            objective = "放大互动趣味，让对话更轻松、有来有回。"
            tone = "风趣、自然、有张力"
            tactics.append("执行轻松调侃：抓住对方话里的可爱点，不嘲讽、不油腻。")
            if stage in {"L3", "L4", "L5"}:
                tactics.append("执行关系推进：植入一点共享语境或下次互动期待。")
        else:
            tactics.append("执行同频回应：字数和能量贴近对方，不抢戏。")

        if conversation_turn_count >= 8 and profile_obj.emotional_need < 60:
            objective = "在情绪饱满时自然留白，避免把话题聊干。"
            relationship_move = "阶段性收束"
            tactics.append("执行长线节奏控制：适度离场，让下次聊天还有余味。")
            avoid.extend(["硬找话题", "机械反问"])

        tactics.append(self._favorability_tactic(favorability_score))
        if favorability_score < 60:
            avoid.extend(["牵手暗示", "身体接触暗示", "过夜暗示", "把暧昧推得太快"])
        elif favorability_score < 70:
            avoid.extend(["直接身体接触", "过夜暗示", "用分数判断能不能碰"])
        else:
            avoid.extend(["跳过明确同意", "把亲密期待说成理所当然"])

        if "猫" not in user_text and intent != "宠物话题":
            avoid.append("没有聊宠物时，不主动提猫或宠物段子。")

        avoid.append("不要连续使用问号制造压迫感。")

        return ReplyPlan(
            objective=objective,
            tone=tone,
            emotional_need=emotional_need,
            relationship_move=relationship_move,
            tactics=self._dedupe(tactics),
            avoid=self._dedupe(avoid),
            candidate_count=6,
            behavior_profile=profile_obj,
            favorability_score=favorability_score,
            favorability_stage=favorability_stage,
            favorability_label=favorability_label,
            intimacy_boundary=intimacy_boundary,
            consent_note=consent_note,
        )

    @staticmethod
    def _normalize_call(
        *,
        args: tuple[Any, ...],
        relationship_state: Mapping[str, Any] | None,
        memory: Mapping[str, Any] | None,
        risk: Any | None,
        profile: Any | None,
        conversation_turn_count: int,
    ) -> tuple[Mapping[str, Any], Mapping[str, Any], Any, Any, int]:
        """Resolve old and new positional call styles into named values."""
        if args:
            if len(args) >= 3 and StrategyPlanner._looks_like_profile(args[0]) and StrategyPlanner._looks_like_risk(args[1]):
                profile = args[0]
                risk = args[1]
                relationship_state = args[2]
                if len(args) >= 4:
                    conversation_turn_count = int(args[3])
            else:
                relationship_state = args[0] if len(args) >= 1 else relationship_state
                memory = args[1] if len(args) >= 2 else memory
                risk = args[2] if len(args) >= 3 else risk
                if len(args) >= 4:
                    profile = args[3]
                if len(args) >= 5:
                    conversation_turn_count = int(args[4])
        return (
            relationship_state if isinstance(relationship_state, Mapping) else {},
            memory if isinstance(memory, Mapping) else {},
            risk,
            profile,
            conversation_turn_count,
        )

    @staticmethod
    def _looks_like_profile(value: Any) -> bool:
        """Return whether a value appears to be a behavior profile."""
        if isinstance(value, BehaviorProfile):
            return True
        return isinstance(value, Mapping) and any(key in value for key in ("warmth", "responsiveness", "guardedness"))

    @staticmethod
    def _looks_like_risk(value: Any) -> bool:
        """Return whether a value appears to be a risk report."""
        if isinstance(value, RiskReport):
            return True
        return isinstance(value, Mapping) and any(key in value for key in ("risk_level", "support", "conflict", "boundary", "crisis"))

    @staticmethod
    def _coerce_analysis(value: Any) -> ConversationAnalysis:
        """Normalize analysis inputs into the current Pydantic model."""
        if isinstance(value, ConversationAnalysis):
            return value
        if isinstance(value, Mapping):
            return ConversationAnalysis.model_validate(value)
        return ConversationAnalysis(
            emotion=str(getattr(value, "emotion", "")),
            intent=str(getattr(value, "intent", "")),
            interest_score=int(getattr(value, "interest_score", 0) or 0),
            relationship_stage=str(getattr(value, "relationship_stage", "L1") or "L1"),
            risk_level=str(getattr(value, "risk_level", "low") or "low"),
        )

    @staticmethod
    def _coerce_risk(value: Any) -> RiskReport:
        """Normalize risk inputs into ``RiskReport``."""
        if isinstance(value, RiskReport):
            return value
        if isinstance(value, Mapping):
            return RiskReport.model_validate(value)
        if value is None:
            return RiskReport()
        return RiskReport(
            risk_level=str(getattr(value, "risk_level", "low") or "low"),
            support=int(getattr(value, "support", 0) or 0),
            conflict=int(getattr(value, "conflict", 0) or 0),
            boundary=int(getattr(value, "boundary", 0) or 0),
            crisis=int(getattr(value, "crisis", 0) or 0),
            safety_instruction=str(getattr(value, "safety_instruction", "") or ""),
        )

    @staticmethod
    def _coerce_profile(
        value: Any,
        analysis: ConversationAnalysis,
        relationship_state: Mapping[str, Any],
        risk: RiskReport,
    ) -> BehaviorProfile:
        """Normalize or build a behavior profile."""
        if isinstance(value, BehaviorProfile):
            return value
        if isinstance(value, Mapping) and StrategyPlanner._looks_like_profile(value):
            return BehaviorProfile.model_validate(value)
        return BehaviorProfiler.profile(analysis, relationship_state, risk)

    @staticmethod
    def _objective_for_intent(intent: str) -> str:
        """Choose a high-level objective from the detected intent."""
        objective_map = {
            "求安慰": "接住她的情绪，让她感觉被理解和偏向。",
            "分享情绪": "先共情，再轻轻打开更多表达空间。",
            "工作压力": "提供情绪价值，别急着给解决方案。",
            "分享生活": "对她的生活细节表现真实兴趣。",
            "调侃": "接住玩笑，轻松回抛一点趣味。",
            "测试": "给稳定回应，不被带节奏，也不防御。",
            "冷淡": "降低压力，轻轻留一个可回的话口。",
            "吃醋": "给确定感，但不夸张承诺。",
            "抱怨": "站在她这边，先让她爽快地吐槽出来。",
            "邀约": "明确回应，顺势推进见面细节。",
        }
        return objective_map.get(intent, "进行对等、舒适的情绪流动。")

    @staticmethod
    def _tone_for_stage(stage: str) -> str:
        """Choose tone by relationship stage."""
        tone_map = {
            "L1": "礼貌、轻松、有边界",
            "L2": "自然、友好、有一点幽默",
            "L3": "熟悉、稳定、能接住细节",
            "L4": "暧昧、俏皮、带一点在意",
            "L5": "亲近、有回忆感、有期待",
            "L6": "亲密、安心、明确偏爱",
        }
        return tone_map.get(stage, "自然、真诚")

    @staticmethod
    def _infer_emotional_need(analysis: ConversationAnalysis, risk: RiskReport, profile: BehaviorProfile) -> str:
        """Infer the likely emotional need behind the latest message."""
        if risk.risk_level != "low" or risk.crisis > 50:
            return "安全感"
        if profile.guardedness > 72:
            return "空间感和低压力"
        intent = analysis.intent
        if intent in {"求安慰", "分享情绪", "工作压力", "抱怨"}:
            return "被理解、被站队、被安抚"
        if intent in {"调侃", "测试"}:
            return "轻松感、稳定感、趣味回应"
        if intent == "冷淡":
            return "空间感和低压力"
        if intent == "吃醋":
            return "确定感和被偏爱"
        if intent == "邀约":
            return "明确回应和期待感"
        return "被关注、被认真接话"

    @staticmethod
    def _relationship_move(
        stage: str,
        intent: str,
        risk: RiskReport,
        profile: BehaviorProfile,
        favorability_score: float = 0.0,
    ) -> str:
        """Choose a relationship move that avoids manipulation and pressure."""
        if risk.risk_level != "low":
            return "稳定陪伴"
        if profile.guardedness > 72 or intent == "冷淡":
            return "后撤半步，给空间"
        if intent == "邀约":
            return "明确接受或给替代时间"
        if favorability_score >= 80:
            return "明确表达在意，但所有亲密都以明确同意为前提"
        if favorability_score >= 70:
            return "轻微拉近距离，观察主动反馈"
        if favorability_score >= 60:
            return "低压力线下推进，牵手前看现场舒适度"
        if favorability_score >= 50:
            return "增加暧昧苗头，但不推进身体接触"
        if stage in {"L4", "L5", "L6"}:
            return "轻微暧昧推进"
        if stage == "L3":
            return "增加熟悉感"
        return "建立舒适感"

    @staticmethod
    def _favorability_tactic(score: float) -> str:
        """Return one consent-safe tactic from the favorability score."""
        if score >= 90:
            return "好感度策略：关系稳定时多表达珍惜和确定感，持续尊重对方边界。"
        if score >= 80:
            return "好感度策略：亲密信号强，可以更坦诚表达期待，但必须等待明确邀请和同意。"
        if score >= 70:
            return "好感度策略：可以让身体距离和语气更近一点，但只根据对方主动反馈继续。"
        if score >= 60:
            return "好感度策略：适合低压力线下推进；牵手只能在现场反馈明确舒服时尝试。"
        if score >= 50:
            return "好感度策略：有好感苗头，重点放在分享、轻调侃和低压力邀约。"
        if score >= 30:
            return "好感度策略：先做舒服的人，少推进，多建立熟悉和信任。"
        return "好感度策略：陌生观望期，只做自然、有边界的回应。"

    @staticmethod
    def _safe_float(value: Any) -> float:
        """Coerce a numeric value into float without raising in planning."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _memory_hint(memory: Mapping[str, Any]) -> str:
        """Build a compact memory hint."""
        pets = memory.get("pets", [])
        if pets and isinstance(pets[0], Mapping):
            pet = pets[0]
            return str(pet.get("breed") or pet.get("species") or pet.get("name") or "宠物")
        interests = memory.get("interests", [])
        if interests:
            return "、".join(str(item) for item in interests[:3])
        city = memory.get("city")
        if city:
            return str(city)
        return "无"

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        """Deduplicate non-empty strings while preserving order."""
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            text = value.strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
        return result


def _demo() -> None:
    """Run a small module smoke test."""
    plan = StrategyPlanner().plan(
        ConversationAnalysis(intent="分享生活", emotion="平静", interest_score=60, relationship_stage="L3", risk_level="low"),
        {"stage": "L3", "stage_label": "熟悉"},
        {},
        RiskReport(),
    )
    print(plan.model_dump())


if __name__ == "__main__":
    _demo()
