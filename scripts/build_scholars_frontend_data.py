# -*- coding: utf-8 -*-
"""生成 docs/scholars_data.js,供前端"学者追踪"板块读取。"""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "database", "scholars_config.json")
LITERATURE_PATH = os.path.join(BASE_DIR, "database", "scholars_literature.json")
OUT_PATH = os.path.join(BASE_DIR, "docs", "scholars_data.js")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def main():
    configs = load_json(CONFIG_PATH, [])
    literature = load_json(LITERATURE_PATH, [])

    lit_by_scholar = {}
    for item in literature:
        lit_by_scholar.setdefault(item["scholar_name"], []).append(item)

    scholars = []
    for c in configs:
        works = lit_by_scholar.get(c["name"], [])
        works_sorted = sorted(works, key=lambda w: w.get("date_added", ""), reverse=True)[:10]
        scholars.append({
            "name": c["name"],
            "category": c["category"],
            "rank": c["rank"],
            "tier": c["tier"],
            "research_topics": c["research_topics"],
            "research_methods": c["research_methods"],
            "why_track": c["why_track"],
            "profile_url": c["profile_url"],
            "tracking_status": c["tracking_status"],
            "literature": works_sorted,
        })

    scholars.sort(key=lambda s: (s["category"], s["rank"]))

    js = "window.SCHOLARS_DATA = " + json.dumps(scholars, ensure_ascii=False, indent=2) + ";\n"
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"已生成 {OUT_PATH},共 {len(scholars)} 位学者")


if __name__ == "__main__":
    main()
