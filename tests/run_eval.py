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


DEFAULT_FORBIDDEN = ["从你的描述来看", "你的情绪我理解", "我会认真分析", "让我们", "必须", "赶紧"]

GREETING_MESSAGES = [
    "你好",
    "hi",
    "哈喽",
    "在吗",
    "刚看到你",
    "晚上好",
    "嗨",
    "你在干嘛",
]

WORK_STRESS_MESSAGES = [
    "今天加班到现在，真的烦死了",
    "老板又催我项目，我快崩溃了",
    "同事把锅甩给我，气死",
    "这周会议好多，累麻了",
    "客户一直改需求，我真的无语",
    "绩效谈话搞得我压力好大",
    "工作到现在还没吃饭",
    "今天被老板说了，心情很差",
    "项目又延期了，我好烦",
    "加班加到怀疑人生",
    "明天还要早会，烦死了",
    "今天工作真的把我耗干了",
]

INVITE_MESSAGES = [
    "周末要不要一起吃个饭",
    "你这周有空吗，出来喝咖啡",
    "下次一起看电影吧",
    "要不要找天见面聊",
    "周六晚上出来走走吗",
    "我想吃火锅，一起吗",
    "有空一起去那家店",
    "下班后要不要喝一杯",
    "要不要出来透透气",
    "这周末你安排一下",
    "哪天一起吃饭呀",
    "我们找个时间见面吧",
]

JEALOUSY_MESSAGES = [
    "你最近是不是和别的女生聊得挺开心啊",
    "她是谁啊，看你回得挺快",
    "你是不是喜欢别人了",
    "和别人聊天比和我开心吗",
    "你朋友圈那个女生是谁",
    "你是不是对她也这样",
    "你还挺会哄别的女生",
    "我怎么感觉你没那么在意我",
]

COMFORT_MESSAGES = [
    "我今天有点难受，哄哄我",
    "突然很委屈，想哭",
    "我现在心里堵得慌",
    "没人懂我这种感觉",
    "我好累，想抱抱",
    "今天真的有点撑不住",
    "我有点emo，不知道跟谁说",
    "心情好差，陪我一会儿",
    "我不开心，你哄我一下",
    "今天破防了，难受",
]

LIFE_SHARE_MESSAGES = [
    "今天吃了一家还不错的面",
    "刚刚路过一家花店好漂亮",
    "我朋友今天给我带了奶茶",
    "今天家里停水了，好离谱",
    "我刚买了一个新杯子",
    "今天下班路上看到晚霞",
    "我家猫又在窗边发呆",
    "今天试了新口红",
    "我刚看完一集剧",
    "今天买菜遇到一个好热情的阿姨",
    "我刚做了个简单晚饭",
    "今天地铁好挤",
]

COLD_MESSAGES = [
    "哦",
    "嗯",
    "随便吧",
    "晚点说",
    "再说吧",
    "没空",
    "不知道",
    "先这样",
    "我有点忙",
    "不想说了",
]

BOUNDARY_TURN_MESSAGES = [
    ["别这样，有点太快了", "最近再说吧"],
    ["你这样我有点压力", "先别聊这个了"],
    ["别闹，我不太舒服", "晚点再说"],
    ["保持点距离吧", "我先忙了"],
    ["这个话题太快了", "算了先不说"],
    ["你别这么急", "我想慢一点"],
    ["先别安排那么多", "最近没空"],
    ["这样有点过了", "我们换个话题吧"],
]

LEADERSHIP_TURN_MESSAGES = [
    ["你安排就好，我听你的", "周末一起吃饭吧"],
    ["你决定吧，我都可以", "那这周见一下？"],
    ["看你安排，我没意见", "找天喝咖啡"],
    ["你来定地方吧", "周六有空"],
    ["你说了算", "下次一起去吃饭"],
    ["随便你安排", "我周末晚上可以"],
    ["你决定时间", "那我们见面聊"],
    ["听你的呀", "一起看电影也行"],
]

PET_MEMORY_TURN_MESSAGES = [
    ["我养了一只布偶猫", "它今天又拆家了"],
    ["我家有只英短", "猫今天把杯子推下去了"],
    ["我家猫叫团子", "它刚刚又躲起来了"],
    ["我养了一只美短猫", "猫今天一直蹭我"],
    ["我家有只狸花猫", "它今天又钻柜子了"],
    ["我家猫特别粘人", "它现在趴我腿上"],
    ["我家的橘猫最近胖了", "它又偷吃了"],
    ["我家猫叫可乐", "它今天一直叫"],
]


def load_cases(path: str | Path = "tests/fixtures/chat_eval_cases.json") -> list[dict[str, Any]]:
    """Load evaluation cases from disk."""
    base_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    return ensure_case_count(base_cases, target_count=100)


def ensure_case_count(base_cases: list[dict[str, Any]], *, target_count: int) -> list[dict[str, Any]]:
    """Return a deterministic evaluation set with at least ``target_count`` cases."""
    if len(base_cases) >= target_count:
        return base_cases[:target_count]
    needed = target_count - len(base_cases)
    return [*base_cases, *generated_cases()[:needed]]


def generated_cases() -> list[dict[str, Any]]:
    """Generate fixed regression cases that broaden common chat coverage."""
    cases: list[dict[str, Any]] = []
    cases.extend(_simple_cases("greeting", GREETING_MESSAGES, expected_intent="分享生活", max_favorability=20))
    cases.extend(
        _simple_cases(
            "work_stress",
            WORK_STRESS_MESSAGES,
            expected_intent="工作压力",
            expected_opportunity_action="安抚",
            max_favorability=40,
            min_confidence_wins=1,
            forbidden_phrases=["你应该", "别想太多", "从你的描述来看"],
        )
    )
    cases.extend(
        _simple_cases(
            "invite",
            INVITE_MESSAGES,
            expected_intent="邀约",
            expected_opportunity_action="邀约",
            min_confidence_wins=1,
            min_favorability=10,
            max_favorability=65,
            forbidden_phrases=["让我们", "我会认真分析", "必须"],
        )
    )
    cases.extend(
        _simple_cases(
            "jealousy",
            JEALOUSY_MESSAGES,
            expected_intent="吃醋",
            max_favorability=50,
            forbidden_phrases=["你的情绪我理解", "无条件", "我全都给你"],
        )
    )
    cases.extend(
        _simple_cases(
            "comfort",
            COMFORT_MESSAGES,
            expected_opportunity_action="安抚",
            min_confidence_wins=1,
            max_favorability=45,
            forbidden_phrases=["别想太多", "你应该", "讲道理"],
        )
    )
    cases.extend(
        _simple_cases(
            "life_share",
            LIFE_SHARE_MESSAGES,
            expected_intent="分享生活",
            max_favorability=45,
            forbidden_phrases=["宠物话题很有趣", "从你的描述来看"],
        )
    )
    cases.extend(
        _simple_cases(
            "cold",
            COLD_MESSAGES,
            max_favorability=35,
            forbidden_phrases=["必须", "赶紧", "为什么不回", "别临时怂"],
        )
    )
    cases.extend(
        _turn_cases(
            "boundary",
            BOUNDARY_TURN_MESSAGES,
            expected_opportunity_action="收住",
            min_confidence_wins=1,
            max_favorability=35,
            forbidden_phrases=["必须", "赶紧", "现在就", "跟我算", "别临时怂"],
        )
    )
    cases.extend(
        _turn_cases(
            "leadership",
            LEADERSHIP_TURN_MESSAGES,
            expected_opportunity_action="邀约",
            min_confidence_wins=1,
            min_favorability=15,
            max_favorability=75,
            expected_profile_min={"leadership_preference": 60},
            expected_reply_any=["安排", "定", "时间", "地方", "周末", "可以"],
            forbidden_phrases=["你说怎样就怎样", "无条件", "听话"],
        )
    )
    cases.extend(
        _turn_cases(
            "memory_pet",
            PET_MEMORY_TURN_MESSAGES,
            max_favorability=50,
            expected_memory_contains=["猫"],
            forbidden_phrases=["宠物话题很有趣", "我会认真分析"],
        )
    )
    return cases


def _simple_cases(
    prefix: str,
    messages: list[str],
    *,
    expected_intent: str | None = None,
    expected_opportunity_action: str | None = None,
    min_confidence_wins: int | None = None,
    min_favorability: int | None = None,
    max_favorability: int | None = None,
    forbidden_phrases: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build one-message fixture cases."""
    result = []
    for index, message in enumerate(messages, 1):
        case: dict[str, Any] = {
            "name": f"auto_{prefix}_{index:02d}",
            "history": [{"role": "user", "content": message}],
            "forbidden_phrases": forbidden_phrases or DEFAULT_FORBIDDEN,
        }
        if expected_intent:
            case["expected_intent"] = expected_intent
        if expected_opportunity_action:
            case["expected_opportunity_action"] = expected_opportunity_action
        if min_confidence_wins is not None:
            case["min_confidence_wins"] = min_confidence_wins
        if min_favorability is not None:
            case["min_favorability"] = min_favorability
        if max_favorability is not None:
            case["max_favorability"] = max_favorability
        result.append(case)
    return result


def _turn_cases(
    prefix: str,
    histories: list[list[str]],
    *,
    expected_opportunity_action: str | None = None,
    min_confidence_wins: int | None = None,
    min_favorability: int | None = None,
    max_favorability: int | None = None,
    expected_profile_min: dict[str, int] | None = None,
    expected_memory_contains: list[str] | None = None,
    expected_reply_any: list[str] | None = None,
    forbidden_phrases: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build turn-by-turn fixture cases."""
    result = []
    for index, history in enumerate(histories, 1):
        case: dict[str, Any] = {
            "name": f"auto_{prefix}_{index:02d}",
            "turn_by_turn": True,
            "history": [{"role": "user", "content": message} for message in history],
            "forbidden_phrases": forbidden_phrases or DEFAULT_FORBIDDEN,
        }
        if expected_opportunity_action:
            case["expected_opportunity_action"] = expected_opportunity_action
        if min_confidence_wins is not None:
            case["min_confidence_wins"] = min_confidence_wins
        if min_favorability is not None:
            case["min_favorability"] = min_favorability
        if max_favorability is not None:
            case["max_favorability"] = max_favorability
        if expected_profile_min:
            case["expected_profile_min"] = expected_profile_min
        if expected_memory_contains:
            case["expected_memory_contains"] = expected_memory_contains
        if expected_reply_any:
            case["expected_reply_any"] = expected_reply_any
        result.append(case)
    return result


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
        growth_support = result.growth_support.model_dump()
        opportunity = growth_support.get("opportunity", {})
        confidence = growth_support.get("confidence", {})
        if case.get("expected_opportunity_action") and opportunity.get("action") != case["expected_opportunity_action"]:
            expectation_failures.append(f"opportunity={opportunity.get('action')}")
        if case.get("min_confidence_wins") is not None:
            wins = confidence.get("wins", [])
            if len(wins) < int(case["min_confidence_wins"]):
                expectation_failures.append(f"confidence_wins_too_low={len(wins)}")
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
                "opportunity": opportunity,
                "confidence": confidence,
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
