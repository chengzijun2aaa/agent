import os
import json
from pathlib import Path
from emotion_agent.memory.conversation_memory import ConversationMemory
from emotion_agent.state.conversation_state import ConversationState

class SessionStorageManager:
    """负责根据不同的聊天命名(user_id)物理隔离并持久化存储记忆与状态。"""
    def __init__(self, data_dir: str = "data/sessions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, user_id: str) -> Path:
        return self.data_dir / f"{user_id}.json"

    def load_session(self, user_id: str) -> tuple[ConversationMemory, ConversationState]:
        """动态加载特定女生的会话历史与画像状态"""
        file_path = self._get_path(user_id)
        
        # 初始化干净的上下文
        memory = ConversationMemory()
        state = ConversationState.new()
        
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # 💡 假设你的 Memory 和 State 实现了 to_dict / from_dict，或者直接恢复数据
                    # 这里如果是自定义类，需要实现对应的反序列化。以下为标准填充逻辑：
                    if "history" in data:
                        # 假设 memory 内部维护一个 messages 列表，直接灌入
                        memory.messages = data["history"]
                    if "state_data" in data:
                        # 假设状态支持字典解包
                        state.update_from_dict(data["state_data"]) 
            except Exception as e:
                print(f"读取 {user_id} 档案失败，执行默认创建: {e}")
                
        return memory, state

    def save_session(self, user_id: str, memory: ConversationMemory, state: ConversationState):
        """将此女生的最新互动记忆与状态序列化落盘"""
        file_path = self._get_path(user_id)
        
        # 提取需要存盘的字典结构
        session_data = {
            "history": getattr(memory, "messages", []),
            "state_data": state.to_dict() if hasattr(state, "to_dict") else vars(state)
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=4)