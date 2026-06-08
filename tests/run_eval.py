"""Lightweight evaluation runner for real chat-style cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emotion_agent.reply_pipeline import ReplyPipeline


def load_cases(path: str | Path = "tests/fixtures/chat_eval_cases.json") -> list[dict[str, Any]]:
    """Load evaluation cases from disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_cases() -> list[dict[str, Any]]:
    """Run the pipeline against the evaluation cases."""
    results: list[dict[str, Any]] = []
    for case in load_cases():
        memory_path = ROOT / "tests" / f"tmp_memory_{case['name']}.json"
        if memory_path.exists():
            memory_path.unlink()
        pipeline = ReplyPipeline(memory_path=memory_path)
        result = pipeline.run(case["history"])
        reply = result.final_reply
        forbidden_hits = [phrase for phrase in case.get("forbidden_phrases", []) if phrase in reply]
        expectation_failures: list[str] = []
        if case.get("expected_intent") and result.analysis.intent != case["expected_intent"]:
            expectation_failures.append(f"intent={result.analysis.intent}")
        if case.get("expected_stage") and result.relationship_state.get("stage") != case["expected_stage"]:
            expectation_failures.append(f"stage={result.relationship_state.get('stage')}")
        if case.get("expected_risk") and result.risk.risk_level != case["expected_risk"]:
            expectation_failures.append(f"risk={result.risk.risk_level}")
        favorability = float(result.relationship_state.get("favorability_score", 0.0))
        if case.get("min_favorability") is not None and favorability < float(case["min_favorability"]):
            expectation_failures.append(f"favorability_too_low={favorability}")
        if case.get("max_favorability") is not None and favorability > float(case["max_favorability"]):
            expectation_failures.append(f"favorability_too_high={favorability}")
        if case.get("expected_memory_contains"):
            memory_dump = json.dumps(result.memory, ensure_ascii=False)
            missing = [item for item in case["expected_memory_contains"] if item not in memory_dump]
            if missing:
                expectation_failures.append(f"memory_missing={','.join(missing)}")
        results.append(
            {
                "name": case["name"],
                "reply": reply,
                "intent": result.analysis.intent,
                "stage": result.relationship_state.get("stage"),
                "favorability": favorability,
                "favorability_label": result.relationship_state.get("favorability_label"),
                "risk": result.risk.risk_level,
                "memory": result.memory,
                "forbidden_hits": forbidden_hits,
                "expectation_failures": expectation_failures,
                "passed": not forbidden_hits and not expectation_failures,
            }
        )
        memory_path.unlink(missing_ok=True)
    return results


def main() -> None:
    """Run cases and print a simple JSON report."""
    print(json.dumps(run_cases(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
