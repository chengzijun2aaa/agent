"""Advanced strategy planning based on continuous behavior profiling and neutral tactics."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from typing import Any, Mapping
from pydantic import BaseModel, ConfigDict, Field

# ============================================================
# 📊 1. 数据模型与画像系统 (Behavior Profile)
# ============================================================

class ConversationAnalysis(BaseModel):
    """Upstream conversation analysis output."""
    intent: str
    emotion: str
    interest_score: int
    relationship_stage: str
    risk_level: str = "low"
    user_raw_text: str = ""

class RiskReport(BaseModel):
    """Risk multi-dimensional evaluation."""
    support: int = 0      # 需要情感支持/倾听的迫切度 (0-100)
    conflict: int = 0     # 当前对话的冲突/火药味指数 (0-100)
    boundary: int = 0     # 对方试探边界/越界的程度 (0-100)
    crisis: int = 0       # 核心安全/关系危机指数 (0-100)
    risk_level: str = "low"

class BehaviorProfile(BaseModel):
    """Continuous behavioral snapshot of the user (0-100)."""
    warmth: int = Field(default=50, description="热情度：言语间的温度与亲和力")
    responsiveness: int = Field(default=50, description="响应度：回复速度、字数及接话意愿")
    playfulness: int = Field(default=50, description="接梗度：对幽默、调侃和开玩笑的接受度")
    guardedness: int = Field(default=50, description="防备心：对隐私、过快推进关系的抵触感")
    emotional_need: int = Field(default=50, description="情绪需求：当前对倾诉、安慰或认同的渴望度")

class ReplyPlan(BaseModel):
    """Concrete plan used by the reply generator (Maintains full compatibility)."""
    model_config = ConfigDict(extra="ignore")

    objective: str
    tone: str
    tactics: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    target_length: str = "short"
    candidate_count: int = 6


# ============================================================
# 🧠 2. 画像分析器 (Behavior Profiler)
# ============================================================

class BehaviorProfiler:
    """Generates a continuous 0-100 behavior profile from upstream analysis."""
    
    @staticmethod
    def profile(analysis: ConversationAnalysis, relationship_state: Mapping[str, Any]) -> BehaviorProfile:
        """Calculate continuous behavioral values instead of rigid classifications."""
        score = analysis.interest_score
        intent = analysis.intent
        
        # 初始默认中性值
        warmth = 50
        responsiveness = 50
        playfulness = 50
        guardedness = 50
        emotional_need = 50

        # 根据上游分析和兴趣分映射连续值
        if score > 70:
            warmth = min(90, 40 + (score // 2))
            responsiveness = min(95, 45 + (score // 2))
        elif score < 40:
            warmth = max(15, score - 10)
            responsiveness = max(20, score)
            guardedness = min(90, 100 - score)

        # 根据意图进行微调
        if intent in {"冷淡", "敷衍"}:
            responsiveness = max(10, responsiveness - 30)
            playfulness = max(10, playfulness - 30)
            guardedness = min(95, guardedness + 25)
        elif intent == "测试":
            guardedness = min(95, guardedness + 35)
            playfulness = min(80, playfulness + 10)  # 废测通常带点好玩性质
        elif intent in {"抱怨", "求安慰"}:
            emotional_need = min(95, emotional_need + 40)
            playfulness = max(15, playfulness - 25)  # 难过时不适合接梗
        elif intent in {"分享生活", "邀约"}:
            playfulness = min(85, playfulness + 15)

        return BehaviorProfile(
            warmth=warmth,
            responsiveness=responsiveness,
            playfulness=playfulness,
            guardedness=guardedness,
            emotional_need=emotional_need
        )


# ============================================================
# 🎯 3. 策略规划器 (Strategy Planner)
# ============================================================

class StrategyPlanner:
    """Plans responses using neutral, high-EQ tactics based oncontinuous user profiles."""

    def plan(
        self,
        analysis: Any,
        profile: Any,
        risk: Any,
        relationship_state: Mapping[str, Any],
        conversation_turn_count: int = 5,
    ) -> ReplyPlan:
        """Create a balanced reply plan using continuous variables and neutral tactics."""
        
        # 1. 🛡️ 全量防御层：动态兼容 dict 和 Pydantic 对象
        analysis_obj = ConversationAnalysis(**analysis) if isinstance(analysis, dict) else analysis
        profile_obj = BehaviorProfile(**profile) if isinstance(profile, dict) else profile
        risk_obj = RiskReport(**risk) if isinstance(risk, dict) else risk

        # 2. 🚨 【核心修复】把 user_text 的定义直接提取到最顶端，防止 free variable 报错
        user_text = getattr(analysis_obj, "user_raw_text", "") or ""
        intent = getattr(analysis_obj, "intent", "") or ""
        stage = str(analysis_obj.relationship_stage or relationship_state.get("stage", "L1"))
        
        # 初始化基础结构
        tactics = [f"关系阶段：{stage}"]
        avoid = ["长篇大论的说教", "过度解读对方的话", "刻意的套路和打压话术"]

        # 3. 🛡️ 自尊防御熔断器（现在 user_text 已经 association 完毕，绝对不会再报错）
        insult_keywords = ["傻卵", "傻x", "有病", "滚", "乐色", "死", "傻逼", "弱智"]
        has_insult = any(word in user_text.lower() for word in insult_keywords)

        if has_insult or risk_obj.conflict > 70 or risk_obj.boundary > 70:
            return ReplyPlan(
                objective="对方言语越界。我方保持绝对的情绪稳定和高位框架，不自证、不说教、不负气认输，用极简或无所谓的姿态终结对线。",
                tone="冷淡、极其简短、松弛且无所谓",
                tactics=[
                    "严格执行【极简冷冻】：回复字数控制在 10 个字以内，绝对不发反问句",
                    "严禁出现任何说教、教育、建议对方‘冷静/缓缓’的词汇",
                    "严禁出现‘我认输/多嘴/怪我’等负气和委屈的认输话术",
                    "可以采用完全置身事外的松弛态度，或者利落的单句客观终结"
                ],
                avoid=[
                    *avoid, "教对方做人", "指出对方脾气大/情绪激动", "低头认错", "阴阳怪气的自嘲",
                    "你情绪有点激动", "先缓缓吧", "算我多嘴", "我认输", "行行行"
                ],
                target_length="short",
                candidate_count=6  # 给足 6 条，方便你在前端挑选最清爽的
            )

        # 默认中性设定
        objective = "保持舒适、自然的同频沟通。"
        tone = "轻松、自然"

        # ============================================================
        # 4. 风险多维拆分处理层 (往下维持你原有的路由逻辑即可...)
        # ============================================================
        # 1. 危机处理 (Crisis) -> 最高优先级响应
        if risk_obj.crisis > 70 or analysis_obj.risk_level == "high":
            return ReplyPlan(
                objective="保持情绪高度抽离，提供安全的边界感，给予理智而客观的缓冲。",
                tone="理性、克制、边界感明确",
                tactics=["使用情绪阻断技术，明确表示理性克制", "给出客观的缓冲地带，不盲目卷入纠纷"],
                avoid=[*avoid, "盲目站队", "过于亲密的安抚"],
                candidate_count=3
            )
        
        # ... 后续逻辑保持不变 ...
        # ============================================================
        # 🛡️ 风险多维拆分处理层
        # ============================================================
        
        # 1. 危机处理 (Crisis) -> 最高优先级响应
        if risk_obj.crisis > 70 or analysis_obj.risk_level == "high":
            return ReplyPlan(
                objective="保持情绪高度抽离，提供安全的边界感，给予理智而客观的缓冲。",
                tone="理性、克制、边界感明确",
                tactics=["使用情绪阻断技术，明确表示理性克制", "给出客观的缓冲地带，不盲目卷入纠纷"],
                avoid=[*avoid, "盲目站队", "过于亲密的安抚"],
                candidate_count=3
            )
            
        # 2. 冲突缓冲 (Conflict)
        elif risk_obj.conflict > 50:
            return ReplyPlan(
                objective="不承接对立情绪，通过平和、客观的态度中和当前的紧绷感。",
                tone="情绪稳定、大度、温和",
                tactics=["承接对立情绪，用不带攻击性的中性语言回应", "淡化冲突焦点，将话题带回理性沟通范围"],
                avoid=[*avoid, "自证清白", "反向指责", "阴阳怪气"],
                candidate_count=4
            )

        # 3. 边界防御 (Boundary)
        elif risk_obj.boundary > 60:
            objective = "明确个人边界，不卑不亢，用轻松但坚定的话术表明立场。"
            tone = "坦诚、清爽、有原则"
            tactics.append("执行【边界感】策略：用坦诚直接的语言标明底线，拒绝越界")
            avoid.extend(["无底线退让", "讨好式顺从"])

        # 4. 情感支持 (Support)
        elif risk_obj.support > 60 or profile_obj.emotional_need > 75:
            objective = "提供高质量的倾听空间，通过共情提供安全感。"
            tone = "温柔、真诚、有支撑感"
            tactics.append("执行【支持/共情】策略：顺应对方的负面情绪，通过倾听和认同提供包容空间")
            avoid.extend(["开玩笑调侃", "理性分析讲道理", "转移话题"])

        # ============================================================
        # 📊 核心多维画像动态调配层
        # ============================================================
        else:
            # A. 处理高防备心 / 低热情 (Guardedness / Low Warmth) -> 慢热冷淡
            if profile_obj.guardedness > 70 or profile_obj.warmth < 40:
                objective = "降低聊天压迫感，给对方留出舒适的社交距离。"
                tone = "松弛、淡定、恰到好处的社交距离"
                tactics.append("执行【轻松】策略：以分享日常或轻松客观的事物开场，不带任何目的性")
                avoid.extend(["高频发问", "过度热情的迎合"])
                
                # 如果同时响应度也极低，果断选择合适时机结束
                if profile_obj.responsiveness < 30:
                    objective = "得体、自然地收尾，不消耗无谓的社交精力。"
                    tactics.append("执行【结束话题】策略：用礼貌、无压力的结束语利落收尾，留白")

            # B. 处理高接梗度 / 高热情 (High Playfulness / High Warmth) -> 氛围良好
            elif profile_obj.playfulness > 60 and profile_obj.warmth >= 50:
                objective = "放大互动中的趣味性，拉近彼此的心理距离。"
                tone = "风趣、活泼、富有张力"
                tactics.append("执行【调侃】策略：抓住对方话语中有趣的切入点进行幽默延伸，可以带有轻微的恶作剧意味")
                
                # 如果关系到了中后期，顺势推进
                if stage in {"L3", "L4", "L5"}:
                    tactics.append("执行【推进关系】策略：在轻松气氛中植入共享语境或未来的模糊交集")
            
            # C. 常规中性互动
            else:
                objective = "进行对等、舒适的情绪流动。"
                tone = "随性、朋友间的熟稔"
                tactics.append("执行【轻松】策略：保持同频的字数和节奏进行自然回应")

        # ============================================================
        # ⏱️ 长线对话控制机制 (Turn Controller)
        # ============================================================
        if conversation_turn_count >= 8 and profile_obj.emotional_need < 60:
            objective = "在交谈情绪饱满的时候优雅离场，不过度消耗话题舒适度。"
            tactics.append("执行【结束话题】策略：主动以‘去处理事情/去运动’等正面理由大方离场")
            avoid.extend(["恋战式硬找话题", "询问式结尾"])

        # 过滤可能通过别的方式漏进来的猫
        tactics = [t for t in tactics if "猫" not in t]
        
        user_text = getattr(analysis_obj, "user_raw_text", "") or ""
        if "猫" not in user_text and analysis_obj.intent != "宠物话题":
            avoid.append("绝对禁止主动提起‘猫’或任何关于宠物的段子/烂梗")

        avoid.append("在一句话中连续使用问号（除非用于温和的幽默反问）")

        return ReplyPlan(
            objective=objective,
            tone=tone,
            tactics=tactics,
            avoid=avoid,
            candidate_count=6
        )