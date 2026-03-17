"""
代码执行器
通过数据提供程序接口获取数据，实现与原版的深度解耦
"""
import os
import sys
from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入数据提供程序（通过 HTTP API，不再直接依赖原版）
from minghua_evo.services.data_provider import (
    get_provider, DataProvider, WeekData, CrossWeekData, MonthlyData
)


@dataclass
class ExecutionResult:
    success: bool
    data: Any
    reply: str
    render_type: str = "text"
    error: Optional[str] = None


def handle_weekly_report(params: Dict, provider: DataProvider = None) -> ExecutionResult:
    try:
        if provider is None:
            provider = get_provider()
        
        # 检查 API 可用性
        if not provider.health_check():
            return ExecutionResult(
                success=False, 
                data=None, 
                reply="数据服务未启动，请运行原版 data_api.py",
                error="API not available"
            )
        
        # 获取参数
        month = params.get("month")
        week = params.get("week")
        week_offset = params.get("week_offset", 0)  # 0=本周, -1=上一周, 1=下一周
        
        # 转换数字周为中文周
        if week:
            cn_week_map = {"1": "第一周", "2": "第二周", "3": "第三周", "4": "第四周", "5": "第五周"}
            week = cn_week_map.get(week, f"第{week}周")
        
        # 如果指定了 week_offset，需要计算实际周数
        # 默认获取本周数据，如果week_offset为-1则获取上一周
        week_data = provider.get_weekly_report(month=month, week=week, week_offset=week_offset)
        
        result_data = {
            "type": "weekly",
            "week": week_data.week,
            "month": week_data.month,
            "summary": week_data.summary,
            "stores": week_data.stores,
            "fruit_stats": week_data.fruit_stats
        }

        return ExecutionResult(
            success=True, 
            data=result_data, 
            reply=f"为您查询 {week_data.month} {week_data.week} 数据", 
            render_type="chart"
        )

    except Exception as e:
        return ExecutionResult(success=False, data=None, reply=f"生成周报出错：{str(e)}", error=str(e))


def handle_monthly_report(params: Dict, provider: DataProvider = None) -> ExecutionResult:
    try:
        if provider is None:
            provider = get_provider()
        
        if not provider.health_check():
            return ExecutionResult(
                success=False, 
                data=None, 
                reply="数据服务未启动",
                error="API not available"
            )
        
        month = params.get("month")
        monthly_data = provider.get_monthly_report(month=month)
        
        result_data = {
            "type": "monthly",
            "month": monthly_data.month,
        }
        
        if monthly_data.summary:
            result_data["summary"] = monthly_data.summary
        if monthly_data.stores:
            result_data["stores"] = monthly_data.stores
        if monthly_data.fruits:
            result_data["fruits"] = monthly_data.fruits

        return ExecutionResult(
            success=True, 
            data=result_data, 
            reply=f"为您查询 {monthly_data.month} 月度数据", 
            render_type="chart"
        )

    except Exception as e:
        return ExecutionResult(success=False, data=None, reply=f"生成月度报告出错：{str(e)}", error=str(e))


def handle_cross_week(params: Dict, provider: DataProvider = None) -> ExecutionResult:
    try:
        if provider is None:
            provider = get_provider()
        
        if not provider.health_check():
            return ExecutionResult(
                success=False, 
                data=None, 
                reply="数据服务未启动",
                error="API not available"
            )
        
        month = params.get("month")
        cross_data = provider.get_cross_week_report(month=month)
        
        result_data = {
            "type": "cross_week",
            "month": cross_data.month,
            "weeks": cross_data.weeks,
            "summary": cross_data.summary,
            "stores": cross_data.stores
        }

        return ExecutionResult(
            success=True, 
            data=result_data, 
            reply=f"为您查询 {cross_data.month} 跨周对比数据", 
            render_type="table"
        )

    except Exception as e:
        return ExecutionResult(success=False, data=None, reply=f"生成跨周对比出错：{str(e)}", error=str(e))


def handle_query_stores(params: Dict, provider: DataProvider = None) -> ExecutionResult:
    try:
        if provider is None:
            provider = get_provider()
        
        if not provider.health_check():
            return ExecutionResult(
                success=False, 
                data=None, 
                reply="数据服务未启动",
                error="API not available"
            )
        
        target_stores = params.get("stores", [])
        stores = provider.get_stores()
        
        if target_stores:
            stores = [s for s in stores if s.get('店铺') in target_stores]

        result_data = {
            "type": "stores",
            "data": stores
        }

        return ExecutionResult(
            success=True, 
            data=result_data, 
            reply=f"为您查询到 {len(stores)} 条店铺数据", 
            render_type="table"
        )

    except Exception as e:
        return ExecutionResult(success=False, data=None, reply=f"查询店铺数据出错：{str(e)}", error=str(e))


def handle_query_fruits(params: Dict, provider: DataProvider = None) -> ExecutionResult:
    try:
        if provider is None:
            provider = get_provider()
        
        if not provider.health_check():
            return ExecutionResult(
                success=False, 
                data=None, 
                reply="数据服务未启动",
                error="API not available"
            )
        
        fruits = provider.get_fruits()

        result_data = {
            "type": "fruits",
            "data": fruits
        }

        return ExecutionResult(
            success=True, 
            data=result_data, 
            reply=f"为您查询到 {len(fruits)} 种水果数据", 
            render_type="chart"
        )

    except Exception as e:
        return ExecutionResult(success=False, data=None, reply=f"查询水果数据出错：{str(e)}", error=str(e))


def handle_custom(params: Dict, provider: DataProvider = None, raw_message: str = "") -> ExecutionResult:
    # 优先使用 raw_message，其次使用 params.get("raw")
    raw = raw_message or params.get("raw", "")
    
    # 检查是否是闲聊
    if params.get("is_greeting"):
        greetings = {
            "你好": "你好！有什么可以帮你的吗？",
            "您好": "您好！有什么可以帮你的吗？",
            "hi": "Hi！有什么可以帮你的吗？",
            "hello": "Hello！有什么可以帮你的吗？",
            "早上好": "早上好！今天想查点什么？",
            "下午好": "下午好！想了解什么数据？",
            "晚上好": "晚上好！需要查点什么？",
            "晚安": "晚安！好梦！",
            "谢谢": "不客气！",
            "感谢": "不客气！",
            "辛苦了": "不客气，应该的！",
            "拜拜": "再见，有需要随时叫我！",
            "再见": "再见，有需要随时叫我！",
            "好的": "收到！",
            "收到": "收到！",
            "明白": "明白！",
            "了解": "了解！",
        }
        reply = greetings.get(raw, f"{raw}！有什么可以帮你的吗？")
        return ExecutionResult(
            success=True,
            data={"type": "greeting"},
            reply=reply,
            render_type="text"
        )
    
    if "店铺" in raw or "门店" in raw:
        return handle_query_stores({"raw": raw}, provider)
    elif "水果" in raw:
        return handle_query_fruits({"raw": raw}, provider)
    elif "周" in raw and "月" not in raw:
        return handle_weekly_report({"raw": raw}, provider)
    elif "月" in raw:
        return handle_monthly_report({"raw": raw}, provider)
    elif "对比" in raw or "趋势" in raw:
        return handle_cross_week({"raw": raw}, provider)

    return ExecutionResult(
        success=True, 
        data={"type": "custom", "message": raw}, 
        reply=f"收到您的需求：{raw}。我会记录并在进化时分析这个需求。", 
        render_type="text"
    )


class CodeExecutor:
    def __init__(self, project_root: str = None, api_host: str = None):
        self.project_root = project_root or PROJECT_ROOT
        self.api_host = api_host
        self.handlers: Dict[str, Callable] = {}
        self._provider = None
        self._register_default_handlers()

    def _get_provider(self) -> DataProvider:
        if self._provider is None:
            self._provider = get_provider(self.api_host)
        return self._provider

    def _register_default_handlers(self):
        self.handlers["VIEW_WEEKLY_REPORT"] = handle_weekly_report
        self.handlers["VIEW_MONTHLY_REPORT"] = handle_monthly_report
        self.handlers["VIEW_CROSS_WEEK"] = handle_cross_week
        self.handlers["QUERY_STORES"] = handle_query_stores
        self.handlers["QUERY_FRUITS"] = handle_query_fruits
        self.handlers["CUSTOM"] = handle_custom

    def register_handler(self, intent_type: str, handler: Callable):
        self.handlers[intent_type] = handler

    def execute(self, intent_type: str, params: Dict = None, raw_message: str = None) -> ExecutionResult:
        params = params or {}
        raw_message = raw_message or ""
        handler = self.handlers.get(intent_type)
        if not handler:
            return ExecutionResult(
                success=False, 
                data=None, 
                reply=f"暂不支持该功能：{intent_type}", 
                error=f"No handler for {intent_type}"
            )

        try:
            provider = self._get_provider()
            # 传递 raw_message 给 handler
            if "raw_message" in handler.__code__.co_varnames:
                result = handler(params, provider, raw_message)
            else:
                result = handler(params, provider)
            return result
        except Exception as e:
            return ExecutionResult(success=False, data=None, reply=f"执行出错：{str(e)}", error=str(e))
