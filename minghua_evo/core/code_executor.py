"""
代码执行器
"""
import os
import sys
from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data_loader import (
    get_all_excel_files, get_week_folders, 
    get_month_folders, load_week_data, sort_dates_numerically,
    get_store_type, get_fruit_category
)
from generators import (
    generate_store_summary, generate_store_trend,
    generate_fruit_purchase_summary, generate_store_detail,
    generate_fruit_overall_summary, generate_txt_report,
    generate_cross_week_report, generate_monthly_report,
    generate_global_cross_week_report
)
from config import DATA_DIR, REPORTS_DIR


def get_real_month_folders():
    all_folders = get_month_folders()
    return [f for f in all_folders if '月' in f.name and '度' not in f.name]


@dataclass
class ExecutionResult:
    success: bool
    data: Any
    reply: str
    render_type: str = "text"
    error: Optional[str] = None


def handle_weekly_report(params: Dict) -> ExecutionResult:
    try:
        month_folders = get_real_month_folders()
        if not month_folders:
            return ExecutionResult(success=False, data=None, reply="暂无数据", error="没有找到数据")

        # 获取周偏移
        week_offset = params.get("week_offset", 0)  # 0=最新, -1=上一周
        
        latest_month = sorted(month_folders, key=lambda x: x.name)[-1]
        week_folders = sorted([d for d in latest_month.iterdir() if d.is_dir()])
        
        if not week_folders:
            return ExecutionResult(success=False, data=None, reply="暂无周数据")

        # 根据偏移获取周
        # week_offset=0: 最新一周, week_offset=-1: 上一周(倒数第二周)
        idx = len(week_folders) - 1 + week_offset
        if idx < 0:
            idx = 0
        if idx >= len(week_folders):
            idx = len(week_folders) - 1
        latest_week = week_folders[idx]
        all_data = load_week_data(latest_week)

        if not all_data:
            return ExecutionResult(success=False, data=None, reply="该周暂无数据")

        df_store = generate_store_summary(all_data)
        if '店铺' in df_store.columns:
            df_store['店铺类型'] = df_store['店铺'].apply(get_store_type)
        
        df_trend = generate_store_trend(all_data)
        df_fruit = generate_fruit_purchase_summary(all_data)
        df_overall = generate_fruit_overall_summary(all_data)
        dates = sort_dates_numerically([d['filename'] for d in all_data])
        txt_report = generate_txt_report(all_data, df_trend, df_fruit, df_overall, dates)

        result_data = {
            "type": "weekly_report",
            "week": latest_week.name,
            "month": latest_month.name,
            "report": txt_report,
            "summary": {
                "店铺数": len(df_store['店铺'].unique()) if '店铺' in df_store.columns else 0,
                "水果种类": len(df_fruit['水果'].unique()) if '水果' in df_fruit.columns else 0,
                "总进货量": df_store['进货量(斤)'].sum() if '进货量(斤)' in df_store.columns else 0,
                "总进货额": df_store['进货额(元)'].sum() if '进货额(元)' in df_store.columns else 0,
            },
            "stores": df_store.to_dict('records') if not df_store.empty else [],
            "fruits": df_fruit.to_dict('records') if not df_fruit.empty else []
        }

        return ExecutionResult(success=True, data=result_data, reply=f"为您生成 {latest_month.name} {latest_week.name} 周报", render_type="chart")

    except Exception as e:
        return ExecutionResult(success=False, data=None, reply=f"生成周报出错：{str(e)}", error=str(e))


def handle_monthly_report(params: Dict) -> ExecutionResult:
    try:
        month_folders = get_real_month_folders()
        if not month_folders:
            return ExecutionResult(success=False, data=None, reply="暂无数据")

        target_month = params.get("month")
        if target_month:
            matched = [m for m in month_folders if target_month in m.name]
            if matched:
                latest_month = matched[0]
            else:
                return ExecutionResult(success=False, data=None, reply=f"未找到 {target_month} 数据")
        else:
            latest_month = sorted(month_folders, key=lambda x: x.name)[-1]

        generate_monthly_report(latest_month)

        # 加载统计数据
        week_folders = sorted([d for d in latest_month.iterdir() if d.is_dir() and '周' in d.name])
        all_week_data = []
        for wf in week_folders:
            wd = load_week_data(wf)
            if wd:
                all_week_data.extend(wd)

        if all_week_data:
            df_store = generate_store_summary(all_week_data)
            if '店铺' in df_store.columns:
                df_store['店铺类型'] = df_store['店铺'].apply(get_store_type)
            df_fruit = generate_fruit_purchase_summary(all_week_data)
        else:
            df_store = None
            df_fruit = None

        monthly_dir = REPORTS_DIR / '月度汇总' / f'{latest_month.name}月度汇总'
        if monthly_dir.exists():
            report_files = sorted(monthly_dir.glob("*_汇报.txt"))
            if report_files:
                with open(report_files[-1], 'r', encoding='utf-8') as f:
                    report_content = f.read()

                result_data = {
                    "type": "monthly_report",
                    "month": latest_month.name,
                    "report": report_content,
                }

                if df_store is not None and not df_store.empty:
                    result_data["summary"] = {
                        "店铺数": len(df_store['店铺'].unique()) if '店铺' in df_store.columns else 0,
                        "水果种类": len(df_fruit['水果'].unique()) if df_fruit is not None and '水果' in df_fruit.columns else 0,
                        "总进货量": df_store['进货量(斤)'].sum() if '进货量(斤)' in df_store.columns else 0,
                        "总进货额": df_store['进货额(元)'].sum() if '进货额(元)' in df_store.columns else 0,
                    }
                    result_data["stores"] = df_store.to_dict('records')
                    result_data["fruits"] = df_fruit.to_dict('records') if df_fruit is not None and not df_fruit.empty else []

                return ExecutionResult(success=True, data=result_data, reply=f"为您生成 {latest_month.name} 月度汇总报告", render_type="chart")

        return ExecutionResult(success=False, data=None, reply="生成月度报告失败")

    except Exception as e:
        return ExecutionResult(success=False, data=None, reply=f"生成月度报告出错：{str(e)}", error=str(e))


def handle_cross_week(params: Dict) -> ExecutionResult:
    try:
        month_folders = get_real_month_folders()
        if not month_folders:
            return ExecutionResult(success=False, data=None, reply="暂无数据")

        target_month = params.get("month")
        if target_month:
            matched = [m for m in month_folders if target_month in m.name]
            latest_month = matched[0] if matched else sorted(month_folders, key=lambda x: x.name)[-1]
        else:
            latest_month = sorted(month_folders, key=lambda x: x.name)[-1]

        week_folders = sorted([d for d in latest_month.iterdir() if d.is_dir()])
        
        if len(week_folders) < 2:
            return ExecutionResult(success=False, data=None, reply="跨周对比需要至少2周数据")

        generate_cross_week_report(week_folders, latest_month)

        cross_week_dir = REPORTS_DIR / '跨周对比' / f'{latest_month.name}跨周对比'
        if cross_week_dir.exists():
            report_files = sorted(cross_week_dir.glob("*_汇报.txt"))
            if report_files:
                with open(report_files[-1], 'r', encoding='utf-8') as f:
                    report_content = f.read()

                result_data = {
                    "type": "cross_week",
                    "month": latest_month.name,
                    "weeks": len(week_folders),
                    "report": report_content
                }

                return ExecutionResult(success=True, data=result_data, reply=f"为您生成 {latest_month.name} 跨周对比报告", render_type="table")

        return ExecutionResult(success=False, data=None, reply="生成跨周对比失败")

    except Exception as e:
        return ExecutionResult(success=False, data=None, reply=f"生成跨周对比出错：{str(e)}", error=str(e))


def handle_query_stores(params: Dict) -> ExecutionResult:
    try:
        target_stores = params.get("stores", [])
        month_folders = get_real_month_folders()
        
        if not month_folders:
            return ExecutionResult(success=False, data=None, reply="暂无数据")

        latest_month = sorted(month_folders, key=lambda x: x.name)[-1]
        week_folders = sorted([d for d in latest_month.iterdir() if d.is_dir()])
        
        if not week_folders:
            return ExecutionResult(success=False, data=None, reply="暂无周数据")

        latest_week = week_folders[-1]
        all_data = load_week_data(latest_week)
        
        if not all_data:
            return ExecutionResult(success=False, data=None, reply="该周暂无数据")

        df_store = generate_store_summary(all_data)
        if '店铺' in df_store.columns:
            df_store['店铺类型'] = df_store['店铺'].apply(get_store_type)

        if target_stores:
            df_store = df_store[df_store['店铺'].isin(target_stores)]

        result_data = {
            "type": "stores",
            "data": df_store.to_dict('records') if not df_store.empty else []
        }

        return ExecutionResult(success=True, data=result_data, reply=f"为您查询到 {len(df_store)} 条店铺数据", render_type="table")

    except Exception as e:
        return ExecutionResult(success=False, data=None, reply=f"查询店铺数据出错：{str(e)}", error=str(e))


def handle_query_fruits(params: Dict) -> ExecutionResult:
    try:
        month_folders = get_real_month_folders()
        
        if not month_folders:
            return ExecutionResult(success=False, data=None, reply="暂无数据")

        latest_month = sorted(month_folders, key=lambda x: x.name)[-1]
        week_folders = sorted([d for d in latest_month.iterdir() if d.is_dir()])
        
        if not week_folders:
            return ExecutionResult(success=False, data=None, reply="暂无周数据")

        latest_week = week_folders[-1]
        all_data = load_week_data(latest_week)
        
        if not all_data:
            return ExecutionResult(success=False, data=None, reply="该周暂无数据")

        df_fruit = generate_fruit_purchase_summary(all_data)

        result_data = {
            "type": "fruits",
            "data": df_fruit.to_dict('records') if not df_fruit.empty else []
        }

        return ExecutionResult(success=True, data=result_data, reply=f"为您查询到 {len(df_fruit)} 种水果数据", render_type="chart")

    except Exception as e:
        return ExecutionResult(success=False, data=None, reply=f"查询水果数据出错：{str(e)}", error=str(e))


def handle_custom(params: Dict) -> ExecutionResult:
    raw = params.get("raw", "")
    
    if "店铺" in raw or "门店" in raw:
        return handle_query_stores({"raw": raw})
    elif "水果" in raw:
        return handle_query_fruits({"raw": raw})
    elif "周" in raw and "月" not in raw:
        return handle_weekly_report({"raw": raw})
    elif "月" in raw:
        return handle_monthly_report({"raw": raw})
    elif "对比" in raw or "趋势" in raw:
        return handle_cross_week({"raw": raw})

    return ExecutionResult(success=True, data={"type": "custom", "message": raw}, reply=f"收到您的需求：{raw}。我会记录并在进化时分析这个需求。", render_type="text")


class CodeExecutor:
    def __init__(self, project_root: str = None):
        self.project_root = project_root or PROJECT_ROOT
        self.handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        self.handlers["VIEW_WEEKLY_REPORT"] = handle_weekly_report
        self.handlers["VIEW_MONTHLY_REPORT"] = handle_monthly_report
        self.handlers["VIEW_CROSS_WEEK"] = handle_cross_week
        self.handlers["QUERY_STORES"] = handle_query_stores
        self.handlers["QUERY_FRUITS"] = handle_query_fruits
        self.handlers["CUSTOM"] = handle_custom

    def register_handler(self, intent_type: str, handler: Callable):
        self.handlers[intent_type] = handler

    def execute(self, intent_type: str, params: Dict = None) -> ExecutionResult:
        params = params or {}
        handler = self.handlers.get(intent_type)
        if not handler:
            return ExecutionResult(success=False, data=None, reply=f"暂不支持该功能：{intent_type}", error=f"No handler for {intent_type}")

        try:
            result = handler(params)
            return result
        except Exception as e:
            return ExecutionResult(success=False, data=None, reply=f"执行出错：{str(e)}", error=str(e))
