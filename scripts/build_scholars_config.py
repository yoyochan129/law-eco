# -*- coding: utf-8 -*-
"""
一次性(可重跑)解析脚本:
读取 database/scholars_raw.json(从Excel导出的100人原始信息),
判定/解析每位学者的可追踪来源类型,写入 database/scholars_config.json。

来源类型:
- nber_people_direct: "主要来源"本身就是NBER作者页,直接可用
- nber_paper_link: "主要来源"是某篇NBER论文链接,自动跳转解析出其NBER作者页
- generic_page: 个人主页/学校教师主页,用通用"快照"方式追踪(非结构化,准确度有限)
- pdf: 简历等PDF链接,标记为暂无法自动追踪
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scholars_common import (
    classify_source, resolve_nber_uid_from_people_page,
    resolve_nber_people_url_from_paper,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "database", "scholars_raw.json")
CONFIG_PATH = os.path.join(BASE_DIR, "database", "scholars_config.json")


def main():
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        scholars = json.load(f)

    configs = []
    stats = {"nber_people_direct": 0, "nber_paper_link_resolved": 0,
              "nber_paper_link_failed": 0, "generic_page": 0, "pdf": 0}

    for s in scholars:
        source_type = classify_source(s["primary_source"])
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

        if source_type == "nber_people_direct":
            uid = resolve_nber_uid_from_people_page(s["primary_source"])
            if uid:
                entry["tracking_type"] = "nber_author"
                entry["nber_uid"] = uid
                entry["tracking_status"] = "active"
                stats["nber_people_direct"] += 1
            else:
                entry["tracking_type"] = "generic_page"
                entry["tracking_status"] = "active"
                stats["generic_page"] += 1

        elif source_type == "nber_paper_link":
            people_url = resolve_nber_people_url_from_paper(s["primary_source"], s["name"])
            if people_url:
                uid = resolve_nber_uid_from_people_page(people_url)
                if uid:
                    entry["tracking_type"] = "nber_author"
                    entry["nber_uid"] = uid
                    entry["profile_url"] = people_url  # 用作者页替代论文页作为主页展示链接
                    entry["tracking_status"] = "active"
                    stats["nber_paper_link_resolved"] += 1
                else:
                    entry["tracking_type"] = "generic_page"
                    entry["tracking_status"] = "manual_only"
                    stats["nber_paper_link_failed"] += 1
            else:
                # 解析失败(通常是论文页作者链接与目标学者姓氏未匹配上,如合著论文里
                # 目标学者不是第一作者、姓氏拼写差异等),如实标注暂无法自动追踪,
                # 不要退化成不可靠的通用主页快照抓取
                entry["tracking_type"] = "generic_page"
                entry["tracking_status"] = "manual_only"
                stats["nber_paper_link_failed"] += 1
            time.sleep(0.5)

        elif source_type == "pdf":
            entry["tracking_type"] = "none"
            entry["tracking_status"] = "manual_only"
            stats["pdf"] += 1

        else:  # generic_page / none
            # 经实测,个人/学校主页的HTML结构差异太大,通用启发式抓取容易把导航栏、
            # 课程介绍、"关于本人"的媒体报道等误判成"学术文献",宁可如实标注"暂无法
            # 自动追踪"也不做低质量/易误导的展示。仍保留 profile_url 供前端展示主页链接。
            entry["tracking_type"] = "generic_page"
            entry["tracking_status"] = "manual_only"
            stats["generic_page"] += 1

        configs.append(entry)
        print(f"[{entry['tracking_type']:12}] {s['name']}")

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(configs, f, ensure_ascii=False, indent=2)

    print("\n=== 解析统计 ===")
    for k, v in stats.items():
        print(f"{k}: {v}")
    print(f"已写入 {CONFIG_PATH}")


if __name__ == "__main__":
    main()
