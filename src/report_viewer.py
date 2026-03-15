#!/usr/bin/env python3
"""
汇报文件Web查看器
启动后访问 http://localhost:8080
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import html

# 路径配置
BASE_DIR = Path(__file__).parent.parent  # 茗花目录
DATA_DIR = BASE_DIR / 'data'
REPORTS_DIR = BASE_DIR / 'reports'  # 报表目录（与data分离）
TEMPLATE_PATH = BASE_DIR / 'src' / 'templates' / 'template.html'

def generate_html():
    """生成HTML页面"""
    # 读取模板
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()
    
    data_folder = BASE_DIR / 'data'
    
    # 全局跨周对比
    global_cross = None
    global_cross_dir = REPORTS_DIR / '跨周对比'
    if global_cross_dir.exists():
        txt_files = sorted(global_cross_dir.glob('全局跨周对比_*_汇报.txt'))
        if txt_files:
            latest = txt_files[-1]
            with open(latest, 'r', encoding='utf-8') as f:
                content = f.read()
            global_cross = {
                'title': '全局跨周对比',
                'file': latest.name,
                'content': content
            }
    
    # 按月份组织：{月份: {week: [...], cross: [...]}}
    month_data = {}
    
    # 从data目录扫描原始数据月份
    if DATA_DIR.exists():
        for month_dir in sorted(DATA_DIR.iterdir()):
            if month_dir.is_dir() and not month_dir.name.startswith('.'):
                month_name = month_dir.name
                month_data[month_name] = {'weeks': [], 'cross': None, 'monthly': None}
                
                # 扫描周汇报（从reports目录）
                reports_month_dir = REPORTS_DIR / month_name
                if reports_month_dir.exists():
                    for week_dir in sorted(reports_month_dir.iterdir()):
                        if not week_dir.is_dir() or week_dir.name == '跨周对比':
                            continue
                        report_dir = week_dir / '汇报'
                        if report_dir.exists():
                            txt_files = sorted(report_dir.glob('*_汇报.txt'))
                            if txt_files:
                                latest = txt_files[-1]
                                with open(latest, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                month_data[month_name]['weeks'].append({
                                    'title': week_dir.name,
                                    'file': latest.name,
                                    'path': str(latest.relative_to(BASE_DIR)),
                                    'content': content
                                })
                
                # 扫描跨周对比（从reports目录）
                cross_dir = REPORTS_DIR / '跨周对比' / f'{month_name}跨周对比'
                if cross_dir.exists():
                    txt_files = sorted(cross_dir.glob('*_汇报.txt'))
                    if txt_files:
                        latest = txt_files[-1]
                        with open(latest, 'r', encoding='utf-8') as f:
                            content = f.read()
                        month_data[month_name]['cross'] = {
                            'title': '跨周对比',
                            'file': latest.name,
                            'path': str(latest.relative_to(BASE_DIR)),
                            'content': content
                        }
                
                # 扫描月度汇总（从reports目录）
                monthly_summary_dir = REPORTS_DIR / '月度汇总' / f'{month_name}月度汇总'
                if monthly_summary_dir.exists():
                    txt_files = sorted(monthly_summary_dir.glob('*_汇报.txt'))
                    if txt_files:
                        latest = txt_files[-1]
                        with open(latest, 'r', encoding='utf-8') as f:
                            content = f.read()
                        month_data[month_name]['monthly'] = {
                            'title': '月度汇总',
                            'file': latest.name,
                            'path': str(latest.relative_to(BASE_DIR)),
                            'content': content
                        }
    
    # 动态内容从这里开始
    html_content = ''
    
    if not month_data:
        html_content += '<div class="empty">暂无汇报文件，请先运行 weekly_report.py 生成汇报</div>'
    else:
        # 遍历每个月
        for month_idx, (month_name, data) in enumerate(month_data.items()):
            weeks = data['weeks']
            cross = data['cross']
            monthly = data.get('monthly')
            
            if not weeks and not cross and not monthly:
                continue
            
            html_content += f'<div class="month-section">\n'
            html_content += f'<div class="month-title">📅 {month_name}</div>\n'
            
            # 该月的下拉选择器
            html_content += '<div class="header">\n'
            
            if weeks:
                html_content += f'''    <div class="selector">
        <span class="selector-label">📊 每周汇总</span>
        <select id="week-{month_idx}-select" onchange="showReport('week', '{month_idx}', this.value)">
'''
                for i, w in enumerate(weeks):
                    selected = 'selected' if i == 0 else ''
                    html_content += f'            <option value="{i}" {selected}>{w["title"]}</option>\n'
                html_content += f'''        </select>
    </div>
    <div class="selector">
        <span class="selector-label">🏪 店铺类型</span>
        <select id="store-type-{month_idx}-select" onchange="filterAllStoreTypes('{month_idx}', this.value)">
            <option value="all">全部</option>
            <option value="自营">🏭 自营店</option>
            <option value="加盟">🔗 加盟店</option>
        </select>
    </div>
'''
            
            if cross:
                html_content += '''    <div class="selector">
        <span class="selector-label">📈 整体汇总</span>
        <select id="cross-{}-select" onchange="showReport('cross', '{}', this.value)">
'''.format(month_idx, month_idx)
                html_content += f'            <option value="0">{cross["title"]}</option>\n'
                html_content += '''        </select>
    </div>
'''
            
            if monthly:
                html_content += '''    <div class="selector">
        <span class="selector-label">📅 月度汇总</span>
        <select id="monthly-{}-select" onchange="showReport('monthly', '{}', this.value)">
'''.format(month_idx, month_idx)
                html_content += f'            <option value="0">{monthly["title"]}</option>\n'
                html_content += '''        </select>
    </div>
'''
            
            html_content += '</div>\n'
            
            # 内容区
            html_content += '<div class="content-wrapper">\n'
            
            for i, w in enumerate(weeks):
                active = 'active' if i == 0 else ''
                content_escaped = html.escape(w['content']).lstrip()
                html_content += f'''    <div class="report-content {active}" id="week-{month_idx}-{i}">
        <div class="report-header">
            <div class="report-title">📊 {w['title']}</div>
            <div class="report-file">{w['file']}</div>
        </div>
{content_escaped}
    </div>
'''
            
            # 三个模块平行显示
            
            if cross:
                # cross和monthly各只有一个选项，默认显示
                active = 'active'
                content_escaped = html.escape(cross['content']).lstrip()
                html_content += f'''    <div class="report-content {active}" id="cross-{month_idx}-0">
        <div class="report-header">
            <div class="report-title">📈 {cross['title']}</div>
            <div class="report-file">{cross['file']}</div>
        </div>
{content_escaped}
    </div>
'''
            
            if monthly:
                # cross和monthly各只有一个选项，默认显示
                active = 'active'
                content_escaped = html.escape(monthly['content']).lstrip()
                html_content += f'''    <div class="report-content {active}" id="monthly-{month_idx}-0">
        <div class="report-header">
            <div class="report-title">📅 {monthly['title']}</div>
            <div class="report-file">{monthly['file']}</div>
        </div>
{content_escaped}
    </div>
'''
            
            html_content += '</div>\n'
            html_content += '</div>\n'
    
    # 替换模板占位符
    
    # 添加全局跨周对比（无视月份）
    if global_cross:
        html_content += f'''<div class="month-section">
<div class="month-title">🌐 全局跨周对比</div>
<div class="content-wrapper">
    <div class="report-content active" id="global-cross-0">
        <div class="report-header">
            <div class="report-title">🌐 {global_cross['title']}</div>
            <div class="report-file">{global_cross['file']}</div>
        </div>
{html.escape(global_cross['content']).lstrip()}
    </div>
</div>
</div>
'''
    html_content = template.replace('{{CONTENT}}', html_content)
    
    # 嵌入viewer.js内容，而不是引用外部文件
    js_path = TEMPLATE_PATH.parent / 'viewer.js'
    with open(js_path, 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    html_content = html_content.replace('<script src="viewer.js"></script>', 
                                         f'<script>{js_content}</script>')
    
    return html_content

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = generate_html()
            self.wfile.write(html.encode('utf-8'))
        else:
            super().do_GET()

def main():
    port = 8080
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"🌸 茗花汇报查看器已启动!")
    print(f"   访问 http://localhost:{port}")
    print(f"   按 Ctrl+C 停止")
    server.serve_forever()

if __name__ == '__main__':
    main()
