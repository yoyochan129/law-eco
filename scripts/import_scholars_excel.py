# -*- coding: utf-8 -*-
"""
从"Top50法学学者与Top50金融学者"Excel文件导入学者名单,生成 database/scholars_raw.json。
之后需要依次运行:
  python3 scripts/build_scholars_config.py       # 解析每位学者的追踪来源
  python3 scripts/scrape_scholars.py              # 抓取最新文献
  python3 scripts/build_scholars_frontend_data.py # 生成前端数据文件

用法: python3 scripts/import_scholars_excel.py /path/to/xxx.xlsx
"""
import json
import os
import sys

import openpyxl

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(BASE_DIR, "database", "scholars_raw.json")

SHEETS = [("Top50法学学者", "法学"), ("Top50金融学者", "金融")]


def main():
    if len(sys.argv) < 2:
        print("用法: python3 scripts/import_scholars_excel.py /path/to/xxx.xlsx")
        sys.exit(1)

    xlsx_path = sys.argv[1]
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)

    scholars = []
    for sheet_name, category in SHEETS:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))[4:]  # 前4行是标题/说明/表头
        for r in rows:
            if not r[0] or not r[1]:
                continue
            scholars.append({
                "rank": r[0],
                "name": r[1].strip(),
                "category": category,
                "research_topics": r[2],
                "research_methods": r[3],
                "why_track": r[4],
                "relevance": r[5],
                "quality": r[6],
                "activity": r[7],
                "composite": r[8],
                "tier": r[9],
                "primary_source": r[10],
                "note": r[11],
            })

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(scholars, f, ensure_ascii=False, indent=2)
    print(f"已导入 {len(scholars)} 位学者 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
