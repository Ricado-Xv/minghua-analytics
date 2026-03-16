"""数据加载模块"""
import pandas as pd
import json
from pathlib import Path
from config import DATA_DIR, BASE_DIR
from datetime import datetime

# 使用DATA_DIR而不是BASE_DIR，避免扫描到非数据目录
BASE_DIR = DATA_DIR

# 加载店铺类型配置
STORE_TYPE_FILE = BASE_DIR.parent / 'stores.json'
_store_type_map = None

def get_store_type(store_name):
    """获取店铺类型（自营/加盟），默认自营"""
    global _store_type_map
    if _store_type_map is None:
        if STORE_TYPE_FILE.exists():
            with open(STORE_TYPE_FILE, 'r', encoding='utf-8') as f:
                _store_type_map = json.load(f)
        else:
            _store_type_map = {}
    return _store_type_map.get(store_name, '自营')

# 加载水果分类配置
FRUIT_CATEGORY_FILE = BASE_DIR.parent / 'fruits.json'
_fruit_category_map = None

def get_fruit_category(fruit_name):
    """获取水果分类（如芒果A->芒果），默认返回原名称"""
    global _fruit_category_map
    if _fruit_category_map is None:
        if FRUIT_CATEGORY_FILE.exists():
            with open(FRUIT_CATEGORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _fruit_category_map = data.get('水果分类映射', {})
        else:
            _fruit_category_map = {}
    return _fruit_category_map.get(fruit_name, fruit_name)

def sort_dates_numerically(dates):
    """按日期数值排序（如3.9 < 3.11）"""
    def date_key(s):
        parts = s.replace('.', ' ').split()
        if len(parts) >= 2:
            try:
                return (int(parts[0]), int(parts[1]))
            except:
                pass
        return (0, 0)
    return sorted(dates, key=date_key)

def get_all_excel_files():
    """自动扫描目录获取所有xlsx文件"""
    files = []
    for subdir in BASE_DIR.iterdir():
        if subdir.is_dir():
            for f in subdir.glob('*.xlsx'):
                files.append(f)
    return sorted(files)

def get_week_folders():
    """获取所有周文件夹（支持月份目录结构）"""
    week_folders = []
    for month_dir in sorted([d for d in BASE_DIR.iterdir() if d.is_dir()]):
        for week_dir in sorted([d for d in month_dir.iterdir() if d.is_dir()]):
            week_folders.append(week_dir)
    return week_folders

def get_month_folders():
    """获取所有月份文件夹"""
    return sorted([d for d in BASE_DIR.iterdir() if d.is_dir()])

def load_week_data(week_folder):
    """加载单个周文件夹的数据"""
    all_data = []
    # 只读取原始数据文件（排除生成的报告：包含日期格式如 2026-03-14）
    xlsx_files = sorted([f for f in week_folder.glob('*.xlsx') if '2026-' not in f.name])
    for filepath in xlsx_files:
        xlsx = pd.ExcelFile(filepath)
        
        df_detail = pd.read_excel(xlsx, sheet_name='门店明细')
        df_price = pd.read_excel(xlsx, sheet_name='单价情况')
        
        all_data.append({
            'detail': df_detail,
            'price': df_price,
            'filename': filepath.stem
        })
    
    return all_data
