"""Application composition root for the WeChat emotion chat agent."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

import os
from dataclasses import dataclass
from typing import Sequence, Any

from emotion_agent.analyzers.base import BaseAnalyzer
from emotion_agent.analyzers.emotion_analyzer import EmotionAnalyzer
from emotion_agent.analyzers.intent_analyzer import IntentAnalyzer
from emotion_agent.analyzers.risk_analyzer import RiskAnalyzer
from emotion_agent.generator.response_generator import ResponseGenerator
from emotion_agent.humanizer.response_humanizer import ResponseHumanizer
from emotion_agent.memory.conversation_memory import ConversationMemory
from emotion_agent.providers.provider_factory import ProviderFactory
from emotion_agent.ranker.response_ranker import ResponseRanker
from emotion_agent.state.conversation_state import ConversationState
from emotion_agent.storage.memory_storage import InMemoryStorage
from emotion_agent.strategy.strategy_selector import StrategySelector
from emotion_agent.utils.config import AgentConfig
from emotion_agent.utils.types import AgentContext, GenerationResult, Message, SenderRole

# 💡 引入刚刚实现的多用户会话存储管理器
# 如果你写在独立文件里，改成：from emotion_agent.storage.session_manager import SessionStorageManager
# 暂且为了演示，我们假设它存在或通过底层调度
from emotion_agent.storage.session_manager import SessionStorageManager


@dataclass(slots=True)
class EmotionChatAgent:
    """Coordinates high-level agent components without embedding business rules."""

    config: AgentConfig
    analyzers: Sequence[BaseAnalyzer]
    strategy_selector: StrategySelector
    generator: ResponseGenerator
    humanizer: ResponseHumanizer
    ranker: ResponseRanker
    
    # 💡 移除原本硬编码的单一 memory 和 state 属性
    # 替换为具备多账号隔离能力的 session_manager
    session_manager: SessionStorageManager

    def handle_message(self, user_id: str, message: str) -> GenerationResult:
        """Run the architectural pipeline with full multi-session isolation."""
        
        # 1. 🛡️ 隔离路由：根据当前传过来的“聊天命名/user_id”精准捞取她的记忆和状态
        memory, state = self.session_manager.load_session(user_id)
        
        # 2. 动态装配这一轮对线的 AgentContext
        inbound = Message(role=SenderRole.USER, content=message)
        context = AgentContext(
            user_id=user_id,
            current_message=inbound,
            recent_messages=memory.get_recent() if hasattr(memory, "get_recent") else [],
            state=state,
        )
        
        # 3. 核心管线开始轰鸣（只针对当前 user_id 的上下文环境计算）
        analyses = [analyzer.analyze(context) for analyzer in self.analyzers]
        strategy = self.strategy_selector.select(context=context, analyses=analyses)
        draft = self.generator.generate(context=context, strategy=strategy, analyses=analyses)
        humanized = self.humanizer.humanize(context=context, draft=draft)
        
        # 4. 排序器决定最优候选
        ranked = self.ranker.rank(context=context, candidates=[humanized])
        
        # 5. 💡 状态回写机制：将本轮更新后的记忆和策略数值安全持久化
        # 假设你的 memory 支持添加新消息
        if hasattr(memory, "add_message"):
            memory.add_message(inbound)
            memory.add_message(Message(role=SenderRole.ASSISTANT, content=ranked.result.text))
            
        self.session_manager.save_session(user_id, memory, state)
        
        return ranked.result


def build_default_agent(config: AgentConfig | None = None) -> EmotionChatAgent:
    """Build a default agent object graph for development and smoke testing."""
    resolved_config = config or AgentConfig()
    provider_factory = ProviderFactory.with_default_providers()
    provider = provider_factory.create(resolved_config.default_provider)

    return EmotionChatAgent(
        config=resolved_config,
        analyzers=(EmotionAnalyzer(), IntentAnalyzer(), RiskAnalyzer()),
        strategy_selector=StrategySelector.default(),
        generator=ResponseGenerator(provider=provider),
        humanizer=ResponseHumanizer(),
        ranker=ResponseRanker(),
        
        # 💡 组装根注入多会话管理器，默认将数据存在项目 root 的 data/sessions 下
        session_manager=SessionStorageManager(data_dir="data/sessions"),
    )


def main() -> None:
    """Run a minimal smoke test for the composed architecture with different girls."""
    agent = build_default_agent()
    print(f"Agent ready: {agent.__class__.__name__}")
    
    # 🧪 测试多账号隔离：给不同的聊天命名进行连续压测
    
    # 战局 A：小林 (高防备)
    res_lin = agent.handle_message(user_id="girl_xiaolin", message="你好")
    print(f"[小林战局] 响应: {res_lin.text!r}")
    
    # 战局 B：薇薇 (暧昧期)
    res_vivi = agent.handle_message(user_id="girl_vivi", message="干嘛呢")
    print(f"[薇薇战局] 响应: {res_vivi.text!r}")


if __name__ == "__main__":
    main()