# -*- coding: utf-8 -*-
"""在不重新抓取的情况下,依据当前 database/articles.json 重新生成周报 Markdown 与前端数据文件。
用于分类规则调整后的重新生成。
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_report import build_report, auto_trend_summary, load_json, save_json, REPORT_DIR, DOCS_DATA_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "articles.json")

parser = argparse.ArgumentParser()
parser.add_argument("--period-start", required=True)
parser.add_argument("--period-end", required=True)
args = parser.parse_args()

db = load_json(DB_PATH, [])
this_week = [a for a in db if a.get("week_of") == args.period_end]

trend_text = auto_trend_summary(this_week, f"{args.period_start} 至 {args.period_end}")
report_md = build_report(args.period_start, args.period_end, this_week, trend_text)

os.makedirs(REPORT_DIR, exist_ok=True)
report_filename = f"商业法律研究动向_{args.period_end}.md"
report_path = os.path.join(REPORT_DIR, report_filename)
with open(report_path, "w", encoding="utf-8") as f:
    f.write(report_md)
print(f"周报已重新生成: {report_path}")

js_content = "window.ARTICLES_DATA = " + json.dumps(db, ensure_ascii=False, indent=2) + ";\n"
js_content += "window.LAST_REPORT = " + json.dumps({
    "period_start": args.period_start,
    "period_end": args.period_end,
    "trend_summary": trend_text,
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
}, ensure_ascii=False, indent=2) + ";\n"
os.makedirs(os.path.dirname(DOCS_DATA_PATH), exist_ok=True)
with open(DOCS_DATA_PATH, "w", encoding="utf-8") as f:
    f.write(js_content)
print(f"前端数据文件已重新生成: {DOCS_DATA_PATH}")
