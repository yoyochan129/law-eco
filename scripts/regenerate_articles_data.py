# -*- coding: utf-8 -*-
"""
轻量脚本:仅根据当前 database/articles.json 重新生成 docs/articles_data.js,
不重新抓取、不重新生成周报。用于网页端"直接编辑标签"功能写回
database/articles.json 之后,由GitHub Actions自动触发重建前端数据文件,
让标签修改尽快体现在网页上。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_report import load_json, DOCS_DATA_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "articles.json")


def main():
    db = load_json(DB_PATH, [])

    # 保留 docs/articles_data.js 里已有的 LAST_REPORT 部分(趋势概括等),
    # 只重写 ARTICLES_DATA 部分,避免覆盖掉最近一次周报生成时写入的概括文字
    last_report_js = "window.LAST_REPORT = {};\n"
    if os.path.exists(DOCS_DATA_PATH):
        with open(DOCS_DATA_PATH, "r", encoding="utf-8") as f:
            existing = f.read()
        marker = "window.LAST_REPORT ="
        idx = existing.find(marker)
        if idx != -1:
            last_report_js = existing[idx:]
            if not last_report_js.strip().endswith(";"):
                last_report_js = last_report_js.rstrip() + "\n"

    js_content = "window.ARTICLES_DATA = " + json.dumps(db, ensure_ascii=False, indent=2) + ";\n"
    js_content += last_report_js

    with open(DOCS_DATA_PATH, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"已根据当前数据库重新生成 {DOCS_DATA_PATH}(共 {len(db)} 篇文章)")


if __name__ == "__main__":
    main()
