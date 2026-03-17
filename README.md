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
python3 src/report_viewer.py
# 访问 http://localhost:8080
```

**数据 API**：
```bash
python3 src/data_api.py
# API: http://localhost:8081
```

---

## 🚀 茗花进化插件

**定位**：通用智能对话助手框架

**功能**：
- 自然语言意图识别
- 对话历史记录
- 自动进化系统
- 智能对话 Web 界面

**启动**：
```bash
python3 server.py
# 访问 http://localhost:3001
```

### 功能特性

#### 智能对话
- 自然语言查询：周报、月报、跨周对比、水果/店铺查询
- 意图识别：支持"上一周周报"、"查看本月情况"等表达
- 实时数据分析与可视化

#### 数据可视化
- 统计卡片：店铺数、水果种类、总进货量、总进货额
- 数据表格：店铺明细、水果明细
- 跨周对比：两周数据对比、环比变化、自营vs加盟

#### 自我进化（开发中）
- 记录用户对话
- AI 分析需求，自动生成设计文档
- 代码版本管理
- 定时/手动触发进化

#### 安全机制
- 目录级代码修改权限控制
- 白名单/黑名单机制

---

## 🔗 插件解耦说明

插件与原版完全解耦，可接入任意项目。

### 架构图

```
原版                          进化插件
┌─────────────┐              ┌─────────────┐
│ data/       │              │ 意图识别    │
│ reports/    │              │ 对话记录    │
└─────────────┘              │ 进化引擎    │
        │                    └─────────────┘
        │ HTTP JSON                 ▲
        ▼                           │
┌─────────────┐                   │
│ data_api.py │ ───────────────────┘
│ (:8081)     │    数据客户端调用
└─────────────┘
```

### 第三方接入

只需提供符合规范的 HTTP JSON API：

```yaml
# config/settings.yaml
data_api:
  host: "http://your-api:8081"
```

#### API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/health` | 健康检查 |
| `GET /api/weekly` | 周数据 |
| `GET /api/stores` | 店铺列表 |
| `GET /api/fruits` | 水果列表（可选） |
| `GET /api/monthly` | 月度数据（可选） |
| `GET /api/cross-week` | 跨周数据（可选） |

#### 响应格式

**周数据**
```json
{
  "week": "第N周",
  "month": "N月",
  "summary": {
    "店铺数": 6,
    "水果种类": 8,
    "总进货量": 1156.1,
    "总进货额": 9865.35
  },
  "stores": [
    {
      "店铺": "店名A",
      "进货量(斤)": 100.5,
      "进货额(元)": 500.0,
      "日期": "3.11",
      "店铺类型": "自营"
    }
  ],
  "fruit_stats": [
    {
      "水果": "苹果",
      "进货量": 50,
      "进货额": 200,
      "波动系数": 15.2
    }
  ]
}
```

---

## 📁 项目结构

```
茗花by_claw/
├── src/                    # 原版代码（参考）
│   ├── data_loader.py
│   ├── generators.py
│   ├── data_api.py         # 数据 API
│   └── templates/
├── minghua_evo/            # 进化插件（独立模块）
│   ├── core/               # 核心引擎
│   │   ├── intent_classifier.py
│   │   ├── code_executor.py
│   │   └── conversation_logger.py
│   ├── services/           # 业务服务
│   │   ├── data_provider.py
│   │   └── evolution_engine.py
│   ├── api/                # API 路由
│   ├── config/             # 配置文件
│   └── COUPLING_ANALYSIS.md # 解耦分析报告
├── frontend/               # 前端
├── data/                  # 数据目录
├── reports/               # 报告目录
├── fruits.json            # 水果分类配置
├── stores.json            # 店铺类型配置
└── server.py              # 服务入口
```

---

## 🛠️ 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 方式一：完整运行（推荐）

```bash
# 启动原版数据 API
cd 茗花
python3 src/data_api.py &

# 启动进化版
cd 茗花by_claw
python3 server.py &
```

访问：
- 原版查看器：http://localhost:8080
- 进化版：http://localhost:3001

### 方式二：插件独立部署

```bash
# 1. 修改配置
vim minghua_evo/config/settings.yaml

# 2. 启动
python3 -c "
from fastapi import FastAPI
from minghua_evo.api import router
import uvicorn
app = FastAPI()
app.include_router(router)
uvicorn.run(app, host='0.0.0.0', port=3001)
"
```

---

## 📖 支持的指令

| 指令 | 说明 |
|------|------|
| 查看周报 | 本周数据汇总 |
| 上一周周报 | 上一周数据 |
| 查看本月情况 | 月度报告 |
| 跨周对比 | 本月内周对比 |
| 查询水果 | 水果销售数据 |
| 查询店铺 | 店铺销售数据 |

---

## 📊 技术栈

- 后端：FastAPI + Python
- 前端：HTML + JavaScript
- 数据处理：Pandas
