# 茗花汇报系统

店铺进货与水果价格周报生成 + Web 查看器

## 目录结构

```
茗花/
├── data/                    # 原始数据目录
│   ├── 3月/                # 月份目录
│   │   └── 3月第一周/      # 周目录
│   │       └── *.xlsx     # 原始数据文件
│   └── ...
├── reports/                 # 生成的报表目录（与data分离）
│   ├── 3月/               # 月份目录
│   │   ├── 3月第一周/
│   │   │   └── 汇报/      # 周报文件
│   │   └── 3月第二周/
│   │       └── 汇报/
│   ├── 跨周对比/           # 跨周对比
│   │   ├── 3月跨周对比/
│   │   └── 全局跨周对比_*.xlsx
│   └── 月度汇总/           # 月度汇总
│       └── 3月月度汇总/
├── stores.json              # 店铺类型配置
├── src/
│   ├── config.py           # 路径配置
│   ├── data_loader.py     # 数据加载模块
│   ├── generators.py      # 报表生成模块
│   ├── report_viewer.py   # Web 查看器
│   ├── weekly_report.py   # 周报生成入口
│   └── templates/
│       ├── template.html  # HTML 模板
│       └── viewer.js     # 前端 JS
└── run_viewer.py          # 启动脚本（自动生成报表）
```

## 店铺类型配置

在 `stores.json` 中配置店铺类型：

```json
{
  "新石油": "加盟",
  "东大": "自营",
  "初创": "自营",
  "太白": "自营",
  "老综通道": "自营",
  "茶坊": "自营"
}
```

## 数据目录规范

**原始数据（data/）：**
```
data/
├── {月份}/                 # 如 "3月"
│   ├── {周}/               # 如 "3月第一周"
│   │   └── *.xlsx         # 原始数据文件
│   └── ...
```

**生成的报表（reports/）：**
```
reports/
├── {月份}/                 # 如 "3月"
│   ├── {周}/               # 如 "3月第一周"
│   │   └── 汇报/           # 生成的汇报
│   └── ...
├── 跨周对比/               # 跨周对比
│   ├── {月份}跨周对比/     # 如 "3月跨周对比"
│   └── 全局跨周对比_*.xlsx # 全局汇总
└── 月度汇总/               # 月度汇总
    └── {月份}月度汇总/     # 如 "3月月度汇总"
```

## 使用方法

### 1. 启动 Web 查看器（自动生成报表）

```bash
cd 茗花
python3 run_viewer.py
# 访问 http://localhost:8080
```

### 2. 单独生成周报

```bash
cd 茗花
python3 src/weekly_report.py
```

## 跨周对比指标说明

跨周对比报告包含以下指标（均按店铺类型区分）：

| 指标 | 说明 |
|------|------|
| 【每周整体情况】 | 每周总进货量/额，按自营/加盟分类 |
| 【环比变化】 | 本周与上周对比，按自营/加盟分类 |
| 【整体趋势】 | 首周vs末周趋势，按自营/加盟分类 |
| 【平均周量】 | 周均进货量/额，按自营/加盟分类 |
| 【日均进货金额对比】 | 每日平均进货金额，按自营/加盟分类 |
| 【水果种类变化】 | 每周新增/减少的水果种类，按自营/加盟分类 |
| 【水果金额环比变化】 | 水果金额环比TOP3，按自营/加盟分类 |
| 【店铺金额环比变化】 | 店铺金额环比TOP3 |

## 前端功能

- **店铺类型筛选**：可选择"全部"、"自营"、"加盟"，实时筛选所有报表
- **自动刷新**：启动时自动重新生成最新报表

## 模块说明

### src/config.py
- 定义数据目录路径
- `DATA_DIR` - 原始数据目录
- `REPORTS_DIR` - 生成的报表目录

### src/data_loader.py
- `sort_dates_numerically(dates)` - 按日期数值排序
- `get_all_excel_files()` - 获取所有 Excel 文件
- `get_week_folders()` - 获取所有周文件夹
- `get_month_folders()` - 获取所有月份文件夹
- `load_week_data(week_folder)` - 加载单周数据
- `get_store_type(store_name)` - 获取店铺类型（自营/加盟）

### src/generators.py
- `generate_store_summary()` - 各店铺进货汇总
- `generate_store_trend()` - 各店铺进货趋势
- `generate_fruit_purchase_summary()` - 各水果进货汇总
- `generate_store_detail()` - 店铺详细明细
- `generate_fruit_overall_summary()` - 水果整体汇总
- `generate_txt_report()` - 生成Txt周报（含店铺类型标签）
- `generate_cross_week_report()` - 生成跨周对比
- `generate_monthly_report()` - 生成月度汇总
- `generate_global_cross_week_report()` - 生成全局跨周对比

### src/report_viewer.py
- Web 服务器，提供 HTML 页面
- 读取 `reports/` 目录动态生成页面
- 支持店铺类型筛选

## 拓展功能

如需新增功能：
1. 先读本 README 了解结构
2. 在对应模块添加函数
3. 更新 README 记录新功能
