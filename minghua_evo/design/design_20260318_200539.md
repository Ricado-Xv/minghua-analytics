# 软件设计文档

**生成时间**: 2026-03-18 20:05:39

---

# 软件设计文档

## 茗花智能汇报系统 - 意图识别模块改进

**版本：** v1.2  
**日期：** 2026-03-18  
**作者：** 架构团队

---

## 1. 系统概述

### 1.1 设计目标

本次软件设计基于需求分析文档，旨在解决以下核心问题：

| 问题 | 设计目标 |
|------|---------|
| 动词前缀覆盖不足 | 扩展动词模式库，支持查下、看看、卖了等 |
| 时间词组合不完整 | 支持时间+业务词的组合匹配 |
| 业务词同义词缺失 | 建立同义词配置机制 |
| 水果查询不可用 | 支持具体水果名称动态匹配 |
| 匹配优先级混乱 | 优化正则匹配算法 |

### 1.2 核心特性

1. **三级混合意图识别**（保持不变）
2. **可配置的同义词扩展机制**
3. **动态水果库匹配**
4. **智能优先级评分算法**
5. **规则热更新支持**

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| **开闭原则** | 对扩展开放，对修改封闭（新增规则无需改代码） |
| **配置优先** | 业务规则尽量外置到配置文件 |
| **渐进增强** | 短期修复 → 中期优化 → 长期架构演进 |
| **向后兼容** | 现有规则平滑迁移 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           茗花智能汇报系统                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐         ┌─────────────────┐                     │
│  │   茗花（原版）    │         │   茗花进化插件    │                     │
│  │   端口: 8081    │◄───────►│   端口: 3001    │                     │
│  └─────────────────┘         └─────────────────┘                     │
│                                   │                                     │
│              ┌────────────────────┼────────────────────┐              │
│              │                    │                    │              │
│              ▼                    ▼                    ▼              │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐       │
│  │   API 路由层    │   │   通用层         │   │   适配层         │       │
│  │  (api/routes)  │   │                 │   │                 │       │
│  │                 │   │ • 意图识别器     │   │ • 代码执行器     │       │
│  │                 │   │ • 对话记录器     │   │ • API 路由      │       │
│  │                 │   │ • 反馈收集器     │   │                 │       │
│  │                 │   │ • 进化引擎       │   │                 │       │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 意图识别模块架构（改进后）

```
┌─────────────────────────────────────────────────────────────────┐
│                    意图识别模块架构 (改进后)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户输入 ──► ┌─────────────────────────────────────────┐      │
│              │          IntentClassifier                │      │
│              │  ┌─────────────────────────────────────┐│      │
│              │  │  第1层: 闲聊过滤 (Greetings)         ││      │
│              │  │  匹配: 你好、早上好、谢谢...          ││      │
│              │  └─────────────────────────────────────┘│      │
│              │                    │                       │      │
│              │                    ▼                       │      │
│              │  ┌─────────────────────────────────────┐│      │
│              │  │  第2层: 正则匹配 (Enhanced)          ││      │
│              │  │  • 动词前缀匹配                       ││      │
│              │  │  • 时间+业务词组合                    ││      │
│              │  │  • 水果动态匹配                       ││      │
│              │  │  • 智能优先级评分                     ││      │
│              │  └─────────────────────────────────────┘│      │
│              │                    │                       │      │
│              │                    ▼                       │      │
│              │  ┌─────────────────────────────────────┐│      │
│              │  │  第3层: 自定义处理器                 ││      │
│              │  │  • 水果名动态检测                    ││      │
│              │  │  • 店铺名动态检测                    ││      │
│              │  └─────────────────────────────────────┘│      │
│              │                    │                       │      │
│              │                    ▼                       │      │
│              │  ┌─────────────────────────────────────┐│      │
│              │  │  第4层: AI 识别 (One-shot)          ││      │
│              │  │  调用 OpenClaw agent                ││      │
│              │  └─────────────────────────────────────┘│      │
│              │                    │                       │      │
│              │                    ▼                       │      │
│              │          ┌─────────────────┐              │      │
│              │          │ Intent 结果      │              │      │
│              │          │ • type          │              │      │
│              │          │ • confidence    │              │      │
│              │          │ • params        │              │      │
│              │          └─────────────────┘              │      │
│              └─────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 模块设计

| 模块 | 职责 | 位置 |
|------|------|------|
| `IntentClassifier` | 意图识别核心逻辑 | `core/intent_classifier.py` |
| `FeedbackCollector` | 用户反馈收集存储 | `core/feedback_collector.py` |
| `EvolutionEngine` | 规则进化与版本管理 | `services/evolution_engine.py` |
| `IntentRulesLoader` | 规则配置加载器（新增） | `core/intent_rules_loader.py` |
| `SynonymManager` | 同义词管理器（新增） | `core/synonym_manager.py` |
| `FruitNameDetector` | 水果名称检测器（新增） | `core/fruit_name_detector.py` |

### 2.4 耦合点分析

```
┌─────────────────────────────────────────────────────────────────┐
│                        耦合点分析                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  intent_classifier.py                                          │
│       │                                                         │
│       ├──► intent_rules.yaml  (配置文件，低耦合)                 │
│       │                                                         │
│       ├──► synonym_manager.py  (新增，内部模块)                 │
│       │                                                         │
│       └──► fruit_name_detector.py  (新增，内部模块)             │
│                                                                 │
│  数据流:                                                         │
│  User Input → Greetings → Regex → Custom → AI → Intent Result   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 模块详细设计

### 3.1 改进的意图识别模块 (IntentClassifier)

#### 3.1.1 类图

```
┌─────────────────────────────────────────────────────────────────┐
│                     IntentClassifier                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  - rules: Dict                                                 │
│  - synonym_manager: SynonymManager                             │
│  - fruit_detector: FruitNameDetector                           │
│  - config: Settings                                            │
│                                                                 │
│  + classify(message: str) -> IntentResult                      │
│  - _greetings_filter(message: str) -> bool                     │
│  - _regex_match(message: str) -> IntentResult                   │
│  - _custom_handler(message: str) -> IntentResult                │
│  - _ai_fallback(message: str) -> IntentResult                  │
│  - _calculate_score(match: Dict) -> float                       │
│  + reload_rules() -> None                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.1.2 改进点

**1. 动词前缀匹配增强**

```python
# 新增动词前缀列表
VERB_PREFIXES = {
    '查看类': ['查看', '查下', '查一下', '查询', '帮我查', '我要查'],
    '看看类': ['看看', '给我看看', '帮忙看看', '让我看看', '看下'],
    '卖类': ['卖了', '卖多少', '卖得怎么样', '好卖吗', '卖得好吗'],
}

def _match_verb_prefix(self, message: str, intent: str) -> float:
    """动词前缀匹配，返回置信度"""
    for verb_type, prefixes in VERB_PREFIXES.items():
        for prefix in prefixes:
            if message.startswith(prefix) or prefix in message:
                return 0.85  # 基础置信度
    return 0.0
```

**2. 时间+业务词组合匹配**

```python
TIME_BUSINESS_COMBOS = {
    'VIEW_MONTHLY_REPORT': [
        ('上月', '销售'), ('上月', '生意'), ('上月', '营收'),
        ('本月', '销售'), ('本月', '生意'), ('本月', '营收'),
        ('3月份', '生意'), ('月份', '销售'),
    ],
    'VIEW_WEEKLY_REPORT': [
        ('第一周', '数据'), ('第二周', '数据'), ('上周', '数据'),
    ],
}

def _match_time_business_combo(self, message: str, intent: str) -> float:
    """时间+业务词组合匹配"""
    combos = TIME_BUSINESS_COMBOS.get(intent, [])
    for time_word, biz_word in combos:
        if time_word in message and biz_word in message:
            return 0.9  # 高置信度
    return 0.0
```

**3. 智能优先级评分**

```python
def _calculate_match_score(self, message: str, intent: str, match_result: Dict) -> float:
    """计算匹配得分"""
    score = match_result.get('base_score', 0.5)
    
    # 长度加分：更具体的表达优先
    match_len = match_result.get('match_length', 0)
    score += (match_len / len(message)) * 0.2
    
    # 组合匹配加分
    if self._match_time_business_combo(message, intent) > 0:
        score += 0.1
    
    # 动词前缀加分
    if self._match_verb_prefix(message, intent) > 0:
        score += 0.1
    
    return min(score, 1.0)  # 最高1.0
```

### 3.2 新增模块

#### 3.2.1 SynonymManager (同义词管理器)

```python
class SynonymManager:
    """同义词管理器"""
    
    def __init__(self, config_path: str = None):
        self.synonym_groups = self._load_synonyms(config_path)
    
    def _load_synonyms(self, config_path: str) -> Dict:
        """加载同义词配置"""
        # 从 intent_rules.yaml 加载 synonym_groups
        pass
    
    def expand_with_synonyms(self, keywords: List[str]) -> List[str]:
        """扩展关键词为同义词"""
        expanded = set(keywords)
        for kw in keywords:
            for group_name, synonyms in self.synonym_groups.items():
                if kw in synonyms:
                    expanded.update(synonyms)
        return list(expanded)
    
    def get_business_words(self) -> List[str]:
        """获取所有业务词"""
        return self.synonym_groups.get('business_data', [])
```

#### 3.2.2 FruitNameDetector (水果名称检测器)

```python
class FruitNameDetector:
    """水果名称检测器"""
    
    def __init__(self, data_provider: DataProvider = None):
        self.data_provider = data_provider
        self.fruits = self._load_fruits()
    
    def _load_fruits(self) -> List[str]:
        """从数据源加载水果列表"""
        if self.data_provider:
            try:
                fruits_data = self.data_provider.get_fruits()
                return [f.get('水果') for f in fruits_data if f.get('水果')]
            except:
                pass
        # 静态备用列表
        return ['苹果', '香蕉', '橙子', '葡萄', '西瓜', '草莓', '芒果', '梨', '桃子', '猕猴桃']
    
    def detect(self, message: str) -> List[str]:
        """检测消息中的水果名称"""
        detected = []
        for fruit in self.fruits:
            if fruit in message:
                detected.append(fruit)
        return detected
    
    def build_pattern(self) -> str:
        """构建水果匹配正则"""
        return f"({'|'.join(self.fruits)}).*(卖|销售|好卖|销量|多少|怎么样)"
```

### 3.3 数据流设计

```
用户输入
    │
    ▼
┌─────────────────┐
│  1. 闲聊过滤    │──是──► 友好回复
└────────┬────────┘
         │否
         ▼
┌─────────────────┐
│  2. 正则匹配    │──匹配成功 + 置信度≥0.8 ──► 返回结果
└────────┬────────┘
         │失败/低置信度
         ▼
┌─────────────────┐
│  3. 自定义处理  │──检测到水果名 ──► QUERY_FRUITS
└────────┬────────┘
         │不匹配
         ▼
┌─────────────────┐
│  4. AI 识别     │──返回识别结果
└────────┬────────┘
         │
         ▼
   返回 IntentResult
```

---

## 4. 接口设计

### 4.1 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 发送消息 |
| `/api/feedback/intent` | POST/GET | 意图反馈 |
| `/api/evolve/trigger` | POST | 触发进化 |
| `/api/evolve/status` | GET | 进化状态 |

### 4.2 内部模块接口

```python
# IntentClassifier 接口
class IntentClassifier:
    def classify(self, message: str) -> IntentResult:
        """
        Args:
            message: 用户输入消息
        Returns:
            IntentResult:
                - type: str  # 意图类型
                - confidence: float  # 置信度 0-1
                - params: Dict  # 提取的参数
        """
        pass

# SynonymManager 接口
class SynonymManager:
    def expand_with_synonyms(self, keywords: List[str]) -> List[str]:
        """扩展关键词"""
        pass
    
    def get_business_words(self) -> List[str]:
        """获取业务词列表"""
        pass

# FruitNameDetector 接口
class FruitNameDetector:
    def detect(self, message: str) -> List[str]:
        """检测水果名"""
        pass
    
    def build_pattern(self) -> str:
        """构建匹配正则"""
        pass
```

---

## 5. 数据库设计

### 5.1 反馈数据存储

```json
// data/feedback/intent_feedback.json
{
  "timestamp": "2026-03-18T20:00:00",
  "message": "查下上月销售",
  "ai_intent": "CUSTOM",
  "correct_intent": "VIEW_MONTHLY_REPORT",
  "user_input": "查下上月销售",
  "comment": "应该是月报",
  "processed": false
}
```

### 5.2 设计文档存储

```
design/
├── _status.json          # 文档状态管理
├── requirements_v1.2.md  # 需求文档
├── design_v1.2.md       # 设计文档
└── changelog.md          # 变更日志
```

---

## 6. 配置设计

### 6.1 意图规则配置 (intent_rules.yaml)

```yaml
# 意图规则
rules:
  VIEW_WEEKLY_REPORT:
    keywords:
      - 周报
      - 本周
      - 上周
      - 周数据
    patterns:
      - "周报"
      - "查看.*周.*数据"
      - "上周.*销售"
      - "本周.*情况"
    verb_prefixes:
      - 查看
      - 查下
      - 看看

  VIEW_MONTHLY_REPORT:
    keywords:
      - 月报
      - 本月
      - 上月
      - 月份
    patterns:
      - "月报"
      - ".*月份.*生意"
      - "上月.*销售"
      - "本月.*营收"
    verb_prefixes:
      - 查看
      - 查下
      - 看看
      - 给我看看

  QUERY_FRUITS:
    keywords:
      - 水果
      - 好卖
    # 新增：水果列表将动态加载
    dynamic_fruits: true

# 同义词配置
synonym_groups:
  business_data:
    - 数据
    - 报表
    - 销售
    - 营收
    - 生意
    - 业绩
    - 情况
    
  time_monthly:
    - 上月
    - 上个月
    - 本月
    - 这个月

# 置信度阈值
thresholds:
  high: 0.8
  low: 0.5
```

### 6.2 进化配置 (settings.yaml)

```yaml
evolution:
  default_trigger: "manual"
  schedule:
    enabled: false
    cron: "0 9 * * *"
  
  # 文档生成设置
  docs:
    output_dir: "design"
    auto_confirm: false
```

---

## 7. 测试计划

### 7.1 单元测试

| 测试模块 | 测试用例 | 预期结果 |
|---------|---------|---------|
| IntentClassifier | 测试动词前缀匹配 | "查下上月销售" → 0.85+ |
| IntentClassifier | 测试时间+业务词组合 | "上月销售" → VIEW_MONTHLY_REPORT |
| SynonymManager | 测试同义词扩展 | "销售" → ["销售", "营收", "生意", ...] |
| FruitNameDetector | 测试水果检测 | "苹果卖了多少" → ["苹果"] |

### 7.2 集成测试

| 测试场景 | 测试步骤 | 预期结果 |
|---------|---------|---------|
| 周报查询 | 输入"查看本周周报" | 识别为 VIEW_WEEKLY_REPORT |
| 月报查询 | 输入"查下上月销售" | 识别为 VIEW_MONTHLY_REPORT |
| 水果查询 | 输入"苹果卖了多少" | 识别为 QUERY_FRUITS |
| 组合表达 | 输入"给我看看3月份的生意" | 识别为 VIEW_MONTHLY_REPORT |

### 7.3 测试用例数据

```python
TEST_CASES = [
    {"input": "周报", "expected": "VIEW_WEEKLY_REPORT"},
    {"input": "查看本周周报", "expected": "VIEW_WEEKLY_REPORT"},
    {"input": "查下上月销售", "expected": "VIEW_MONTHLY_REPORT"},
    {"input": "给我看看3月份的生意", "expected": "VIEW_MONTHLY_REPORT"},
    {"input": "苹果卖了多少", "expected": "QUERY_FRUITS"},
    {"input": "香蕉好卖吗", "expected": "QUERY_FRUITS"},
    {"input": "店铺销售排名", "expected": "QUERY_STORES"},
]
```

---

## 8. 实施计划

### 8.1 短期（1-2周）

1. 修改 `intent_rules.yaml` 添加缺失规则
2. 增强 `_regex_match` 方法
3. 添加单元测试

### 8.2 中期（2-4周）

1. 实现 `SynonymManager` 模块
2. 实现 `FruitNameDetector` 模块
3. 集成到 `IntentClassifier`

### 8.3 长期（1-2个月）

1. 重构意图识别架构
2. 引入机器学习模型
3. 开放自定义 API

---

*本文档由进化引擎自动生成*

---

*本文档由进化引擎自动生成*
