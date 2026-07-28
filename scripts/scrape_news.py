# -*- coding: utf-8 -*-
"""
「每周新闻」抓取脚本:
1. 遍历 news_sources_config.NEWS_SOURCES,拉取RSS
2. 只保留发布时间在最近7天内的条目(本次要求:只抓过去一周的新闻,不做历史回填)
3. 按来源策略提取发言人
4. 摘要处理:原文有摘要则整段机器翻译,没有摘要则留空(不拼凑节选)
5. 按URL去重后写入 database/news.json
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
from deep_translator import GoogleTranslator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from news_sources_config import NEWS_SOURCES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS_DB_PATH = os.path.join(BASE_DIR, "database", "news.json")
LOG_PATH = os.path.join(BASE_DIR, "logs", "scrape_news_log.json")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
HEADERS = {"User-Agent": UA}
TIMEOUT = 15
LOOKBACK_DAYS = 7

translator = GoogleTranslator(source="en", target="zh-CN")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clean_html(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", BeautifulSoup(text, "html.parser").get_text(" ")).strip()


def parse_date_safe(raw):
    if not raw:
        return None
    try:
        dt = dtparser.parse(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def translate_full(text):
    if not text:
        return ""
    try:
        return translator.translate(text[:4500]) or ""
    except Exception as exc:
        print(f"[warn] 翻译失败: {exc}")
        return ""


def extract_speaker_title_prefix(title, sep):
    """形如 'Name: Title' 或 'Name, Title' 的标题,取分隔符前的姓名部分"""
    if sep not in title:
        return "", title
    name, rest = title.split(sep, 1)
    name = name.strip()
    rest = rest.strip()
    # 名字部分通常很短(不像正常句子),超过6个词大概率不是人名,放弃识别
    if 0 < len(name.split()) <= 5 and len(name) < 40:
        return name, rest
    return "", title


MIN_REAL_SUMMARY_LEN = 40


def looks_like_name_not_summary(text):
    """SEC speeches的RSS summary字段有时只是发言人姓名/职位(如'Commissioner Hester M. Peirce'),
    不是真正摘要;真实摘要通常是完整句子且明显更长,这里用长度做启发式判断
    (不能用是否含句号判断,因为姓名里的中间名缩写'M.'本身就带句号)"""
    return bool(text) and len(text) <= 60


def extract_speaker_detail_byline(url):
    """SEC speeches详情页署名提取(尽力而为,请求失败或未命中返回空字符串)"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(" ", strip=True)[:800]
        m = re.search(r"\bby\s+((?:[A-Z][a-zA-Z.\'-]+\s*){1,4})", text)
        if m:
            return m.group(1).strip()
    except Exception as exc:
        print(f"[warn] SEC详情页抓取失败: {exc}")
    return ""


def process_source(source, cutoff):
    d = feedparser.parse(source["feed_url"])
    strategy = source["speaker_strategy"]
    items = []

    for e in d.entries:
        title = clean_html(e.get("title", "")).strip()
        link = e.get("link", "").strip()
        if not title or not link:
            continue

        pub_raw = e.get("published", "") or e.get("updated", "")
        pub_dt = parse_date_safe(pub_raw)
        if pub_dt and pub_dt < cutoff:
            continue  # 超过回看窗口,跳过(RSS通常按时间倒序,可以考虑提前break,这里保守用continue)

        raw_summary = clean_html(e.get("summary", ""))
        speaker = ""
        display_title = title

        if strategy == "feed_author":
            speaker = e.get("author", "") or ""
        elif strategy == "title_prefix":
            speaker, display_title = extract_speaker_title_prefix(
                title, source["title_prefix_sep"]
            )
        elif strategy == "detail_page_byline":
            if looks_like_name_not_summary(raw_summary):
                # RSS的summary字段实际是发言人姓名/职位,不是摘要内容
                speaker = raw_summary
                raw_summary = ""
            else:
                speaker = extract_speaker_detail_byline(link)
                time.sleep(2)  # SEC.gov 有较严格的速率限制,放慢请求
        # strategy == "none": speaker留空,前端用 default_org 兜底展示

        if raw_summary and len(raw_summary) < MIN_REAL_SUMMARY_LEN:
            raw_summary = ""  # 太短,大概率不是真实摘要,按规则留空不拼凑
        summary_zh = translate_full(raw_summary) if raw_summary else ""

        items.append({
            "title": display_title,
            "speaker": speaker,
            "org": source.get("default_org", ""),
            "date": pub_dt.strftime("%Y-%m-%d") if pub_dt else "",
            "summary_zh": summary_zh,
            "url": link,
            "source": source["name"],
        })

    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period-end", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    news_db = load_json(NEWS_DB_PATH, [])
    known_urls = {n["url"] for n in news_db}
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    all_new = []
    run_log = {"run_time": datetime.now(timezone.utc).isoformat(), "sources": []}

    for source in NEWS_SOURCES:
        try:
            items = process_source(source, cutoff)
            new_items = [it for it in items if it["url"] not in known_urls]
            for it in new_items:
                it["date_added"] = datetime.now(timezone.utc).isoformat()
                it["week_of"] = args.period_end
                it["id"] = re.sub(r"\W+", "", it["url"])[-16:]
                known_urls.add(it["url"])
            all_new.extend(new_items)
            run_log["sources"].append({
                "source": source["name"], "status": "ok",
                "fetched_in_window": len(items), "new": len(new_items),
            })
            print(f"[ok] {source['name']}: within_window={len(items)} new={len(new_items)}")
        except Exception as exc:
            run_log["sources"].append({"source": source["name"], "status": "error", "reason": str(exc)})
            print(f"[error] {source['name']}: {exc}")
        time.sleep(1)

    news_db.extend(all_new)
    save_json(NEWS_DB_PATH, news_db)

    logs = load_json(LOG_PATH, [])
    logs.append(run_log)
    save_json(LOG_PATH, logs)

    print(f"\n共新增 {len(all_new)} 条新闻(近{LOOKBACK_DAYS}天窗口), 新闻库总数 {len(news_db)}")


if __name__ == "__main__":
    main()
