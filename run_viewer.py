#!/usr/bin/env python3
"""启动汇报查看器"""
import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# 先运行报表生成
print("=" * 50)
print("📊 先生成汇报数据...")
print("=" * 50)
from weekly_report import main as generate_reports
generate_reports()

print("\n" + "=" * 50)
print("🌸 启动汇报查看器...")
print("=" * 50 + "\n")

from report_viewer import main

if __name__ == '__main__':
    main()
