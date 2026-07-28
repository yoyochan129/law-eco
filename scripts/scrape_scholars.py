# -*- coding: utf-8 -*-
"""
「学者追踪」抓取脚本:
1. 读取 database/scholars_config.json(已解析出的追踪来源)
2. nber_author 类型: 调用NBER作者作品API,取最新10篇(含摘要)
3. generic_page 类型: 抓取教师主页"快照",与上次快照做diff,找出新增链接
4. 中文翻译标题+摘要(有摘要才翻译)
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
from scholars_common import fetch_nber_author_works, snapshot_faculty_page

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "database", "scholars_config.json")
LITERATURE_PATH = os.path.join(BASE_DIR, "database", "scholars_literature.json")
SNAPSHOTS_PATH = os.path.join(BASE_DIR, "database", "scholars_snapshots.json")
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

    snapshots = load_json(SNAPSHOTS_PATH, {})

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

        elif ttype == "generic_page":
            url = cfg["profile_url"]
            current = snapshot_faculty_page(url)
            prev_urls = set(snapshots.get(name, []))
            fresh_links = [it for it in current if it["url"] not in prev_urls and it["url"] not in known]
            # 首次运行(prev_urls为空)时,只取前10条作为初始基线展示,避免把整页导航链接当"新文献"灌进去
            if not prev_urls:
                fresh_links = fresh_links[:10]
            for it in fresh_links:
                it["scholar_name"] = name
                it["category"] = cfg["category"]
                it["authors"] = it["authors"] or name
                it["title_zh"] = translate(it["title"])
                it["abstract_zh"] = ""
                it["date_added"] = datetime.now(timezone.utc).isoformat()
                it["week_of"] = args.period_end
                new_items.append(it)
            snapshots[name] = [it["url"] for it in current]
            print(f"[ok] {name} (generic_page snapshot): page_links={len(current)} new={len(fresh_links)}")
            time.sleep(1)

        else:
            print(f"[skip] {name}: tracking_status={cfg.get('tracking_status')}")

    literature.extend(new_items)
    save_json(LITERATURE_PATH, literature)
    save_json(SNAPSHOTS_PATH, snapshots)

    prev_updates = load_json(UPDATES_PATH, [])
    save_json(UPDATES_PATH, prev_updates + new_items)

    print(f"\n本次新增文献 {len(new_items)} 条,学者文献库总数 {len(literature)}")


if __name__ == "__main__":
    main()
