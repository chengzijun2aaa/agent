"""Small command-line launcher for the emotion reply pipeline."""

from __future__ import annotations

import sys

from emotion_agent import ReplyPipeline
from emotion_agent.providers import DeepSeekProvider


def main() -> None:
    """Run the reply pipeline from command-line chat messages."""
    chat_history = sys.argv[1:] or ["你在干嘛"]
    pipeline = ReplyPipeline(llm=DeepSeekProvider(), memory_path="memory.json")
    result = pipeline.run(chat_history)
    print(result.final_reply)


if __name__ == "__main__":
    main()
