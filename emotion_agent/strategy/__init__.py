"""Strategy components for response planning."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sitecustomize  # noqa: F401

from emotion_agent.strategy.base import BaseStrategySelector
from emotion_agent.strategy.reply_strategy import ReplyStrategy
from emotion_agent.strategy.strategy_planner import ReplyPlan, StrategyPlanner
from emotion_agent.strategy.strategy_selector import StrategySelector

__all__ = ["BaseStrategySelector", "ReplyPlan", "ReplyStrategy", "StrategyPlanner", "StrategySelector"]


def _demo() -> None:
    """Run a small package smoke test."""
    print("Strategy package ready")


if __name__ == "__main__":
    _demo()
