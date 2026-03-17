# 茗花智能汇报系统

一个可自我进化的智能汇报 Web 应用。

---

## 📦 项目组成

本项目由两个独立软件组成：

| 软件 | 说明 | 端口 |
|------|------|------|
| **茗花（原版）** | 水果进货数据管理系统 | 8080 / 8081 |
| **茗花进化插件** | 智能对话助手框架 | 3001 |

---

## 🌸 茗花（原版软件）

**定位**：水果进货数据汇报系统

**功能**：
- Excel 数据导入处理
- 报告生成（周报/月报/跨周对比）
- Web 端报告查看器
- 数据 API 服务

**启动**：
```bash
cd 茗花
python3 src/data_api.py
# API: http://localhost:8081
```

---

## 🚀 茗花进化插件

**定位**：通用智能对话助手框架

**功能**：
- 自然语言意图识别（分级识别：正则 → AI）
- 用户反馈收集机制
- 自我进化系统
- 智能对话 Web 界面

**启动**：
```bash
cd 茗花by_claw
python3 server.py
# 访问 http://localhost:3001
```

---

## ✨ 核心特性

### 1. 智能意图识别

采用**混合识别模式**：

```
用户输入
    ↓
┌─────────────────────────────────────┐
│  第1层：闲聊过滤                    │
│  匹配 greetings 关键词              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  第2层：正则匹配                    │
│  匹配 intent_rules.yaml 规则        │
│  置信度 > 0.8 → 直接返回           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  第3层：AI 识别                    │
│  One-shot 模式，无记忆              │
│  每次独立判断                       │
└─────────────────────────────────────┘
```

**时间上下文感知**：
- "上周" → 自动计算为当前周的上一周
- "本月" → 自动识别当前月份
- "上个月" → 自动计算为上个月

### 2. 用户反馈机制

每次识别结果后，用户可选择：
- ✓ 正确 - 确认识别结果
- ✗ 不准 - 提交期望的提问方式

反馈数据存储在：`data/feedback/intent_feedback.json`

### 3. 可进化架构

- 意图规则解耦到配置文件
- 支持自定义正则规则
- 进化引擎可读取反馈改进规则

---

## 📁 目录结构

```
茗花by_claw/
├── README.md                 # 本文件
├── server.py                 # 进化版服务入口
├── minghua_evo/
│   ├── core/
│   │   ├── intent_classifier.py    # 意图识别器
│   │   ├── code_executor.py        # 执行器
│   │   ├── feedback_collector.py     # 反馈收集器
│   │   └── conversation_logger.py   # 对话记录
│   ├── services/
│   │   ├── data_provider.py        # 数据客户端
│   │   └── evolution_engine.py      # 进化引擎
│   ├── api/
│   │   └── routes.py               # API 路由
│   ├── config/
│   │   ├── settings.yaml           # 系统配置
│   │   ├── intent_rules.yaml        # 意图规则 ⭐
│   │   └── permissions.yaml        # 权限配置
│   └── data/
│       └── feedback/
│           └── intent_feedback.json # 用户反馈 ⭐
└── frontend/
    └── dist/
        └── index.html        # Web 前端
```

---

## ⚙️ 配置说明

### 意图识别配置

文件：`minghua_evo/config/intent_rules.yaml`

```yaml
# 意图规则
rules:
  VIEW_WEEKLY_REPORT:
    keywords:
      - 周报
      - 本周
      - 上周
    patterns:
      - "周报"
      - "本周.*销售"

# 闲聊过滤
greetings:
  - 你好
  - 谢谢

# 置信度阈值
thresholds:
  high: 0.8   # 直接返回
  low: 0.5   # 走AI
```

### OpenClaw 配置

文件：`minghua_evo/config/settings.yaml`

```yaml
intent_classifier:
  use_ai: true
  host: "http://127.0.0.1:18789"
  agent: "test-agent"
  timeout: 60
```

---

## 🚦 快速开始

### 1. 启动原版（数据 API）

```bash
cd 茗花
python3 src/data_api.py
```

### 2. 启动进化版

```bash
cd 茗花by_claw
python3 server.py
# 访问 http://localhost:3001
```

### 3. 首次配置（必须）

AI 意图识别需要独立的 test-agent：

```bash
# 在项目根目录执行（会自动删除已存在的 test-agent）
cd /path/to/茗花by_claw

# 创建 test-agent，workspace 指向插件目录
openclaw agents delete test-agent --force 2>/dev/null
openclaw agents add test-agent --workspace ./minghua_evo --model MiniMax-M2.5
```

**test-agent 配置说明：**
- workspace: `minghua_evo/` （插件目录）
- 可访问插件代码（当前目录）
- 可访问宿主项目（`../src/`）
- 用途：意图识别的 AI 识别功能

**说明**：test-agent 的 workspace 设置为 `minghua_evo/` 目录，可通过 `../` 访问宿主项目（如 `../src/`）。

---

## 📖 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 发送消息 |
| `/api/feedback/intent` | POST | 提交反馈 |
| `/api/feedback/intent` | GET | 获取反馈列表 |
| `/api/evolve/trigger` | POST | 触发进化 |

---

## 🔧 意图识别模块详细设计

见 `docs/软件设计文档.md` 第4节
