"""Application composition root for the WeChat emotion chat agent."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from dataclasses import dataclass
from typing import Sequence

from emotion_agent.analyzers.base import BaseAnalyzer
from emotion_agent.analyzers.conversation_analyzer import ConversationAnalyzer
from emotion_agent.analyzers.emotion_analyzer import EmotionAnalyzer
from emotion_agent.analyzers.risk_analyzer import RiskAnalyzer
from emotion_agent.generator.response_generator import ResponseGenerator
from emotion_agent.humanizer.response_humanizer import ResponseHumanizer
from emotion_agent.providers.provider_factory import ProviderFactory
from emotion_agent.ranker.response_ranker import ResponseRanker
from emotion_agent.storage.session_manager import SessionStorageManager
from emotion_agent.strategy.strategy_selector import StrategySelector
from emotion_agent.strategy.strategy_planner import StrategyPlanner
from emotion_agent.utils.config import AgentConfig
from emotion_agent.utils.types import AgentContext, GenerationResult, Message, SenderRole


@dataclass(slots=True)
class EmotionChatAgent:
    """Long-lived WeChat emotional chat agent."""

    config: AgentConfig
    analyzers: Sequence[BaseAnalyzer]
    strategy_selector: StrategySelector
    planner: StrategyPlanner
    generator: ResponseGenerator
    humanizer: ResponseHumanizer
    ranker: ResponseRanker
    session_manager: SessionStorageManager

    def handle_message(self, user_id: str, message: str) -> GenerationResult:
        memory, state = self.session_manager.load_session(user_id)
        
        inbound = Message(role=SenderRole.USER, content=message)
        context = AgentContext(
            user_id=user_id,
            current_message=inbound,
            recent_messages=memory.get_recent() if hasattr(memory, "get_recent") else [],
            state=state,
        )

        analyses = [analyzer.analyze(context) for analyzer in self.analyzers]
        strategy = self.strategy_selector.select(context=context, analyses=analyses)
        
        plan = self.planner.plan(
            analysis=analyses[0] if analyses else None,
            relationship_state=state
        )

        draft_list = self.generator.generate(
            chat_history=context.recent_messages + [inbound],
            plan=plan,
            relationship_state=state,
            memory=memory.__dict__ if hasattr(memory, "__dict__") else {}
        )
        
        final_draft = draft_list[0] if isinstance(draft_list, list) and draft_list else draft_list
        humanized = self.humanizer.humanize(context=context, draft=final_draft)
        ranked = self.ranker.rank(context=context, candidates=[humanized])

        if hasattr(memory, "add_message"):
            memory.add_message(inbound)
            memory.add_message(Message(role=SenderRole.ASSISTANT, content=ranked.result.text))
            
        self.session_manager.save_session(user_id, memory, state)
        return ranked.result


def build_conquest_agent(config: AgentConfig | None = None) -> EmotionChatAgent:
    """Build the default relationship progression agent."""
    resolved_config = config or AgentConfig()
    provider_factory = ProviderFactory.with_default_providers()
    provider = provider_factory.create(resolved_config.default_provider)

    return EmotionChatAgent(
        config=resolved_config,
        analyzers=(
            ConversationAnalyzer(llm=provider),
            EmotionAnalyzer(),
            RiskAnalyzer(),
        ),
        strategy_selector=StrategySelector.default(),
        planner=StrategyPlanner(),
        generator=ResponseGenerator(provider=provider),
        humanizer=ResponseHumanizer(),
        ranker=ResponseRanker(),
        session_manager=SessionStorageManager(data_dir="data/sessions"),
    )


# ==================== 兼容旧代码 ====================
def build_default_agent(config: AgentConfig | None = None) -> EmotionChatAgent:
    """兼容 chat_server.py 等旧代码的导入"""
    return build_conquest_agent(config)


def main() -> None:
    """测试入口"""
    agent = build_conquest_agent()
    print("【微信情感聊天 Agent】已启动\n")

    tests = [
        ("girl_xiaolin", "你好，今天好累想哭"),
        ("girl_vivi", "干嘛呢？想你了"),
    ]
    for user_id, msg in tests:
        res = agent.handle_message(user_id=user_id, message=msg)
        print(f"【{user_id}】 ← {msg}")
        print(f"【AI回复】 → {res.text}\n")


if __name__ == "__main__":
    main()
