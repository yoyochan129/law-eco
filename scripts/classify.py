# -*- coding: utf-8 -*-
"""
文章主题分类(启发式关键词打分 + 优先级规则 + 人工核对样本覆盖)。

基础规则:
- 依据 title + abstract 的实质内容(不依据来源机构)
- 每篇最多 3 个 topics,选分数最高的一个作为 primary_topic
- 无法判断时归入"其他"
- OVERRIDES 中的题目为人工核对过的分类样本,优先级最高(精确标题匹配)

在关键词打分之上,叠加以下人工制定的优先级/互斥规则(按顺序生效):
1. 出现 DeFi、代币化、加密货币等信号词 -> 强制拉高"区块链"权重,确保被选中
2. "bank"类词反复出现(词频>=3,不含"bankruptcy") -> 强化"银行",同时抑制
   "央行和货币政策"/"稳定币"/"信贷市场"与其同时出现,除非这三者本身证据也很强
3. "证券法"与"司法和执法"同时命中时,优先"证券法"(证券诉讼/证券执法
   一律算证券法,不再计入司法和执法)
4. "司法和执法"与除方法论标签(行为研究/实验/实证研究/DID/因果推断/机器学习)
   以外的其他主题互斥:一旦命中"司法和执法",只保留它与命中的方法论标签
5. 如果最终标签只剩"实证研究"一个,自动归入"其他"(单独的"实证研究"信息量太低)
"""
import re

METHODOLOGY_TOPICS = {"行为研究", "实验", "实证研究", "DID", "因果推断", "机器学习"}

TOPICS = [
    "公司治理", "公司并购", "破产法", "证券法", "金融监管", "竞争法和反垄断法",
    "司法和执法", "合同", "信贷市场", "债券市场", "衍生品市场", "金融科技",
    "支付", "AI", "央行和货币政策", "银行", "稳定币", "非银机构", "私募信贷",
    "绿色金融", "行为研究", "实验", "实证研究", "DID", "因果推断", "机器学习",
    "其他",
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
        "securities litigation", "securities class action",
        "rule 10b-5", "blue sky law", "regulation d", "exempt offering",
        "securities act", "exchange act", "ipo regulation", "underwriter",
        "securities exchange commission", "market manipulation",
    ],
    # "尽量避免分类到金融监管,除非直接涉及监管、合规":去掉裸词"regulation"/
    # "regulatory"/"supervision",只保留明确指向监管/合规本身的复合词
    "金融监管": [
        "financial regulation", "regulatory compliance", "regulatory reform",
        "prudential regulation", "macroprudential", "capital requirement",
        "basel", "systemic risk regulation", "disclosure rule", "rulemaking",
        "reporting rule", "comment letter", "provisioning rule",
        "regulatory burden", "compliance cost", "regulatory arbitrage",
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
    # 只有讨论合同条款/合同义务/违约责任本身才算"合同";泛泛的"transaction
    # cost"/"markets and hierarchies"等理论性词汇挪去,不再算作合同的信号
    "合同": [
        "contract terms", "contractual obligation", "breach of contract",
        "contract remedies", "contract law", "contract enforcement",
        "contract default", "default clause", "loan covenant",
        "covenant violation", "covenant", "franchising", "franchise agreement",
        "non-disclosure agreement",
    ],
    "信贷市场": [
        "credit market", "loan market", "lending market", "credit spread",
        "credit risk", "loan pricing", "credit supply", "credit access",
        "corporate loan", "syndicated loan", "credit rationing",
        "credit constraints", "loan contract", "credit line",
    ],
    "债券市场": [
        "bond market", "bond pricing", "bond yield", "bond issuance",
        "corporate bond", "government bond", "treasury bond",
        "sovereign bond", "bond fund", "yield curve", "bond spread",
        "eurobond",
    ],
    "衍生品市场": [
        "derivative", "derivatives market", "option pricing",
        "futures market", "swap market", "credit default swap",
        "hedging instrument", "forward contract", "options contract",
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
    # 不把关税/财政/外汇这类宏观经济论文划入央行和货币政策,去掉过于宽泛的
    # "exchange rate policy",只保留明确指向货币政策/央行本身的词
    "央行和货币政策": [
        "monetary policy", "central bank", "interest rate policy",
        "inflation targeting", "quantitative easing", "policy rate",
        "central bank independence", "central bank communication",
        "forward guidance",
    ],
    "银行": [
        "bank lending", "bank capital", "bank failure", "bank run",
        "deposit insurance", "commercial bank", "bank regulation",
        "banking sector", "bank holding company", "bail-in", "deposit",
        "bank acquisition", "digitalisation of banking", "cyber stress test",
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
    # 特指随机实验/调查实验/实验室实验,不含自然实验/准实验(那些归因果推断)
    "实验": [
        "randomized controlled trial", "randomized experiment",
        "field experiment", "lab experiment", "laboratory experiment",
        "survey experiment", "experimental design", "randomized trial",
        " rct ",
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

# DeFi/代币化/加密货币信号词:命中即强制拉高"区块链"权重。
# "defi"用单词边界匹配,避免命中"deficit"/"defined"等词里的"defi"子串。
CRYPTO_SIGNALS = [
    "decentralized finance", "tokeniz", "cryptocurrency",
    "crypto asset", "crypto-asset", "bitcoin", "ethereum", "crypto exchange",
    "crypto lending", "digital asset trading", "smart contract",
]
CRYPTO_SIGNAL_RE = re.compile(r"\bdefi\b")

BANK_WORD_RE = re.compile(r"\bbanks?\b|\bbanking\b")

# 人工核对过的分类样本:精确标题匹配,优先级高于关键词打分
OVERRIDES = {
    "Emission Impossible: Corporate Climate Goals Moving from Adoption to Execution": ["公司治理", "绿色金融"],
    "The Half-Trillion-Dollar Joint Venture Blind Spot": ["公司治理"],
    "Him Too? The Corporate Consequences of Epstein Connections": ["公司治理"],
    "Who is Afraid of Eurobonds? -- by Francesco Bianchi, Qingyuan Fang, Leonardo Melosi, Anna Rogantini Picco": ["债券市场", "央行和货币政策"],
    "The Environmental Costs of Sanctions: Flaring and Venting in Venezuela -- by Michele Fioretti, Kavanaugh FitzPatrick, Alessandro Iaria": ["司法和执法"],
    "Counterproductive Sustainable Investing: The Impact Elasticity of Brown and Green Firms -- by Samuel M. Hartzmark, Kelly Shue": ["绿色金融"],
    "Beliefs That Predict Returns and Beliefs That Attract Flows: Policy Insights and Sentiment Catering in Mutual Funds -- by Zhenyu Gao, Wei Xiong, Jian Yuan": ["非银机构"],
    "Effects of Lottery Incentives for Influenza Vaccination: Evidence from a Large-Scale Randomized Trial and Causal Forest Analysis -- by Kelsey Moran, Gail Rosenbaum, Amir Goren, Michelle Meyer, Christopher F. Chabris, Joseph J. Doyle Jr.": ["机器学习"],
    "The AI investment race": ["AI"],
    "Post-GFC rewiring of the global financial system": ["非银机构"],
    "Money as a coordination device: some historical lessons": ["区块链"],
    "Fiscal threats in a changing global financial system": ["财政和主权债", "债券市场"],
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
    "Tradition or tragedy: Arranged marriages and domestic violence": ["其他"],
    "Financial innovation and local governments investment": ["其他"],
}

# OVERRIDES 中出现、但不在 TOPICS 标准列表里的标签(用户样本中出现的新分类)
_EXTRA_TOPICS_FROM_OVERRIDES = ["区块链", "财政和主权债"]
for _t in _EXTRA_TOPICS_FROM_OVERRIDES:
    if _t not in TOPICS:
        TOPICS.insert(TOPICS.index("其他"), _t)

MAX_TOPICS = 3


def classify_article(title, abstract):
    if title in OVERRIDES:
        topics = OVERRIDES[title][:MAX_TOPICS]
        return {"topics": topics, "primary_topic": topics[0]}

    text = f"{title} {abstract}".lower()
    title_lower = title.lower()

    scores = {}
    for topic, kws in KEYWORDS.items():
        score = 0
        for kw in kws:
            if kw in text:
                score += 3 if kw in title_lower else 1
        if score > 0:
            scores[topic] = score

    # 规则1: DeFi/代币化/加密货币 -> 强制确保"区块链"被选中且权重领先
    if any(sig in text for sig in CRYPTO_SIGNALS) or CRYPTO_SIGNAL_RE.search(text):
        scores["区块链"] = max(scores.values(), default=0) + 10

    # 规则2: "bank"类词反复出现 -> 强化银行,抑制与央行/稳定币/信贷市场同时出现
    # (bankruptcy不计入,用词边界正则避免"bankruptcy"里的"bank"子串误计)
    # 注意:必须先有明确的"银行"关键词命中才叠加此规则,否则作者所属机构名称
    # 里恰好带"Bank"(如"Norges Bank Investment Management"这类机构署名)
    # 会被误判成"文章是关于银行的"
    bank_mentions = len(BANK_WORD_RE.findall(text))
    if bank_mentions >= 3 and scores.get("银行", 0) > 0:
        scores["银行"] += 5
        for suppressed in ("央行和货币政策", "稳定币", "信贷市场"):
            if scores.get(suppressed, 0) < 4:
                scores.pop(suppressed, None)

    # 规则3: 证券诉讼/证券执法一律算证券法,不与司法和执法并存
    if scores.get("证券法", 0) > 0 and scores.get("司法和执法", 0) > 0:
        scores.pop("司法和执法", None)

    if not scores:
        return {"topics": ["其他"], "primary_topic": "其他"}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    topics = [t for t, _ in ranked]

    # 规则4: 司法和执法与非方法论主题互斥(方法论标签除外)
    if "司法和执法" in topics:
        topics = ["司法和执法"] + [t for t in topics if t in METHODOLOGY_TOPICS and t != "司法和执法"]

    topics = topics[:MAX_TOPICS] or ["其他"]

    # 规则5: 只剩"实证研究"一个标签时,归入"其他"
    if topics == ["实证研究"]:
        topics = ["其他"]

    return {"topics": topics, "primary_topic": topics[0]}
