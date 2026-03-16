"""报表生成模块"""
import pandas as pd
from pathlib import Path
from datetime import datetime
from data_loader import sort_dates_numerically, load_week_data, get_fruit_category
from config import DATA_DIR, REPORTS_DIR

# 设置中文显示
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)


def generate_store_summary(all_data):
    """生成各店铺进货汇总"""
    records = []
    for data in all_data:
        df = data['detail']
        store_sum = df.groupby('店名').agg({'数量': 'sum', '总价': 'sum'}).reset_index()
        store_sum['日期'] = data['filename']
        store_sum.columns = ['店铺', '进货量(斤)', '进货额(元)', '日期']
        records.append(store_sum)
    
    return pd.concat(records, ignore_index=True)


def generate_store_trend(all_data):
    """生成各店铺进货趋势"""
    records = []
    for data in all_data:
        df = data['detail']
        store_sum = df.groupby('店名')['总价'].sum().reset_index()
        store_sum['日期'] = data['filename']
        records.append(store_sum)
    
    df = pd.concat(records, ignore_index=True)
    pivot = df.pivot(index='店名', columns='日期', values='总价').fillna(0)
    pivot = pivot.reset_index()
    pivot.columns.name = None
    
    dates = sort_dates_numerically([d['filename'] for d in all_data])
    
    pivot['波动系数%'] = (pivot[dates].std(axis=1) / pivot[dates].mean(axis=1) * 100).round(1)
    pivot.loc[pivot[dates].mean(axis=1) == 0, '波动系数%'] = 0
    
    result_cols = ['店名'] + dates + ['波动系数%']
    return pivot[result_cols]


def generate_fruit_purchase_summary(all_data):
    """生成各水果进货汇总（按分类合并）"""
    all_records = []
    date_cols = []
    
    for data in all_data:
        df = data['detail']
        df_valid = df[df['总价'] > 0].copy()
        # 应用水果分类映射
        df_valid['水果'] = df_valid['水果'].apply(get_fruit_category)
        # 按水果分类汇总
        fruit_sum = df_valid.groupby('水果').agg({'数量': 'sum', '总价': 'sum'}).reset_index()
        fruit_sum['日期'] = data['filename']
        all_records.append(fruit_sum)
        date_cols.append(data['filename'])
    
    df = pd.concat(all_records, ignore_index=True)
    
    # 透视表：按日期展开
    pivot_qty = df.pivot(index='水果', columns='日期', values='数量').fillna(0)
    pivot_amount = df.pivot(index='水果', columns='日期', values='总价').fillna(0)
    
    result = pivot_qty.reset_index()
    result.columns = ['水果'] + [f'{c}_量' for c in result.columns[1:]]
    
    amount_df = pivot_amount.reset_index()
    amount_df.columns = ['水果'] + [f'{c}_额' for c in amount_df.columns[1:]]
    
    result = result.merge(amount_df, on='水果', how='outer').fillna(0)
    
    amount_cols = [f'{d}_额' for d in date_cols]
    result['波动系数%'] = (result[amount_cols].std(axis=1) / result[amount_cols].mean(axis=1) * 100).round(1)
    result.loc[result[amount_cols].mean(axis=1) == 0, '波动系数%'] = 0
    
    return result
    result['波动系数%'] = (result[amount_cols].std(axis=1) / result[amount_cols].mean(axis=1) * 100).round(1)
    result.loc[result[amount_cols].mean(axis=1) == 0, '波动系数%'] = 0
    
    return result


def generate_store_detail(all_data):
    """生成每家店的详细进货明细"""
    all_records = []
    for data in all_data:
        df = data['detail']
        df_valid = df[df['总价'] > 0].copy()
        df_valid['日期'] = data['filename']
        all_records.append(df_valid)
    
    df = pd.concat(all_records, ignore_index=True)
    
    summary = df.groupby(['店名', '水果']).agg({'数量': 'sum', '总价': 'sum'}).reset_index()
    summary.columns = ['店铺', '水果', '总进货量(斤)', '总进货额(元)']
    
    return summary.sort_values(['店铺', '总进货额(元)'], ascending=[True, False])


def generate_fruit_overall_summary(all_data):
    """生成水果整体汇总"""
    all_records = []
    for data in all_data:
        df = data['detail']
        df_valid = df[df['总价'] > 0].copy()
        df_valid['日期'] = data['filename']
        all_records.append(df_valid)
    
    df = pd.concat(all_records, ignore_index=True)
    
    summary = df.groupby('水果').agg({'数量': 'sum', '总价': 'sum'}).reset_index()
    summary.columns = ['水果', '总进货量(斤)', '总进货额(元)']
    
    return summary.sort_values('总进货额(元)', ascending=False)


def generate_txt_report(all_data, df_store_trend, df_fruit, df_fruit_overall, dates):
    """生成Txt格式周报"""
    from data_loader import get_store_type
    
    # 1. 整体情况
    total_amount = sum(d['detail']['总价'].sum() for d in all_data)
    avg_amount = total_amount / len(dates) if dates else 0
    
    txt = f"周报汇报\n"
    txt += f"周期：{dates[0]} - {dates[-1]}\n\n"
    txt += "【整体情况】\n"
    txt += f"本周总进货额：¥{total_amount:.2f}\n"
    txt += f"日均进货额：¥{avg_amount:.2f}\n\n"
    
    # 2. 各店进货情况（按类型分组）
    txt += "【各店进货情况】\n"
    # 按行求和（每个店铺所有日期的进货额相加）
    store_totals = df_store_trend[dates].sum(axis=1)
    store_totals.index = df_store_trend['店名']  # 设置店铺名索引
    store_totals = store_totals.sort_values(ascending=False)
    df_fruit_pivot = df_fruit.set_index('水果')
    
    # 先按类型分组计算
    self_operation_total = 0  # 自营合计
    franchise_total = 0       # 加盟合计
    
    for i, store in enumerate(store_totals.index, 1):
        amount = store_totals[store]
        store_type = get_store_type(store)
        type_label = "🏭自营" if store_type == "自营" else "🔗加盟"
        
        vol_row = df_store_trend.loc[df_store_trend['店名'] == store, '波动系数%']
        volatility = vol_row.values[0] if len(vol_row) > 0 else 0
        vol_text = f"波动{volatility:.1f}%"
        if volatility < 20:
            vol_text += " 稳定"
        elif volatility < 50:
            vol_text += " 波动较大"
        else:
            vol_text += " 波动剧烈"
        
        txt += f"{i}. {store} {type_label}：¥{amount:.2f} ({vol_text})\n"
        
        # 累加到分类合计
        if store_type == "自营":
            self_operation_total += amount
        else:
            franchise_total += amount
    
    # 分类合计
    txt += f"  ├─ 自营店合计：¥{self_operation_total:.2f}\n"
    txt += f"  └─ 加盟店合计：¥{franchise_total:.2f}\n"
    
    # 3. 水果整体进货情况
    txt += f"\n【水果整体进货情况】\n"
    txt += f"本周水果总进货额：¥{total_amount:.2f}\n\n"
    
    top_fruits = df_fruit_overall.head(10)
    for _, row in top_fruits.iterrows():
        fruit = row['水果']
        qty = row['总进货量(斤)']
        amount = row['总进货额(元)']
        
        if fruit in df_fruit_pivot.index:
            volatility = df_fruit_pivot.loc[fruit, '波动系数%']
            vol_text = f"(波动{volatility:.1f}%"
            if volatility < 20:
                vol_text += " 稳定)"
            elif volatility < 50:
                vol_text += " 波动较大)"
            else:
                vol_text += " 波动剧烈)"
        else:
            vol_text = ""
        
        txt += f"- 【{fruit}】：{qty:.1f}斤 / ¥{amount:.2f} {vol_text}\n"
    
    return txt


def generate_cross_week_report(week_folders, month_folder):
    """生成跨周对比报告"""
    month_name = month_folder.name
    
    # 收集每周的整体数据
    week_summaries = []
    for week_folder in week_folders:
        all_data = load_week_data(week_folder)
        if not all_data:
            continue
        
        dates = sort_dates_numerically([d['filename'] for d in all_data])
        
        all_records = []
        for data in all_data:
            df = data['detail']
            df_valid = df[df['总价'] > 0].copy()
            all_records.append(df_valid)
        
        df = pd.concat(all_records, ignore_index=True)
        
        total_qty = df['数量'].sum()
        total_amount = df['总价'].sum()
        
        fruit_summary = df.groupby('水果').agg({'数量': 'sum', '总价': 'sum'}).reset_index()
        fruit_summary.columns = ['水果', '进货量(斤)', '进货额(元)']
        
        store_summary = df.groupby('店名').agg({'数量': 'sum', '总价': 'sum'}).reset_index()
        store_summary.columns = ['店铺', '进货量(斤)', '进货额(元)']
        
        # 收集该周的水果种类（只统计有进货的）
        fruit_types = set(df[df['总价'] > 0]['水果'].unique())
        
        # 每种水果的进货额（用于环比）
        fruit_amounts = dict(zip(fruit_summary['水果'], fruit_summary['进货额(元)']))
        
        # 按店铺类型分别统计水果
        from data_loader import get_store_type
        df_self = df[df['店名'].apply(lambda x: get_store_type(x) == '自营')]
        df_franchise = df[df['店名'].apply(lambda x: get_store_type(x) == '加盟')]
        
        # 自营店水果种类
        fruit_types_self = set(df_self[df_self['总价'] > 0]['水果'].unique()) if len(df_self) > 0 else set()
        # 加盟店水果种类
        fruit_types_franchise = set(df_franchise[df_franchise['总价'] > 0]['水果'].unique()) if len(df_franchise) > 0 else set()
        
        # 自营店水果金额
        fruit_summary_self = df_self.groupby('水果').agg({'总价': 'sum'}).reset_index() if len(df_self) > 0 else pd.DataFrame()
        fruit_amounts_self = dict(zip(fruit_summary_self['水果'], fruit_summary_self['总价'])) if len(fruit_summary_self) > 0 else {}
        
        # 加盟店水果金额
        fruit_summary_franchise = df_franchise.groupby('水果').agg({'总价': 'sum'}).reset_index() if len(df_franchise) > 0 else pd.DataFrame()
        fruit_amounts_franchise = dict(zip(fruit_summary_franchise['水果'], fruit_summary_franchise['总价'])) if len(fruit_summary_franchise) > 0 else {}
        
        # 每个店铺的进货额（用于环比）
        store_amounts = dict(zip(store_summary['店铺'], store_summary['进货额(元)']))
        
        week_summaries.append({
            'week': week_folder.name,
            'dates': dates,
            'total_qty': total_qty,
            'total_amount': total_amount,
            'fruits': fruit_summary,
            'stores': store_summary,
            'fruit_types': fruit_types,
            'fruit_types_self': fruit_types_self,  # 自营店水果种类
            'fruit_types_franchise': fruit_types_franchise,  # 加盟店水果种类
            'fruit_amounts': fruit_amounts,  # 水果金额 dict
            'fruit_amounts_self': fruit_amounts_self,  # 自营店水果金额
            'fruit_amounts_franchise': fruit_amounts_franchise,  # 加盟店水果金额
            'store_amounts': store_amounts  # 店铺金额 dict
        })
    
    if len(week_summaries) < 2:
        print("  ⚠️ 周数不足，跳过跨周对比")
        return
    
    # 生成跨周对比Excel（reports目录下）
    cross_base_dir = REPORTS_DIR / '跨周对比'
    output_dir = cross_base_dir / f'{month_name}跨周对比'
    
    if output_dir.exists() and any(output_dir.glob('跨周对比_*.xlsx')):
        print(f"  ⏭️ 已有跨周对比报告，跳过")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    output_name = f"跨周对比_{now.strftime('%Y-%m-%d_%H-%M-%S')}"
    excel_path = output_dir / f'{output_name}.xlsx'
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        overview_data = []
        for ws in week_summaries:
            overview_data.append({
                '周': ws['week'],
                '周期': f"{ws['dates'][0]} - {ws['dates'][-1]}",
                '进货量(斤)': ws['total_qty'],
                '进货额(元)': ws['total_amount']
            })
        pd.DataFrame(overview_data).to_excel(writer, sheet_name='每周概览', index=False)
        
        all_fruits = pd.concat([ws['fruits'] for ws in week_summaries], ignore_index=True)
        fruit_compare = all_fruits.groupby('水果').agg({'进货量(斤)': 'sum', '进货额(元)': 'sum'}).reset_index()
        fruit_compare = fruit_compare.sort_values('进货额(元)', ascending=False)
        fruit_compare.to_excel(writer, sheet_name='水果对比', index=False)
        
        # 添加店铺类型
        from data_loader import get_store_type
        all_stores = pd.concat([ws['stores'] for ws in week_summaries], ignore_index=True)
        all_stores['店铺类型'] = all_stores['店铺'].apply(get_store_type)
        store_compare = all_stores.groupby(['店铺', '店铺类型']).agg({'进货量(斤)': 'sum', '进货额(元)': 'sum'}).reset_index()
        store_compare = store_compare.sort_values('进货额(元)', ascending=False)
        store_compare.to_excel(writer, sheet_name='店铺对比', index=False)
    
    df_store_compare = store_compare
    df_fruit_compare = fruit_compare
    
    txt_path = output_dir / f'{output_name}_汇报.txt'
    txt_content = generate_cross_week_txt(week_summaries, df_store_compare, df_fruit_compare)
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    
    print(f"  ✅ 跨周对比: {excel_path.name}")
    print(f"  ✅ 跨周汇报: {txt_path.name}")


def generate_cross_week_txt(week_summaries, df_store_compare, df_fruit_compare):
    """生成跨周对比Txt汇报"""
    from data_loader import get_store_type
    
    first_week = week_summaries[0]
    last_week = week_summaries[-1]
    total_weeks = len(week_summaries)
    
    txt = f"跨周对比汇报（共{total_weeks}周）\n"
    txt += f"周期：{first_week['dates'][0]} - {last_week['dates'][-1]}\n\n"
    
    # 每周整体情况 - 按店铺类型
    txt += "【每周整体情况】\n"
    for ws in week_summaries:
        # 按类型计算
        store_amounts = ws['store_amounts']
        self_op = sum(amt for s, amt in store_amounts.items() if get_store_type(s) == '自营')
        franchise = sum(amt for s, amt in store_amounts.items() if get_store_type(s) == '加盟')
        txt += f"- {ws['week']}：{ws['dates'][0]} - {ws['dates'][-1]}\n"
        txt += f"    总计：{ws['total_qty']:.1f}斤，¥{ws['total_amount']:.2f}\n"
        txt += f"    🏭自营：¥{self_op:.2f}\n"
        txt += f"    🔗加盟：¥{franchise:.2f}\n"
    
    # 环比变化 - 按店铺类型
    if len(week_summaries) >= 2:
        latest = week_summaries[-1]
        prev = week_summaries[-2]
        
        # 总体环比
        qty_change = latest['total_qty'] - prev['total_qty']
        amount_change = latest['total_amount'] - prev['total_amount']
        qty_pct = (qty_change / prev['total_qty'] * 100) if prev['total_qty'] > 0 else 0
        amount_pct = (amount_change / prev['total_amount'] * 100) if prev['total_amount'] > 0 else 0
        
        # 自营环比
        prev_self = sum(amt for s, amt in prev['store_amounts'].items() if get_store_type(s) == '自营')
        curr_self = sum(amt for s, amt in latest['store_amounts'].items() if get_store_type(s) == '自营')
        self_change = curr_self - prev_self
        self_pct = (self_change / prev_self * 100) if prev_self > 0 else 0
        
        # 加盟环比
        prev_franchise = sum(amt for s, amt in prev['store_amounts'].items() if get_store_type(s) == '加盟')
        curr_franchise = sum(amt for s, amt in latest['store_amounts'].items() if get_store_type(s) == '加盟')
        franchise_change = curr_franchise - prev_franchise
        franchise_pct = (franchise_change / prev_franchise * 100) if prev_franchise > 0 else 0
        
        txt += f"\n【环比变化】({prev['week']} → {latest['week']})\n"
        txt += f"- 总计：¥{amount_change:+.2f} ({amount_pct:+.1f}%)\n"
        txt += f"  🏭自营：¥{self_change:+.2f} ({self_pct:+.1f}%)\n"
        txt += f"  🔗加盟：¥{franchise_change:+.2f} ({franchise_pct:+.1f}%)\n"
    
    # 整体趋势 - 按店铺类型
    if first_week['week'] != last_week['week']:
        qty_trend = last_week['total_qty'] - first_week['total_qty']
        amount_trend = last_week['total_amount'] - first_week['total_amount']
        qty_trend_pct = (qty_trend / first_week['total_qty'] * 100) if first_week['total_qty'] > 0 else 0
        amount_trend_pct = (amount_trend / first_week['total_amount'] * 100) if first_week['total_amount'] > 0 else 0
        
        # 自营趋势
        first_self = sum(amt for s, amt in first_week['store_amounts'].items() if get_store_type(s) == '自营')
        last_self = sum(amt for s, amt in last_week['store_amounts'].items() if get_store_type(s) == '自营')
        self_trend = last_self - first_self
        self_trend_pct = (self_trend / first_self * 100) if first_self > 0 else 0
        
        # 加盟趋势
        first_franchise = sum(amt for s, amt in first_week['store_amounts'].items() if get_store_type(s) == '加盟')
        last_franchise = sum(amt for s, amt in last_week['store_amounts'].items() if get_store_type(s) == '加盟')
        franchise_trend = last_franchise - first_franchise
        franchise_trend_pct = (franchise_trend / first_franchise * 100) if first_franchise > 0 else 0
        
        txt += f"\n【整体趋势】({first_week['week']} → {last_week['week']})\n"
        txt += f"- 总计：¥{amount_trend:+.2f} ({amount_trend_pct:+.1f}%)\n"
        txt += f"  🏭自营：¥{self_trend:+.2f} ({self_trend_pct:+.1f}%)\n"
        txt += f"  🔗加盟：¥{franchise_trend:+.2f} ({franchise_trend_pct:+.1f}%)\n"
    
    # 平均周量 - 按店铺类型
    avg_qty = sum(ws['total_qty'] for ws in week_summaries) / len(week_summaries)
    avg_self = sum(sum(amt for s, amt in ws['store_amounts'].items() if get_store_type(s) == '自营') for ws in week_summaries) / len(week_summaries)
    avg_franchise = sum(sum(amt for s, amt in ws['store_amounts'].items() if get_store_type(s) == '加盟') for ws in week_summaries) / len(week_summaries)
    
    txt += f"\n【平均周量】\n"
    txt += f"- 总计：{avg_qty:.1f}斤，¥{avg_qty * 4:.2f}\n"  # 假设每周约4天
    txt += f"  🏭自营：¥{avg_self:.2f}/周\n"
    txt += f"  🔗加盟：¥{avg_franchise:.2f}/周\n"
    
    # 日均进货金额对比（按店铺类型）
    if len(week_summaries) >= 2:
        from data_loader import get_store_type
        
        txt += "\n【日均进货金额对比】\n"
        
        for i in range(len(week_summaries)):
            curr_week = week_summaries[i]
            days_count = len(curr_week['dates'])
            
            # 按类型分别计算
            store_amounts = curr_week['store_amounts']
            self_op_amount = sum(amt for store, amt in store_amounts.items() if get_store_type(store) == '自营')
            franchise_amount = sum(amt for store, amt in store_amounts.items() if get_store_type(store) == '加盟')
            
            curr_daily_total = curr_week['total_amount'] / days_count if days_count > 0 else 0
            curr_daily_self = self_op_amount / days_count if days_count > 0 else 0
            curr_daily_franchise = franchise_amount / days_count if days_count > 0 else 0
            
            if i == 0:
                # 第一周没有上周对比
                txt += f"- {curr_week['week']}（{days_count}天）：\n"
                txt += f"    总计：¥{curr_daily_total:.2f}/天\n"
                txt += f"    🏭自营：¥{curr_daily_self:.2f}/天\n"
                txt += f"    🔗加盟：¥{curr_daily_franchise:.2f}/天\n"
            else:
                prev_week = week_summaries[i - 1]
                prev_days = len(prev_week['dates'])
                prev_store_amounts = prev_week['store_amounts']
                prev_self = sum(amt for store, amt in prev_store_amounts.items() if get_store_type(store) == '自营')
                prev_franchise = sum(amt for store, amt in prev_store_amounts.items() if get_store_type(store) == '加盟')
                
                prev_daily_total = prev_week['total_amount'] / prev_days if prev_days > 0 else 0
                prev_daily_self = prev_self / prev_days if prev_days > 0 else 0
                prev_daily_franchise = prev_franchise / prev_days if prev_days > 0 else 0
                
                daily_change_total = curr_daily_total - prev_daily_total
                daily_change_self = curr_daily_self - prev_daily_self
                daily_change_franchise = curr_daily_franchise - prev_daily_franchise
                
                txt += f"- {curr_week['week']}（{days_count}天）：\n"
                txt += f"    总计：¥{curr_daily_total:.2f}/天（{daily_change_total:+.2f}）\n"
                txt += f"    🏭自营：¥{curr_daily_self:.2f}/天（{daily_change_self:+.2f}）\n"
                txt += f"    🔗加盟：¥{curr_daily_franchise:.2f}/天（{daily_change_franchise:+.2f}）\n"
    
    # 水果种类变化分析 - 逐周环比（按店铺类型）
    if len(week_summaries) >= 2:
        txt += "\n【水果种类变化】\n"
        
        # 第1周：没有上一周，全部是新增
        first_week = week_summaries[0]
        
        # 自营
        curr_fruits_self = first_week.get('fruit_types_self', set())
        txt += f"- {first_week['week']} 🏭自营：新增 {len(curr_fruits_self)} 种\n"
        for fruit in sorted(curr_fruits_self):
            txt += f"    + {fruit}\n"
        
        # 加盟
        curr_fruits_franchise = first_week.get('fruit_types_franchise', set())
        txt += f"- {first_week['week']} 🔗加盟：新增 {len(curr_fruits_franchise)} 种\n"
        for fruit in sorted(curr_fruits_franchise):
            txt += f"    + {fruit}\n"
        
        # 后续每周：和上一周比
        for i in range(1, len(week_summaries)):
            prev_week = week_summaries[i - 1]
            curr_week = week_summaries[i]
            
            # 自营
            prev_fruits_self = prev_week.get('fruit_types_self', set())
            curr_fruits_self = curr_week.get('fruit_types_self', set())
            added_self = curr_fruits_self - prev_fruits_self
            removed_self = prev_fruits_self - curr_fruits_self
            
            txt += f"- {curr_week['week']} 🏭自营：新增 {len(added_self)} 种，减少 {len(removed_self)} 种\n"
            for fruit in sorted(added_self):
                txt += f"    + {fruit}\n"
            for fruit in sorted(removed_self):
                txt += f"    - {fruit}\n"
            
            # 加盟
            prev_fruits_franchise = prev_week.get('fruit_types_franchise', set())
            curr_fruits_franchise = curr_week.get('fruit_types_franchise', set())
            added_franchise = curr_fruits_franchise - prev_fruits_franchise
            removed_franchise = prev_fruits_franchise - curr_fruits_franchise
            
            txt += f"- {curr_week['week']} 🔗加盟：新增 {len(added_franchise)} 种，减少 {len(removed_franchise)} 种\n"
            for fruit in sorted(added_franchise):
                txt += f"    + {fruit}\n"
            for fruit in sorted(removed_franchise):
                txt += f"    - {fruit}\n"
    
    # 水果金额环比变化（前3，按店铺类型）
    if len(week_summaries) >= 2:
        txt += "\n【水果金额环比变化】\n"
        
        for i in range(1, len(week_summaries)):
            prev_week = week_summaries[i - 1]
            curr_week = week_summaries[i]
            
            # 自营店水果金额变化
            prev_amounts_self = prev_week.get('fruit_amounts_self', {})
            curr_amounts_self = curr_week.get('fruit_amounts_self', {})
            
            all_fruits_self = set(prev_amounts_self.keys()) | set(curr_amounts_self.keys())
            changes_self = []
            for fruit in all_fruits_self:
                prev_amt = prev_amounts_self.get(fruit, 0)
                curr_amt = curr_amounts_self.get(fruit, 0)
                change = curr_amt - prev_amt
                changes_self.append((fruit, change))
            
            changes_sorted_self = sorted(changes_self, key=lambda x: x[1], reverse=True)
            top_increase_self = [(f, c) for f, c in changes_sorted_self if c > 0][:3]
            top_decrease_self = [(f, c) for f, c in changes_sorted_self if c < 0][-3:][::-1]
            
            txt += f"- {curr_week['week']} 🏭自营 vs {prev_week['week']}：\n"
            if top_increase_self:
                txt += "    增加TOP3：\n"
                for fruit, change in top_increase_self:
                    txt += f"        + {fruit}：¥{change:+.2f}\n"
            if top_decrease_self:
                txt += "    减少TOP3：\n"
                for fruit, change in top_decrease_self:
                    txt += f"        - {fruit}：¥{change:.2f}\n"
            
            # 加盟店水果金额变化
            prev_amounts_franchise = prev_week.get('fruit_amounts_franchise', {})
            curr_amounts_franchise = curr_week.get('fruit_amounts_franchise', {})
            
            all_fruits_franchise = set(prev_amounts_franchise.keys()) | set(curr_amounts_franchise.keys())
            changes_franchise = []
            for fruit in all_fruits_franchise:
                prev_amt = prev_amounts_franchise.get(fruit, 0)
                curr_amt = curr_amounts_franchise.get(fruit, 0)
                change = curr_amt - prev_amt
                changes_franchise.append((fruit, change))
            
            changes_sorted_franchise = sorted(changes_franchise, key=lambda x: x[1], reverse=True)
            top_increase_franchise = [(f, c) for f, c in changes_sorted_franchise if c > 0][:3]
            top_decrease_franchise = [(f, c) for f, c in changes_sorted_franchise if c < 0][-3:][::-1]
            
            txt += f"- {curr_week['week']} 🔗加盟 vs {prev_week['week']}：\n"
            if top_increase_franchise:
                txt += "    增加TOP3：\n"
                for fruit, change in top_increase_franchise:
                    txt += f"        + {fruit}：¥{change:+.2f}\n"
            if top_decrease_franchise:
                txt += "    减少TOP3：\n"
                for fruit, change in top_decrease_franchise:
                    txt += f"        - {fruit}：¥{change:.2f}\n"
    
    # 店铺金额环比变化（前3）
    if len(week_summaries) >= 2:
        from data_loader import get_store_type
        
        txt += "\n【店铺金额环比变化】\n"
        
        for i in range(1, len(week_summaries)):
            prev_week = week_summaries[i - 1]
            curr_week = week_summaries[i]
            
            prev_amounts = prev_week['store_amounts']
            curr_amounts = curr_week['store_amounts']
            
            # 计算变化
            all_stores = set(prev_amounts.keys()) | set(curr_amounts.keys())
            changes = []
            for store in all_stores:
                prev_amt = prev_amounts.get(store, 0)
                curr_amt = curr_amounts.get(store, 0)
                change = curr_amt - prev_amt
                store_type = get_store_type(store)
                changes.append((store, change, store_type))
            
            # 排序
            changes_sorted = sorted(changes, key=lambda x: x[1], reverse=True)
            
            # 前3增加
            top_increase = [(s, c, t) for s, c, t in changes_sorted if c > 0][:3]
            # 前3减少
            top_decrease = [(s, c, t) for s, c, t in changes_sorted if c < 0][-3:][::-1]
            
            txt += f"- {curr_week['week']} vs {prev_week['week']}：\n"
            
            if top_increase:
                txt += "    增加TOP3：\n"
                for store, change, store_type in top_increase:
                    type_label = "🏭自营" if store_type == "自营" else "🔗加盟"
                    txt += f"        + {store} {type_label}：¥{change:+.2f}\n"
            else:
                txt += "    增加：无\n"
            
            if top_decrease:
                txt += "    减少TOP3：\n"
                for store, change, store_type in top_decrease:
                    type_label = "🏭自营" if store_type == "自营" else "🔗加盟"
                    txt += f"        - {store} {type_label}：¥{change:.2f}\n"
            else:
                txt += "    减少：无\n"
    
    return txt


def generate_monthly_report(month_folder):
    """生成月度汇总报告（简单算账版）"""
    from data_loader import get_store_type
    
    month_name = month_folder.name
    
    all_records = []
    week_names = []
    
    for week_folder in sorted(month_folder.iterdir()):
        if not week_folder.is_dir() or week_folder.name in ['跨周对比', '月度汇总']:
            continue
        
        all_data = load_week_data(week_folder)
        if not all_data:
            continue
        
        for data in all_data:
            df = data['detail']
            df_valid = df[df['总价'] > 0].copy()
            # 添加店铺类型列
            df_valid['店铺类型'] = df_valid['店名'].apply(get_store_type)
            all_records.append(df_valid)
            week_names.append(week_folder.name)
    
    if not all_records:
        print(f"  ⚠️ 无有效数据，跳过月度汇总")
        return
    
    df = pd.concat(all_records, ignore_index=True)
    
    # 创建月度汇总目录（reports目录下）
    monthly_base_dir = REPORTS_DIR / '月度汇总'
    output_dir = monthly_base_dir / f'{month_name}月度汇总'
    
    if output_dir.exists() and any(output_dir.glob(f'{month_name}_月度汇总_*.xlsx')):
        print(f"  ⏭️ 已有月度汇总，跳过")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    output_name = f"{month_name}_月度汇总_{now.strftime('%Y-%m-%d_%H-%M-%S')}"
    excel_path = output_dir / f'{output_name}.xlsx'
    
    fruit_summary = df.groupby('水果').agg({'数量': 'sum', '总价': 'sum'}).reset_index()
    fruit_summary.columns = ['水果', '进货量(斤)', '进货额(元)']
    fruit_summary = fruit_summary.sort_values('进货额(元)', ascending=False)
    
    # 按店铺汇总时包含类型
    store_summary = df.groupby(['店名', '店铺类型']).agg({'数量': 'sum', '总价': 'sum'}).reset_index()
    store_summary.columns = ['店铺', '店铺类型', '进货量(斤)', '进货额(元)']
    store_summary = store_summary.sort_values('进货额(元)', ascending=False)
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        fruit_summary.to_excel(writer, sheet_name='按水果', index=False)
        store_summary.to_excel(writer, sheet_name='按店铺', index=False)
    
    txt_content = f"月度汇总汇报\n"
    txt_content += f"月份：{month_name}\n\n"
    
    txt_content += "【按水果汇总】\n"
    for _, row in fruit_summary.iterrows():
        txt_content += f"- {row['水果']}：{row['进货量(斤)']:.1f}斤，¥{row['进货额(元)']:.2f}\n"
    
    total_fruit_amount = fruit_summary['进货额(元)'].sum()
    txt_content += f"\n水果总计：¥{total_fruit_amount:.2f}\n"
    
    # 按店铺汇总（带类型标签）
    txt_content += "\n【按店铺汇总】\n"
    self_operation_total = 0
    franchise_total = 0
    
    for _, row in store_summary.iterrows():
        store_type = row['店铺类型']
        type_label = "🏭自营" if store_type == "自营" else "🔗加盟"
        txt_content += f"- {row['店铺']} {type_label}：{row['进货量(斤)']:.1f}斤，¥{row['进货额(元)']:.2f}\n"
        
        if store_type == "自营":
            self_operation_total += row['进货额(元)']
        else:
            franchise_total += row['进货额(元)']
    
    # 分类合计
    txt_content += f"  ├─ 自营店合计：¥{self_operation_total:.2f}\n"
    txt_content += f"  └─ 加盟店合计：¥{franchise_total:.2f}\n"
    
    total_store_amount = store_summary['进货额(元)'].sum()
    txt_content += f"\n店铺总计：¥{total_store_amount:.2f}\n"
    
    txt_path = output_dir / f'{output_name}_汇报.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    
    print(f"  ✅ 月度汇总: {excel_path.name}")
    print(f"  ✅ 月度汇报: {txt_path.name}")


def generate_global_cross_week_report(data_folder):
    """生成无视月份的全局跨周对比报告"""
    all_week_summaries = []
    
    for month_dir in sorted(data_folder.iterdir()):
        if not month_dir.is_dir() or month_dir.name in ['跨周对比', '月度汇总']:
            continue
        
        for week_folder in sorted(month_dir.iterdir()):
            if not week_folder.is_dir() or week_folder.name in ['跨周对比', '月度汇总']:
                continue
            
            all_data = load_week_data(week_folder)
            if not all_data:
                continue
            
            dates = sort_dates_numerically([d['filename'] for d in all_data])
            
            all_records = []
            for data in all_data:
                df = data['detail']
                df_valid = df[df['总价'] > 0].copy()
                all_records.append(df_valid)
            
            if not all_records:
                continue
            
            df = pd.concat(all_records, ignore_index=True)
            total_qty = df['数量'].sum()
            total_amount = df['总价'].sum()
            
            fruit_summary = df.groupby('水果').agg({'数量': 'sum', '总价': 'sum'}).reset_index()
            fruit_summary.columns = ['水果', '进货量(斤)', '进货额(元)']
            
            store_summary = df.groupby('店名').agg({'数量': 'sum', '总价': 'sum'}).reset_index()
            store_summary.columns = ['店铺', '进货量(斤)', '进货额(元)']
            # 添加店铺类型
            from data_loader import get_store_type
            store_summary['店铺类型'] = store_summary['店铺'].apply(get_store_type)
            
            all_week_summaries.append({
                'week': week_folder.name,
                'month': month_dir.name,
                'dates': dates,
                'total_qty': total_qty,
                'total_amount': total_amount,
                'fruits': fruit_summary,
                'stores': store_summary
            })
    
    if len(all_week_summaries) < 2:
        print("  ⚠️ 全局周数不足，跳过全局跨周对比")
        return
    
    output_dir = REPORTS_DIR / '跨周对比'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_dir.exists() and any(output_dir.glob('全局跨周对比_*.xlsx')):
        print("  ⏭️ 已有全局跨周对比，跳过")
        return
    
    now = datetime.now()
    output_name = f"全局跨周对比_{now.strftime('%Y-%m-%d_%H-%M-%S')}"
    excel_path = output_dir / f'{output_name}.xlsx'
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        overview_data = []
        for ws in all_week_summaries:
            overview_data.append({
                '周': ws['week'],
                '月份': ws['month'],
                '周期': f"{ws['dates'][0]} - {ws['dates'][-1]}",
                '进货量(斤)': ws['total_qty'],
                '进货额(元)': ws['total_amount']
            })
        pd.DataFrame(overview_data).to_excel(writer, sheet_name='每周概览', index=False)
        
        all_fruits = pd.concat([ws['fruits'] for ws in all_week_summaries], ignore_index=True)
        fruit_total = all_fruits.groupby('水果').agg({'进货量(斤)': 'sum', '进货额(元)': 'sum'}).reset_index()
        fruit_total = fruit_total.sort_values('进货额(元)', ascending=False)
        fruit_total.to_excel(writer, sheet_name='按水果汇总', index=False)
        
        all_stores = pd.concat([ws['stores'] for ws in all_week_summaries], ignore_index=True)
        store_total = all_stores.groupby(['店铺', '店铺类型']).agg({'进货量(斤)': 'sum', '进货额(元)': 'sum'}).reset_index()
        store_total = store_total.sort_values('进货额(元)', ascending=False)
        store_total.to_excel(writer, sheet_name='按店铺汇总', index=False)
    
    txt_content = f"全局跨周对比汇报（共{len(all_week_summaries)}周）\n"
    first_week = all_week_summaries[0]
    last_week = all_week_summaries[-1]
    txt_content += f"周期：{first_week['dates'][0]} - {last_week['dates'][-1]}\n\n"
    
    txt_content += "【每周整体情况】\n"
    for ws in all_week_summaries:
        txt_content += f"- {ws['week']}（{ws['month']}）：{ws['dates'][0]} - {ws['dates'][-1]}，总进货 {ws['total_qty']:.1f}斤，¥{ws['total_amount']:.2f}\n"
    
    avg_qty = sum(ws['total_qty'] for ws in all_week_summaries) / len(all_week_summaries)
    avg_amount = sum(ws['total_amount'] for ws in all_week_summaries) / len(all_week_summaries)
    txt_content += f"\n【平均周量】\n"
    txt_content += f"- 周均进货量：{avg_qty:.1f}斤\n"
    txt_content += f"- 周均进货额：¥{avg_amount:.2f}\n"
    
    # 添加店铺对比（带类型）
    txt_content += "\n【店铺对比】\n"
    self_operation_total = 0
    franchise_total = 0
    
    for _, row in store_total.iterrows():
        store_type = row['店铺类型']
        type_label = "🏭自营" if store_type == "自营" else "🔗加盟"
        txt_content += f"- {row['店铺']} {type_label}：{row['进货量(斤)']:.1f}斤，¥{row['进货额(元)']:.2f}\n"
        
        if store_type == "自营":
            self_operation_total += row['进货额(元)']
        else:
            franchise_total += row['进货额(元)']
    
    txt_content += f"  ├─ 自营店合计：¥{self_operation_total:.2f}\n"
    txt_content += f"  └─ 加盟店合计：¥{franchise_total:.2f}\n"
    
    txt_path = output_dir / f'{output_name}_汇报.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    
    print(f"  ✅ 全局跨周对比: {excel_path.name}")
    print(f"  ✅ 全局跨周汇报: {txt_path.name}")
