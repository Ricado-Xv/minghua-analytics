"""配置模块（示例）"""
from pathlib import Path

# 路径配置 - 根据实际情况修改
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
REPORTS_DIR = BASE_DIR / 'reports'  # 报表输出目录（与data分离）
