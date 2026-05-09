const api = "/api/h5";
const tokenKey = "haibao_h5_token";
const stateKey = "haibao_h5_draft";
const app = document.querySelector("#app");
const toastEl = document.querySelector("#toast");

let draft = JSON.parse(localStorage.getItem(stateKey) || "{}");
let route = location.hash.replace("#", "") || "home";
let lastTask = null;
let waitingProgressTimer = null;

const styles = [
  ["premium_commercial", "高级商业广告", "产品广告、品牌宣传"],
  ["xiaohongshu", "小红书种草风", "生活方式、种草分享"],
  ["ecommerce", "电商主图风", "商品销售、平台主图"],
  ["minimal", "极简高级风", "家居、香氛、服装"],
];

const posterTypes = [
  ["product", "产品宣传海报", "适合新品、食品、设备、日用品推广", "type-product", "icon_01_product_bag.png", "type-product-poster.png"],
  ["xiaohongshu", "小红书种草图", "适合民宿、美妆、生活方式内容", "type-xhs", "icon_02_heart.png", "type-xiaohongshu.png"],
  ["main_image", "电商主图", "适合商品销售和平台展示", "type-shop", "icon_03_cart.png", "type-ecommerce-main.png"],
  ["promotion", "活动促销海报", "适合门店活动、节日促销", "type-promo", "icon_04_megaphone.png", "type-promotion.png"],
];

const posterTypeStyleMap = {
  product: "premium_commercial",
  xiaohongshu: "xiaohongshu",
  main_image: "ecommerce",
  promotion: "premium_commercial",
};

const ratios = ["1:1", "3:4", "4:5", "9:16", "16:9"];
const qualityOptions = [
  ["medium", "高清", 8],
  ["high", "超清", 10],
];
const uploadCompressOptions = {
  maxSide: 2200,
  quality: 0.88,
  maxRawSize: 30 * 1024 * 1024,
};

const homeFeatures = [
  ["product", "产品海报", "突出卖点", "产品海报icon.png"],
  ["xiaohongshu", "小红书封面", "种草必备", "小红书icon.png"],
  ["main_image", "电商主图", "提升点击率", "电商主图icon.png"],
  ["promotion", "活动促销", "吸睛利器", "活动促销icon.png"],
];

const homeStyles = [
  ["premium_commercial", "高级商业广告", "质感 · 专业 · 高级", "ChatGPT Image 2026年4月28日 下午02_39_46.png"],
  ["xiaohongshu", "小红书 Ins", "清新 · 种草 · 吸睛", "ChatGPT Image 2026年4月28日 下午02_40_47.png"],
  ["ecommerce", "黑黑金奢华", "高端 · 奢华 · 大气", "ChatGPT Image 2026年4月28日 下午02_41_56.png"],
  ["minimal", "清新自然", "自然 · 清新 · 舒适", "ChatGPT Image 2026年4月28日 下午02_43_36.png"],
];

function token() { return localStorage.getItem(tokenKey); }
function saveDraft() { localStorage.setItem(stateKey, JSON.stringify(draft)); }
function go(name) { route = name; location.hash = name; render(); }
function toast(message) {
  toastEl.textContent = formatErrorMessage(message).split("\n")[0];
  toastEl.classList.add("show");
  setTimeout(() => toastEl.classList.remove("show"), 2400);
}
function asset(url) { return url || ""; }
function authHeaders() { return token() ? { Authorization: `Bearer ${token()}` } : {}; }
function formatErrorMessage(detail) {
  if (!detail) return "请求失败";
  if (typeof detail === "string") return detail;
  if (detail.message) return detail.message;
  if (Array.isArray(detail)) return detail.map(item => item.msg || JSON.stringify(item)).join("\n");
  return JSON.stringify(detail, null, 2);
}
function normalizeText(value) {
  const text = String(value ?? "").trim();
  return ["", "无", "暂无", "none", "null", "undefined", "N/A"].includes(text) ? "" : text;
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}), ...authHeaders() };
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const res = await fetch(api + path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(formatErrorMessage(data.detail || data || "请求失败"));
  return data;
}

function isTabRoute(name = route) {
  return ["home", "type", "mine"].includes(name);
}

function layout(content, nav = isTabRoute()) {
  app.className = `app-shell route-${route} ${nav ? "has-nav" : "no-nav"}`;
  app.innerHTML = content + (nav ? bottomNav() : "");
}

function topbar(title, right = "") {
  return `<div class="topbar"><button class="back" onclick="historyBack()">‹</button><strong>${title}</strong><div class="topbar-right">${right}</div></div>`;
}

function historyBack() {
  const map = {
    product: "type",
    reference: "product",
    copy: "reference",
    confirm: "copy",
    waiting: "confirm",
    result: "home",
    edit: "result",
    plaza: "home",
    works: "mine",
    work: "works",
    likes: "mine",
    points: "mine",
  };
  go(map[route] || "home");
}

function progress(step, label) {
  return `<div class="step-head">
    <div class="step-count">${step}/4 ${label}</div>
    <div class="step-bars">${[1,2,3,4].map(i => `<span class="${i <= step ? "active" : ""}"></span>`).join("")}</div>
  </div>`;
}

function bottomNav() {
  const createActive = route === "type";
  return `<nav class="nav">
    <button class="${route === "home" ? "active" : ""}" onclick="go('home')"><img class="nav-img" src="/h5-static/assets/ui_v1/common/${route === "home" ? "nav-home-active.svg" : "nav-home.svg"}" alt=""><span>首页</span></button>
    <button class="${createActive ? "active" : ""}" onclick="startFlow()"><img class="nav-img" src="/h5-static/assets/ui_v1/common/${createActive ? "nav-create-active.svg" : "nav-create.svg"}" alt=""><span>生成</span></button>
    <button class="${route === "mine" ? "active" : ""}" onclick="needLogin(()=>go('mine'))"><img class="nav-img" src="/h5-static/assets/ui_v1/common/${route === "mine" ? "nav-mine-active.svg" : "nav-mine.svg"}" alt=""><span>我的</span></button>
  </nav>`;
}

function needLogin(next) {
  if (!token()) {
    draft.afterLogin = route === "auth" ? "home" : route;
    saveDraft();
    go("auth");
    return;
  }
  next();
}

function startFlow() {
  needLogin(() => {
    draft = { productImages: [], referenceImages: [], ratio: "9:16", imageQuality: "high", style: "premium_commercial", posterType: "product" };
    saveDraft();
    go("type");
  });
}

async function render() {
  if (route === "auth") return renderAuth();
  if (route === "type") return renderType();
  if (route === "product") return renderProduct();
  if (route === "reference") return renderReference();
  if (route === "copy") return renderCopy();
  if (route === "style") return go("confirm");
  if (route === "confirm") return renderConfirm();
  if (route === "waiting") return renderWaiting();
  if (route === "result") return renderResult();
  if (route === "edit") return renderEdit();
  if (route === "plaza") return renderPlaza();
  if (route === "works") return renderWorks();
  if (route === "work") return renderWorkDetail();
  if (route === "likes") return renderLikedWorks();
  if (route === "points") return renderPoints();
  if (route === "mine") return renderMine();
  return renderHome();
}

async function renderHome() {
  let points = "120";
  let profile = null;
  let featuredWorks = [];
  if (token()) {
    try {
      profile = await request("/user/profile");
      points = profile.points_balance;
    } catch {
      localStorage.removeItem(tokenKey);
    }
  }
  try {
    featuredWorks = (await request("/works/featured")).list || [];
  } catch {
    featuredWorks = [];
  }
  const homeWorksHtml = featuredWorks.length
    ? featuredWorks.map(w => workFeedCard(w, { context: "home", clickAction: "go('plaza')" })).join("")
    : homeStyles.map((s, index) => workFeedCard({
        title: s[1],
        cover_url: `/h5-static/assets/ui_v1/home/${s[3]}`,
        author_name: "图生意官方",
        likes_count: [126, 98, 83, 72][index] || 66,
      }, { context: "home", clickAction: "go('plaza')" })).join("");
  layout(`
    <div class="home-head">
      <div class="brand-row"><img class="home-brand-logo" src="/h5-static/assets/ui_v1/brand/logo_t.png" alt="图生意"></div>
      <div class="head-pills">
        ${profile ? `<button class="pill points-pill" onclick="go('points')"><span>★</span>积分 ${points}</button>` : ""}
        ${profile ? `<button class="home-user-chip" onclick="go('mine')"><span class="home-avatar">${escapeHtml((profile.username || "U").slice(0, 1).toUpperCase())}</span><b>${escapeHtml(profile.username || "用户")}</b></button>` : `<button class="home-user-chip guest" onclick="go('auth')"><span class="home-avatar">U</span><b>登录</b></button>`}
      </div>
    </div>
    <section class="home-hero">
      <img class="home-hero-bg" src="/h5-static/assets/ui_v1/home/首页底图.png" alt="">
      <div class="home-hero-copy">
        <h1>AI 产品海报生成器</h1>
        <p>上传产品图，填写文案，<br>30 秒生成广告海报</p>
      </div>
      <button class="home-generate-btn" onclick="startFlow()">✦ 立即生成</button>
    </section>
    <section class="grid-4 feature-strip">
      ${homeFeatures.map(item => `<button class="feature card" onclick="pickPosterTypeFromHome('${item[0]}')"><img src="/h5-static/assets/ui_v1/home/${item[3]}" alt=""><b>${item[1]}</b><span>${item[2]}</span></button>`).join("")}
    </section>
    <div class="section-head home-section-head"><h2>热门作品</h2><button onclick="go('plaza')">作品广场 ›</button></div>
    <section class="home-work-grid">${homeWorksHtml}</section>
  `);
}

function workFeedCard(work, options = {}) {
  const context = options.context || "plaza";
  const clickAction = options.clickAction ? ` onclick="${options.clickAction}"` : "";
  const versionId = work.version_id || "";
  const title = escapeHtml(work.title || "AI 营销海报");
  const author = escapeHtml(work.author_name || "图生意用户");
  const cover = asset(work.cover_url || "");
  const likes = Number(work.likes_count || 0);
  const likeNode = versionId
    ? `<button id="like_${versionId}" class="feed-like ${work.liked_by_me ? "liked" : ""}" onclick="likePlaza(event, '${versionId}')"><span>♥</span><b>${likes}</b></button>`
    : `<span class="feed-like readonly"><span>♥</span><b>${likes}</b></span>`;
  return `<article class="work-feed-card ${context === "home" ? "home-work-card" : "plaza-card"}"${clickAction}>
    <img class="work-feed-image" src="${cover}" alt="${title}" loading="lazy" ${context === "plaza" ? `onclick="downloadImage('${cover}')"` : ""}>
    <div class="work-feed-meta">
      <b class="work-feed-title">${title}</b>
      <div class="work-feed-sub"><span class="work-feed-author">${author}</span>${likeNode}</div>
    </div>
  </article>`;
}

function pickPosterTypeFromHome(type) {
  needLogin(() => {
    draft = { productImages: [], referenceImages: [], ratio: "9:16", imageQuality: "high", style: posterTypeStyleMap[type] || "premium_commercial", posterType: type };
    saveDraft();
    go("product");
  });
}

function pickStyleFromHome(style) {
  needLogin(() => {
    draft = { productImages: [], referenceImages: [], ratio: "9:16", imageQuality: "high", style, posterType: "product" };
    saveDraft();
    go("type");
  });
}

function renderAuth() {
  layout(`
    <section class="auth-page">
      <div class="auth-brand">
        <img class="brand-logo-img brand-logo-title" src="/h5-static/assets/ui_v1/brand/logo_t.png" alt="图生意">
        <p>一张好图，帮你多卖一点</p>
      </div>
      <div class="login-panel">
        <div class="field"><label>账号</label><input id="username" placeholder="请输入用户名"></div>
        <div class="field"><label>密码</label><input id="password" type="password" placeholder="至少 6 位"></div>
        <button class="primary" onclick="auth('login')">登录</button>
        <button class="secondary soft-secondary" onclick="auth('register')">注册并领取 50 积分</button>
      </div>
      <p class="auth-tool-note">一款为商家量身打造的AI营销工具</p>
      <p class="agreement">登录即表示同意用户协议和隐私政策</p>
    </section>
  `, false);
}

async function auth(mode) {
  try {
    const data = await request(`/auth/${mode}`, {
      method: "POST",
      body: JSON.stringify({ username: username.value, password: password.value }),
    });
    localStorage.setItem(tokenKey, data.token);
    toast(mode === "register" ? "注册成功，已赠送积分" : "登录成功");
    go(draft.afterLogin || "home");
  } catch (e) { toast(e.message); }
}

function renderType() {
  ensureAuthRoute();
  layout(`<section class="type-page">
    <header class="type-hero">
      <span class="type-spark type-spark-left">✦</span>
      <h1>选择你要生成的内容</h1>
      <span class="type-spark type-spark-right">✦</span>
      <p>不同场景使用不同海报模板</p>
    </header>
    <section class="type-list">
      ${posterTypes.map(type => `<button class="type-card ${type[3]}" onclick="pickPosterTypeAndNext('${type[0]}')">
        <div class="type-copy">
          <img class="type-icon" src="/h5-static/assets/ui_v1/common/${type[4]}" alt="">
          <b>${type[1]}</b>
          <p>${type[2]}</p>
        </div>
        <span class="type-visual"><img src="/h5-static/assets/ui_v1/type/${type[5]}" alt=""></span>
        <span class="type-arrow">›</span>
      </button>`).join("")}
    </section>
  </section>`);
}

function pickPosterType(type) {
  draft.posterType = type;
  saveDraft();
  render();
}

function pickPosterTypeAndNext(type) {
  draft.posterType = type;
  draft.style = posterTypeStyleMap[type] || "premium_commercial";
  saveDraft();
  go("product");
}

function renderProduct() {
  ensureAuthRoute();
  layout(`${topbar("上传产品图")}${progress(1, "上传产品图")}
    ${uploadGrid("productImages", "product")}
    <section class="tips-card card">
      <b>上传建议</b>
      <div><span>1</span><p>主体清晰，尽量避免文字、水印和大面积遮挡。</p></div>
      <div><span>2</span><p>多角度图片会让模型更好理解产品结构。</p></div>
    </section>
    <button class="primary bottom-action" onclick="nextProduct()">下一步</button>`);
}

function renderReference() {
  ensureAuthRoute();
  layout(`${topbar("上传参考图")}${progress(2, "上传参考图")}
    <div class="page-title"><h1>添加参考素材</h1><p class="muted">背景、Logo、模板或品牌风格都可以，可跳过。</p></div>
    ${uploadGrid("referenceImages", "reference")}
    <div class="actions bottom-pair"><button class="ghost" onclick="go('copy')">跳过</button><button class="primary" onclick="go('copy')">下一步</button></div>`);
}

function uploadGrid(key, imageType) {
  const items = draft[key] || [];
  const labels = imageType === "product"
    ? ["主产品图 必填", "角度图 可选", "细节图 可选", "包装图 可选"]
    : ["背景参考 可选", "Logo 参考 可选", "模板参考 可选", "其他参考 可选"];
  const cells = [...items.map((item, index) => `<div class="slot has-image"><img src="${asset(item.image_url)}"><button onclick="removeImage('${key}',${index})">×</button><small>${labels[index] || "参考图"}</small></div>`)];
  if (items.length < 4) cells.push(`<label class="slot upload-slot"><input class="hidden-input" type="file" accept="image/*" multiple onchange="uploadFiles(event,'${key}','${imageType}')"><div><b>＋</b><strong>${labels[items.length]}</strong><span>点击上传</span></div></label>`);
  while (cells.length < 4) cells.push(`<div class="slot empty-slot"><div><strong>${labels[cells.length]}</strong><span>等待上传</span></div></div>`);
  return `<section class="upload-grid">${cells.join("")}</section>`;
}

async function uploadFiles(event, key, imageType) {
  const files = Array.from(event.target.files || []);
  for (const file of files) {
    if ((draft[key] || []).length >= 4) return toast("最多只能上传 4 张");
    try {
      const uploadFile = await compressImageForUpload(file);
      const form = new FormData();
      form.append("image_type", imageType);
      form.append("reference_type", imageType === "reference" ? (document.querySelector("#refType")?.value || "other") : "");
      form.append("file", uploadFile);
      const data = await request("/upload/image", { method: "POST", body: form });
      draft[key] = [...(draft[key] || []), data];
      saveDraft();
      toast("上传成功");
      render();
    } catch (e) { toast(e.message); }
  }
}

function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("图片读取失败，请换一张图片"));
    };
    image.src = url;
  });
}

async function compressImageForUpload(file) {
  if (!file.type.startsWith("image/")) throw new Error("请选择图片文件");
  if (file.size > uploadCompressOptions.maxRawSize) throw new Error("图片过大，请先压缩后重新上传");
  if (!window.HTMLCanvasElement) return file;
  const image = await loadImageFromFile(file);
  const scale = Math.min(1, uploadCompressOptions.maxSide / Math.max(image.naturalWidth, image.naturalHeight));
  const width = Math.max(1, Math.round(image.naturalWidth * scale));
  const height = Math.max(1, Math.round(image.naturalHeight * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(image, 0, 0, width, height);
  const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", uploadCompressOptions.quality));
  if (!blob) return file;
  const compressed = new File([blob], file.name.replace(/\.[^.]+$/, "") + ".jpg", { type: "image/jpeg" });
  return compressed.size < file.size || file.size > 2 * 1024 * 1024 ? compressed : file;
}

function removeImage(key, index) {
  draft[key].splice(index, 1);
  saveDraft();
  render();
}

function nextProduct() {
  if (!draft.productImages || draft.productImages.length < 1) return toast("请至少上传 1 张产品图");
  go("reference");
}

function renderCopy() {
  ensureAuthRoute();
  layout(`${topbar("填写文案")}${progress(3, "填写文案")}
    <section class="form-card card">
      <div class="field"><label>主标题</label><input id="title" maxlength="30" value="${draft.title || ""}" placeholder="可不填，例如：好水出好鱼"><small>可选 · 0/30</small></div>
      <div class="field"><label>副标题</label><input id="subtitle" maxlength="40" value="${draft.subtitle || ""}" placeholder="可不填，例如：来自密云水库的鲜活鱼"><small>可选 · 0/40</small></div>
      <div class="field"><label>卖点文案</label><textarea id="selling" maxlength="140" placeholder="可不填，AI 会根据产品图和模板自动发挥">${draft.selling_points || ""}</textarea><small>可选 · 0/140</small></div>
    </section>
    <div class="actions bottom-pair"><button class="ghost" onclick="go('reference')">上一步</button><button class="primary" onclick="saveCopy()">下一步</button></div>`);
}

function saveCopy() {
  draft.title = normalizeText(title.value);
  draft.subtitle = normalizeText(subtitle.value);
  draft.selling_points = normalizeText(selling.value);
  saveDraft();
  go("confirm");
}

function renderStyle() {
  ensureAuthRoute();
  const ratio = draft.ratio || "3:4";
  layout(`${topbar("选择风格")}${progress(4, "选择风格")}
    <div class="page-title"><h1>选择海报气质</h1><p class="muted">第一阶段提供 4 个基础风格。</p></div>
    <section class="grid-2">${styles.map((s, i) => `<button class="style-card card ${draft.style === s[0] ? "active" : ""}" onclick="pickStyle('${s[0]}')"><div class="style-thumb style-thumb-${i}"></div><b>${s[1]}</b><span>${s[2]}</span></button>`).join("")}</section>
    <h2>画幅比例</h2>
    <div class="segmented">${["1:1","3:4","4:5"].map(r => `<button class="${ratio === r ? "active" : ""}" onclick="pickRatio('${r}')">${r}</button>`).join("")}</div>
    <button class="primary bottom-action" onclick="go('confirm')">下一步</button>`);
}

function pickStyle(style) { draft.style = style; saveDraft(); render(); }
function pickRatio(ratio) { draft.ratio = ratio; saveDraft(); render(); }
function pickQuality(quality) { draft.imageQuality = quality; saveDraft(); render(); }
function updateRatio(value) { draft.ratio = value; saveDraft(); }
function updateQuality(value) { draft.imageQuality = value; saveDraft(); render(); }

function imageThumbStrip(images, emptyText) {
  const list = images || [];
  if (!list.length) return `<div class="confirm-empty">${emptyText}</div>`;
  return `<div class="confirm-thumbs">${list.map(item => `<img src="${asset(item.image_url)}" alt="">`).join("")}</div>`;
}

function confirmImageGrid() {
  const images = [...(draft.productImages || []), ...(draft.referenceImages || [])];
  return imageThumbStrip(images, "未上传图片");
}

function renderConfirm() {
  ensureAuthRoute();
  const style = styles.find(s => s[0] === draft.style)?.[1] || "高级商业广告";
  const ratio = draft.ratio || "9:16";
  const quality = draft.imageQuality || "high";
  const qualityMeta = qualityOptions.find(item => item[0] === quality) || qualityOptions[0];
  const taskError = draft.lastTaskError;
  layout(`${topbar("确认生成")}${progress(4, "确认生成")}
    ${taskError ? `<section class="task-error card"><b>生成失败</b><p>${escapeHtml(taskError.message || "生成失败，请稍后重试")}</p><button onclick="clearTaskError()">我知道了</button></section>` : ""}
    <section class="confirm-images card">${confirmImageGrid()}</section>
    <section class="panel card summary-list">
      <div><span>生成类型</span><b>${posterTypes.find(t => t[0] === draft.posterType)?.[1] || "产品宣传海报"}</b></div>
      <div><span>风格</span><b>${style}</b></div>
      <div><span>主标题</span><b>${draft.title || "AI 自动发挥"}</b></div>
      <div><span>副标题</span><b>${draft.subtitle || "AI 自动发挥"}</b></div>
      <div><span>卖点文案</span><b>${draft.selling_points || "AI 自动发挥"}</b></div>
    </section>
    <section class="confirm-options card">
      <label><span>比例</span><select onchange="updateRatio(this.value)">${ratios.map(r => `<option value="${r}" ${ratio === r ? "selected" : ""}>${r}</option>`).join("")}</select></label>
      <label><span>质量</span><select onchange="updateQuality(this.value)">${qualityOptions.map(q => `<option value="${q[0]}" ${quality === q[0] ? "selected" : ""}>${q[1]}</option>`).join("")}</select></label>
    </section>
    <section class="confirm-submit-row"><div class="confirm-cost"><span>★</span><b>${qualityMeta[2]}</b><em>积分</em></div><button class="primary" onclick="createTask()">确认生成</button></section>`);
}

async function createTask() {
  try {
    draft.lastTaskError = null;
    const data = await request("/poster/generate", {
      method: "POST",
      body: JSON.stringify({
        product_image_ids: (draft.productImages || []).map(i => i.image_id),
        reference_image_ids: (draft.referenceImages || []).map(i => i.image_id),
        title: normalizeText(draft.title),
        subtitle: normalizeText(draft.subtitle),
        selling_points: normalizeText(draft.selling_points),
        style: draft.style || "premium_commercial",
        poster_type: draft.posterType || "product",
        ratio: draft.ratio || "9:16",
        image_quality: draft.imageQuality || "high",
      }),
    });
    lastTask = data.task_id;
    draft.lastTask = data.task_id;
    saveDraft();
    go("waiting");
  } catch (e) { toast(e.message); }
}

function renderWaiting() {
  ensureAuthRoute();
  layout(`<section class="waiting">
    <div class="waiting-logo-progress" id="waitProgress">
      <div class="waiting-logo-core"><img src="/h5-static/assets/ui_v1/brand/logo.png" alt="图生意"></div>
    </div>
    <p class="waiting-progress-label"><span id="waitPercent">0%</span></p>
    <h1>正在生成海报</h1>
    <p class="muted" id="waitText">正在分析产品图</p>
    <p class="muted">可以关闭页面或切到后台，生成成功会进入作品库；如接口超时会自动失败并退还积分。</p>
    <button class="secondary soft-secondary" onclick="go('works')">先去作品库</button>
  </section>`, false);
  startWaitingProgress();
  pollTask(draft.lastTask);
}

function clearWaitingProgress() {
  if (waitingProgressTimer) clearInterval(waitingProgressTimer);
  waitingProgressTimer = null;
}

function startWaitingProgress() {
  clearWaitingProgress();
  const startedAt = Date.now();
  const expectedMs = 80 * 1000;
  const tick = () => {
    const progress = document.querySelector("#waitProgress");
    if (!progress || route !== "waiting") return clearWaitingProgress();
    const ratio = Math.min((Date.now() - startedAt) / expectedMs, 0.98);
    const percent = Math.round(ratio * 100);
    progress.style.setProperty("--progress", `${ratio * 360}deg`);
    const label = document.querySelector("#waitPercent");
    if (label) label.textContent = `${percent}%`;
  };
  tick();
  waitingProgressTimer = setInterval(tick, 500);
}

async function pollTask(taskId) {
  if (!taskId) {
    draft.lastTaskError = { message: "没有找到生成任务，请重新提交。" };
    saveDraft();
    toast("没有找到生成任务");
    return go("confirm");
  }
  const words = ["正在分析产品图", "正在理解宣传文案", "正在匹配海报风格", "正在生成海报", "正在优化画面细节"];
  let i = 0;
  const startedAt = Date.now();
  const maxWaitMs = 270 * 1000;
  const textTimer = setInterval(() => {
    const el = document.querySelector("#waitText");
    if (el) el.textContent = words[++i % words.length];
  }, 1400);
  const timer = setInterval(async () => {
    try {
      const task = await request(`/poster/task/${taskId}`);
      if (task.status === "success") {
        clearInterval(timer); clearInterval(textTimer);
        clearWaitingProgress();
        draft.lastTaskError = null;
        draft.currentTask = task; saveDraft(); go("result");
      }
      if (task.status === "failed") {
        clearInterval(timer); clearInterval(textTimer);
        clearWaitingProgress();
        draft.lastTaskError = { message: task.error_message || "生成失败，积分已退还", task_id: task.task_id };
        saveDraft();
        toast(draft.lastTaskError.message); go("confirm");
      }
      if (Date.now() - startedAt > maxWaitMs) {
        clearInterval(timer); clearInterval(textTimer);
        clearWaitingProgress();
        draft.lastTaskError = {
          message: "生成超时，请重新提交。若任务已扣积分，系统会自动退还。",
          task_id: task.task_id,
        };
        saveDraft();
        toast("生成超时，已返回确认页");
        go("confirm");
      }
    } catch (e) {
      clearInterval(timer); clearInterval(textTimer); clearWaitingProgress();
      draft.lastTaskError = { message: e.message, task_id: taskId };
      saveDraft();
      toast(e.message); go("confirm");
    }
  }, 1200);
}

function clearTaskError() {
  draft.lastTaskError = null;
  saveDraft();
  render();
}

function renderResult() {
  ensureAuthRoute();
  const task = draft.currentTask || {};
  layout(`${topbar("生成完成", `<button class="saved-badge">已保存</button>`)}
    <div class="page-title result-title"><h1>生成完成</h1><p class="muted">作品已自动保存到作品库。</p></div>
    <section class="result-frame">
      <img class="poster-preview" src="${asset(task.result_image_url)}" alt="生成海报">
      <span class="version-chip">V1 初次生成</span>
    </section>
    <div class="result-actions">
      <button class="primary" onclick="downloadImage('${task.result_image_url || ""}')">下载原图</button>
      <button class="secondary" onclick="go('edit')">继续修改</button>
    </div>
    <div class="result-links"><button onclick="go('confirm')">重新生成</button><button onclick="go('works')">作品库</button></div>`);
}

function downloadImage(url) {
  if (!url) return toast("图片还没有生成");
  window.open(url, "_blank");
}

async function saveWork(workId) {
  try {
    await request(`/works/${workId}/save`, { method: "POST" });
    toast("已保存到作品库");
  } catch (e) { toast(e.message); }
}

function renderEdit() {
  ensureAuthRoute();
  layout(`${topbar("二次修改")}
    <div class="page-title"><h1>继续优化海报</h1><p class="muted">修改后的图片和原图都会保留在作品库。</p></div>
    <section class="form-card card">
      <div class="field"><label>修改意见</label><textarea id="editText" placeholder="例如：背景换成黑金风格，产品放大，标题更醒目"></textarea></div>
      <div class="segmented" style="flex-wrap:wrap">${["产品更突出","背景更高级","标题更大","去掉文字","画面更简洁","色彩更明亮"].map(x => `<button onclick="editText.value+='${x}；'">${x}</button>`).join("")}</div>
    </section>
    <button class="primary bottom-action" onclick="modifyTask()">消耗 8 积分继续生成</button>`);
}

async function modifyTask() {
  const task = draft.currentTask || {};
  try {
    const data = await request("/poster/modify", {
      method: "POST",
      body: JSON.stringify({ work_id: task.work_id, version_id: task.version_id, edit_instruction: editText.value }),
    });
    draft.lastTask = data.task_id; saveDraft(); go("waiting");
  } catch (e) { toast(e.message); }
}

async function renderWorks() {
  ensureAuthRoute();
  try {
    const [data, active] = await Promise.all([request("/works"), request("/poster/tasks?status=active")]);
    const activeHtml = active.list.length ? `<section class="panel card"><b>生成中</b><p class="muted">有 ${active.list.length} 个任务正在后台处理，完成后会自动出现在这里。</p>${active.list.map(t => `<p>${t.status === "running" ? "生成中" : "排队中"} · ${t.points_cost} 积分</p>`).join("")}</section>` : "";
    layout(`${topbar("作品库")}
      ${activeHtml}
      ${data.list.length ? data.list.map(w => `<article class="work-item card" onclick="openWork('${w.work_id}','${w.version_id || ""}')"><img src="${asset(w.cover_url)}"><div><b>${w.title}</b><p class="muted">V${w.version_no || w.latest_version} · ${w.edit_instruction || "初次生成"}</p><p class="muted">${new Date(w.created_at || w.updated_at).toLocaleString()}</p></div></article>`).join("") : `<section class="panel card" style="text-align:center"><h2>还没有作品</h2><p class="muted">上传一张产品图，生成你的第一张 AI 海报</p><button class="primary" onclick="startFlow()">立即生成</button></section>`}`);
  } catch (e) { toast(e.message); }
}

async function renderPlaza() {
  try {
    const data = await request("/works/plaza");
    layout(`${topbar("作品广场")}
      <div class="plaza-title"><h1>热门作品</h1><p>看看大家正在生成的高质量营销图。</p></div>
      ${data.list.length ? `<section class="masonry-grid">${data.list.map(w => workFeedCard(w, { context: "plaza" })).join("")}</section>` : `<section class="panel card" style="text-align:center"><h2>还没有公开作品</h2><p class="muted">生成成功的作品会自动进入作品库，后续可在这里展示。</p><button class="primary" onclick="startFlow()">立即生成</button></section>`}`);
  } catch (e) { toast(e.message); }
}

async function renderLikedWorks() {
  ensureAuthRoute();
  try {
    const data = await request("/works/liked");
    layout(`${topbar("我的喜欢")}
      <div class="plaza-title"><h1>我的喜欢</h1><p>这里保存你在作品广场点过赞的灵感图。</p></div>
      ${data.list.length ? `<section class="masonry-grid">${data.list.map(w => workFeedCard(w, { context: "plaza" })).join("")}</section>` : `<section class="panel card" style="text-align:center"><h2>还没有喜欢的作品</h2><p class="muted">去作品广场给喜欢的海报点个赞，这里会自动收集。</p><button class="primary" onclick="go('plaza')">去作品广场</button></section>`}`);
  } catch (e) { toast(e.message); }
}

async function likePlaza(event, versionId) {
  event.stopPropagation();
  if (!token()) {
    draft.afterLogin = "plaza";
    saveDraft();
    go("auth");
    return;
  }
  try {
    const data = await request(`/works/versions/${versionId}/like`, { method: "POST" });
    const button = document.querySelector(`#like_${versionId}`);
    if (button) {
      button.classList.toggle("liked", data.liked_by_me);
      const count = button.querySelector("b");
      if (count) count.textContent = data.likes_count;
    }
    toast(data.liked_by_me ? "已点赞" : "点赞成功");
  } catch (e) { toast(e.message); }
}

function openWork(workId, versionId = "") {
  draft.openWorkId = workId;
  draft.openVersionId = versionId;
  saveDraft();
  go("work");
}

async function renderWorkDetail() {
  ensureAuthRoute();
  try {
    const work = await request(`/works/${draft.openWorkId}`);
    const selected = work.versions.find(v => v.version_id === draft.openVersionId) || work.versions[work.versions.length - 1];
    draft.currentTask = { work_id: work.work_id, version_id: selected.version_id, result_image_url: selected.image_url };
    saveDraft();
    layout(`${topbar("作品详情")}
      <section class="result-frame">
        <img class="poster-preview" src="${asset(selected.image_url)}" alt="作品海报">
        <span class="version-chip">V${selected.version_no} 当前版本</span>
      </section>
      <div class="result-actions">
        <button class="primary" onclick="downloadImage('${selected.image_url || ""}')">下载原图</button>
        <button class="secondary" onclick="go('edit')">继续修改</button>
      </div>
      <section class="panel card work-version-panel">
        <b>${work.title}</b>
        <p class="muted">当前查看 V${selected.version_no}，共 ${work.versions.length} 个版本</p>
        <button class="version-toggle" onclick="toggleVersionInfo()">展开版本信息</button>
        <div class="version-list hidden" id="versionList">${work.versions.map(v => `<p>V${v.version_no} ${v.edit_instruction || "初次生成"}</p>`).join("")}</div>
      </section>`);
  } catch (e) { toast(e.message); go("works"); }
}

function toggleVersionInfo() {
  const list = document.querySelector("#versionList");
  const button = document.querySelector(".version-toggle");
  if (!list || !button) return;
  const isHidden = list.classList.toggle("hidden");
  button.textContent = isHidden ? "展开版本信息" : "收起版本信息";
}

async function renderPoints() {
  ensureAuthRoute();
  try {
    const data = await request("/points/records");
    layout(`${topbar("积分中心")}
      <section class="points-hero"><p>当前积分</p><h1>${data.balance}</h1><span>POINTS</span></section>
      <h2>积分明细</h2>
      ${data.records.map(r => `<article class="record-item card"><div><b>${r.scene}</b><p class="muted">${new Date(r.created_at).toLocaleString()}</p></div><span class="${r.amount > 0 ? "amount-pos" : "amount-neg"}">${r.amount > 0 ? "+" : ""}${r.amount}</span></article>`).join("")}`);
  } catch (e) { toast(e.message); }
}

async function renderMine() {
  ensureAuthRoute();
  try {
    const [user, liked] = await Promise.all([request("/user/profile"), request("/works/liked")]);
    layout(`
      <section class="profile-card">
        <div class="avatar">${user.username.slice(0, 1).toUpperCase()}</div>
        <div><h1>${user.username}</h1><p>普通用户 · 当前积分 ${user.points_balance}</p></div>
      </section>
      <section class="mine-stats">
        <button class="stat-card card" onclick="go('works')"><b>我的作品</b><span>查看全部版本</span></button>
        <button class="stat-card card" onclick="go('likes')"><b>我的喜欢</b><span>已喜欢 ${(liked.list || []).length} 个作品</span></button>
      </section>
      <section class="menu-card card">
        <button onclick="go('works')"><span>▣</span>作品库</button>
        <button onclick="go('likes')"><span>♥</span>我的喜欢</button>
        <button onclick="go('points')"><span>◎</span>积分使用情况</button>
        <button onclick="toast('会员功能将在后续版本开放')"><span>◇</span>会员中心</button>
        <button onclick="toast('客服功能将在后续版本开放')"><span>?</span>联系客服</button>
      </section>
      <button class="logout-bottom" onclick="logout()">退出登录</button>`);
  } catch (e) { toast(e.message); }
}

function logout() {
  localStorage.removeItem(tokenKey);
  toast("已退出登录");
  go("home");
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function ensureAuthRoute() {
  if (!token()) go("auth");
}

window.addEventListener("hashchange", () => {
  route = location.hash.replace("#", "") || "home";
  render();
});
render();
