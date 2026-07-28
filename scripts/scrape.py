# -*- coding: utf-8 -*-
"""
抓取脚本:遍历 sources_config.SOURCES 中 status=active 的来源,
拉取最新文章,与 database/articles.json 中已有 URL 去重后,
将新文章写入 database/new_articles_raw.json (待分类)。

用法: python3 scrape.py
"""
import json
import os
import re
import sys
import time
import hashlib
from datetime import datetime, timezone

import requests
import feedparser
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources_config import SOURCES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "articles.json")
STATE_PATH = os.path.join(BASE_DIR, "database", "state.json")
RAW_OUT_PATH = os.path.join(BASE_DIR, "database", "new_articles_raw.json")
LOG_PATH = os.path.join(BASE_DIR, "logs", "scrape_log.json")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

HEADERS = {"User-Agent": UA}
TIMEOUT = 15

JUNK_TITLES = {
    "print edition", "editorial board", "front matter", "issue information",
    "table of contents", "masthead", "back matter", "cover",
}


def is_junk_title(title):
    return title.strip().lower() in JUNK_TITLES


NON_ENGLISH_CHARS = re.compile(
    r"[äöüßÄÖÜàâçéèêëîïôùûÿñáéíóúüñ¿¡ãõâêôàèìòùæœ]"
)


def is_non_english_title(title):
    """基于特征字符的启发式判断(比 langdetect 对短标题更可靠,避免误杀英文标题)"""
    return bool(NON_ENGLISH_CHARS.search(title))


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def url_hash(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def clean_html(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def fetch_soup(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None


def get_og_description(soup):
    tag = soup.find("meta", property="og:description")
    if tag and tag.get("content"):
        return clean_html(tag["content"])
    return ""


def fix_glued_names(text):
    """修复芝加哥大学期刊RSS中作者/机构名无分隔符粘连的问题
    例如 'Roy BaharadHebrew University of Jerusalem' -> 'Roy Baharad, Hebrew University of Jerusalem'
    """
    if not text:
        return text
    return re.sub(r"([a-z])([A-Z])", r"\1, \2", text)


def extract_author_from_content(html):
    """尝试从正文HTML中提取作者/机构信息(启发式,提取失败返回空字符串)"""
    if not html:
        return ""
    text = clean_html(html)[:400]
    patterns = [
        r"Posted by ([^,]+),\s*([^,\.]+?),\s*on",
        r"^[Bb]y\s+([A-Z][^,\.]{2,60})(?:,\s*([^\.]{2,80}))?",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            groups = [g for g in m.groups() if g]
            return " / ".join(g.strip() for g in groups)
    return ""


def parse_rss_generic(source):
    d = feedparser.parse(source["feed_url"])
    items = []
    for e in d.entries:
        title = clean_html(e.get("title", "")).strip()
        link = e.get("link", "").strip()
        if not title or not link:
            continue
        abstract = clean_html(
            e.get("dcterms_abstract")
            or (e.get("content", [{}])[0].get("value") if e.get("content") else None)
            or e.get("summary", "")
        )
        author = e.get("author", "") or ""
        if not author:
            author = extract_author_from_content(
                (e.get("content", [{}])[0].get("value") if e.get("content") else None)
                or e.get("summary", "")
            )
        elif source.get("fix_author_glue") and "," not in author:
            author = fix_glued_names(author)
        keywords = [t.get("term") for t in (e.get("tags") or []) if t.get("term")]
        pub_date = e.get("published", "") or e.get("updated", "")
        items.append({
            "title": title,
            "authors": author,
            "abstract": abstract[:1200],
            "keywords": keywords,
            "url": link,
            "source": source["name"],
            "publish_date": pub_date,
        })
    return items


def parse_rss_filtered(source):
    items = parse_rss_generic({**source, "feed_url": source["feed_url"]})
    flt = source.get("link_filter")
    if flt:
        items = [it for it in items if flt in it["url"]]
    return items


def parse_html_safe(source):
    """SAFE working papers: 首页发布列表 (静态HTML最新几条)"""
    items = []
    try:
        resp = requests.get(source["page_url"], headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/publications/pub-details-startseite/publicationname/" in href:
                title = a.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                full_url = href if href.startswith("http") else "https://safe-frankfurt.de" + href
                items.append({
                    "title": title,
                    "authors": "",
                    "abstract": "",
                    "keywords": [],
                    "url": full_url,
                    "source": source["name"],
                    "publish_date": "",
                })
    except Exception as exc:
        print(f"[warn] SAFE fetch failed: {exc}")
    # 去重(同一篇文章在页面中可能重复出现多次)
    seen = set()
    uniq = []
    for it in items:
        if it["url"] not in seen:
            seen.add(it["url"])
            uniq.append(it)
    return uniq


def parse_html_yalejreg(source):
    """Yale Journal on Regulation: 首页文章列表 (静态HTML)"""
    items = []
    try:
        resp = requests.get(source["page_url"], headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # 仅保留形如 /print/<文章slug>/ 的详情页链接,过滤掉分类/期号等导航链接
            m = re.match(r"^https?://www\.yalejreg\.com/print/[a-z0-9\-]{5,}/?$", href)
            if not m:
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            items.append({
                "title": title,
                "authors": "",
                "abstract": "",
                "keywords": [],
                "url": href,
                "source": source["name"],
                "publish_date": "",
            })
    except Exception as exc:
        print(f"[warn] Yale JReg fetch failed: {exc}")
    seen = set()
    uniq = []
    for it in items:
        if it["url"] not in seen:
            seen.add(it["url"])
            uniq.append(it)
    return uniq


PARSERS = {
    "rss": parse_rss_generic,
    "rss_filtered": parse_rss_filtered,
    "html_safe": parse_html_safe,
    "html_yalejreg": parse_html_yalejreg,
}


# ---------------- 详情页补全(仅对新文章调用,避免重复请求) ----------------

def enrich_bis_wp(item):
    """BIS Working Paper 详情页: og:description 作摘要, a.authorlnk 作作者"""
    soup = fetch_soup(item["url"])
    if not soup:
        return item
    abstract = get_og_description(soup)
    if abstract:
        item["abstract"] = abstract
    authors = [a.get_text(strip=True) for a in soup.select("a.authorlnk")]
    if authors:
        item["authors"] = ", ".join(dict.fromkeys(authors))  # 去重保序
    return item


def enrich_safe(item):
    """SAFE 详情页: .tx-mmpublications 结构中提取作者/关键词/摘要"""
    soup = fetch_soup(item["url"])
    if not soup:
        return item
    container = soup.select_one(".tx-mmpublications")
    if not container:
        return item

    for box in container.select(".item"):
        h4 = box.find("h4")
        if not h4:
            continue
        label = h4.get_text(strip=True).lower()
        if label == "authors":
            names = [a.get_text(strip=True).rstrip(",") for a in box.find_all("a")]
            if names:
                item["authors"] = ", ".join(names)
        elif label == "keywords":
            text = box.get_text(" ", strip=True).replace("Keywords", "", 1).strip()
            if text:
                item["keywords"] = [k.strip() for k in text.split(",") if k.strip()]

    abstract_p = container.select_one(".main-content p")
    if abstract_p:
        text = abstract_p.get_text(" ", strip=True)
        if len(text) > 40:
            item["abstract"] = text
    return item


def enrich_yalejreg(item):
    """Yale Journal on Regulation 详情页: og:description 作摘要, .meta-author 作作者"""
    soup = fetch_soup(item["url"])
    if not soup:
        return item
    abstract = get_og_description(soup)
    if abstract:
        item["abstract"] = abstract
    author_el = soup.select_one(".meta-author")
    if author_el:
        item["authors"] = author_el.get_text(strip=True)
    return item


ENRICHERS = {
    "bis_wp": enrich_bis_wp,
    "safe_wp": enrich_safe,
    "yale_jreg": enrich_yalejreg,
}


def main():
    db = load_json(DB_PATH, [])
    known_urls = {a["url"] for a in db}

    all_new = []
    run_log = {"run_time": datetime.now(timezone.utc).isoformat(), "sources": []}

    for source in SOURCES:
        if source.get("status") != "active":
            run_log["sources"].append({
                "source": source["name"], "status": "pending",
                "reason": source.get("reason", ""),
            })
            continue

        parser = PARSERS.get(source["type"])
        if not parser:
            run_log["sources"].append({
                "source": source["name"], "status": "error",
                "reason": f"未知类型 {source['type']}",
            })
            continue

        try:
            items = parser(source)
            items = [it for it in items if not is_junk_title(it["title"])]
            items = [it for it in items if not is_non_english_title(it["title"])]
            new_items = [it for it in items if it["url"] not in known_urls]

            enricher = ENRICHERS.get(source["id"])
            if enricher:
                for it in new_items:
                    try:
                        enricher(it)
                    except Exception as exc:
                        print(f"[warn] enrich failed for {it['url']}: {exc}")
                    time.sleep(1)

            for it in new_items:
                it["id"] = url_hash(it["url"])
                known_urls.add(it["url"])
            all_new.extend(new_items)
            run_log["sources"].append({
                "source": source["name"], "status": "ok",
                "fetched": len(items), "new": len(new_items),
            })
            print(f"[ok] {source['name']}: fetched={len(items)} new={len(new_items)}")
        except Exception as exc:
            run_log["sources"].append({
                "source": source["name"], "status": "error", "reason": str(exc),
            })
            print(f"[error] {source['name']}: {exc}")

        time.sleep(1)  # 礼貌性请求间隔

    save_json(RAW_OUT_PATH, all_new)

    logs = load_json(LOG_PATH, [])
    logs.append(run_log)
    save_json(LOG_PATH, logs)

    print(f"\n共发现 {len(all_new)} 篇新文章 (未分类), 已写入 {RAW_OUT_PATH}")


if __name__ == "__main__":
    main()
