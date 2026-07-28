# -*- coding: utf-8 -*-
"""对 database/articles.json 中已有文章按最新 classify.py 规则重新打标签。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import classify_article

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "articles.json")

with open(DB_PATH, "r", encoding="utf-8") as f:
    db = json.load(f)

for a in db:
    cls = classify_article(a["title"], a.get("abstract", ""))
    a["topics"] = cls["topics"]
    a["primary_topic"] = cls["primary_topic"]

with open(DB_PATH, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"已重新分类 {len(db)} 篇文章")
