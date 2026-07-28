# -*- coding: utf-8 -*-
"""
汇总脚本:
1. 读取 database/new_articles_raw.json
2. 对每篇文章分类(classify.py)
3. 生成周报 Markdown -> 周报/商业法律研究动向_YYYY-MM-DD.md
4. 合并进 database/articles.json
5. 重新生成 docs/articles_data.js (供前端页面读取)
6. 更新 database/state.json

趋势概括段落通过 --trend-file 传入一个纯文本文件(每段一行/用空行分隔),
若不传则自动生成一段基于统计数据的简要概括。
"""
import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

from dateutil import parser as dtparser
from deep_translator import GoogleTranslator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import classify_article, TOPICS

_translator = GoogleTranslator(source="en", target="zh-CN")


def translate_text(text):
    if not text:
        return ""
    try:
        return _translator.translate(text[:4500]) or ""
    except Exception as exc:
        print(f"[warn] 翻译失败: {exc}")
        return ""

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "database", "new_articles_raw.json")
DB_PATH = os.path.join(BASE_DIR, "database", "articles.json")
STATE_PATH = os.path.join(BASE_DIR, "database", "state.json")
DOCS_DATA_PATH = os.path.join(BASE_DIR, "docs", "articles_data.js")
REPORT_DIR = os.path.join(BASE_DIR, "周报")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_date(raw):
    if not raw:
        return ""
    try:
        dt = dtparser.parse(raw)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def auto_trend_summary(articles, period_label):
    topic_counter = Counter()
    for a in articles:
        topic_counter[a["primary_topic"]] += 1
    top_topics = topic_counter.most_common(5)
    source_counter = Counter(a["source"] for a in articles)
    top_sources = source_counter.most_common(3)

    lines = []
    lines.append(
        f"本期（{period_label}）共收录 {len(articles)} 篇新文章，"
        f"覆盖来源 {len(source_counter)} 个。从主题分布看，"
        + "、".join(f"{t}（{c}篇）" for t, c in top_topics)
        + "是本周最集中的研究领域。"
    )
    lines.append(
        "本周产出较多的来源包括："
        + "、".join(f"{s}（{c}篇）" for s, c in top_sources)
        + "，反映出这些机构在相关议题上的持续关注度。"
    )
    lines.append(
        "整体来看，本周研究议题横跨公司治理、金融监管、货币政策与金融市场等多个维度，"
        "既有聚焦具体政策评论与实务问题的博客类文章，也有采用实证方法、"
        "因果识别策略的学术工作论文，体现出商业法律与金融交叉领域研究方法的多样性。"
    )
    lines.append(
        "需要说明的是，由于本次为系统首次运行，数据库中尚无历史基线，"
        "因此本期报告呈现的是各数据源当前可获取的全部最新文章（而非严格意义上"
        "\"上次运行后新增\"的增量），后续每周运行将仅呈现真正的增量新文章。"
    )
    return "\n\n".join(lines)


def build_report(period_start, period_end, articles, trend_text):
    lines = []
    lines.append("## 商业法律研究动向")
    lines.append(f"报告周期：{period_start} — {period_end}")
    lines.append("")
    lines.append("## 本周研究趋势概括")
    lines.append("")
    lines.append(trend_text)
    lines.append("")
    lines.append("## 各来源新文章")
    lines.append("")

    by_source = defaultdict(list)
    for a in articles:
        by_source[a["source"]].append(a)

    for source, items in by_source.items():
        lines.append(f"### {source}")
        lines.append("")
        for a in items:
            lines.append(f"**{a['title']}**")
            if a.get("title_zh"):
                lines.append(f"*{a['title_zh']}*")
            lines.append("")
            lines.append(f"- 作者：{a['authors'] or '（见原文链接）'}")
            lines.append(f"- 摘要：{a['abstract'] or '（原文未提供摘要，详见链接）'}")
            if a.get("abstract_zh"):
                lines.append(f"- 摘要（中文）：{a['abstract_zh']}")
            kw = "、".join(a["keywords"]) if a["keywords"] else "无"
            lines.append(f"- 关键词：{kw}")
            lines.append(f"- 原文链接：{a['url']}")
            lines.append(f"- 分类：{' / '.join(a['topics'])}（主分类：{a['primary_topic']}）")
            lines.append("")
        lines.append("")

    lines.append("## \U0001F4CC 索引")
    lines.append("")
    by_topic = defaultdict(list)
    for a in articles:
        for t in a["topics"]:
            by_topic[t].append(a)

    for topic in TOPICS:
        items = by_topic.get(topic, [])
        lines.append(f"### {topic}（{len(items)}）")
        if items:
            for a in items:
                lines.append(f"- [{a['title']}]({a['url']})")
        lines.append("")

    lines.append(f"## 报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period-start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--period-end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--trend-file", default=None, help="趋势概括文本文件路径(可选)")
    args = parser.parse_args()

    raw_articles = load_json(RAW_PATH, [])
    if not raw_articles:
        print("没有新文章,跳过本次报告生成。")
        return

    week_of = args.period_end
    classified = []
    for a in raw_articles:
        cls = classify_article(a["title"], a.get("abstract", ""))
        a["topics"] = cls["topics"]
        a["primary_topic"] = cls["primary_topic"]
        a["publish_date_norm"] = normalize_date(a.get("publish_date", ""))
        a["week_of"] = week_of
        a["date_added"] = datetime.now(timezone.utc).isoformat()
        a["title_zh"] = translate_text(a["title"])
        time.sleep(0.3)
        a["abstract_zh"] = translate_text(a.get("abstract", ""))
        time.sleep(0.3)
        classified.append(a)

    if args.trend_file and os.path.exists(args.trend_file):
        with open(args.trend_file, "r", encoding="utf-8") as f:
            trend_text = f.read().strip()
    else:
        trend_text = auto_trend_summary(
            classified, f"{args.period_start} 至 {args.period_end}"
        )

    report_md = build_report(args.period_start, args.period_end, classified, trend_text)

    os.makedirs(REPORT_DIR, exist_ok=True)
    report_filename = f"商业法律研究动向_{args.period_end}.md"
    report_path = os.path.join(REPORT_DIR, report_filename)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"周报已生成: {report_path}")

    db = load_json(DB_PATH, [])
    db.extend(classified)
    save_json(DB_PATH, db)
    print(f"数据库已更新,当前总数: {len(db)}")

    state = load_json(STATE_PATH, {})
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["last_report"] = report_filename
    save_json(STATE_PATH, state)

    # 重新生成前端数据文件
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
    print(f"前端数据文件已更新: {DOCS_DATA_PATH}")

    # 清空本次已处理的 raw 文件,避免重复处理
    save_json(RAW_PATH, [])

    print(f"\n新增文章数: {len(classified)}")
    print(f"数据库当前总数: {len(db)}")


if __name__ == "__main__":
    main()
