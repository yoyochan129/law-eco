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
    // 已经超过这个门槛了。
    //
    // 排查过两种方案都不可靠:
    // 1. download_url(raw.githubusercontent.com)是CDN,提交后短时间内会
    //    返回缓存的旧内容,连续编辑时会把上一次编辑结果覆盖掉
    // 2. Accept: application/vnd.github.raw+json 这个内容协商头在实测中
    //    行为不稳定(带Authorization头时可能拿到的不是原始数组,导致后续
    //    articles.findIndex不是函数的报错)
    // 最终改用 Git Data 的 Blobs API(/git/blobs/{sha}):这是底层、语义
    // 明确的接口,不受文件大小限制,不经CDN,永远返回稳定的
    // {content(base64), encoding:"base64"} 结构,不存在内容协商的不确定性。
    const token = getToken();
    if (!token) {
      throw new Error("NO_TOKEN");
    }
    const headers = { Authorization: `token ${token}`, Accept: "application/vnd.github+json" };
    const contentsUrl = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`;

    const metaResp = await fetch(contentsUrl, { headers });
    if (!metaResp.ok) {
      const errBody = await metaResp.json().catch(() => ({}));
      const err = new Error(errBody.message || `获取文件元信息失败(HTTP ${metaResp.status})`);
      err.status = metaResp.status;
      throw err;
    }
    const meta = await metaResp.json();

    const blobUrl = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/git/blobs/${meta.sha}`;
    const blobResp = await fetch(blobUrl, { headers });
    if (!blobResp.ok) {
      throw new Error(`获取文件内容失败(HTTP ${blobResp.status})`);
    }
    const blob = await blobResp.json();
    if (blob.encoding !== "base64" || typeof blob.content !== "string") {
      throw new Error("获取到的文件内容格式不符合预期(非base64编码)");
    }
    const articles = JSON.parse(base64ToUtf8(blob.content));
    if (!Array.isArray(articles)) {
      throw new Error("解析出的文章数据不是数组,可能是文件内容异常");
    }
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
