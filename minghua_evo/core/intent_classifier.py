"""
意图识别器
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from enum import Enum


class IntentType(Enum):
    VIEW_WEEKLY_REPORT = "VIEW_WEEKLY_REPORT"
    VIEW_MONTHLY_REPORT = "VIEW_MONTHLY_REPORT"
    VIEW_CROSS_WEEK = "VIEW_CROSS_WEEK"
    QUERY_STORES = "QUERY_STORES"
    QUERY_FRUITS = "QUERY_FRUITS"
    GENERATE_REPORT = "GENERATE_REPORT"
    CUSTOM = "CUSTOM"


@dataclass
class Intent:
    type: IntentType
    confidence: float
    params: Dict
    raw_message: str


class IntentClassifier:
    RULES = {
        IntentType.VIEW_WEEKLY_REPORT: [r"周报", r"本周", r"这周", r"上一周", r"上一周周报"],
        IntentType.VIEW_MONTHLY_REPORT: [r"月报", r"本月", r"月度", r"一个月"],
        IntentType.VIEW_CROSS_WEEK: [r"跨周", r"对比", r"趋势"],
        IntentType.QUERY_STORES: [r"店铺", r"门店", r"哪家店"],
        IntentType.QUERY_FRUITS: [r"水果", r"哪种.*好卖"],
        IntentType.GENERATE_REPORT: [r"生成.*报", r"制作.*报"],
    }

    def __init__(self):
        self.custom_handlers: List[Callable] = []

    def classify(self, message: str) -> Intent:
        message = message.strip()
        for intent_type, patterns in self.RULES.items():
            for pattern in patterns:
                if re.search(pattern, message):
                    params = self._extract_params(message, intent_type)
                    return Intent(type=intent_type, confidence=0.9, params=params, raw_message=message)
        
        for handler in self.custom_handlers:
            result = handler(message)
            if result:
                return result
        
        return Intent(type=IntentType.CUSTOM, confidence=0.5, params={"raw": message}, raw_message=message)

    def _extract_params(self, message: str, intent_type: IntentType) -> Dict:
        params = {}
        
        # 识别"上一周"
        if "上一周" in message:
            params["week_offset"] = -1  # 上一周
        
        month_match = re.search(r"(\d+)月", message)
        if month_match:
            params["month"] = month_match.group(1)
        week_match = re.search(r"第(\d+)周", message)
        if week_match:
            params["week"] = week_match.group(1)
        store_match = re.findall(r"([^\s]+店|[\u4e00-\u9fa5]+店)", message)
        if store_match:
            params["stores"] = store_match
        return params

    def register_handler(self, handler: Callable):
        self.custom_handlers.append(handler)

    def add_rule(self, intent_type: IntentType, patterns: List[str]):
        if intent_type in self.RULES:
            self.RULES[intent_type].extend(patterns)
        else:
            self.RULES[intent_type] = patterns
