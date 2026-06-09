"""Strategy Planner - PUA高价值框架版（层层递进战略）"""

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
    """PUA高价值框架决策引擎 - 层层递进"""

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

        # ==================== PUA高价值框架决策（重构优先级解耦策略踩踏） ====================
        
        # 核心升级：如果意图已经显性触发“暧昧/性张力/撒娇”，即便脆弱度高，也绝不转为纯长辈式安慰，而是高价值拉扯
        if intent in {"撒娇", "性暗示"} or sexual_tension >= 60:
            objective = "回应她的信号，同时制造轻微张力"
            tone = "松弛、带点坏、保持框架"
            action_type = "轻暧昧拉扯"
            tactics = [
                "先自然接住她的撒娇或暗示，用轻调侃或反差回应",
                "不要立刻猛烈升级过度承诺，保持高价值男性的节奏感",
                "如果她同时表达了脆弱，在拉扯尾端给一句极其精准的专属偏爱，形成‘大叔与坏小子’的复合张力"
            ]

        elif intent in {"求安慰", "抱怨", "分享情绪", "工作压力"} or vuln >= 70:
            objective = "先接住情绪建立安全感，再寻找时机拉回高价值框架"
            tone = "稳重、温暖、具备绝对主导感"
            action_type = "接情绪"
            tactics = [
                "真实接住她的情绪，高价值男性绝不讲大道理，也不做无意义的复读机安慰",
                "提供内核稳定的情绪黑洞支撑，让她产生‘天塌下来有你托底’的错觉",
                "前期重点是提供高舒适度，避免闺蜜式连续追问，适时切入带领性话题"
            ]

        elif intent == "邀约" or (favor_release >= 60 and escalation != "low"):
            objective = "趁热打铁，高姿态主导推进"
            tone = "果断、带领、不纠结"
            action_type = "邀约推进"
            tactics = [
                "明确回应并给出方向，我来安排，你来出席即可",
                "提供确定性的模糊邀约或用选择题降低对方的防备压力",
                "建立见面后的轻松预期，绝不为了见一面而拉低姿态投其所好"
            ]

        elif intent in {"测试", "框架挑战", "吃醋"}:
            objective = "稳住核心框架，降维反向筛选价值"
            tone = "戏谑 + 情绪稳定 + 高姿态"
            action_type = "框架应对"
            tactics = [
                "不慌张、不解释、不自证，视其为小女孩的无闹取闹",
                "使用轻度幽默进行推拉，或者通过反向资格审视反客为主",
                "在框架彻底夯实后给一点甜头或确定感，避免演变成真正的对抗"
            ]

        elif intent in {"冷淡", "敷衍", "撤退"}:
            objective = "优雅后撤，利用神秘感重新建立吸引"
            tone = "极致松弛 + 神秘距离感"
            action_type = "后撤"
            tactics = [
                "精简回复字数，不提供多余的情绪输出，斩断其对你的特权感",
                "利落切断话题或留下微小的钩子，主动离场以降低需求感",
                "将主动权和情绪反弹的空间留给对方，静待她下一次破冰"
            ]

        else:
            objective = "建立多维吸引，制造良性情绪波动"
            tone = "风趣 + 游刃有余 + 有底线"
            action_type = "调侃"
            tactics = [
                "轻松接话并在对话中加入轻微的情绪推拉",
                "侧面无形展示高价值生活方式或认知，不追着聊，随时准备撤回",
                "在话题结束时留下可延伸的情绪口子"
            ]

        # 通用框架层层递进约束
        tactics.extend([
            f"动态框架参数 -> 阶段: {stage} | 当前意图: {intent} | 综合脆弱度: {vuln} | 实时性张力: {sexual_tension}",
            "严控自我节奏：高价值核心是不盲目自证，不随对方的情绪试探而频繁起伏",
            "推进铁律：前期做好深层情绪推拉与共鸣，严禁在舒适度未达标前盲目暴露显性需求感",
            "不可触碰的红线：任何阶段都必须有底线思维，不对无理试探进行任何妥协式跪舔"
        ])

        return ReplyPlan(
            objective=objective,
            tone=tone,
            action_type=action_type,
            emotional_need="被看见，同时感到被高价值雄性吸引",
            relationship_move="自然且在绝对框架内掌控推进节奏",
            tactics=self._dedupe(tactics),
            avoid=["低情商废话安慰", "过度共情导致失去雄性带领感", "闺蜜式陪聊泥潭", "油腻的工业糖精话术", "暴露饥渴感和特权感"],
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
    # 模拟输入：测试在多重意图重叠（撒娇且高脆弱度）时，高价值拉扯机制是否能够成功跑通，而不被错误下沉
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