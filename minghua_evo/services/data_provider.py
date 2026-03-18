"""
数据提供程序接口
为进化插件提供统一的数据访问接口
支持多数据源：HTTP API / Mock 数据
返回值适配：直接返回 API 原始数据，由调用方决定如何使用
"""
import os
import json
import urllib.request
import urllib.parse
import yaml
from typing import Dict, List, Any, Optional


def load_settings() -> Dict:
    """加载 settings.yaml 配置"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(os.path.dirname(current_dir), "config", "settings.yaml")
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


# ============================================================
# 数据提供者抽象基类
# ============================================================

class DataProviderBase:
    """数据提供者基类 - 定义标准接口"""
    
    # 标准 API 端点配置模板
    DEFAULT_ENDPOINTS = {
        'health': '/api/health',
        'months': '/api/months',
        'weeks': '/api/weeks',
        'weekly': '/api/weekly',
        'monthly': '/api/monthly',
        'cross_week': '/api/cross-week',
        'stores': '/api/stores',
        'fruits': '/api/fruits',
    }
    
    def health_check(self) -> bool:
        raise NotImplementedError
    
    def get_months(self) -> Dict:
        """获取所有月份 - 返回原始数据"""
        raise NotImplementedError
    
    def get_weeks(self, month: str = None) -> Dict:
        """获取指定月份下的周列表 - 返回原始数据"""
        raise NotImplementedError
    
    def get_weekly_report(self, month: str = None, week: str = None, week_offset: int = 0) -> Dict:
        """获取周数据 - 返回原始数据"""
        raise NotImplementedError
    
    def get_cross_week_report(self, month: str = None) -> Dict:
        """获取跨周对比数据 - 返回原始数据"""
        raise NotImplementedError
    
    def get_monthly_report(self, month: str = None) -> Dict:
        """获取月度数据 - 返回原始数据"""
        raise NotImplementedError
    
    def get_stores(self) -> Dict:
        """获取店铺列表 - 返回原始数据"""
        raise NotImplementedError
    
    def get_fruits(self) -> Dict:
        """获取水果列表 - 返回原始数据"""
        raise NotImplementedError


# ============================================================
# HTTP 数据提供者
# ============================================================

class HTTPDataProvider(DataProviderBase):
    """HTTP API 数据提供者 - 从配置读取 API 端点"""
    
    def __init__(self, base_url: str = None):
        settings = load_settings()
        dp_config = settings.get('data_provider', {}).get('http', {})
        
        # 基础 URL
        if base_url:
            self.base_url = base_url.rstrip('/')
        elif dp_config.get('base_url'):
            self.base_url = dp_config['base_url'].rstrip('/')
        else:
            host = dp_config.get('host', 'localhost')
            port = dp_config.get('port', 8081)
            self.base_url = f"http://{host}:{port}"
        
        # API 端点配置
        endpoints_config = dp_config.get('endpoints', {})
        self.endpoints = {**self.DEFAULT_ENDPOINTS, **endpoints_config}
    
    def _get(self, endpoint_key: str, params: Dict = None) -> Dict:
        """根据端点 key 获取原始数据"""
        endpoint = self.endpoints.get(endpoint_key, self.DEFAULT_ENDPOINTS.get(endpoint_key, endpoint_key))
        url = f"{self.base_url}{endpoint}"
        
        if params:
            params = {k: v for k, v in params.items() if v is not None}
            if params:
                url += '?' + urllib.parse.urlencode(params)
        
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/json')
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    
    def health_check(self) -> bool:
        try:
            result = self._get('health')
            return result.get('status') == 'ok'
        except:
            return False
    
    def get_months(self) -> Dict:
        return self._get('months')
    
    def get_weeks(self, month: str = None) -> Dict:
        return self._get('weeks', {'month': month} if month else None)
    
    def get_weekly_report(self, month: str = None, week: str = None, week_offset: int = 0) -> Dict:
        params = {}
        if month:
            params['month'] = month
        if week:
            params['week'] = week
        if week_offset != 0:
            params['week_offset'] = week_offset
        return self._get('weekly', params)
    
    def get_cross_week_report(self, month: str = None) -> Dict:
        return self._get('cross_week', {'month': month} if month else None)
    
    def get_monthly_report(self, month: str = None) -> Dict:
        return self._get('monthly', {'month': month} if month else None)
    
    def get_stores(self) -> Dict:
        return self._get('stores')
    
    def get_fruits(self) -> Dict:
        return self._get('fruits')
    
    def get_endpoints(self) -> Dict[str, str]:
        return self.endpoints.copy()


# ============================================================
# Mock 数据提供者
# ============================================================

class MockDataProvider(DataProviderBase):
    """Mock 数据提供者 - 用于测试/离线演示"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
    
    def health_check(self) -> bool:
        return True
    
    def get_months(self) -> Dict:
        return {"months": ["3月", "2月", "1月"]}
    
    def get_weeks(self, month: str = None) -> Dict:
        return {"weeks": ["第一周", "第二周", "第三周", "第四周"]}
    
    def get_weekly_report(self, month: str = None, week: str = None, week_offset: int = 0) -> Dict:
        return {
            "week": week or "第一周",
            "month": month or "3月",
            "summary": {"店铺数": 5, "水果种类": 10, "总进货量": 1000.0, "总进货额": 5000.0},
            "stores": [
                {"店铺": "店铺A", "进货量(斤)": 200.0, "进货额(元)": 1000.0},
                {"店铺": "店铺B", "进货量(斤)": 180.0, "进货额(元)": 900.0},
            ],
            "fruit_stats": [
                {"水果": "苹果", "销量": 100.0},
                {"水果": "香蕉", "销量": 80.0},
            ]
        }
    
    def get_cross_week_report(self, month: str = None) -> Dict:
        return {
            "month": month or "3月",
            "weeks": 2,
            "summary": {"第一周": {"进货额": 5000.0}, "第二周": {"进货额": 5500.0}},
            "stores": []
        }
    
    def get_monthly_report(self, month: str = None) -> Dict:
        return {
            "month": month or "3月",
            "summary": {"店铺数": 5, "水果种类": 10, "总进货量": 4000.0, "总进货额": 20000.0},
            "stores": [],
            "fruits": []
        }
    
    def get_stores(self) -> Dict:
        return {"stores": [
            {"店铺": "店铺A", "类型": "自营"},
            {"店铺": "店铺B", "类型": "加盟"},
        ]}
    
    def get_fruits(self) -> Dict:
        return {"fruits": [
            {"水果": "苹果"},
            {"水果": "香蕉"},
            {"水果": "橙子"},
        ]}


# ============================================================
# 统一入口
# ============================================================

class DataProvider:
    """
    统一数据访问接口
    返回原始数据字典，由调用方自行适配
    """
    
    def __init__(self, provider: DataProviderBase = None):
        self._provider = provider
    
    @property
    def provider(self) -> DataProviderBase:
        if self._provider is None:
            settings = load_settings()
            dp_config = settings.get('data_provider', {})
            provider_type = dp_config.get('type', 'http')
            
            if provider_type == 'mock':
                self._provider = MockDataProvider(dp_config.get('mock', {}))
            else:
                self._provider = HTTPDataProvider()
        
        return self._provider
    
    def health_check(self) -> bool:
        return self.provider.health_check()
    
    def get_months(self) -> Dict:
        return self.provider.get_months()
    
    def get_weeks(self, month: str = None) -> Dict:
        return self.provider.get_weeks(month)
    
    def get_weekly_report(self, month: str = None, week: str = None, week_offset: int = 0) -> Dict:
        return self.provider.get_weekly_report(month, week, week_offset)
    
    def get_cross_week_report(self, month: str = None) -> Dict:
        return self.provider.get_cross_week_report(month)
    
    def get_monthly_report(self, month: str = None) -> Dict:
        return self.provider.get_monthly_report(month)
    
    def get_stores(self) -> Dict:
        return self.provider.get_stores()
    
    def get_fruits(self) -> Dict:
        return self.provider.get_fruits()
    
    @staticmethod
    def get_config() -> Dict:
        settings = load_settings()
        return settings.get('data_provider', {})
    
    @staticmethod
    def get_default_endpoints() -> Dict[str, str]:
        return DataProviderBase.DEFAULT_ENDPOINTS.copy()


# 单例
_provider: Optional[DataProvider] = None


def get_provider() -> DataProvider:
    global _provider
    if _provider is None:
        _provider = DataProvider()
    return _provider


def reset_provider():
    global _provider
    _provider = None
