#!/usr/bin/env python3
"""
店铺进货与水果价格周报生成器
自动分析最近数据，生成Excel + MD报告
"""
from pathlib import Path
from datetime import datetime
import pandas as pd
from data_loader import (
    sort_dates_numerically, get_all_excel_files, get_week_folders,
    get_month_folders, load_week_data
)
from generators import (
    generate_store_summary, generate_store_trend,
    generate_fruit_purchase_summary, generate_store_detail,
    generate_fruit_overall_summary, generate_txt_report,
    generate_cross_week_report, generate_cross_week_txt,
    generate_global_cross_week_report, generate_monthly_report
)

# 设置中文显示
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)

# 路径配置
from config import DATA_DIR, REPORTS_DIR
FOLDER = DATA_DIR


def process_week(week_folder, month_name):
    """处理单个周，生成报告"""
    week_name = week_folder.name
    print(f"\n📂 处理: {week_name}")
    
    all_data = load_week_data(week_folder)
    if not all_data:
        print(f"  ⚠️ {week_name} 无数据")
        return None
    
    # 检查汇报目录是否已有报告（reports目录下）
    output_dir = REPORTS_DIR / month_name / week_name / '汇报'
    if output_dir.exists() and any(output_dir.iterdir()):
        print(f"  ⏭️ {week_name} 已有报告，跳过")
        # 读取已有的汇报文件内容返回
        existing_files = sorted(output_dir.glob('*_汇报.txt'))
        if existing_files:
            with open(existing_files[-1], 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    now = datetime.now()
    output_name = f"{week_name}_{now.strftime('%Y-%m-%d_%H-%M-%S')}"
    excel_path = output_dir / f'{output_name}.xlsx'
    txt_path = output_dir / f'{output_name}_汇报.txt'
    
    # 生成Excel
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_store_summary = generate_store_summary(all_data)
        df_store_summary.to_excel(writer, sheet_name='各店进货明细', index=False)
        
        df_store_trend = generate_store_trend(all_data)
        df_store_trend.to_excel(writer, sheet_name='各店进货趋势', index=False)
        
        df_fruit = generate_fruit_purchase_summary(all_data)
        df_fruit.to_excel(writer, sheet_name='水果进货汇总', index=False)
        
        df_fruit_overall = generate_fruit_overall_summary(all_data)
        df_fruit_overall.to_excel(writer, sheet_name='整体汇总', index=False)
        
        df_detail = generate_store_detail(all_data)
        df_detail.to_excel(writer, sheet_name='店铺水果明细', index=False)
    
    print(f"  ✅ Excel: {excel_path.name}")
    
    # 生成Txt
    dates = sort_dates_numerically([d['filename'] for d in all_data])
    txt_content = generate_txt_report(all_data, df_store_trend, df_fruit, df_fruit_overall, dates)
    
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    
    print(f"  ✅ Txt: {txt_path.name}")
    
    return txt_content

def main():
    print("🚀 正在生成周报...\n")
    
    # 按月份分组处理
    month_folders = get_month_folders()
    
    for month_folder in month_folders:
        month_name = month_folder.name
        week_folders = sorted([d for d in month_folder.iterdir() if d.is_dir()])
        print(f"📅 {month_name}：{len(week_folders)} 个周")
        
        # 处理每周汇报
        for week_folder in week_folders:
            result = process_week(week_folder, month_name)
            if result:
                print(f"\n{'='*50}")
                print(f"📊 {week_folder.name} 汇报")
                print('='*50)
                print(result)
        
        # 生成月份内的跨周对比
        if len(week_folders) >= 2:
            print(f"\n📈 生成 {month_name} 跨周对比报告...")
            generate_cross_week_report(week_folders, month_folder)
        
        # 生成月度汇总
        print(f"\n📅 生成 {month_name} 月度汇总...")
        generate_monthly_report(month_folder)
    
    # 生成全局跨周对比（无视月份）
    print(f"\n🌐 生成全局跨周对比报告...")
    generate_global_cross_week_report(FOLDER)


if __name__ == '__main__':
    main()

