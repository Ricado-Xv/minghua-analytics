# 茗花智能汇报系统 - 进化插件

一个可**自我进化**的智能对话助手框架。

---

## 🎯 定位

通用智能对话助手框架，通过 HTTP API 与宿主系统通信，实现完全解耦。

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🤖 三级混合意图识别 | 闲聊过滤 → 正则匹配 → AI 识别 |
| 📝 用户反馈机制 | 识别错误 / 新需求分类收集，支持 txt 上传 |
| 🔄 自我进化 | 从需求生成需求/设计文档 |
| ⚙️ 配置化数据源 | HTTP API / Mock 数据可切换 |
| 🖥️ 前后端解耦 | iframe 嵌入宿主系统页面 |
| 📖 宿主文档获取 | 自动获取宿主的 README 和设计文档 |

---

## 🚀 快速开始

### 1. 启动宿主项目（数据 API）

```bash
python3 src/data_api.py
# API: http://localhost:8081
```

### 2. 启动进化插件

```bash
python3 server.py
# 访问: http://localhost:3001
```

### 3. 访问

| 地址 | 说明 |
|------|------|
| http://localhost:3001 | 插件主界面 |
| http://localhost:3001/viewer.html | 数据查看器 |
| http://localhost:8081/api/weekly | 数据 API |

---

## 💡 功能

### 智能对话

- 自然语言输入
- 自动意图识别
- 数据查询（周报/月报/跨周对比/水果/店铺）

### 用户反馈

- 识别正确/不准反馈
- 新功能需求收集
- txt 文件批量上传

### 文档管理

- 需求文档（带版本、状态）
- 设计文档
- 需求池查看

### 进化系统

- 从需求生成需求文档
- 从需求生成设计文档

### 宿主集成

- 自动获取宿主 README
- 自动获取宿主设计文档
- 配置化页面映射

---

## ⚙️ 配置

### 数据源配置

```yaml
# settings.yaml
data_provider:
  type: "http"
  http:
    host: "localhost"
    port: 8081
    endpoints:
      weekly: "/api/weekly"
      monthly: "/api/monthly"
```

### 意图规则

```yaml
# intent_rules.yaml
rules:
  VIEW_WEEKLY_REPORT:
    keywords: [周报, 本周, 上周]
    patterns: [周报, 查看.*周.*数据]
```

---

## 📁 目录结构

```
茗花by_claw/
├── server.py                    # 服务入口
├── src/                       # 宿主项目
│   └── templates/
│       └── viewer.html        # 数据查看器
├── minghua_evo/             # 进化插件
│   ├── core/                 # 核心模块
│   ├── services/             # 服务模块
│   ├── api/                  # API 路由
│   ├── config/               # 配置文件
│   ├── design/               # 生成的文档
│   └── data/feedback/        # 反馈数据
└── frontend/
    └── dist/
        └── index.html        # 插件前端
```

---

## 🔌 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 发送消息 |
| `/api/feedback/requirement` | POST | 提交需求 |
| `/api/evolve/generate-requirements` | POST | 生成需求文档 |
| `/api/docs/list` | GET | 文档列表 |
| `/api/host-docs` | GET | 宿主文档 |

---

*插件与宿主完全解耦，可独立部署运行。*
