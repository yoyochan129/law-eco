# -*- coding: utf-8 -*-
"""
数据来源配置。
status: active(可自动抓取) / pending(暂不可自动抓取,已记录原因)
"""

SOURCES = [
    # ---------------- 可自动抓取 (RSS) ----------------
    {
        "id": "harvard_corpgov",
        "name": "Harvard Law School Forum on Corporate Governance",
        "type": "rss",
        "feed_url": "https://corpgov.law.harvard.edu/feed/",
        "status": "active",
    },
    {
        "id": "columbia_blogs",
        "name": "Columbia Law School Blogs (CLS Blue Sky Blog)",
        "type": "rss",
        "feed_url": "https://clsbluesky.law.columbia.edu/feed/",
        "status": "active",
    },
    {
        "id": "oxford_business_law_blog",
        "name": "Oxford Business Law Blog",
        "type": "rss_filtered",
        "feed_url": "https://blogs.law.ox.ac.uk/rss.xml",
        "link_filter": "/oblb/",
        "status": "active",
    },
    {
        "id": "nber_wp",
        "name": "NBER Working Paper",
        "type": "rss",
        "feed_url": "https://www.nber.org/rss/new.xml",
        "status": "active",
        "no_reliable_date": True,
        "note": "RSS条目不含可解析的发布日期,无法按周过滤,依赖feed本身只推送新增论文的特性",
    },
    {
        "id": "bis_wp",
        "name": "BIS Working Paper",
        "type": "rss",
        "feed_url": "https://www.bis.org/doclist/wppubls.rss",
        "status": "active",
    },
    {
        "id": "bis_speech",
        "name": "BIS speech",
        "type": "rss",
        "feed_url": "https://www.bis.org/doclist/mgmtspeeches.rss",
        "status": "moved_to_news",
        "note": "已迁移至「每周新闻」板块(见 news_sources_config.py),"
                "不再作为研究文章来源抓取,避免重复出现在两个板块",
    },
    {
        "id": "michigan_law_econ",
        "name": "Michigan Law & Economics Working Papers",
        "type": "rss",
        "feed_url": "https://repository.law.umich.edu/law_econ_current/recent.rss",
        "status": "active",
    },
    {
        "id": "journal_of_finance",
        "name": "Journal of Finance",
        "type": "rss",
        "feed_url": "https://onlinelibrary.wiley.com/action/showFeed?jc=15406261&type=etoc&feed=rss",
        "status": "active",
    },
    {
        "id": "jels",
        "name": "Journal of Empirical Legal Studies",
        "type": "rss",
        "feed_url": "https://onlinelibrary.wiley.com/action/showFeed?jc=17401461&type=etoc&feed=rss",
        "status": "active",
    },
    {
        "id": "journal_legal_studies",
        "name": "Journal of Legal Studies",
        "type": "rss",
        "feed_url": "https://www.journals.uchicago.edu/action/showFeed?type=etoc&feed=rss&jc=jls",
        "status": "active",
        "fix_author_glue": True,
        "note": "摘要在RSS中仅为期刊卷期信息,完整摘要页(journals.uchicago.edu)受Cloudflare人机验证保护,自动化请求无法获取,已尝试requests与WebFetch均返回403",
    },
    {
        "id": "journal_law_econ",
        "name": "Journal of Law and Economics",
        "type": "rss",
        "feed_url": "https://www.journals.uchicago.edu/action/showFeed?type=etoc&feed=rss&jc=jle",
        "status": "active",
        "fix_author_glue": True,
        "note": "摘要在RSS中仅为期刊卷期信息,完整摘要页(journals.uchicago.edu)受Cloudflare人机验证保护,自动化请求无法获取,已尝试requests与WebFetch均返回403",
    },
    {
        "id": "irle",
        "name": "International Review of Law and Economics",
        "type": "rss",
        "feed_url": "https://rss.sciencedirect.com/publication/science/01448188",
        "status": "active",
        "note": "摘要在RSS中仅为出版元数据(卷期/作者列表),完整摘要页(sciencedirect.com)受Cloudflare人机验证保护,自动化请求无法获取,已尝试requests与WebFetch均返回403",
    },
    # ---------------- 可自动抓取 (静态HTML列表) ----------------
    {
        "id": "safe_wp",
        "name": "SAFE Working Paper Series",
        "type": "html_safe",
        "page_url": "https://safe-frankfurt.de/en/publications/safe-working-papers.html",
        "status": "active",
    },
    {
        "id": "yale_jreg",
        "name": "Yale Journal on Regulation",
        "type": "html_yalejreg",
        "page_url": "https://www.yalejreg.com/",
        "status": "active",
        "no_reliable_date": True,
        "note": "首页及文章详情页均无任何可提取的发布日期信号(已核实),"
                "无法按周过滤,依赖首页只展示近期文章的特性",
    },
    # ---------------- 可自动抓取 (Drupal JSON:API) ----------------
    {
        "id": "ecgi_wp",
        "name": "European Corporate Governance Institute (ECGI) working paper",
        "type": "ecgi_jsonapi",
        "page_url": "https://www.ecgi.global/publications/working-papers",
        "status": "active",
        "note": "网页本身是前端JS渲染无法直接抓取,但底层Drupal JSON:API "
                "(www.ecgi.global/jsonapi/node/working_paper) 公开可访问,已改为通过该接口抓取",
    },
    # ---------------- 可自动抓取 (IDEAS/RePEc 公开镜像) ----------------
    {
        "id": "nyfed_staff_reports",
        "name": "Federal Reserve Bank of New York staff report",
        "type": "repec_series",
        "repec_list_url": "https://ideas.repec.org/s/fip/fednsr.html",
        "repec_path_prefix": "/p/fip/fednsr/",
        "page_url": "https://www.newyorkfed.org/research/staff_reports/index.html",
        "status": "active",
        "note": "官网由Akamai机器人防护+前端JS渲染保护,无法直接抓取;"
                "改为通过 IDEAS/RePEc 的公开镜像(ideas.repec.org/s/fip/fednsr.html)抓取,"
                "详情页citation_*元标签含完整标题/作者/摘要/关键词/日期",
    },
    {
        "id": "bis_bulletin",
        "name": "BIS bulletin",
        "type": "repec_series",
        "repec_list_url": "https://ideas.repec.org/s/bis/bisblt.html",
        "repec_path_prefix": "/p/bis/bisblt/",
        "page_url": "https://www.bis.org/bisbulletins/index.htm",
        "status": "active",
        "note": "官网页面为前端SPA(JS动态加载)且无对应RSS;"
                "改为通过 IDEAS/RePEc 的公开镜像(ideas.repec.org/s/bis/bisblt.html)抓取",
    },
    {
        "id": "coase_sandor",
        "name": "Coase-Sandor Institute for Law & Economics Research Paper Series",
        "type": "rss",
        "feed_url": "https://chicagounbound.uchicago.edu/law_and_economics/recent.rss",
        "status": "active",
        "note": "该系列实际托管于芝加哥大学 Chicago Unbound (Digital Commons平台),"
                "而非SSRN;Digital Commons提供公开RSS,可直接抓取完整摘要与作者",
    },
    {
        "id": "nyu_law_econ",
        "name": "NYU Law & Economics Research Paper Series",
        "type": "pending",
        "page_url": "https://www.ssrn.com/index.cfm/en/nyu-law-econ/",
        "status": "pending",
        "reason": "SSRN Cloudflare人机验证拦截,无法直接抓取",
    },
    {
        "id": "gmu_law_econ",
        "name": "Antonin Scalia Law School (George Mason) Law & Economics Research Paper Series",
        "type": "pending",
        "page_url": "https://www.ssrn.com/index.cfm/en/george-mason-law-econ/",
        "status": "pending",
        "reason": "SSRN Cloudflare人机验证拦截,无法直接抓取",
    },
    {
        "id": "northwestern_law_econ",
        "name": "Northwestern Pritzker School of Law, Law & Economics Research Paper Series",
        "type": "pending",
        "page_url": "https://www.ssrn.com/index.cfm/en/northwestern-law-econ/",
        "status": "pending",
        "reason": "SSRN Cloudflare人机验证拦截,无法直接抓取",
    },
    {
        "id": "stanford_law_econ",
        "name": "Stanford Law School, John M. Olin Program in Law & Economics Working Paper Series",
        "type": "pending",
        "page_url": "https://www.ssrn.com/index.cfm/en/stanford-law-econ/",
        "status": "pending",
        "reason": "SSRN Cloudflare人机验证拦截,无法直接抓取",
    },
    {
        "id": "ucla_law_econ",
        "name": "UCLA School of Law, Law & Economics Research Paper Series",
        "type": "pending",
        "page_url": "https://www.ssrn.com/index.cfm/en/ucla-law-economics/",
        "status": "pending",
        "reason": "SSRN Cloudflare人机验证拦截,无法直接抓取",
    },
    {
        "id": "penn_law_econ",
        "name": "UPenn Carey Law School, Law & Economics Research Paper Series",
        "type": "pending",
        "page_url": "https://www.ssrn.com/index.cfm/en/penn-law-econ/",
        "status": "pending",
        "reason": "SSRN Cloudflare人机验证拦截,无法直接抓取",
    },
    {
        "id": "yale_public_law",
        "name": "Yale Law School, Public Law & Legal Theory Research Paper Series",
        "type": "pending",
        "page_url": "https://www.ssrn.com/index.cfm/en/yale-public-law/",
        "status": "pending",
        "reason": "SSRN Cloudflare人机验证拦截,无法直接抓取",
    },
    {
        "id": "eth_law_econ",
        "name": "ETH Center for Law & Economics Working Papers",
        "type": "pending",
        "page_url": "https://lawecon.ethz.ch/research/workingpapers.html",
        "status": "pending",
        "reason": "页面仅含导航/页脚静态内容,论文列表未在静态HTML中出现,需后续人工确认加载方式",
    },
    {
        "id": "rfs",
        "name": "Review of Financial Studies",
        "type": "pending",
        "page_url": "https://academic.oup.com/rfs",
        "status": "pending",
        "reason": "Oxford Academic(OUP)对自动化请求启用Cloudflare人机验证,无法直接抓取"
                  "(已用具体期号页面 /rfs/issue/39/8 重测,仍返回403,确认是站点级拦截而非页面级)",
    },
    {
        "id": "review_of_finance",
        "name": "Review of Finance",
        "type": "pending",
        "page_url": "https://academic.oup.com/rof",
        "status": "pending",
        "reason": "Oxford Academic(OUP)对自动化请求启用Cloudflare人机验证,无法直接抓取",
    },
    {
        "id": "aler",
        "name": "American Law and Economics Review",
        "type": "pending",
        "page_url": "https://academic.oup.com/aler",
        "status": "pending",
        "reason": "Oxford Academic(OUP)对自动化请求启用Cloudflare人机验证,无法直接抓取"
                  "(已用具体期号页面 /aler/issue/25/1 重测,仍返回403,确认是站点级拦截而非页面级)",
    },
    {
        "id": "jleo",
        "name": "Journal of Law, Economics, & Organization",
        "type": "pending",
        "page_url": "https://academic.oup.com/jleo",
        "status": "pending",
        "reason": "Oxford Academic(OUP)对自动化请求启用Cloudflare人机验证,无法直接抓取"
                  "(已用具体期号页面 /jleo/issue/42/2 重测,仍返回403,确认是站点级拦截而非页面级)",
    },
    {
        "id": "ejle",
        "name": "European Journal of Law & Economics",
        "type": "html_springer",
        "page_url": "https://link.springer.com/journal/10657",
        "status": "active",
        "note": "期刊主页本身无反爬限制,静态HTML里的\"最新文章\"区块可直接解析出"
                "5篇左右最新文章链接;单篇文章详情页也无反爬限制,"
                "citation_author/citation_author_institution元标签可拿到作者及机构,"
                "正文中的Abstract区块可拿到完整摘要",
    },
]
