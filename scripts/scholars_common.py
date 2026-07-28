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


PUB_HEADINGS = {
    "publications", "scholarship", "selected publications",
    "selected scholarship", "articles", "journal articles",
    "selected works", "working papers",
}
STOP_HEADINGS = PUB_HEADINGS | {
    "presentations", "other publications", "book sections", "education",
    "education and experience", "media", "in the media", "teaching",
    "additional activities", "biography",
}


def extract_year(text):
    m = re.findall(r"(19|20)\d{2}", text)
    return m[-1] if m else ""  # 取最后一个年份,通常引用格式里年份在末尾


LINK_LABEL_SUFFIX = re.compile(
    r"\s*(ssrn|www|cu|pdf|doi|link)+\s*$", re.IGNORECASE
)


def clean_citation_text(text):
    """去掉页面上引用文字末尾常见的相邻链接标签(如'... (2019). ssrn cu'
    里的'ssrn cu'其实是两个独立的下载链接文字,被get_text()拼接了进来)"""
    prev = None
    while prev != text:
        prev = text
        text = LINK_LABEL_SUFFIX.sub("", text).rstrip()
    return text


def scrape_faculty_page_citations(url, scholar_name, limit=10):
    """针对个人/学校教师主页的文献抓取(比 snapshot_faculty_page 更精确):
    策略1: 收集页面里所有指向SSRN论文的链接(链接文字通常就是完整引用,
           这个信号误报率极低,不会像抓全部长链接那样把导航栏/课程介绍抓进来)
    策略2: 定位"Publications"/"Scholarship"等标题元素,只提取该标题到下一个
           同级标题之间的内容块,且要求文本包含年份数字,进一步降低误判
    两种信号取并集去重,仍然抓不到时如实返回空列表,不做进一步猜测。
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return []

    citations = []
    seen_texts = set()
    generic_texts = {
        "here", "link", "view", "ssrn", "read more", "paper", "download",
        "pdf", "available here", "download pdf", "view on ssrn",
    }

    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        # 只认"某一篇具体论文"的链接,排除SSRN作者页/系列页/搜索页等泛链接
        if not re.search(r"ssrn\.com/(sol3/)?(papers|abstract)", href) and "abstract_id=" not in href:
            continue
        text = a.get_text(strip=True)
        if len(text) < 20 or text.lower() in generic_texts or text in seen_texts:
            continue
        seen_texts.add(text)
        citations.append({
            "title": clean_citation_text(text[:300]),
            "authors": scholar_name,
            "date": extract_year(text),
            "abstract": "",
            "url": a["href"],
        })

    # 标题文字可能在多处出现(如页面顶部tab导航复用了"Publications"字样),
    # 逐个尝试直到找到真的带年份的文献列表,而不是只信第一个命中
    heading_tags = soup.find_all(["h1", "h2", "h3", "h4", "h5", "strong", "b"])
    for h in heading_tags:
        if h.get_text(strip=True).lower() not in PUB_HEADINGS:
            continue
        block_citations = []
        for sib in h.find_all_next():
            sib_text = sib.get_text(strip=True).lower() if sib.name in ("h1", "h2", "h3", "h4", "h5", "strong", "b") else ""
            if sib.name in ("h1", "h2", "h3") or (sib_text and sib_text in STOP_HEADINGS and sib_text not in PUB_HEADINGS):
                break
            if sib.name in ("li", "p"):
                text = sib.get_text(" ", strip=True)
                if len(text) < 25 or not re.search(r"(19|20)\d{2}", text) or text in seen_texts:
                    continue
                link = sib.find("a", href=True)
                block_citations.append({
                    "title": clean_citation_text(text[:300]),
                    "authors": scholar_name,
                    "date": extract_year(text),
                    "abstract": "",
                    "url": link["href"] if link else url,
                })
            if len(block_citations) >= limit:
                break
        if block_citations:
            for c in block_citations:
                if c["title"] not in seen_texts:
                    seen_texts.add(c["title"])
                    citations.append(c)
            break  # 找到真正有效的文献列表后就不再继续找其他同名标题

    return citations[:limit]
