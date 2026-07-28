# -*- coding: utf-8 -*-
"""学者追踪板块的共用工具函数(来源类型判定、NBER作者页解析等)。"""
import re

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
HEADERS = {"User-Agent": UA}
TIMEOUT = 15


def classify_source(url):
    if not url:
        return "none"
    if "nber.org/people" in url:
        return "nber_people_direct"
    if "nber.org/papers" in url:
        return "nber_paper_link"
    if url.lower().endswith(".pdf"):
        return "pdf"
    return "generic_page"


def surname_matches(link_text, full_name):
    """粗略判断NBER论文页里的作者链接文字是否对应目标学者(按姓氏匹配)"""
    surname = full_name.strip().split()[-1].lower().strip(".,")
    return surname in link_text.lower()


def resolve_nber_uid_from_people_page(people_url):
    """访问 nber.org/people/{slug} 页面,提取内嵌JS配置里的uid"""
    try:
        resp = requests.get(people_url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        m = re.search(r"uid/(\d+)", resp.text)
        return m.group(1) if m else None
    except Exception:
        return None


def resolve_nber_people_url_from_paper(paper_url, scholar_name):
    """访问 nber.org/papers/wXXXXX 页面,在作者链接列表里找到与目标学者姓氏匹配的
    /people/ 链接(排除页面底部NBER理事会等固定出现的人名)"""
    try:
        resp = requests.get(paper_url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select('a[href*="/people/"]'):
            text = a.get_text(strip=True)
            if surname_matches(text, scholar_name):
                href = a["href"]
                return "https://www.nber.org" + href if href.startswith("/") else href
    except Exception:
        return None
    return None


def fetch_nber_author_works(uid, limit=10):
    """调用NBER内部的用户作品列表API,返回该作者的最新工作论文/文章"""
    api_url = (
        f"https://www.nber.org/api/v1/user_generic_listing/uid/{uid}/"
        "contentType,contentType,contentType,contentType,contentType,contentType,"
        "contentType,contentType/working_paper,book,chapter,dataset,interview,"
        "lecture,center_paper,article/search"
    )
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []

    items = []
    for r in data.get("results", []):
        if r.get("type") not in ("working_paper", "article"):
            continue
        authors = [
            BeautifulSoup(a, "html.parser").get_text(strip=True)
            for a in r.get("authors", [])
        ]
        url = r.get("url", "")
        full_url = "https://www.nber.org" + url if url.startswith("/") else url
        items.append({
            "title": r.get("title", ""),
            "authors": ", ".join(authors),
            "date": r.get("displaydate", ""),
            "abstract": r.get("abstract", ""),
            "url": full_url,
        })
    return items[:limit]


def snapshot_faculty_page(url, min_text_len=25, max_links=40):
    """通用教师主页"快照"抓取:粗略识别页面中可能是文献/著作的链接
    (启发式:链接文字较长、非导航栏常见词),供后续按周做diff比对使用。
    不保证能准确抓到"发表日期"和"摘要"(个人主页格式差异太大),仅作为
    "监测是否有新内容出现"的基线。
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return []

    nav_words = {
        "home", "about", "contact", "faculty", "admissions", "academics",
        "search", "menu", "login", "directory", "news", "events", "privacy",
        "accessibility", "sitemap", "facebook", "twitter", "linkedin",
        "instagram", "youtube",
    }
    items = []
    seen_urls = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if len(text) < min_text_len:
            continue
        if text.lower() in nav_words:
            continue
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        full_url = href if href.startswith("http") else requests.compat.urljoin(url, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        year_match = re.search(r"(19|20)\d{2}", text)
        items.append({
            "title": text,
            "authors": "",
            "date": year_match.group(0) if year_match else "",
            "abstract": "",
            "url": full_url,
        })
        if len(items) >= max_links:
            break
    return items
