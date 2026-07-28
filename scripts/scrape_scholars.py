# -*- coding: utf-8 -*-
"""
「学者追踪」抓取脚本:
1. 读取 database/scholars_config.json(已解析出的追踪来源,每人可能有多个
   按优先级排列的 tracking_methods)
2. 按优先级依次尝试: google_scholar -> nber_author -> faculty_citations,
   前一个失败/受限(如Google Scholar被限流返回None)才用下一个,确保单一
   来源当次不可用时该学者也不会颗粒无收
3. 中文翻译标题+摘要(有摘要才翻译)
4. 更新 database/scholars_literature.json(每位学者的知识库,前端"最新10篇"
   展示用)与 database/scholars_updates.json(本次新增,用于生成"本周学者
   动态"周报章节)
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from deep_translator import GoogleTranslator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scholars_common import (
    fetch_google_scholar_works, fetch_google_scholar_citation_detail,
    fetch_nber_author_works, scrape_faculty_page_citations, GS_REQUEST_DELAY,
)

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


def try_google_scholar(method, name, known):
    works = fetch_google_scholar_works(method["gs_user_id"], limit=10)
    time.sleep(GS_REQUEST_DELAY)
    if works is None:
        return None  # 请求失败/被限流,调用方应尝试下一个来源
    fresh = [w for w in works if w["url"] not in known]
    for w in fresh:
        detail = fetch_google_scholar_citation_detail(w["url"])
        time.sleep(GS_REQUEST_DELAY)
        if detail:
            w.update({k: v for k, v in detail.items() if v})
    return works, fresh


def try_nber(method, name, known):
    works = fetch_nber_author_works(method["nber_uid"], limit=10)
    time.sleep(1)
    fresh = [w for w in works if w["url"] not in known]
    return works, fresh


def try_faculty_citations(method, name, known):
    works = scrape_faculty_page_citations(method["url"], name, limit=10)
    time.sleep(1)
    fresh = [w for w in works if w["url"] not in known]
    return works, fresh


HANDLERS = {
    "google_scholar": try_google_scholar,
    "nber_author": try_nber,
    "faculty_citations": try_faculty_citations,
}


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
        methods = cfg.get("tracking_methods") or []
        if cfg.get("tracking_status") != "active" or not methods:
            print(f"[skip] {name}: tracking_status={cfg.get('tracking_status')}")
            continue

        known = known_urls_by_scholar.get(name, set())
        result = None
        used_method = None

        for method in methods:
            handler = HANDLERS.get(method["type"])
            if not handler:
                continue
            outcome = handler(method, name, known)
            if outcome is not None:
                result = outcome
                used_method = method["type"]
                break
            print(f"[fallback] {name}: {method['type']} 不可用,尝试下一个来源")

        if result is None:
            print(f"[error] {name}: 所有来源均不可用,本次跳过")
            continue

        total_works, fresh = result
        for w in fresh:
            w["scholar_name"] = name
            w["category"] = cfg["category"]
            w["title_zh"] = translate(w["title"])
            w["abstract_zh"] = translate(w.get("abstract", "")) if w.get("abstract") else ""
            w["date_added"] = datetime.now(timezone.utc).isoformat()
            w["week_of"] = args.period_end
            w["source_method"] = used_method
            new_items.append(w)
        print(f"[ok] {name} ({used_method}): total={len(total_works)} new={len(fresh)}")

    literature.extend(new_items)
    save_json(LITERATURE_PATH, literature)

    prev_updates = load_json(UPDATES_PATH, [])
    save_json(UPDATES_PATH, prev_updates + new_items)

    print(f"\n本次新增文献 {len(new_items)} 条,学者文献库总数 {len(literature)}")


if __name__ == "__main__":
    main()
