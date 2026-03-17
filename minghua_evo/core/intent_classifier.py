"""
意图识别器 - IntentClassifier

分级识别机制：
1. 闲聊过滤 → 2. 正则匹配 → 3. AI 识别

配置文件:
  - intent_rules.yaml: 正则规则（可独立进化）
  - settings.yaml: OpenClaw 配置
========================================
"""
import re
import json
import subprocess
import os
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from enum import Enum

# 尝试导入 yaml
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ========================================
# 配置加载
# ========================================

def load_config() -> dict:
    """从配置文件加载"""
    # 获取 config 目录路径
    module_dir = os.path.dirname(os.path.abspath(__file__))  # core/
    config_dir = os.path.join(os.path.dirname(module_dir), "config")  # minghua_evo/config
    
    # 默认配置
    defaults = {
        "intent_rules": {
            "rules": {},
            "greetings": [],
            "thresholds": {"high": 0.8, "low": 0.5}
        },
        "intent_classifier": {
            "use_ai": True,
            "host": "http://127.0.0.1:18789",
            "token": "",
            "agent": "test-agent",
            "timeout": 60
        }
    }
    
    # 加载 intent_rules.yaml
    rules_path = os.path.join(config_dir, "intent_rules.yaml")
    if os.path.exists(rules_path) and HAS_YAML:
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules_config = yaml.safe_load(f)
                if rules_config:
                    defaults["intent_rules"].update(rules_config)
        except Exception:
            pass
    
    # 加载 settings.yaml
    settings_path = os.path.join(config_dir, "settings.yaml")
    if os.path.exists(settings_path) and HAS_YAML:
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)
                if settings and "intent_classifier" in settings:
                    defaults["intent_classifier"].update(settings["intent_classifier"])
        except Exception:
            pass
    
    return defaults


# 加载配置
_config = load_config()
_rules_config = _config.get("intent_rules", {})
_intent_config = _config.get("intent_classifier", {})


# ========================================
# 时间上下文
# ========================================

from datetime import datetime, timedelta
import calendar

def get_current_time_context() -> dict:
    """获取当前时间上下文"""
    now = datetime.now()
    
    # 当前月份
    current_month = now.month
    
    # 计算当前周（在月度中的第几周）
    # 简单计算：按日期/7
    week_of_month = (now.day - 1) // 7 + 1
    
    # 计算周几
    weekday = now.weekday()  # 0=周一
    
    return {
        "year": now.year,
        "month": current_month,
        "month_cn": f"{current_month}月",
        "week_of_month": week_of_month,
        "week_cn": f"第{week_of_month}周",
        "weekday": weekday,
        "date": now.day,
        "now": now
    }


# 缓存时间上下文
_time_context = None

def get_time_context() -> dict:
    """获取缓存的时间上下文"""
    global _time_context
    if _time_context is None:
        _time_context = get_current_time_context()
    return _time_context

# 规则配置
INTENT_RULES = _rules_config.get("rules", {})
GREETING_KEYWORDS = _rules_config.get("greetings", [])
THRESHOLD_HIGH = _rules_config.get("thresholds", {}).get("high", 0.8)
THRESHOLD_LOW = _rules_config.get("thresholds", {}).get("low", 0.5)

# OpenClaw 配置
USE_AI = _intent_config.get("use_ai", True)
OPENCLAW_HOST = _intent_config.get("host", "http://127.0.0.1:18789")
OPENCLAW_TOKEN = _intent_config.get("token", "")
DEFAULT_AGENT = _intent_config.get("agent", "test-agent")
AI_TIMEOUT = _intent_config.get("timeout", 60)


# ========================================
# 意图类型
# ========================================

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
    """意图结果"""
    type: IntentType
    confidence: float
    params: Dict
    raw_message: str


# ========================================
# 编译正则规则
# ========================================

def compile_rules() -> Dict:
    """编译正则规则，包含优先级"""
    compiled = {}
    
    for intent_name, config in INTENT_RULES.items():
        try:
            intent_type = IntentType[intent_name]
        except KeyError:
            continue
        
        patterns = []
        
        # 添加 keyword 精确匹配
        keywords = config.get("keywords", [])
        for kw in keywords:
            patterns.append((kw, re.escape(kw), 0.95))
        
        # 添加正则表达式
        regex_list = config.get("patterns", [])
        for pattern in regex_list:
            patterns.append((pattern, pattern, 0.9))
        
        # 获取优先级，默认为 0
        priority = config.get("priority", 0)
        
        compiled[intent_type] = {
            "patterns": patterns,
            "priority": priority
        }
    
    return compiled


# 预编译规则（缓存）
_COMPILED_RULES = compile_rules()


# ========================================
# AI 识别提示词（简化版）
# ========================================

AI_CLASSIFY_PROMPT = """你是一个意图识别助手。

支持意图：VIEW_WEEKLY_REPORT|VIEW_MONTHLY_REPORT|VIEW_CROSS_WEEK|QUERY_STORES|QUERY_FRUITS|GENERATE_REPORT|CUSTOM

闲聊词（返回CUSTOM）：{greetings}

用户输入：{message}

返回JSON：{{"intent":"类型","confidence":0.0-1.0,"params":{{"key":"value"}}}}"""


# ========================================
# 意图识别器
# ========================================

class IntentClassifier:
    """分级意图识别器"""
    
    def __init__(self, use_ai: bool = None):
        """初始化"""
        self.custom_handlers: List[Callable] = []
        self.use_ai = use_ai if use_ai is not None else USE_AI

    def classify(self, message: str) -> Intent:
        """识别意图 - 主入口"""
        message = message.strip()
        
        # 第一层：闲聊过滤
        if message in GREETING_KEYWORDS:
            return Intent(
                type=IntentType.CUSTOM,
                confidence=1.0,
                params={"is_greeting": True},
                raw_message=message
            )
        
        # 第二层：正则匹配
        intent, confidence, params = self._regex_match(message)
        if intent and confidence >= THRESHOLD_HIGH:
            return Intent(
                type=intent,
                confidence=confidence,
                params=params,
                raw_message=message
            )
        
        # 第三层：自定义处理器
        for handler in self.custom_handlers:
            result = handler(message)
            if result:
                return result
        
        # 第四层：AI 识别
        if self.use_ai:
            ai_result = self._ai_classify(message)
            if ai_result:
                return ai_result
        
        # 兜底
        return Intent(
            type=IntentType.CUSTOM,
            confidence=0.5,
            params={"raw": message},
            raw_message=message
        )

    def _regex_match(self, message: str) -> tuple:
        """正则匹配（支持优先级）"""
        best_match = None
        best_score = 0.0  # 综合分数 = 置信度 + 优先级*0.1
        best_params = {}
        
        for intent_type, rule in _COMPILED_RULES.items():
            patterns = rule.get("patterns", [])
            priority = rule.get("priority", 0)
            
            for keyword, pattern, base_confidence in patterns:
                if re.search(pattern, message):
                    # 提取参数
                    params = self._extract_params(message, intent_type)
                    
                    # 置信度
                    confidence = base_confidence if keyword != message else 0.95
                    
                    # 综合分数 = 置信度 + 优先级
                    score = confidence + priority * 0.1
                    
                    if score > best_score:
                        best_match = intent_type
                        best_score = score
                        best_params = params
        
        if best_match:
            return best_match, best_score, best_params
        return None, 0.0, {}

    def _ai_classify(self, message: str) -> Optional[Intent]:
        """AI 识别 - One-shot 模式（无记忆）"""
        try:
            return self._ai_classify_one_shot(message)
        except Exception as e:
            print(f"[IntentClassifier] AI 识别失败: {e}")
            return None

    def _ai_classify_one_shot(self, message: str) -> Optional[Intent]:
        """One-shot AI 识别"""
        prompt = AI_CLASSIFY_PROMPT.format(
            message=message,
            greetings="|".join(GREETING_KEYWORDS[:10])  # 限制长度
        )
        
        # 使用唯一 session_id，每次全新会话（无记忆）
        session_id = f"intent-{uuid.uuid4().hex[:8]}"
        
        result = subprocess.run(
            [
                "openclaw",
                "agent",
                "--agent", DEFAULT_AGENT,
                "--session-id", session_id,  # 唯一 session，无记忆
                "-m", prompt,
                "--json"
            ],
            capture_output=True,
            text=True,
            timeout=AI_TIMEOUT
        )
        
        if result.returncode != 0:
            print(f"[IntentClassifier] AI 识别失败: {result.stderr}")
            return None
        
        # 解析 JSON
        output = result.stdout.strip()
        json_start = output.find('{')
        json_end = output.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = output[json_start:json_end]
            data = json.loads(json_str)
        else:
            data = json.loads(output)
        
        intent_str = data.get("intent", "CUSTOM")
        try:
            intent_type = IntentType[intent_str]
        except KeyError:
            intent_type = IntentType.CUSTOM
        
        return Intent(
            type=intent_type,
            confidence=data.get("confidence", 0.7),
            params=data.get("params", {}),
            raw_message=message
        )

    def _extract_params(self, message: str, intent_type: IntentType) -> Dict:
        """提取参数 - 支持时间上下文"""
        params = {}
        
        # 获取当前时间上下文
        ctx = get_time_context()
        
        # 处理"上周"/"上一周" -> 计算实际周
        if "上一周" in message or "上周" in message:
            if "month" not in params:  # 如果没有指定月份
                # 上周 = 当前周 - 1
                last_week = ctx["week_of_month"] - 1
                if last_week < 1:
                    # 跨月了
                    last_month = ctx["month"] - 1
                    if last_month < 1:
                        last_month = 12
                    params["month"] = str(last_month)
                    # 上月的最后一周
                    params["week"] = "4"  # 简化处理
                else:
                    params["week"] = str(last_week)
                    params["month"] = str(ctx["month"])
        
        # 处理"本月"/"这月" -> 当前月
        elif "本月" in message or "这月" in message:
            params["month"] = str(ctx["month"])
            params["week_offset"] = 0  # 本周
        
        # 处理"上月"/"上个月" -> 上月
        elif "上月" in message or "上个月" in message:
            last_month = ctx["month"] - 1
            if last_month < 1:
                last_month = 12
            params["month"] = str(last_month)
        
        # 处理"下月"/"下个月" -> 下月
        elif "下月" in message or "下个月" in message:
            next_month = ctx["month"] + 1
            if next_month > 12:
                next_month = 1
            params["month"] = str(next_month)
        
        # 处理"下一周"
        elif "下一周" in message:
            next_week = ctx["week_of_month"] + 1
            params["week"] = str(next_week)
            params["month"] = str(ctx["month"])
        
        # 提取显式月份（如"3月"、"12月"）
        month_match = re.search(r"(\d+)月", message)
        if month_match:
            params["month"] = month_match.group(1)
        
        # 提取显式周数（支持中文和数字）
        week_match = re.search(r"第([一二三四五六七八九十\d]+)周", message)
        if week_match:
            week_num = week_match.group(1)
            cn_num_map = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
            if week_num in cn_num_map:
                params["week"] = str(cn_num_map[week_num])
            else:
                params["week"] = week_num
        
        # 提取店铺
        store_match = re.findall(r"([^\s]+店|[\u4e00-\u9fa5]+店)", message)
        if store_match:
            params["stores"] = store_match
        
        return params

    def register_handler(self, handler: Callable):
        """注册自定义处理器"""
        self.custom_handlers.append(handler)

    def add_rule(self, intent_type: IntentType, patterns: List[str]):
        """动态添加规则（运行时）"""
        pass  # 规则从配置文件加载

    def disable_ai(self):
        """禁用 AI"""
        self.use_ai = False

    def enable_ai(self):
        """启用 AI"""
        self.use_ai = True

    @staticmethod
    def reload_rules():
        """重新加载规则（用于进化）"""
        global _COMPILED_RULES, _rules_config, GREETING_KEYWORDS, THRESHOLD_HIGH, THRESHOLD_LOW
        _config = load_config()
        _rules_config = _config.get("intent_rules", {})
        INTENT_RULES = _rules_config.get("rules", {})
        GREETING_KEYWORDS = _rules_config.get("greetings", [])
        THRESHOLD_HIGH = _rules_config.get("thresholds", {}).get("high", 0.8)
        THRESHOLD_LOW = _rules_config.get("thresholds", {}).get("low", 0.5)
        _COMPILED_RULES = compile_rules()
