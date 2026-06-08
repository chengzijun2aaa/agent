"""Small command-line launcher for the emotion reply pipeline."""

from __future__ import annotations

import os
import sys

from emotion_agent import ReplyPipeline
from emotion_agent.providers import ClaudeProvider, DeepSeekProvider, GeminiProvider, OpenAIProvider


def create_llm_provider() -> object:
    """Create a provider for CLI runs; DeepSeek is the restored default."""
    provider_name = os.getenv("EMOTION_AGENT_PROVIDER", "deepseek").strip().lower()
    providers = {
        "deepseek": DeepSeekProvider,
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "gemini": GeminiProvider,
    }
    return providers.get(provider_name, DeepSeekProvider)()


def main() -> None:
    """Run the reply pipeline from command-line chat messages."""
    chat_history = sys.argv[1:] or ["你在干嘛"]
    pipeline = ReplyPipeline(llm=create_llm_provider(), memory_path="memory.json")
    result = pipeline.run(chat_history)
    print(result.final_reply)


if __name__ == "__main__":
    main()
