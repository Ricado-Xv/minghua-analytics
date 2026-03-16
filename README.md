# 茗花智能汇报系统

一个可自我进化的智能汇报 Web 应用。

## 功能特性

### 智能对话
- 自然语言查询：周报、月报、跨周对比、水果/店铺查询
- 意图识别：支持"上一周周报"、"查看本月情况"等表达
- 实时数据分析与可视化

### 数据可视化
- 统计卡片：店铺数、水果种类、总进货量、总进货额
- 数据表格：店铺明细、水果明细
- 跨周对比：两周数据对比、环比变化、自营vs加盟

### 自我进化（开发中）
- 记录用户对话
- AI 分析需求，自动生成设计文档
- 代码版本管理
- 定时/手动触发进化

### 安全机制
- 目录级代码修改权限控制
- 白名单/黑名单机制

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

```bash
cp src/config_template.py src/config.py
```

### 运行

```bash
# 原版
python3 -m src.report_viewer 8080

# 进化版
python3 server.py
```

访问 http://localhost:8080 或 http://localhost:3001

## 支持的指令

| 指令 | 说明 |
|------|------|
| 查看周报 | 本周数据汇总 |
| 上一周周报 | 上一周数据 |
| 查看本月情况 | 月度报告 |
| 跨周对比 | 本月内周对比 |
| 查询水果 | 水果销售数据 |
| 查询店铺 | 店铺销售数据 |

## 项目结构

```
src/                    # 原项目代码
minghua_evo/           # 进化系统（独立模块）
frontend/              # 前端
data/                  # 数据目录
fruits.json            # 水果分类配置
stores.json            # 店铺类型配置
server.py              # Web 服务入口
```

## 技术栈

- 后端：FastAPI + Python
- 前端：HTML + JavaScript
- 数据处理：Pandas
