(function () {
  const TOPIC_ORDER = [
    "公司治理", "公司并购", "破产法", "金融监管", "竞争法和反垄断法",
    "司法和执法", "合同", "金融市场", "金融科技", "支付", "AI",
    "央行和货币政策", "银行", "稳定币", "非银机构", "私募信贷", "绿色金融",
    "行为研究", "实验", "实证研究", "DID", "因果推断", "机器学习",
    "区块链", "财政和主权债", "其他",
  ];

  const articles = (window.ARTICLES_DATA || []).slice().sort((a, b) => {
    return (b.date_added || "").localeCompare(a.date_added || "");
  });
  const news = (window.NEWS_DATA || []).slice().sort((a, b) => {
    return (b.date || "").localeCompare(a.date || "");
  });
  const lastReport = window.LAST_REPORT || {};

  const state = {
    mode: "articles", // "articles" | "news"
    search: "",
    week: null,
    sources: new Set(),
    topics: new Set(),
  };

  function activeDataset() {
    return state.mode === "news" ? news : articles;
  }

  function uniqueCount(list, key) {
    const map = new Map();
    list.forEach((item) => {
      const v = item[key];
      if (!v) return;
      map.set(v, (map.get(v) || 0) + 1);
    });
    return map;
  }

  function renderTopbarStats() {
    const sources = new Set(articles.map((a) => a.source));
    const el = document.getElementById("topbarStats");
    el.innerHTML = `
      <span>数据来源 <b>${sources.size}</b> 个</span>
      <span>文章总数 <b>${articles.length}</b> 篇</span>
      <span>本周新闻 <b>${news.length}</b> 条</span>
      <span>最新报告 <b>${lastReport.period_end || "—"}</b></span>
    `;
  }

  function renderTrend() {
    const body = document.getElementById("trendBody");
    const text = lastReport.trend_summary || "暂无趋势概括。";
    body.innerHTML = text
      .split(/\n\s*\n/)
      .map((p) => `<p>${escapeHtml(p)}</p>`)
      .join("");
  }

  function renderWeekList() {
    const counts = uniqueCount(activeDataset(), state.mode === "news" ? "week_of" : "week_of");
    const weeks = Array.from(counts.keys()).sort().reverse();
    const el = document.getElementById("weekList");
    el.innerHTML = weeks
      .map(
        (w) => `
        <div class="filter-item ${state.week === w ? "active" : ""}" data-week="${w}">
          <span>${w}</span><span class="count">${counts.get(w)}</span>
        </div>`
      )
      .join("");
    el.querySelectorAll(".filter-item").forEach((node) => {
      node.addEventListener("click", () => {
        const w = node.getAttribute("data-week");
        state.week = state.week === w ? null : w;
        renderAll();
      });
    });
  }

  function renderSourceList() {
    const counts = uniqueCount(activeDataset(), "source");
    const sources = Array.from(counts.keys()).sort();
    const el = document.getElementById("sourceList");
    el.innerHTML = sources
      .map(
        (s) => `
        <div class="filter-item ${state.sources.has(s) ? "active" : ""}" data-source="${escapeAttr(s)}">
          <span>${escapeHtml(s)}</span><span class="count">${counts.get(s)}</span>
        </div>`
      )
      .join("");
    el.querySelectorAll(".filter-item").forEach((node) => {
      node.addEventListener("click", () => {
        const s = node.getAttribute("data-source");
        if (state.sources.has(s)) state.sources.delete(s);
        else state.sources.add(s);
        renderAll();
      });
    });
  }

  function renderTopicList() {
    const counts = new Map();
    articles.forEach((a) => {
      (a.topics || []).forEach((t) => counts.set(t, (counts.get(t) || 0) + 1));
    });
    const el = document.getElementById("topicList");
    el.innerHTML = TOPIC_ORDER.filter((t) => counts.has(t))
      .map(
        (t) => `
        <div class="filter-item ${state.topics.has(t) ? "active" : ""}" data-topic="${escapeAttr(t)}">
          <span>${t}</span><span class="count">${counts.get(t)}</span>
        </div>`
      )
      .join("");
    el.querySelectorAll(".filter-item").forEach((node) => {
      node.addEventListener("click", () => {
        const t = node.getAttribute("data-topic");
        if (state.topics.has(t)) state.topics.delete(t);
        else state.topics.add(t);
        renderAll();
      });
    });
  }

  function matchesArticle(article) {
    if (state.week && article.week_of !== state.week) return false;
    if (state.sources.size && !state.sources.has(article.source)) return false;
    if (state.topics.size) {
      const topics = article.topics || [];
      if (!topics.some((t) => state.topics.has(t))) return false;
    }
    if (state.search) {
      const hay = [
        article.title,
        article.title_zh,
        article.abstract,
        article.abstract_zh,
        (article.keywords || []).join(" "),
        article.authors,
      ]
        .join(" ")
        .toLowerCase();
      if (!hay.includes(state.search.toLowerCase())) return false;
    }
    return true;
  }

  function matchesNews(item) {
    if (state.week && item.week_of !== state.week) return false;
    if (state.sources.size && !state.sources.has(item.source)) return false;
    if (state.search) {
      const hay = [item.title, item.summary_zh, item.speaker, item.org]
        .join(" ")
        .toLowerCase();
      if (!hay.includes(state.search.toLowerCase())) return false;
    }
    return true;
  }

  function renderArticles() {
    const filtered = articles.filter(matchesArticle);
    const list = document.getElementById("articleList");
    const empty = document.getElementById("emptyState");
    document.getElementById("resultCount").textContent = `共 ${filtered.length} 篇`;

    if (!filtered.length) {
      list.innerHTML = "";
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";

    list.innerHTML = filtered
      .map((a) => {
        const keywordTags = (a.keywords || [])
          .slice(0, 6)
          .map((k) => `<span class="tag">${escapeHtml(k)}</span>`)
          .join("");
        const topicTags = (a.topics || [])
          .map((t) => `<span class="tag topic">${escapeHtml(t)}</span>`)
          .join("");
        return `
        <article class="article-card">
          <h3 class="article-title"><a href="${escapeAttr(a.url)}" target="_blank" rel="noopener">${escapeHtml(a.title)}</a></h3>
          ${a.title_zh ? `<div class="article-title-zh">${escapeHtml(a.title_zh)}</div>` : ""}
          <div class="article-meta">${escapeHtml(a.authors || "作者信息见原文")} ${a.publish_date_norm ? " · " + a.publish_date_norm : ""}</div>
          <div class="article-abstract">${escapeHtml(a.abstract || "原文未提供摘要，详见链接。")}</div>
          ${a.abstract_zh ? `<div class="article-abstract-zh">${escapeHtml(a.abstract_zh)}</div>` : ""}
          <div class="article-tags">
            <span class="tag source">${escapeHtml(a.source)}</span>
            ${topicTags}
            ${keywordTags}
          </div>
          <div class="article-footer">
            <a class="read-link" href="${escapeAttr(a.url)}" target="_blank" rel="noopener">阅读原文 →</a>
          </div>
        </article>`;
      })
      .join("");
  }

  function renderNews() {
    const filtered = news.filter(matchesNews);
    const list = document.getElementById("newsList");
    const empty = document.getElementById("newsEmptyState");
    document.getElementById("newsResultCount").textContent = `共 ${filtered.length} 条`;

    if (!filtered.length) {
      list.innerHTML = "";
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";

    list.innerHTML = filtered
      .map((n) => {
        const speakerDisplay = n.speaker || n.org || "机构公告，无具名发言人";
        const summary = n.summary_zh
          ? escapeHtml(n.summary_zh)
          : "（无摘要，详见原文）";
        return `
        <article class="article-card">
          <h3 class="article-title"><a href="${escapeAttr(n.url)}" target="_blank" rel="noopener">${escapeHtml(n.title)}</a></h3>
          <div class="article-meta">${escapeHtml(speakerDisplay)} ${n.date ? " · " + escapeHtml(n.date) : ""}</div>
          <div class="article-abstract-zh" style="border-left:none;padding-left:0;">${summary}</div>
          <div class="article-tags">
            <span class="tag source">${escapeHtml(n.source)}</span>
          </div>
          <div class="article-footer">
            <a class="read-link" href="${escapeAttr(n.url)}" target="_blank" rel="noopener">阅读原文 →</a>
          </div>
        </article>`;
      })
      .join("");
  }

  function renderAll() {
    renderWeekList();
    renderSourceList();
    if (state.mode === "articles") {
      renderTopicList();
      renderArticles();
    } else {
      renderNews();
    }
  }

  function switchTab(mode) {
    state.mode = mode;
    state.week = null;
    state.sources.clear();
    state.topics.clear();

    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === mode);
    });
    document.getElementById("trendCard").style.display = mode === "articles" ? "" : "none";
    document.getElementById("articleSection").style.display = mode === "articles" ? "" : "none";
    document.getElementById("newsSection").style.display = mode === "news" ? "" : "none";
    document.getElementById("topicBlock").style.display = mode === "articles" ? "" : "none";

    renderAll();
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
  function escapeAttr(str) {
    return escapeHtml(str).replace(/"/g, "&quot;");
  }

  document.getElementById("searchInput").addEventListener("input", (e) => {
    state.search = e.target.value.trim();
    if (state.mode === "articles") renderArticles();
    else renderNews();
  });

  document.getElementById("resetBtn").addEventListener("click", () => {
    state.search = "";
    state.week = null;
    state.sources.clear();
    state.topics.clear();
    document.getElementById("searchInput").value = "";
    renderAll();
  });

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.getAttribute("data-tab")));
  });

  renderTopbarStats();
  renderTrend();
  renderAll();
})();
