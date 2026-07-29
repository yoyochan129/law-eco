// 通过 GitHub Contents API 直接读写 database/articles.json,
// 用于网页端"编辑文章标签"功能。这个网站是纯静态GitHub Pages站点,
// 没有后端服务器,唯一能把编辑结果真正持久化的办法就是让浏览器直接
// 调用GitHub API把改动提交回仓库。
//
// Token只保存在你自己浏览器的 localStorage 里,只会被发送给
// api.github.com,不会经过任何其他服务器。建议创建一个"fine-grained
// personal access token",只授权这一个仓库的 Contents 读写权限,
// 不要用拥有全部仓库权限的经典token。
(function () {
  const REPO_OWNER = "yoyochan129";
  const REPO_NAME = "law-eco";
  const FILE_PATH = "database/articles.json";
  const BRANCH = "main";
  const TOKEN_KEY = "gh_pat_law_eco";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || "";
  }

  function setToken(token) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  }

  function utf8ToBase64(str) {
    const bytes = new TextEncoder().encode(str);
    let binary = "";
    bytes.forEach((b) => (binary += String.fromCharCode(b)));
    return btoa(binary);
  }

  function base64ToUtf8(b64) {
    const binary = atob(b64.replace(/\n/g, ""));
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  }

  async function apiRequest(method, body) {
    const token = getToken();
    if (!token) {
      throw new Error("NO_TOKEN");
    }
    const url = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`;
    const resp = await fetch(method === "GET" ? `${url}?ref=${BRANCH}` : url, {
      method,
      headers: {
        Authorization: `token ${token}`,
        Accept: "application/vnd.github+json",
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) {
      const errBody = await resp.json().catch(() => ({}));
      const err = new Error(errBody.message || `GitHub API 请求失败(HTTP ${resp.status})`);
      err.status = resp.status;
      throw err;
    }
    return resp.json();
  }

  async function fetchArticlesFile() {
    // GitHub Contents API的GET响应对超过1MB的文件不会内嵌base64内容
    // (content字段会是空字符串,encoding为"none"),database/articles.json
    // 已经超过这个门槛了。sha从标准接口正常拿到(不受文件大小影响)。
    //
    // 真正的文件内容【不能】通过 download_url(raw.githubusercontent.com)拿——
    // 那是一层CDN,实测发现提交后短时间内会返回缓存的旧内容,导致连续编辑
    // 多篇文章时,后一次编辑读到的还是上上次提交前的旧数据,保存时把上一次
    // 编辑的结果覆盖掉了(这个bug实际把用户好几次编辑结果冲掉过)。
    // 改为对同一个 contents API 端点加 Accept: application/vnd.github.raw+json
    // 请求头,直接从 api.github.com 拿原始内容,不经过CDN,读到的一定是最新
    // 提交的内容,同时依然不受1MB门槛限制。
    const token = getToken();
    if (!token) {
      throw new Error("NO_TOKEN");
    }
    const url = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`;

    const metaResp = await fetch(url, {
      headers: { Authorization: `token ${token}`, Accept: "application/vnd.github+json" },
    });
    if (!metaResp.ok) {
      const errBody = await metaResp.json().catch(() => ({}));
      const err = new Error(errBody.message || `获取文件元信息失败(HTTP ${metaResp.status})`);
      err.status = metaResp.status;
      throw err;
    }
    const meta = await metaResp.json();

    const rawResp = await fetch(url, {
      headers: { Authorization: `token ${token}`, Accept: "application/vnd.github.raw+json" },
    });
    if (!rawResp.ok) {
      throw new Error(`获取文件内容失败(HTTP ${rawResp.status})`);
    }
    const articles = await rawResp.json();
    return { sha: meta.sha, articles };
  }

  async function saveArticlesFile(articles, sha, commitMessage) {
    const content = utf8ToBase64(JSON.stringify(articles, null, 2));
    return apiRequest("PUT", {
      message: commitMessage,
      content,
      sha,
      branch: BRANCH,
    });
  }

  // 更新单篇文章的标签(topics/primary_topic),自动处理"先拉取最新sha再提交"
  // 以降低并发编辑冲突概率;冲突时抛出 CONFLICT 错误由调用方提示用户重试。
  async function updateArticleTopics(articleId, newTopics, newPrimaryTopic) {
    const { sha, articles } = await fetchArticlesFile();
    const idx = articles.findIndex((a) => a.id === articleId);
    if (idx === -1) {
      throw new Error("NOT_FOUND");
    }
    articles[idx].topics = newTopics;
    articles[idx].primary_topic = newPrimaryTopic;
    articles[idx].manually_tagged = true; // 防止之后的自动重新分类脚本覆盖人工编辑
    const title = articles[idx].title || articleId;
    try {
      await saveArticlesFile(articles, sha, `手动编辑标签: ${title}`);
    } catch (err) {
      if (err.status === 409) {
        const conflictErr = new Error("CONFLICT");
        conflictErr.name = "CONFLICT";
        throw conflictErr;
      }
      throw err;
    }
    return articles[idx];
  }

  window.GitHubSync = {
    getToken,
    setToken,
    updateArticleTopics,
    REPO_OWNER,
    REPO_NAME,
  };
})();
