# 茗花进化插件 - 软件设计文档

**版本：** v1.3  
**日期：** 2026-03-18  
**作者：** 架构团队

---

## 1. 系统概述

### 1.1 定位

**茗花进化插件** 是一个通用智能对话助手框架，通过 HTTP API 与宿主系统通信，实现完全解耦。

### 1.2 核心特性

- 🤖 三级混合意图识别
- 📝 用户反馈机制（识别错误 / 新需求）
- 🔄 自我进化系统
- ⚙️ 配置化数据源
- 🖥️ 前后端解耦

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     茗花进化插件                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │   前端 UI    │───▶│  FastAPI   │───▶│   核心模块   │      │
│  │  (index.html)│    │  (routes)  │    │             │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│                                                 │              │
│                              ┌──────────────────┼──────────┐   │
│                              ▼                  ▼          ▼   │
│                      ┌─────────────┐  ┌─────────────┐ ┌────┐  │
│                      │  Intent     │  │  Data       │ │Feed-│  │
│                      │  Classifier │  │  Provider   │ │back │  │
│                      └─────────────┘  └─────────────┘ └────┘  │
│                              │                  │          │      │
│                              ▼                  ▼          ▼      │
│                      ┌─────────────┐  ┌─────────────┐ ┌────┐  │
│                      │  Evolution  │  │ HTTP API   │ │JSON│  │
│                      │  Engine     │  │ (宿主)      │ │文件 │  │
│                      └─────────────┘  └─────────────┘ └────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 前端架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      插件前端 (index.html)                       │
├──────────────────┬────────────────────────────────────────────┤
│                  │                                            │
│   左侧聊天区      │           右侧 iframe                      │
│                  │    (嵌入宿主系统前端页面)                    │
│  - 对话输入      │                                            │
│  - 反馈按钮     │    viewer.html?type=weekly                │
│  - 新需求收集   │                                            │
│                  │                                            │
└──────────────────┴────────────────────────────────────────────┘
```

---

## 3. 模块详细设计

### 3.1 数据提供模块

**文件**：`services/data_provider.py`

```
DataProvider (Facade)
    ├── HTTPDataProvider    # HTTP API 数据源
    └── MockDataProvider   # Mock 数据源
```

**配置**：
```yaml
data_provider:
  type: "http"
  http:
    host: "localhost"
    port: 8081
    endpoints:
      health: "/api/health"
      months: "/api/months"
      weekly: "/api/weekly"
      monthly: "/api/monthly"
      cross_week: "/api/cross-week"
      stores: "/api/stores"
      fruits: "/api/fruits"
```

### 3.2 意图识别模块

**文件**：`core/intent_classifier.py`

```
用户输入
    │
    ▼
┌───────────────────┐
│ 第1层: 闲聊过滤    │ → 匹配 greetings 关键词
└───────────────────┘
    │
    ▼
┌───────────────────┐
│ 第2层: 正则匹配    │ → 匹配 intent_rules.yaml
└───────────────────┘
    │ 置信度 < 0.8
    ▼
┌───────────────────┐
│ 第3层: AI 识别    │ → OpenClaw Agent
└───────────────────┘
```

### 3.3 反馈收集模块

**文件**：`core/feedback_collector.py`

**数据结构**：

| 文件 | 类型 | 说明 |
|------|------|------|
| `intent_feedback.json` | 意图反馈 | 识别错误的纠正 |
| `requirements.json` | 新需求 | 用户描述的新功能 |

**收集入口**：

| 场景 | 触发 |
|------|------|
| 识别为 CUSTOM | 自动弹出新需求表单 |
| 用户点击"✗不准" | 可选"识别错误"或"新需求" |

### 3.4 进化引擎模块

**文件**：`services/evolution_engine.py`

```
用户反馈 → 读取反馈 → AI 分析 → 生成文档 → 更新规则
```

**触发方式**：
- 手动触发：`/api/evolve/trigger`
- 定时触发：`settings.yaml` 配置 cron

### 3.5 文档生成模块

**文件**：`core/requirements_doc_generator.py`

**生成内容**：
- 需求分析文档 (`requirements_*.md`)
- 软件设计文档 (`design_*.md`)

**存储**：`minghua_evo/design/`

---

## 4. 接口设计

### 4.1 对话 API

```bash
POST /api/chat
{"message": "周报"}

# Response
{
  "intent": "VIEW_WEEKLY_REPORT",
  "reply": "为您查询...",
  "data": {...}
}
```

### 4.2 反馈 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/feedback/intent` | POST | 提交意图反馈 |
| `/api/feedback/intent` | GET | 获取反馈列表 |
| `/api/feedback/requirement` | POST | 提交新需求 |
| `/api/feedback/requirement` | GET | 获取需求列表 |

### 4.3 进化 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/evolve/trigger` | POST | 触发进化 |
| `/api/evolve/status` | GET | 进化状态 |

### 4.4 文档 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/docs/list` | GET | 文档列表 |
| `/api/docs/{filename}` | GET | 文档内容 |

### 4.5 配置 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/config` | GET | 系统配置 |

---

## 5. 配置设计

### 5.1 settings.yaml

```yaml
# 数据源
data_provider:
  type: "http"
  http:
    host: "localhost"
    port: 8081
    endpoints:
      health: "/api/health"
      # ...

# 意图识别
intent_classifier:
  use_ai: true
  host: "http://127.0.0.1:18789"
  agent: "test-agent"

# 进化
evolution:
  default_trigger: "manual"
  schedule:
    enabled: false

# 宿主系统
host_system:
  url: "http://localhost:3001"
  pages:
    VIEW_WEEKLY_REPORT: "/viewer.html?type=weekly"
```

### 5.2 intent_rules.yaml

```yaml
rules:
  VIEW_WEEKLY_REPORT:
    keywords: [周报, 本周, 上周]
    patterns: [周报, 查看.*周.*数据]

greetings: [你好, 谢谢]

thresholds:
  high: 0.8
  low: 0.5
```

---

## 6. 数据流设计

### 6.1 对话流程

```
用户输入 → /api/chat → IntentClassifier → CodeExecutor
                                    ↓
                              DataProvider
                                    ↓
                              返回数据 → 前端渲染
```

### 6.2 反馈流程

```
识别为 CUSTOM
    ↓
前端显示新需求表单
    ↓
用户提交 → /api/feedback/requirement
    ↓
存入 requirements.json
```

### 6.3 进化流程

```
触发进化 → 读取反馈 → AI 分析 → 生成文档 → 更新规则
```

---

## 7. 目录结构

```
minghua_evo/
├── core/
│   ├── intent_classifier.py      # 意图识别
│   ├── code_executor.py          # 执行器
│   ├── feedback_collector.py      # 反馈收集
│   └── requirements_doc_generator.py  # 文档生成
├── services/
│   ├── data_provider.py           # 数据抽象
│   └── evolution_engine.py        # 进化引擎
├── api/
│   └── routes.py                 # API 路由
├── config/
│   ├── settings.yaml              # 系统配置
│   └── intent_rules.yaml         # 意图规则
├── design/
│   ├── requirements_*.md          # 需求文档
│   └── design_*.md               # 设计文档
└── data/
    └── feedback/
        ├── intent_feedback.json   # 意图反馈
        └── requirements.json      # 新需求
```

---

## 8. 部署

### 8.1 依赖

```
fastapi>=0.100.0
uvicorn>=0.20.0
pyyaml>=6.0
```

### 8.2 启动

```bash
cd 茗花by_claw
python3 server.py
# 访问 http://localhost:3001
```

---

*本文档由进化引擎自动生成*
