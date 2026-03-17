"""
数据提供程序接口
为进化插件提供统一的数据访问接口
"""
import os
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


# 默认配置
DEFAULT_API_HOST = os.environ.get('MINGHUA_API_HOST', 'http://localhost:8081')


@dataclass
class WeekData:
    """周数据 - 纯业务数据，无报告概念"""
    week: str
    month: str
    summary: Dict[str, Any]
    stores: List[Dict]
    fruit_stats: List[Dict]  # 水果统计数据（去掉了时间维度）


@dataclass
class CrossWeekData:
    """跨周对比数据 - 纯业务数据"""
    month: str
    weeks: int
    summary: Dict[str, Any]
    stores: List[Dict]


@dataclass
class MonthlyData:
    """月度数据 - 纯业务数据"""
    month: str
    summary: Optional[Dict[str, Any]] = None
    stores: List[Dict] = None
    fruits: List[Dict] = None


class DataProvider:
    """
    统一数据访问接口
    通过 HTTP API 获取数据，实现与原版的深度解耦
    使用标准库 urllib，无需额外依赖
    """
    
    def __init__(self, api_host: str = None):
        self.api_host = api_host or DEFAULT_API_HOST
    
    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        url = f"{self.api_host}{endpoint}"
        if params:
            url += '?' + urllib.parse.urlencode(params)
        
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/json')
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    
    def health_check(self) -> bool:
        """检查 API 是否可用"""
        try:
            return self._get('/api/health').get('status') == 'ok'
        except:
            return False
    
    def get_months(self) -> List[str]:
        """获取所有月份"""
        result = self._get('/api/months')
        return result.get('months', [])
    
    def get_weeks(self, month: str = None) -> List[str]:
        """获取指定月份下的周列表"""
        params = {'month': month} if month else {}
        result = self._get('/api/weeks', params)
        return result.get('weeks', [])
    
    def get_weekly_report(self, month: str = None, week: str = None, week_offset: int = 0) -> WeekData:
        """获取周数据
        
        Args:
            month: 月份（如 "3月"）
            week: 周数（如 "第二周"）
            week_offset: 相对本周的偏移量（0=本周, -1=上一周, 1=下一周）
        """
        params = {}
        if month:
            params['month'] = month
        if week:
            params['week'] = week
        if week_offset != 0:
            params['week_offset'] = week_offset
        
        result = self._get('/api/weekly', params)
        
        return WeekData(
            week=result.get('week', ''),
            month=result.get('month', ''),
            summary=result.get('summary', {}),
            stores=result.get('stores', []),
            fruit_stats=result.get('fruit_stats', [])
        )
    
    def get_cross_week_report(self, month: str = None) -> CrossWeekData:
        """获取跨周对比数据"""
        params = {'month': month} if month else {}
        result = self._get('/api/cross-week', params)
        
        return CrossWeekData(
            month=result.get('month', ''),
            weeks=result.get('weeks', 0),
            summary=result.get('summary', {}),
            stores=result.get('stores', [])
        )
    
    def get_monthly_report(self, month: str = None) -> MonthlyData:
        """获取月度数据"""
        params = {'month': month} if month else {}
        result = self._get('/api/monthly', params)
        
        return MonthlyData(
            month=result.get('month', ''),
            summary=result.get('summary'),
            stores=result.get('stores', []),
            fruits=result.get('fruits', [])
        )
    
    def get_stores(self) -> List[Dict]:
        """获取店铺列表"""
        result = self._get('/api/stores')
        return result.get('stores', [])
    
    def get_fruits(self) -> List[Dict]:
        """获取水果列表"""
        result = self._get('/api/fruits')
        return result.get('fruits', [])


# 单例
_provider: Optional[DataProvider] = None


def get_provider(api_host: str = None) -> DataProvider:
    """获取数据提供者单例"""
    global _provider
    if _provider is None:
        _provider = DataProvider(api_host)
    return _provider


def reset_provider():
    """重置提供者（用于测试）"""
    global _provider
    _provider = None
