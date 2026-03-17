"""
意图识别反馈收集器

功能：
- 收集用户对识别结果的反馈
- 支持用户自定义正确的意图和输入内容
- 存储反馈数据供进化引擎使用
"""
import json
import os
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class IntentFeedback:
    """反馈数据"""
    message: str  # 用户原始输入
    ai_intent: str  # AI 识别结果
    correct_intent: Optional[str] = None  # 用户修正的意图
    user_input: Optional[str] = None  # 用户自定义输入（覆盖原始）
    comment: Optional[str] = None  # 备注
    timestamp: str = None  # 时间戳
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class FeedbackCollector:
    """反馈收集器"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # 默认路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(os.path.dirname(current_dir), "data", "feedback")
        
        self.data_dir = data_dir
        self.feedback_file = os.path.join(data_dir, "intent_feedback.json")
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        # 初始化文件
        if not os.path.exists(self.feedback_file):
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def add_feedback(
        self,
        message: str,
        ai_intent: str,
        correct_intent: str = None,
        user_input: str = None,
        comment: str = None
    ) -> bool:
        """
        添加反馈
        
        Args:
            message: 用户原始输入
            ai_intent: AI 识别结果
            correct_intent: 用户修正的意图（可选）
            user_input: 用户自定义输入（可选，会覆盖message）
            comment: 备注
            
        Returns:
            是否成功
        """
        try:
            # 读取现有反馈
            feedbacks = self._load_feedbacks()
            
            # 创建新反馈
            feedback = {
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "ai_intent": ai_intent,
            }
            
            if correct_intent:
                feedback["correct_intent"] = correct_intent
            if user_input:
                feedback["user_input"] = user_input
            if comment:
                feedback["comment"] = comment
            
            feedbacks.append(feedback)
            
            # 保存
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(feedbacks, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"[FeedbackCollector] 添加反馈失败: {e}")
            return False
    
    def _load_feedbacks(self) -> List[dict]:
        """加载所有反馈"""
        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def get_feedbacks(self) -> List[dict]:
        """获取所有反馈"""
        return self._load_feedbacks()
    
    def get_unprocessed_feedbacks(self) -> List[dict]:
        """获取未处理的反馈（用于进化）"""
        feedbacks = self._load_feedbacks()
        return [f for f in feedbacks if not f.get("processed", False)]
    
    def mark_processed(self, indices: List[int]):
        """标记已处理"""
        try:
            feedbacks = self._load_feedbacks()
            for i in indices:
                if 0 <= i < len(feedbacks):
                    feedbacks[i]["processed"] = True
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(feedbacks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[FeedbackCollector] 标记失败: {e}")
    
    def clear(self):
        """清空所有反馈"""
        with open(self.feedback_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)


# 单例
_collector = None

def get_collector() -> FeedbackCollector:
    """获取反馈收集器单例"""
    global _collector
    if _collector is None:
        _collector = FeedbackCollector()
    return _collector
