# -*- coding: utf-8 -*-
"""
一次性维护脚本:
1. 删除非论文条目(Print Edition / Editorial Board / Front Matter 等)与非英文文献
2. 按最新 classify.py 规则重新分类全部文章
3. 为标题与摘要补充中文翻译(title_zh / abstract_zh),已翻译过的跳过
"""
import json
import os
import sys
import time

import re

from deep_translator import GoogleTranslator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import classify_article

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "articles.json")

JUNK_TITLES = {
    "print edition", "editorial board", "front matter", "issue information",
    "table of contents", "masthead", "back matter", "cover",
}

translator = GoogleTranslator(source="en", target="zh-CN")


def is_junk(title):
    return title.strip().lower() in JUNK_TITLES


NON_ENGLISH_CHARS = re.compile(
    r"[äöüßÄÖÜàâçéèêëîïôùûÿñáéíóúüñ¿¡ãõâêôàèìòùæœ]"
)


def is_non_english(title):
    """基于特征字符的启发式判断(比 langdetect 对短标题更可靠,避免误杀英文标题)"""
    return bool(NON_ENGLISH_CHARS.search(title))


def translate_text(text):
    if not text:
        return ""
    try:
        # Google免费接口单次请求长度上限约5000字符,超长先截断
        result = translator.translate(text[:4500])
        return result or ""
    except Exception as exc:
        print(f"[warn] 翻译失败: {exc}")
        return ""


def main():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    before = len(db)
    kept = []
    removed_junk = 0
    removed_non_en = 0
    for a in db:
        if is_junk(a["title"]):
            removed_junk += 1
            continue
        if is_non_english(a["title"]):
            removed_non_en += 1
            continue
        kept.append(a)

    print(f"清理前 {before} 篇, 删除非论文条目 {removed_junk} 篇, 删除非英文文献 {removed_non_en} 篇")

    for a in kept:
        cls = classify_article(a["title"], a.get("abstract", ""))
        a["topics"] = cls["topics"]
        a["primary_topic"] = cls["primary_topic"]

    translated_count = 0
    for i, a in enumerate(kept):
        if not a.get("title_zh"):
            a["title_zh"] = translate_text(a["title"])
            time.sleep(0.3)
            translated_count += 1
        if a.get("abstract") and not a.get("abstract_zh"):
            a["abstract_zh"] = translate_text(a["abstract"])
            time.sleep(0.3)
        if (i + 1) % 20 == 0:
            print(f"  已处理 {i + 1}/{len(kept)}")

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    print(f"完成。剩余 {len(kept)} 篇,新增翻译 {translated_count} 篇标题。")


if __name__ == "__main__":
    main()
