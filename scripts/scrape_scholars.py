# -*- coding: utf-8 -*-
"""
「学者追踪」抓取脚本:
1. 读取 database/scholars_config.json(已解析出的追踪来源)
2. nber_author 类型: 调用NBER作者作品API,取最新10篇(含摘要)
3. faculty_citations 类型: 从个人/学校主页提取SSRN论文链接与
   "Publications"类标题下的带年份引用列表(build_scholars_config.py
   已确认该来源能提取到真实文献才会标记为此类型)
4. 中文翻译标题(faculty_citations类型通常无摘要可翻译)
5. 更新 database/scholars_literature.json(每位学者的知识库,前端"最新10篇"展示用)
   与 database/scholars_updates.json(本次新增,用于生成"本周学者动态"周报章节)
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from deep_translator import GoogleTranslator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scholars_common import fetch_nber_author_works, scrape_faculty_page_citations

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "database", "scholars_config.json")
LITERATURE_PATH = os.path.join(BASE_DIR, "database", "scholars_literature.json")
UPDATES_PATH = os.path.join(BASE_DIR, "database", "scholars_updates.json")

translator = GoogleTranslator(source="en", target="zh-CN")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def translate(text):
    if not text:
        return ""
    try:
        return translator.translate(text[:4500]) or ""
    except Exception as exc:
        print(f"[warn] 翻译失败: {exc}")
        return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period-end", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--limit", type=int, default=0, help="仅处理前N位学者(调试用)")
    args = parser.parse_args()

    configs = load_json(CONFIG_PATH, [])
    if args.limit:
        configs = configs[: args.limit]

    literature = load_json(LITERATURE_PATH, [])
    known_urls_by_scholar = {}
    for item in literature:
        known_urls_by_scholar.setdefault(item["scholar_name"], set()).add(item["url"])

    new_items = []

    for cfg in configs:
        name = cfg["name"]
        ttype = cfg["tracking_type"] if cfg.get("tracking_status") == "active" else "manual_only"
        known = known_urls_by_scholar.get(name, set())

        if ttype == "nber_author":
            works = fetch_nber_author_works(cfg["nber_uid"], limit=10)
            fresh = [w for w in works if w["url"] not in known]
            for w in fresh:
                w["scholar_name"] = name
                w["category"] = cfg["category"]
                w["title_zh"] = translate(w["title"])
                w["abstract_zh"] = translate(w["abstract"]) if w["abstract"] else ""
                w["date_added"] = datetime.now(timezone.utc).isoformat()
                w["week_of"] = args.period_end
                new_items.append(w)
            print(f"[ok] {name} (nber_author): total={len(works)} new={len(fresh)}")
            time.sleep(1)

        elif ttype == "faculty_citations":
            url = cfg["profile_url"]
            works = scrape_faculty_page_citations(url, name, limit=10)
            fresh = [w for w in works if w["url"] not in known]
            for w in fresh:
                w["scholar_name"] = name
                w["category"] = cfg["category"]
                w["title_zh"] = translate(w["title"])
                w["abstract_zh"] = ""
                w["date_added"] = datetime.now(timezone.utc).isoformat()
                w["week_of"] = args.period_end
                new_items.append(w)
            print(f"[ok] {name} (faculty_citations): total={len(works)} new={len(fresh)}")
            time.sleep(1)

        else:
            print(f"[skip] {name}: tracking_status={cfg.get('tracking_status')}")

    literature.extend(new_items)
    save_json(LITERATURE_PATH, literature)

    prev_updates = load_json(UPDATES_PATH, [])
    save_json(UPDATES_PATH, prev_updates + new_items)

    print(f"\n本次新增文献 {len(new_items)} 条,学者文献库总数 {len(literature)}")


if __name__ == "__main__":
    main()
