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
        result = run_case_pipeline(pipeline, case)
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
        for key, minimum in case.get("expected_profile_min", {}).items():
            value = result.memory.get("profile", {}).get(key, 0)
            if float(value) < float(minimum):
                expectation_failures.append(f"profile_{key}_too_low={value}")
        if case.get("expected_reply_any"):
            if not any(item in reply for item in case["expected_reply_any"]):
                expectation_failures.append("reply_missing_expected_signal")
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


def run_case_pipeline(pipeline: ReplyPipeline, case: dict[str, Any]) -> Any:
    """Run one case either as a single batch or turn-by-turn server simulation."""
    if not case.get("turn_by_turn"):
        return pipeline.run(case["history"])

    simulated_history: list[dict[str, str]] = []
    result = None
    for raw_item in case["history"]:
        item = normalize_eval_message(raw_item)
        simulated_history.append(item)
        if item["role"] == "user":
            result = pipeline.run(simulated_history[-20:])
            simulated_history.append({"role": "assistant", "content": result.final_reply})
    if result is None:
        result = pipeline.run(simulated_history[-20:])
    return result


def normalize_eval_message(item: Any) -> dict[str, str]:
    """Normalize one fixture message into the chat server shape."""
    if isinstance(item, str):
        return {"role": "user", "content": item}
    return {"role": str(item.get("role", "user")), "content": str(item.get("content", ""))}


def main() -> None:
    """Run cases and print a simple JSON report."""
    print(json.dumps(run_cases(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
