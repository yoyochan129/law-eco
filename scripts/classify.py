# -*- coding: utf-8 -*-
"""
文章主题分类(启发式关键词打分 + 人工校对样本覆盖)。
规则:
- 依据 title + abstract 的实质内容(不依据来源机构)
- 每篇最多 2 个 topics,选分数最高的一个作为 primary_topic
- 无法判断时归入"其他"
- OVERRIDES 中的题目为人工核对过的分类样本,优先级最高(精确标题匹配)
"""
import re

TOPICS = [
    "公司治理", "公司并购", "破产法", "证券法", "金融监管", "竞争法和反垄断法",
    "司法和执法", "合同", "金融市场", "金融科技", "支付", "AI",
    "央行和货币政策", "银行", "稳定币", "非银机构", "私募信贷", "绿色金融",
    "行为研究", "实验", "实证研究", "DID", "因果推断", "机器学习", "其他",
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
        "corporate disclosure", "sustainability reporting", "climate goal",
        "corporate climate", "joint venture", "pay gap",
    ],
    "公司并购": [
        "merger", "acquisition", "takeover", "tender offer", "m&a",
        "acquirer", "target firm", "buyout", "merger agreement",
        "acquisition activity", "deal activity", "merger control",
    ],
    "破产法": [
        "bankruptcy", "insolvency", "chapter 11", "restructuring",
        "financial distress", "reorganization", "debtor", "creditor rights",
        "liquidation", "workout", "distressed",
    ],
    "证券法": [
        "securities law", "securities regulation", "sec rule",
        "sec commissioner", "sec enforcement", "insider trading",
        "proxy rules", "tender offer rules", "prospectus", "broker-dealer",
        "registration statement", "public offering", "securities fraud",
        "rule 10b-5", "blue sky law", "regulation d", "exempt offering",
        "securities act", "exchange act", "ipo regulation", "underwriter",
        "securities exchange commission",
    ],
    "金融监管": [
        "regulation", "regulatory", "supervision", "supervisory",
        "prudential", "basel", "capital requirement", "compliance",
        "systemic risk", "macroprudential", "disclosure rule",
        "rulemaking", "reporting rule", "comment letter",
        "provisioning rule", "financial governance",
    ],
    "竞争法和反垄断法": [
        "antitrust", "competition law", "merger review", "monopoly",
        "cartel", "market power", "merger control", "anticompetitive",
        "predatory pricing",
    ],
    "司法和执法": [
        "litigation", "court decision", "judicial", "enforcement action",
        "lawsuit", "class action", "settlement", "prosecution", "prosecutor",
        "judge", "legal liability", "doj",
        "delaware supreme court", "delaware chancery", "court of chancery",
        "supreme court", "constitutional court", "discoverable",
        "breach of fiduciary duty", "sentencing", "sentences", "plea",
        "leniency", "trust in journalists", "rule of law",
        "legal uncertainty", "highest court", "racial disparities",
        "trademark confusion", "crime, punishment", "criminal", "verdict",
    ],
    "合同": [
        "contract", "contractual", "covenant", "franchising",
        "franchise agreement", "contract terms", "contract remedies",
        "contract law", "non-disclosure", "search efforts",
        "markets and hierarchies", "transaction cost",
    ],
    "金融市场": [
        "stock market", "asset pricing", "trading", "market liquidity",
        "market microstructure", "volatility", "equity market",
        "bond market", "capital markets", "stock return", "ipo",
        "securities market", "eurobond", "sovereign debt", "fiscal risk",
        "financial system",
    ],
    "金融科技": [
        "fintech", "digital payment", "digital lending", "online lending",
        "peer-to-peer lending", "robo-advisor", "mobile banking",
        "crowdfunding", "financial technology", "technological transformation",
    ],
    "支付": [
        "payment system", "cross-border payment", "payment infrastructure",
        "instant payment", "remittance", "card payment", "payment network",
    ],
    "AI": [
        "artificial intelligence", "large language model", "generative ai",
        "ai governance", "algorithmic decision", "chatgpt", "genai",
        "ai regulation", "ai adoption", "advanced driver-assistance",
        "ai investment",
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
        "contingent convertible", "coco bond",
    ],
    "稳定币": [
        "stablecoin", "digital currency", "cbdc", "central bank digital currency",
        "tokenized deposit",
    ],
    "非银机构": [
        "non-bank", "nonbank", "shadow banking", "money market fund",
        "hedge fund", "pension fund", "insurance company", "asset manager",
        "nbfi", "mutual fund",
    ],
    "私募信贷": [
        "private credit", "private debt", "direct lending", "leveraged loan",
        "private equity financing", "private equity",
    ],
    "绿色金融": [
        "green bond", "climate finance", "sustainable finance",
        "esg investing", "carbon", "climate risk", "renewable energy",
        "climate transition", "sustainable investing", "emission",
        "flaring and venting", "environmental cost",
    ],
    "行为研究": [
        "behavioral", "cognitive bias", "nudge", "psychology",
        "bounded rationality", "heuristics", "beliefs that predict",
        "sentiment",
    ],
    "实验": [
        "experiment", "randomized", "randomized controlled trial", " rct ",
        "field experiment", "lab experiment", "experimental test",
        "randomized experiment",
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
        "quasi-experiment", "causal forest",
    ],
    "机器学习": [
        "machine learning", "deep learning", "neural network",
        "natural language processing", "text-as-data", "random forest",
        "text analysis", "large language model",
    ],
}

# 人工核对过的分类样本:精确标题匹配,优先级高于关键词打分
OVERRIDES = {
    "Emission Impossible: Corporate Climate Goals Moving from Adoption to Execution": ["公司治理", "绿色金融"],
    "The Half-Trillion-Dollar Joint Venture Blind Spot": ["公司治理"],
    "Him Too? The Corporate Consequences of Epstein Connections": ["公司治理"],
    "Who is Afraid of Eurobonds? -- by Francesco Bianchi, Qingyuan Fang, Leonardo Melosi, Anna Rogantini Picco": ["金融市场", "央行和货币政策"],
    "The Environmental Costs of Sanctions: Flaring and Venting in Venezuela -- by Michele Fioretti, Kavanaugh FitzPatrick, Alessandro Iaria": ["司法和执法"],
    "Counterproductive Sustainable Investing: The Impact Elasticity of Brown and Green Firms -- by Samuel M. Hartzmark, Kelly Shue": ["绿色金融"],
    "Beliefs That Predict Returns and Beliefs That Attract Flows: Policy Insights and Sentiment Catering in Mutual Funds -- by Zhenyu Gao, Wei Xiong, Jian Yuan": ["非银机构"],
    "Effects of Lottery Incentives for Influenza Vaccination: Evidence from a Large-Scale Randomized Trial and Causal Forest Analysis -- by Kelsey Moran, Gail Rosenbaum, Amir Goren, Michelle Meyer, Christopher F. Chabris, Joseph J. Doyle Jr.": ["机器学习"],
    "The AI investment race": ["AI"],
    "Post-GFC rewiring of the global financial system": ["金融市场"],
    "Money as a coordination device: some historical lessons": ["区块链"],
    "Fiscal threats in a changing global financial system": ["财政和主权债", "金融市场"],
    "Strengthening financial governance and cooperation amid rapid technological transformation": ["金融科技", "金融监管"],
    "Cross-border payments - a catalyst for global integration and growth": ["支付"],
    "Facebook Decision Enables IRS to Seek - CWI Enforcement Against Meta": ["竞争法和反垄断法"],
    "Mobility-Restricting Covenants in Business Contracts: The Case of Franchising": ["合同"],
    "Limits of Contingent Convertible Bonds: Evidence from the Credit Suisse Collapse": ["银行"],
    "Prosecutor Transparency Project: Racial Disparities Study (Washtenaw County, Michigan)": ["司法和执法"],
    "Remedies for Non-Disclosure in Asset Sales: Voidance vs. Damages": ["合同"],
    "Private Equity and Pay Gaps Inside the Firm": ["公司治理", "非银机构"],
    "Learning to Navigate a New Financial Technology": ["金融科技"],
    "Can Disclaimers of Affiliation Dispel Trademark Confusion? Evidence From Two Randomized Experiments": ["司法和执法", "实验"],
    "Crime, Punishment, and Expectations": ["司法和执法"],
    "Is the German Constitutional Court Partisan?": ["司法和执法"],
    "Differentiation through Legal Uncertainty": ["司法和执法"],
    "Charging Leniency and Federal Sentences": ["司法和执法"],
    "Color Helps Consumers Notice and Understand Contract Terms": ["合同"],
    "A (Plea) Offer You Can Refuse": ["司法和执法"],
    "The Reasons Highest Courts Give: England, France, Germany: 1880–89 and 2007–16": ["司法和执法"],
    "Contract Remedies and Search Efforts": ["合同"],
    "The Impact of the Dodd-Frank Act on Acquisition Activity": ["公司并购"],
    "Growing Awareness to Reduce Labor Abuse: An Experimental Test of a Migrant Domestic Workers’ Rights Awareness Campaign": ["实验"],
    "The Rule of Law Predicts Trust in Journalists": ["司法和执法"],
    "AI at the Wheel: The Effectiveness of Advanced Driver-Assistance Systems": ["AI"],
    "Beyond markets and hierarchies: Williamson's legacy and the frontiers of institutional analysis": ["合同"],
    "Tradition or tragedy: Arranged marriages and domestic violence": ["实证研究"],
    "Financial innovation and local governments investment": ["实证研究"],
}

# OVERRIDES 中出现、但不在 TOPICS 标准列表里的标签(用户样本中出现的新分类)
_EXTRA_TOPICS_FROM_OVERRIDES = ["区块链", "财政和主权债"]
for _t in _EXTRA_TOPICS_FROM_OVERRIDES:
    if _t not in TOPICS:
        TOPICS.insert(TOPICS.index("其他"), _t)


def classify_article(title, abstract):
    if title in OVERRIDES:
        topics = OVERRIDES[title][:2]
        return {"topics": topics, "primary_topic": topics[0]}

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
