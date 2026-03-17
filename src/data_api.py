"""
原版数据 API 服务
为进化插件提供数据接口，实现深度解耦
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import json
import sys

# 路径配置
BASE_DIR = Path(__file__).parent.parent  # 茗花目录
DATA_DIR = BASE_DIR / 'data'
REPORTS_DIR = BASE_DIR / 'reports'

# 添加 src 到路径
SRC_DIR = BASE_DIR / 'src'
sys.path.insert(0, str(SRC_DIR))

from data_loader import (
    get_week_folders, 
    get_month_folders, load_week_data, sort_dates_numerically,
    get_store_type, get_fruit_category
)
from generators import (
    generate_store_summary, generate_store_trend,
    generate_fruit_purchase_summary,
    generate_fruit_overall_summary, generate_txt_report,
    generate_cross_week_report, generate_monthly_report
)
from config import DATA_DIR as CONFIG_DATA_DIR, REPORTS_DIR as CONFIG_REPORTS_DIR


def get_real_month_folders():
    all_folders = get_month_folders()
    return [f for f in all_folders if '月' in f.name and '度' not in f.name]


class APIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        # 健康检查
        if path == '/api/health':
            self._send_json({"status": "ok"})
            return
        
        # 月份列表
        if path == '/api/months':
            month_folders = get_real_month_folders()
            months = sorted([f.name for f in month_folders])
            self._send_json({"months": months})
            return
        
        # 指定月份下的周列表
        if path == '/api/weeks':
            month = query.get('month', [None])[0]
            if not month:
                self._send_json({"error": "Missing month param"}, 400)
                return
            
            month_folders = get_real_month_folders()
            matched = [m for m in month_folders if month in m.name]
            if not matched:
                self._send_json({"error": "Month not found"}, 404)
                return
            
            month_path = matched[0]
            week_folders = sorted([d.name for d in month_path.iterdir() if d.is_dir()])
            self._send_json({"weeks": week_folders})
            return
        
        # 周报数据
        if path == '/api/weekly':
            month = query.get('month', [None])[0]
            week = query.get('week', [None])[0]
            
            month_folders = get_real_month_folders()
            if not month_folders:
                self._send_json({"error": "No data"}, 404)
                return
            
            # 获取指定月份
            if month:
                matched = [m for m in month_folders if month in m.name]
                if matched:
                    latest_month = matched[0]
                else:
                    latest_month = sorted(month_folders, key=lambda x: x.name)[-1]
            else:
                latest_month = sorted(month_folders, key=lambda x: x.name)[-1]
            
            # 获取指定周
            week_folders = sorted([d for d in latest_month.iterdir() if d.is_dir()])
            if week:
                matched_week = [w for w in week_folders if week in w.name]
                if matched_week:
                    latest_week = matched_week[0]
                elif week_folders:
                    latest_week = week_folders[-1]
                else:
                    self._send_json({"error": "No week data"}, 404)
                    return
            else:
                latest_week = week_folders[-1] if week_folders else None
            
            if not latest_week:
                self._send_json({"error": "No week data"}, 404)
                return
            
            all_data = load_week_data(latest_week)
            if not all_data:
                self._send_json({"error": "No data"}, 404)
                return
            
            df_store = generate_store_summary(all_data)
            if '店铺' in df_store.columns:
                df_store['店铺类型'] = df_store['店铺'].apply(get_store_type)
            df_trend = generate_store_trend(all_data)
            df_fruit = generate_fruit_purchase_summary(all_data)
            df_overall = generate_fruit_overall_summary(all_data)
            dates = sort_dates_numerically([d['filename'] for d in all_data])
            txt_report = generate_txt_report(all_data, df_trend, df_fruit, df_overall, dates)
            
            # 简化水果数据（去除时间维度）
            fruit_stats = []
            if not df_fruit.empty:
                for _, row in df_fruit.iterrows():
                    fruit_stats.append({
                        "水果": row.get('水果', ''),
                        "进货量": float(row.get('数量', 0)),
                        "进货额": float(row.get('总价', 0)),
                        "波动系数": float(row.get('波动系数%', 0))
                    })
            
            result = {
                "week": latest_week.name,
                "month": latest_month.name,
                "summary": {
                    "店铺数": int(len(df_store['店铺'].unique())) if '店铺' in df_store.columns else 0,
                    "水果种类": int(len(df_fruit['水果'].unique())) if '水果' in df_fruit.columns else 0,
                    "总进货量": float(df_store['进货量(斤)'].sum()) if '进货量(斤)' in df_store.columns else 0,
                    "总进货额": float(df_store['进货额(元)'].sum()) if '进货额(元)' in df_store.columns else 0,
                },
                "stores": df_store.to_dict('records') if not df_store.empty else [],
                "fruit_stats": fruit_stats
            }
            
            self._send_json(result)
            return
        
        # 跨周对比数据
        if path == '/api/cross-week':
            month = query.get('month', [None])[0]
            
            month_folders = get_real_month_folders()
            if not month_folders:
                self._send_json({"error": "No data"}, 404)
                return
            
            if month:
                matched = [m for m in month_folders if month in m.name]
                latest_month = matched[0] if matched else sorted(month_folders, key=lambda x: x.name)[-1]
            else:
                latest_month = sorted(month_folders, key=lambda x: x.name)[-1]
            
            week_folders = sorted([d for d in latest_month.iterdir() if d.is_dir()])
            
            if len(week_folders) < 2:
                self._send_json({"error": "Need at least 2 weeks"}, 400)
                return
            
            generate_cross_week_report(week_folders, latest_month)
            
            # 加载跨周数据用于结构化返回
            all_week_data = []
            for wf in week_folders:
                wd = load_week_data(wf)
                if wd:
                    all_week_data.extend(wd)
            
            if all_week_data:
                df_store = generate_store_summary(all_week_data)
                if '店铺' in df_store.columns:
                    df_store['店铺类型'] = df_store['店铺'].apply(get_store_type)
            
            cross_week_dir = REPORTS_DIR / '跨周对比' / f'{latest_month.name}跨周对比'
            if cross_week_dir.exists() or all_week_data:
                result = {
                    "month": latest_month.name,
                    "weeks": len(week_folders),
                    "summary": {
                        "周数": len(week_folders)
                    },
                    "stores": df_store.to_dict('records') if all_week_data and not df_store.empty else []
                }
                self._send_json(result)
                return
            
            self._send_json({"error": "No data"}, 404)
            return
        
        # 月度汇总数据
        if path == '/api/monthly':
            month = query.get('month', [None])[0]
            
            month_folders = get_real_month_folders()
            if not month_folders:
                self._send_json({"error": "No data"}, 404)
                return
            
            if month:
                matched = [m for m in month_folders if month in m.name]
                if matched:
                    latest_month = matched[0]
                else:
                    self._send_json({"error": "Month not found"}, 404)
                    return
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
            
            # 返回结构化数据，不返回报告文本
            result = {
                "month": latest_month.name,
            }
            
            if df_store is not None and not df_store.empty:
                result["summary"] = {
                    "店铺数": int(len(df_store['店铺'].unique())),
                    "水果种类": int(len(df_fruit['水果'].unique())) if df_fruit is not None and '水果' in df_fruit.columns else 0,
                    "总进货量": float(df_store['进货量(斤)'].sum()),
                    "总进货额": float(df_store['进货额(元)'].sum()),
                }
                result["stores"] = df_store.to_dict('records')
                result["fruits"] = df_fruit.to_dict('records') if df_fruit is not None and not df_fruit.empty else []
            
            self._send_json(result)
            return
            return
        
        # 店铺列表
        if path == '/api/stores':
            month_folders = get_real_month_folders()
            if not month_folders:
                self._send_json({"error": "No data"}, 404)
                return
            
            latest_month = sorted(month_folders, key=lambda x: x.name)[-1]
            week_folders = sorted([d for d in latest_month.iterdir() if d.is_dir()])
            
            if not week_folders:
                self._send_json({"error": "No week data"}, 404)
                return
            
            latest_week = week_folders[-1]
            all_data = load_week_data(latest_week)
            
            if not all_data:
                self._send_json({"error": "No data"}, 404)
                return
            
            df_store = generate_store_summary(all_data)
            if '店铺' in df_store.columns:
                df_store['店铺类型'] = df_store['店铺'].apply(get_store_type)
            
            stores = df_store.to_dict('records') if not df_store.empty else []
            self._send_json({"stores": stores})
            return
        
        # 水果列表
        if path == '/api/fruits':
            month_folders = get_real_month_folders()
            if not month_folders:
                self._send_json({"error": "No data"}, 404)
                return
            
            latest_month = sorted(month_folders, key=lambda x: x.name)[-1]
            week_folders = sorted([d for d in latest_month.iterdir() if d.is_dir()])
            
            if not week_folders:
                self._send_json({"error": "No week data"}, 404)
                return
            
            latest_week = week_folders[-1]
            all_data = load_week_data(latest_week)
            
            if not all_data:
                self._send_json({"error": "No data"}, 404)
                return
            
            df_fruit = generate_fruit_purchase_summary(all_data)
            fruits = df_fruit.to_dict('records') if not df_fruit.empty else []
            self._send_json({"fruits": fruits})
            return
        
        # 404
        self._send_json({"error": "Not found"}, 404)
    
    def log_message(self, format, *args):
        pass  # 静默日志


def main():
    port = 8081
    server = HTTPServer(('0.0.0.0', port), APIHandler)
    print(f"📡 原版数据 API 已启动!")
    print(f"   访问 http://localhost:{port}")
    print(f"   进化插件可通过此接口获取数据")
    print(f"   按 Ctrl+C 停止")
    server.serve_forever()

if __name__ == '__main__':
    main()
