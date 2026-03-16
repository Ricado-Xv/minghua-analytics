"""
对话记录器
"""
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict


@dataclass
class ConversationEntry:
    id: str
    timestamp: str
    user_message: str
    intent: str
    params: Dict
    reply: str
    success: bool


class StorageAdapter:
    def save(self, data: List[Dict], file_path: str):
        raise NotImplementedError
    def load(self, file_path: str) -> List[Dict]:
        raise NotImplementedError


class JSONStorageAdapter(StorageAdapter):
    def save(self, data: List[Dict], file_path: str):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    def load(self, file_path: str) -> List[Dict]:
        if not os.path.exists(file_path):
            return []
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)


class ConversationLogger:
    def __init__(self, project_root: str = None, storage: str = "json", storage_file: str = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.storage_type = storage
        
        if storage_file:
            self.storage_file = storage_file
        else:
            self.storage_file = os.path.join(self.project_root, "data", "conversations", "conversations.json")

        if storage == "json":
            self.storage = JSONStorageAdapter()
        else:
            raise NotImplementedError("数据库存储方式暂未实现")

        self._conversations: List[Dict] = []
        self._load()

    def _load(self):
        self._conversations = self.storage.load(self.storage_file)

    def _save(self):
        self.storage.save(self._conversations, self.storage_file)

    def log(self, user_message: str, intent: str, params: Dict, reply: str, success: bool = True) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        conv_id = f"conv_{timestamp}"

        entry = ConversationEntry(
            id=conv_id,
            timestamp=datetime.now().isoformat(),
            user_message=user_message,
            intent=intent,
            params=params,
            reply=reply,
            success=success
        )

        self._conversations.append(asdict(entry))
        self._save()
        return conv_id

    def get_history(self, limit: int = 100) -> List[Dict]:
        return self._conversations[-limit:] if self._conversations else []

    def get_recent_conversations(self, hours: int = 24) -> List[Dict]:
        now = datetime.now()
        recent = []
        for conv in self._conversations:
            conv_time = datetime.fromisoformat(conv["timestamp"])
            if (now - conv_time).total_seconds() <= hours * 3600:
                recent.append(conv)
        return recent

    def export_for_ai(self, limit: int = 50) -> str:
        recent = self.get_history(limit)
        if not recent:
            return "暂无对话记录"
        lines = ["=== 最近对话记录 ==="]
        for conv in recent:
            lines.append(f"\n【{conv['timestamp']}】")
            lines.append(f"用户：{conv['user_message']}")
            lines.append(f"意图：{conv['intent']}")
            lines.append(f"回复：{conv['reply']}")
        return "\n".join(lines)

    def clear(self):
        self._conversations = []
        self._save()

    def switch_storage(self, storage: str, **kwargs):
        if storage == "json":
            self.storage = JSONStorageAdapter()
            self.storage_type = storage
        else:
            raise NotImplementedError(f"不支持的存储方式: {storage}")
