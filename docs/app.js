(function () {
  const TOPIC_ORDER = [
    "公司治理", "公司并购", "破产法", "证券法", "金融监管", "竞争法和反垄断法",
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
  const scholars = window.SCHOLARS_DATA || [];
  const lastReport = window.LAST_REPORT || {};

  const state = {
    mode: "articles", // "articles" | "news" | "scholars"
    search: "",
    week: null,
    sources: new Set(),
    topics: new Set(),
    scholarSearch: "",
    selectedScholar: null,
    editingArticleId: null,
    editDraftTopics: [],
    editError: "",
    editSaving: false,
  };

  const TIER_CLASS = { "第一梯队": "tier-1", "核心追踪": "tier-2", "专题追踪": "tier-3" };

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
      <span>追踪学者 <b>${scholars.length}</b> 位</span>
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

  function renderTagEditorHtml(a) {
    const draft = state.editDraftTopics;
    const chips = draft
      .map(
        (t) => `
        <span class="tag-chip" data-topic="${escapeAttr(t)}">
          ${escapeHtml(t)}
          <button type="button" class="tag-remove-btn" data-topic="${escapeAttr(t)}">×</button>
        </span>`
      )
      .join("");
    const remaining = TOPIC_ORDER.filter((t) => !draft.includes(t));
    const options = remaining.map((t) => `<option value="${escapeAttr(t)}">${escapeHtml(t)}</option>`).join("");
    const disabled = draft.length >= 2 ? "disabled" : "";
    const msg = state.editError
      ? `<span class="tag-editor-msg" style="color:#cf222e;">${escapeHtml(state.editError)}</span>`
      : state.editSaving
      ? `<span class="tag-editor-msg">保存中…</span>`
      : "";
    return `
      <div class="tag-editor" data-article-id="${escapeAttr(a.id)}">
        <div class="tag-editor-current">${chips || '<span class="tag-editor-msg">还没有标签,从下面选择添加</span>'}</div>
        <select class="tag-add-select" ${disabled}>
          <option value="">${draft.length >= 2 ? "最多2个标签" : "+ 添加标签…"}</option>
          ${options}
        </select>
        <div class="tag-editor-actions">
          <button type="button" class="tab-btn active tag-save-btn" style="border-radius:8px;padding:6px 14px;">保存</button>
          <button type="button" class="reset-btn tag-cancel-btn" style="width:auto;padding:6px 14px;">取消</button>
          ${msg}
        </div>
      </div>`;
  }

  function openTagEditor(a) {
    state.editingArticleId = a.id;
    state.editDraftTopics = (a.topics || []).slice();
    state.editError = "";
    state.editSaving = false;
    renderArticles();
  }

  function closeTagEditor() {
    state.editingArticleId = null;
    state.editDraftTopics = [];
    state.editError = "";
    state.editSaving = false;
    renderArticles();
  }

  async function saveTagEdit(a) {
    if (!window.GitHubSync || !window.GitHubSync.getToken()) {
      state.editError = "请先点右上角「⚙ 编辑设置」配置GitHub Token";
      renderArticles();
      return;
    }
    state.editSaving = true;
    state.editError = "";
    renderArticles();
    const newTopics = state.editDraftTopics.slice(0, 2);
    const newPrimary = newTopics[0] || "其他";
    try {
      await window.GitHubSync.updateArticleTopics(a.id, newTopics.length ? newTopics : ["其他"], newPrimary);
      a.topics = newTopics.length ? newTopics : ["其他"];
      a.primary_topic = newPrimary;
      closeTagEditor();
    } catch (err) {
      state.editSaving = false;
      if (err.message === "NO_TOKEN") {
        state.editError = "请先点右上角「⚙ 编辑设置」配置GitHub Token";
      } else if (err.name === "CONFLICT") {
        state.editError = "保存冲突(可能有其他修改正在进行),请重试一次";
      } else if (err.status === 401 || err.status === 403) {
        state.editError = "Token无效或权限不足,请在编辑设置里检查";
      } else {
        state.editError = "保存失败: " + (err.message || "未知错误");
      }
      renderArticles();
    }
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
        const isEditing = state.editingArticleId === a.id;
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
            <button type="button" class="tag-edit-btn" data-article-id="${escapeAttr(a.id)}">✎ 编辑标签</button>
          </div>
          ${isEditing ? renderTagEditorHtml(a) : ""}
          <div class="article-footer">
            <a class="read-link" href="${escapeAttr(a.url)}" target="_blank" rel="noopener">阅读原文 →</a>
          </div>
        </article>`;
      })
      .join("");

    list.querySelectorAll(".tag-edit-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-article-id");
        const article = articles.find((x) => x.id === id);
        if (article) openTagEditor(article);
      });
    });
    list.querySelectorAll(".tag-remove-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const t = btn.getAttribute("data-topic");
        state.editDraftTopics = state.editDraftTopics.filter((x) => x !== t);
        renderArticles();
      });
    });
    list.querySelectorAll(".tag-add-select").forEach((sel) => {
      sel.addEventListener("change", () => {
        if (sel.value && state.editDraftTopics.length < 2) {
          state.editDraftTopics.push(sel.value);
        }
        renderArticles();
      });
    });
    list.querySelectorAll(".tag-save-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.closest(".tag-editor").getAttribute("data-article-id");
        const article = articles.find((x) => x.id === id);
        if (article) saveTagEdit(article);
      });
    });
    list.querySelectorAll(".tag-cancel-btn").forEach((btn) => {
      btn.addEventListener("click", closeTagEditor);
    });
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

  function matchesScholar(s) {
    if (!state.scholarSearch) return true;
    const hay = [s.name, s.research_topics, s.research_methods].join(" ").toLowerCase();
    return hay.includes(state.scholarSearch.toLowerCase());
  }

  function renderScholarGroup(category, containerId) {
    const list = scholars.filter((s) => s.category === category).filter(matchesScholar);
    const el = document.getElementById(containerId);
    el.innerHTML = list
      .map((s) => {
        const tierClass = TIER_CLASS[s.tier] || "tier-3";
        const active = state.selectedScholar && state.selectedScholar.name === s.name;
        return `
        <div class="scholar-item ${active ? "active" : ""}" data-scholar="${escapeAttr(s.name)}">
          <span class="scholar-rank">${s.rank}</span>
          <span class="scholar-tier-dot ${tierClass}" title="${escapeAttr(s.tier)}"></span>
          <span class="scholar-name">${escapeHtml(s.name)}</span>
        </div>`;
      })
      .join("");
    el.querySelectorAll(".scholar-item").forEach((node) => {
      node.addEventListener("click", () => {
        const name = node.getAttribute("data-scholar");
        state.selectedScholar = scholars.find((s) => s.name === name) || null;
        renderScholars();
      });
    });
  }

  function renderScholarDetail() {
    const el = document.getElementById("scholarsDetail");
    const s = state.selectedScholar;
    if (!s) {
      el.innerHTML = '<div class="scholar-placeholder">从左侧选择一位学者查看详情</div>';
      return;
    }

    const statusNote = s.tracking_status === "manual_only"
      ? '<div class="scholar-status-note">该学者暂无法自动追踪最新文献，请通过主页链接自行查看。</div>'
      : "";

    const litCards = (s.literature || [])
      .map((w) => `
        <article class="article-card">
          <h3 class="article-title"><a href="${escapeAttr(w.url)}" target="_blank" rel="noopener">${escapeHtml(w.title)}</a></h3>
          ${w.title_zh ? `<div class="article-title-zh">${escapeHtml(w.title_zh)}</div>` : ""}
          <div class="article-meta">${escapeHtml(w.authors || s.name)} ${w.date ? " · " + escapeHtml(w.date) : ""}</div>
          <div class="article-abstract">${escapeHtml(w.abstract || "原文未提供摘要，详见链接。")}</div>
          ${w.abstract_zh ? `<div class="article-abstract-zh">${escapeHtml(w.abstract_zh)}</div>` : ""}
          <div class="article-footer">
            <a class="read-link" href="${escapeAttr(w.url)}" target="_blank" rel="noopener">阅读原文 →</a>
          </div>
        </article>`)
      .join("");

    el.innerHTML = `
      <div class="scholar-profile-card">
        <div class="scholar-profile-header">
          <h2>${escapeHtml(s.name)}</h2>
          ${s.profile_url ? `<a class="read-link" href="${escapeAttr(s.profile_url)}" target="_blank" rel="noopener">访问个人/学校主页 →</a>` : `<span class="scholar-status-note" style="margin-top:0;">暂未能确认本人主页链接</span>`}
        </div>
        <div class="scholar-profile-field"><b>研究领域</b>${escapeHtml(s.research_topics || "")}</div>
        <div class="scholar-profile-field"><b>研究方法</b>${escapeHtml(s.research_methods || "")}</div>
        <div class="scholar-profile-field"><b>为什么值得追踪</b>${escapeHtml(s.why_track || "")}</div>
        ${statusNote}
      </div>
      <div class="article-section-header">
        <h2>最新文献</h2>
        <span class="result-count">${s.literature.length ? "共 " + s.literature.length + " 篇" : ""}</span>
      </div>
      <div class="article-list">
        ${litCards || '<div class="empty-state">暂无可自动获取的文献，请通过主页链接查看。</div>'}
      </div>
    `;
  }

  function renderScholars() {
    renderScholarGroup("法学", "lawScholarList");
    renderScholarGroup("金融", "financeScholarList");
    renderScholarDetail();
  }

  function renderAll() {
    if (state.mode === "scholars") {
      renderScholars();
      return;
    }
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
    document.getElementById("mainLayout").style.display = mode === "scholars" ? "none" : "flex";
    document.getElementById("scholarsLayout").style.display = mode === "scholars" ? "flex" : "none";
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

  document.getElementById("scholarSearchInput").addEventListener("input", (e) => {
    state.scholarSearch = e.target.value.trim();
    renderScholars();
  });

  function openSettingsModal() {
    const modal = document.getElementById("settingsModal");
    const input = document.getElementById("tokenInput");
    const status = document.getElementById("tokenStatus");
    input.value = window.GitHubSync ? window.GitHubSync.getToken() : "";
    status.textContent = "";
    status.className = "modal-status";
    modal.style.display = "flex";
  }
  function closeSettingsModal() {
    document.getElementById("settingsModal").style.display = "none";
  }

  document.getElementById("settingsBtn").addEventListener("click", openSettingsModal);
  document.getElementById("modalCloseBtn").addEventListener("click", closeSettingsModal);
  document.getElementById("settingsModal").addEventListener("click", (e) => {
    if (e.target.id === "settingsModal") closeSettingsModal();
  });
  document.getElementById("tokenSaveBtn").addEventListener("click", () => {
    const val = document.getElementById("tokenInput").value.trim();
    if (!window.GitHubSync) return;
    window.GitHubSync.setToken(val);
    const status = document.getElementById("tokenStatus");
    status.textContent = val ? "已保存到本设备浏览器" : "Token为空,未保存";
    status.className = "modal-status ok";
  });
  document.getElementById("tokenClearBtn").addEventListener("click", () => {
    if (!window.GitHubSync) return;
    window.GitHubSync.setToken("");
    document.getElementById("tokenInput").value = "";
    const status = document.getElementById("tokenStatus");
    status.textContent = "已清除";
    status.className = "modal-status ok";
  });

  renderTopbarStats();
  renderTrend();
  renderAll();
})();
