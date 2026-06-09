"""Strategy Planner - low-pressure relationship communication strategy."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from emotion_agent.analyzers.conversation_analyzer import ConversationAnalysis
from emotion_agent.analyzers.risk_detector import RiskReport


class BehaviorProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    warmth: int = Field(default=50)
    responsiveness: int = Field(default=50)
    playfulness: int = Field(default=50)
    guardedness: int = Field(default=50)
    emotional_need: int = Field(default=50)
    vulnerability: int = Field(default=0)


class ReplyPlan(BaseModel):
    """动态行动计划"""
    model_config = ConfigDict(extra="ignore")

    objective: str
    tone: str
    action_type: str = "推进"
    emotional_need: str = "被看见"
    relationship_move: str = "自然推进"
    tactics: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    target_length: str = "medium"
    candidate_count: int = 8
    behavior_profile: BehaviorProfile = Field(default_factory=BehaviorProfile)


class StrategyPlanner:
    """Plan the next reply with comfort, pacing, and clear boundaries."""

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

        intent = getattr(analysis_obj, "intent", "分享生活")
        stage = str(relationship_state.get("stage", getattr(analysis_obj, "relationship_stage", "L1")))
        
        # 修正：统一从经过强制转换的最安全的数据对象中提取指标
        vuln = getattr(profile_obj, "vulnerability", 50)
        sexual_tension = getattr(analysis_obj, "sexual_tension", 0)
        escalation = getattr(analysis_obj, "escalation_window", "low")
        favor_release = getattr(analysis_obj, "favor_release", 0)
        risk_instruction = str(getattr(risk_obj, "strategy_instruction", "") or "")

        # ==================== 低压力沟通决策（舒适感优先） ====================
        
        if "BACK_OFF" in risk_instruction:
            objective = "对方表现出回避或压力信号，先退回安全社交距离"
            tone = "克制、尊重、低压力"
            action_type = "边界回应"
            tactics = [
                "完全接受对方当下的节奏，不解释、不追问、不提出新要求",
                "回复控制在一句话内，表达尊重和空间感",
                "不把冷淡、拒绝或回避理解成需要反击的信号"
            ]

        elif intent in {"撒娇", "亲近表达", "性暗示"} or sexual_tension >= 60:
            objective = "回应她释放的轻松信号，同时维持舒适边界"
            tone = "松弛、轻微调侃、不过度"
            action_type = "轻暧昧拉扯"
            tactics = [
                "先自然接住她的撒娇或暗示，用轻调侃或反差回应",
                "不要立刻升级或过度承诺，保持节奏稳定",
                "如果她同时表达了脆弱，在尾端给一句具体、温和的偏爱，形成温柔和幽默的轻微反差"
            ]

        elif intent in {"求安慰", "抱怨", "分享情绪", "工作压力"} or vuln >= 70:
            objective = "先接住情绪建立安全感，再视氛围转回轻松话题"
            tone = "稳重、温暖、有稳定感"
            action_type = "接情绪"
            tactics = [
                "真实接住她的情绪，不讲大道理，也不做无意义的复读机安慰",
                "提供稳定承接，让她感到当下被理解、被看见",
                "前期重点是提供高舒适度，避免连续追问，适时给一个轻量话题出口"
            ]

        elif intent == "邀约" or (favor_release >= 60 and escalation != "low"):
            objective = "在对方释放明确窗口时，低压力落地安排"
            tone = "清晰、轻松、不纠结"
            action_type = "邀约推进"
            tactics = [
                "明确回应并给出一个清晰但可拒绝的轻量选择",
                "用时间、地点或活动中的一个变量降低对方的决策压力",
                "建立轻松预期，不让邀约显得急迫或沉重"
            ]

        elif intent in {"边界试探", "测试", "框架挑战", "吃醋"}:
            objective = "稳住情绪，不进入防御性解释"
            tone = "轻松、稳定、给一点确定感"
            action_type = "稳定回应"
            tactics = [
                "不慌张、不连环解释、不自证，把它视为对方在寻找安全感",
                "使用轻度幽默化解紧张，再给一点确定感",
                "避免把试探升级成对抗"
            ]

        elif intent in {"冷淡", "敷衍", "撤退"}:
            objective = "尊重边界，退回安全社交距离"
            tone = "克制、松弛、留空间"
            action_type = "后撤"
            tactics = [
                "精简回复字数，不提供多余解释，也不提出新要求",
                "利落结束当前话题或留下一个很轻的口子",
                "把空间留给对方，等待她下一次自然开启"
            ]

        else:
            objective = "延续轻松互动，建立舒适的来回感"
            tone = "风趣、自然、有边界"
            action_type = "调侃"
            tactics = [
                "轻松接话并制造一点自然的情绪起伏",
                "结合真实生活细节，不追着聊，保留松弛感",
                "在话题结束时留下可延伸的轻口子"
            ]

        # 通用舒适感约束
        tactics.extend([
            f"动态沟通参数 -> 阶段: {stage} | 当前意图: {intent} | 情绪脆弱度: {vuln} | 亲近信号: {sexual_tension}",
            "严控自我节奏：高价值核心是不盲目自证，不随对方的情绪试探而频繁起伏",
            "推进铁律：前期做好深层情绪推拉与共鸣，严禁在舒适度未达标前盲目暴露显性需求感",
            "不可触碰的红线：任何阶段都必须有底线思维，不对无理试探进行任何妥协式跪舔"
        ])

        return ReplyPlan(
            objective=objective,
            tone=tone,
            action_type=action_type,
            emotional_need="被看见，并感到交流是轻松安全的",
            relationship_move="在舒适感和边界感内自然推进",
            tactics=self._dedupe(tactics),
            avoid=["低情商废话安慰", "过度解释", "连续追问", "油腻的工业糖精话术", "急迫推进和压迫感"],
            target_length="medium",
            candidate_count=8,
            behavior_profile=profile_obj,
        )

    # ==================== 以下为修复并兼容后的辅助方法 ====================

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
        if args:
            if len(args) >= 3 and StrategyPlanner._looks_like_profile(args[0]) and StrategyPlanner._looks_like_risk(args[1]):
                profile = args[0]
                risk = args[1]
                relationship_state = args[2]
            else:
                relationship_state = args[0] if len(args) >= 1 else relationship_state
                memory = args[1] if len(args) >= 2 else memory
                risk = args[2] if len(args) >= 3 else risk
                if len(args) >= 4:
                    profile = args[3]
        return (
            # 修正：使用更广泛的 Mapping 验证兼容性，防止特殊 Map 类型数据被清空
            relationship_state if isinstance(relationship_state, Mapping) else {},
            memory if isinstance(memory, Mapping) else {},
            risk,
            profile,
            conversation_turn_count,
        )

    @staticmethod
    def _looks_like_profile(value: Any) -> bool:
        if isinstance(value, BehaviorProfile):
            return True
        return isinstance(value, Mapping) and any(k in value for k in ("warmth", "responsiveness", "guardedness"))

    @staticmethod
    def _looks_like_risk(value: Any) -> bool:
        if isinstance(value, RiskReport):
            return True
        return isinstance(value, Mapping) and any(k in value for k in ("risk_level", "vulnerability"))

    @staticmethod
    def _coerce_analysis(value: Any) -> ConversationAnalysis:
        if isinstance(value, ConversationAnalysis):
            return value
        if isinstance(value, Mapping):
            try:
                return ConversationAnalysis.model_validate(value)
            except:
                pass
        return ConversationAnalysis(
            intent=str(getattr(value, "intent", "分享生活")),
            vulnerability=int(getattr(value, "vulnerability", 50)),
            sexual_tension=int(getattr(value, "sexual_tension", 0)),
        )

    @staticmethod
    def _coerce_risk(value: Any) -> RiskReport:
        if isinstance(value, RiskReport):
            return value
        if isinstance(value, Mapping):
            try:
                return RiskReport.model_validate(value)
            except:
                pass
        return RiskReport(risk_level="low", vulnerability=int(getattr(value, "vulnerability", 40)))

    @staticmethod
    def _coerce_profile(
        value: Any,
        analysis: ConversationAnalysis,
        relationship_state: Mapping[str, Any],
        risk: RiskReport,
    ) -> BehaviorProfile:
        if isinstance(value, BehaviorProfile):
            return value
        if isinstance(value, Mapping) and StrategyPlanner._looks_like_profile(value):
            try:
                return BehaviorProfile.model_validate(value)
            except:
                pass
                
        # 修正：在兜底逻辑中，必须优先从已经分析出的结构化对象中提取真实脆弱度，决不能硬编码写死
        extracted_vuln = int(getattr(analysis, "vulnerability", getattr(risk, "vulnerability", 50)))
        
        return BehaviorProfile(
            warmth=60,
            responsiveness=65,
            playfulness=55,
            guardedness=45,
            emotional_need=70,
            vulnerability=extracted_vuln  # 动态打通数据流，阻断Bug
        )

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for v in values:
            text = str(v).strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
        return result


def _demo() -> None:
    planner = StrategyPlanner()
    # 模拟输入：测试在多重意图重叠时，系统是否能兼顾情绪承接和舒适边界。
    plan = planner.plan(
        ConversationAnalysis(
            intent="撒娇",
            emotion="委屈",
            vulnerability=75,
            sexual_tension=60,
            relationship_stage="L3"
        )
    )
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    _demo()
