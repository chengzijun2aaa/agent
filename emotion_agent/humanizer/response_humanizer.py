from __future__ import annotations
import random
import re
from typing import List, Tuple

# 模拟缺失的依赖，方便直接运行调试
class Message:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

class AgentContext:
    def __init__(self, user_id: str, current_message: Message, recent_messages: list, state: dict):
        self.user_id = user_id
        self.current_message = current_message
        self.recent_messages = recent_messages
        self.state = state

class GenerationResult:
    def __init__(self, text: str):
        self.text = text

class BaseHumanizer:
    pass


class ResponseHumanizer(BaseHumanizer):
    """把AI回复变成真实、有框架的男人随手发的微信 (优化版)"""

    def humanize(self, context: AgentContext, draft: GenerationResult) -> GenerationResult:
        text = (draft.text or "").strip()
        if not text:
            draft.text = "嗯？"
            return draft

        # 1. 语义降级（去AI味）
        text = self._remove_ai_tone(text)
        
        # 2. 结构重组（短句化与截断）
        text = self._shorten(text)
        
        # 3. 乱序/口语节奏（加入停顿）
        text = self._add_rhythm(text)
        
        # 4. 真实感与框架（后缀控制，避免重复累加）
        text = self._add_imperfection_and_frame(text, context)

        draft.text = text.strip()
        return draft

    def _remove_ai_tone(self, text: str) -> str:
        """去除咨询师/高情商模板，转为大白话"""
        replacements: List[Tuple[str, str]] = [
            (r"我理解你(现在)?", "懂了"),
            (r"你的情绪", ""),
            (r"先缓一口气", "喘口气"),
            (r"你可以", "你就"),
            (r"我听着呢", "说"),
            (r"提供支持", ""),
            (r"情绪价值", ""),
            (r"我会一直陪着你的", "我在"),
            (r"真的很难受", "挺难熬"),
        ]
        # 使用正则替换，支持更灵活的匹配
        for pattern, repl in replacements:
            text = re.sub(pattern, repl, text)
        return text

    def _shorten(self, text: str) -> str:
        """强制短小精悍，按标点或合理位置截断，避免生硬切字"""
        if len(text) <= 35:
            return text
            
        # 尝试在最后的标点符号处截断，而不是硬切
        split_pts = [m.start() for m in re.finditer(r"[，。！？、\s]", text)]
        valid_pts = [p for p in split_pts if 20 <= p <= 35]
        
        if valid_pts:
            text = text[:max(valid_pts)] + "…"
        else:
            # 如果没有合适的标点，再进行物理截断
            text = text[:30].rstrip() + "…"
        return text

    def _add_rhythm(self, text: str) -> str:
        """增加口语节奏（将部分逗号替换为真人打字的空格或省略号）"""
        if "，" in text and random.random() > 0.5:
            # 随机把第一个逗号换成空格或空格+点，模拟微信打断
            text = text.replace("，", random.choice([" ", "… "]), 1)
        return text

    def _add_imperfection_and_frame(self, text: str, context: AgentContext) -> str:
        """统一控制不完美感与高价值框架，避免后缀堆叠"""
        # 剥离原有的句尾强标点
        text = text.rstrip("。！？ ")
        
        rand = random.random()
        
        # 语气词库分类
        high_value_suffixes = ["，问题不大", "，行了", "，先这样"]
        lazy_suffixes = ["…", " 哈", " 嗯？", ""]
        
        if len(text) < 25:
            if rand > 0.85:
                text += random.choice(high_value_suffixes)
            elif rand > 0.60:
                text += random.choice(lazy_suffixes)
            else:
                text += "…" if not text.endswith("…") else ""
        else:
            if rand > 0.7:
                text += "…"
                
        return text


if __name__ == "__main__":
    # 测试运行
    h = ResponseHumanizer()
    draft = GenerationResult(text="我理解你现在很难受，先缓一口气，我会一直陪着你的。")
    ctx = AgentContext(
        user_id="test",
        current_message=Message(role="USER", content="今天好累想哭"),
        recent_messages=[],
        state={}
    )
    
    # 模拟多次运行看随机效果
    print("--- 优化后生成测试 ---")
    for _ in range(5):
        print(h.humanize(ctx, draft).text)