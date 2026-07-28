# -*- coding: utf-8 -*-
"""
一次性(可重跑)解析脚本:
读取 database/scholars_raw.json(从Excel导出的100人原始信息)、
database/scholars_gs_ids.json(人工/agent通过网络搜索核实过的Google Scholar
学者主页user id)、database/scholars_nber_ids.json(NBER作者页uid,金融学者
覆盖较全),写入 database/scholars_config.json。

设计为"瀑布式"多重来源,而不是每人只认定一种来源:
1. google_scholar(首选): 覆盖面最广、摘要/期刊/完整作者名单最全,但
   实测发现Google对自动化请求的限流比较敏感且不总能快速恢复
   (同一环境内短时间大量测试后,即使降低到3秒一次的请求间隔,仍可能
   持续大批量失败,不像是单纯"频率超限几分钟自动解除"那么简单)
2. nber_author(次选): 金融学者常见的备用来源,过去实测非常稳定,
   从未触发限流,但只覆盖NBER-affiliated的经济学者,法学学者通常没有
3. faculty_citations(再次选): 个人/学校主页的SSRN链接与"Publications"
   类标题下的带年份引用列表

抓取时(scrape_scholars.py)会按上述优先级依次尝试,前一个失败/受限才用
下一个,这样即使Google Scholar当次不可用,也不会让学者"颗粒无收";这也是
应对"这次环境里Google Scholar被限流"的务实做法——保留Google Scholar作为
首选(尊重"改用Google Scholar"的要求),但不因为它当次失败就让整条数据
链路空手而归。
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scholars_common import scrape_faculty_page_citations

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "database", "scholars_raw.json")
GS_IDS_PATH = os.path.join(BASE_DIR, "database", "scholars_gs_ids.json")
NBER_IDS_PATH = os.path.join(BASE_DIR, "database", "scholars_nber_ids.json")
CONFIG_PATH = os.path.join(BASE_DIR, "database", "scholars_config.json")


def main():
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        scholars = json.load(f)
    with open(GS_IDS_PATH, "r", encoding="utf-8") as f:
        gs_ids = json.load(f)
    with open(NBER_IDS_PATH, "r", encoding="utf-8") as f:
        nber_ids = json.load(f)

    configs = []
    stats = {"google_scholar": 0, "nber_author": 0, "faculty_citations": 0,
              "manual_only": 0}

    for s in scholars:
        entry = {
            "name": s["name"],
            "category": s["category"],
            "rank": s["rank"],
            "tier": s["tier"],
            "research_topics": s["research_topics"],
            "research_methods": s["research_methods"],
            "why_track": s["why_track"],
            "profile_url": s["primary_source"],
        }

        methods = []
        if s["name"] in gs_ids:
            methods.append({"type": "google_scholar", "gs_user_id": gs_ids[s["name"]]})
            entry["gs_profile_url"] = f"https://scholar.google.com/citations?user={gs_ids[s['name']]}&hl=en"
        if s["name"] in nber_ids:
            methods.append({"type": "nber_author", "nber_uid": nber_ids[s["name"]]})

        has_faculty_page = bool(s["primary_source"]) and not s["primary_source"].lower().endswith(".pdf")
        if has_faculty_page:
            probe = scrape_faculty_page_citations(s["primary_source"], s["name"], limit=1)
            if probe:
                methods.append({"type": "faculty_citations", "url": s["primary_source"]})
            time.sleep(0.5)

        entry["tracking_methods"] = methods
        entry["tracking_status"] = "active" if methods else "manual_only"

        if methods:
            stats[methods[0]["type"]] += 1
        else:
            stats["manual_only"] += 1

        configs.append(entry)
        print(f"[{'+'.join(m['type'] for m in methods) or 'manual_only':40}] {s['name']}")

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(configs, f, ensure_ascii=False, indent=2)

    print("\n=== 解析统计(按首选来源计) ===")
    for k, v in stats.items():
        print(f"{k}: {v}")
    print(f"已写入 {CONFIG_PATH}")


if __name__ == "__main__":
    main()
