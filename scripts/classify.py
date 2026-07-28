# -*- coding: utf-8 -*-
"""
文章主题分类(启发式关键词打分)。
规则:
- 依据 title + abstract 的实质内容(不依据来源机构)
- 每篇最多 2 个 topics,选分数最高的一个作为 primary_topic
- 无法判断时归入"其他"
"""
import re

TOPICS = [
    "公司治理", "破产法", "金融监管", "竞争法和反垄断法", "司法和执法",
    "金融市场", "金融科技", "AI", "央行和货币政策", "银行", "稳定币",
    "非银机构", "私募信贷", "绿色金融", "行为研究", "实证研究", "DID",
    "因果推断", "机器学习", "其他",
]

# 关键词均为小写,匹配时对 title+abstract 做小写子串检索
KEYWORDS = {
    "公司治理": [
        "corporate governance", "board of directors", "board diversity",
        "board refreshment", "board oversight", "executive compensation",
        "ceo pay", "shareholder", "stakeholder", "proxy voting",
        "shareholder activism", "esg disclosure", "ownership structure",
        "dual-class", "dual class shares", "say-on-pay", "director liability",
        "insider ownership", "corporate purpose", "annual meeting",
        "corporate disclosure", "sustainability reporting",
    ],
    "破产法": [
        "bankruptcy", "insolvency", "chapter 11", "restructuring",
        "financial distress", "reorganization", "debtor", "creditor rights",
        "liquidation", "workout", "distressed",
    ],
    "金融监管": [
        "regulation", "regulatory", "supervision", "supervisory",
        "prudential", "basel", "capital requirement", "compliance",
        "systemic risk", "macroprudential", "disclosure rule", "sec rule",
        "rulemaking", "reporting rule", "comment letter", "sec commissioner",
        "securities law", "provisioning rule",
    ],
    "竞争法和反垄断法": [
        "antitrust", "competition law", "merger review", "monopoly",
        "cartel", "market power", "merger control", "anticompetitive",
        "predatory pricing",
    ],
    "司法和执法": [
        "litigation", "court decision", "judicial", "enforcement action",
        "lawsuit", "class action", "settlement", "prosecution", "judge",
        "legal liability", "sec enforcement", "doj", "delaware supreme court",
        "delaware chancery", "court of chancery", "supreme court",
        "discoverable", "breach of fiduciary duty",
    ],
    "金融市场": [
        "stock market", "asset pricing", "trading", "market liquidity",
        "market microstructure", "volatility", "equity market",
        "bond market", "capital markets", "stock return", "ipo",
        "securities market",
    ],
    "金融科技": [
        "fintech", "digital payment", "digital lending", "online lending",
        "peer-to-peer lending", "robo-advisor", "mobile banking",
        "crowdfunding",
    ],
    "AI": [
        "artificial intelligence", "large language model", "generative ai",
        "ai governance", "algorithmic decision", "chatgpt", "genai",
        "ai regulation", "ai adoption",
    ],
    "央行和货币政策": [
        "monetary policy", "central bank", "interest rate policy",
        "inflation targeting", "quantitative easing", "federal reserve",
        "policy rate", "exchange rate policy",
    ],
    "银行": [
        "bank lending", "bank capital", "bank failure", "bank run",
        "deposit insurance", "commercial bank", "bank regulation",
        "banking sector", "bank holding company", "bail-in", "deposit",
        "bank acquisition", "consumer credit", "credit supply",
        "digitalisation of banking", "cyber stress test", "credit line",
    ],
    "稳定币": [
        "stablecoin", "digital currency", "cbdc", "central bank digital currency",
        "tokenized deposit",
    ],
    "非银机构": [
        "non-bank", "nonbank", "shadow banking", "money market fund",
        "hedge fund", "pension fund", "insurance company", "asset manager",
        "nbfi",
    ],
    "私募信贷": [
        "private credit", "private debt", "direct lending", "leveraged loan",
        "private equity financing",
    ],
    "绿色金融": [
        "green bond", "climate finance", "sustainable finance",
        "esg investing", "carbon", "climate risk", "renewable energy",
        "climate transition",
    ],
    "行为研究": [
        "behavioral", "cognitive bias", "nudge", "psychology",
        "bounded rationality", "heuristics",
    ],
    "实证研究": [
        "empirical evidence", "empirical analysis", "panel data",
        "survey evidence", "cross-sectional",
    ],
    "DID": [
        "difference-in-differences", "diff-in-diff", "staggered adoption",
        "event study design",
    ],
    "因果推断": [
        "causal inference", "instrumental variable", "regression discontinuity",
        "causal effect", "identification strategy", "natural experiment",
        "quasi-experiment",
    ],
    "机器学习": [
        "machine learning", "deep learning", "neural network",
        "natural language processing", "text-as-data", "random forest",
        "text analysis", "large language model",
    ],
}


def classify_article(title, abstract):
    text = f"{title} {abstract}".lower()
    scores = {}
    for topic, kws in KEYWORDS.items():
        score = 0
        for kw in kws:
            if kw in text:
                # 标题命中权重更高
                score += 3 if kw in title.lower() else 1
        if score > 0:
            scores[topic] = score

    if not scores:
        return {"topics": ["其他"], "primary_topic": "其他"}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    topics = [t for t, _ in ranked[:2]]
    primary = ranked[0][0]
    return {"topics": topics, "primary_topic": primary}
