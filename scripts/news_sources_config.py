# -*- coding: utf-8 -*-
"""
「每周新闻」板块数据源配置。
与 sources_config.py(研究文章)分开维护,因为字段结构和展示方式不同。
"""

NEWS_SOURCES = [
    {
        "id": "bis_speech_news",
        "name": "BIS speech",
        "feed_url": "https://www.bis.org/doclist/mgmtspeeches.rss",
        "speaker_strategy": "feed_author",
    },
    {
        "id": "sec_press",
        "name": "SEC Press Releases",
        "feed_url": "https://www.sec.gov/news/pressreleases.rss",
        "speaker_strategy": "none",
        "default_org": "U.S. Securities and Exchange Commission",
    },
    {
        "id": "sec_speeches",
        "name": "SEC Speeches & Statements",
        "feed_url": "https://www.sec.gov/news/speeches-statements.rss",
        "speaker_strategy": "detail_page_byline",
    },
    {
        "id": "ecb_press",
        "name": "ECB News & Publications",
        "feed_url": "https://www.ecb.europa.eu/rss/press.html",
        "speaker_strategy": "title_prefix",
        "title_prefix_sep": ":",
        "default_org": "European Central Bank",
    },
    {
        "id": "fed_press",
        "name": "Federal Reserve News & Events",
        "feed_url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "speaker_strategy": "none",
        "default_org": "Federal Reserve Board",
    },
    {
        "id": "fed_speeches",
        "name": "Federal Reserve News & Events",
        "feed_url": "https://www.federalreserve.gov/feeds/speeches_and_testimony.xml",
        "speaker_strategy": "title_prefix",
        "title_prefix_sep": ",",
    },
    {
        "id": "boe_news",
        "name": "Bank of England News",
        "feed_url": "https://www.bankofengland.co.uk/rss/news",
        "speaker_strategy": "none",
        "default_org": "Bank of England",
    },
]
