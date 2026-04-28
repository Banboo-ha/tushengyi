const api = "/api/h5";
const tokenKey = "haibao_h5_token";
const stateKey = "haibao_h5_draft";
const app = document.querySelector("#app");
const toastEl = document.querySelector("#toast");

let draft = JSON.parse(localStorage.getItem(stateKey) || "{}");
let route = location.hash.replace("#", "") || "home";
let lastTask = null;

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
  toastEl.textContent = message;
  toastEl.classList.add("show");
  setTimeout(() => toastEl.classList.remove("show"), 2400);
}
function asset(url) { return url || ""; }
function authHeaders() { return token() ? { Authorization: `Bearer ${token()}` } : {}; }

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}), ...authHeaders() };
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const res = await fetch(api + path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "请求失败");
  return data;
}

function layout(content, nav = true) {
  app.className = `app-shell route-${route}`;
  app.innerHTML = content + (nav ? bottomNav() : "");
}

function topbar(title, right = "") {
  return `<div class="topbar"><button class="back" onclick="historyBack()">‹</button><strong>${title}</strong><div class="topbar-right">${right}</div></div>`;
}

function historyBack() {
  const map = { type: "home", product: "type", reference: "product", copy: "reference", style: "copy", confirm: "style", result: "home", edit: "result" };
  go(map[route] || "home");
}

function progress(step, label) {
  return `<div class="step-head">
    <div class="step-count">${step}/5 ${label}</div>
    <div class="step-bars">${[1,2,3,4,5].map(i => `<span class="${i <= step ? "active" : ""}"></span>`).join("")}</div>
  </div>`;
}

function bottomNav() {
  const createActive = ["type","product","reference","copy","style","confirm","waiting","result","edit"].includes(route);
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
    draft = { productImages: [], referenceImages: [], ratio: "3:4", style: "premium_commercial", posterType: "product" };
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
  if (route === "style") return renderStyle();
  if (route === "confirm") return renderConfirm();
  if (route === "waiting") return renderWaiting();
  if (route === "result") return renderResult();
  if (route === "edit") return renderEdit();
  if (route === "plaza") return renderPlaza();
  if (route === "works") return renderWorks();
  if (route === "work") return renderWorkDetail();
  if (route === "points") return renderPoints();
  if (route === "mine") return renderMine();
  return renderHome();
}

async function renderHome() {
  let points = "120";
  if (token()) {
    try { points = (await request("/user/profile")).points_balance; } catch { localStorage.removeItem(tokenKey); }
  }
  layout(`
    <div class="home-head">
      <div class="brand-row"><img class="home-brand-logo" src="/h5-static/assets/ui_v1/brand/logo_t.png" alt="图生意"></div>
      <div class="head-pills">
        <button class="pill points-pill" onclick="needLogin(()=>go('points'))"><span>★</span>积分 ${points}</button>
        <button class="pill muted-pill" onclick="toast('会员功能将在后续版本开放')"><span>♛</span>会员</button>
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
    <section class="home-work-grid">${homeStyles.map(s => `<button class="home-work-card" onclick="go('plaza')"><img src="/h5-static/assets/ui_v1/home/${s[3]}" alt="${s[1]}"></button>`).join("")}</section>
  `);
}

function pickPosterTypeFromHome(type) {
  needLogin(() => {
    draft = { productImages: [], referenceImages: [], ratio: "3:4", style: "premium_commercial", posterType: type };
    saveDraft();
    go("product");
  });
}

function pickStyleFromHome(style) {
  needLogin(() => {
    draft = { productImages: [], referenceImages: [], ratio: "3:4", style, posterType: "product" };
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
    <button class="type-back" onclick="historyBack()">‹</button>
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
    <p class="type-tip">后续可在生成页修改比例与风格</p>
  </section>`, false);
}

function pickPosterType(type) {
  draft.posterType = type;
  saveDraft();
  render();
}

function pickPosterTypeAndNext(type) {
  draft.posterType = type;
  saveDraft();
  go("product");
}

function renderProduct() {
  ensureAuthRoute();
  layout(`${topbar("上传产品图")}${progress(1, "上传产品图")}
    <div class="page-title"><h1>上传你的产品图</h1><p class="muted">产品图必填 1-4 张，建议包含主图、细节图、包装图。</p></div>
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
    <div class="field"><label>参考类型</label><select id="refType"><option value="background">背景参考</option><option value="logo">Logo 参考</option><option value="style">品牌风格</option><option value="layout">排版模板</option><option value="color">色彩参考</option><option value="other">其他</option></select></div>
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
    const form = new FormData();
    form.append("image_type", imageType);
    form.append("reference_type", imageType === "reference" ? (document.querySelector("#refType")?.value || "other") : "");
    form.append("file", file);
    try {
      const data = await request("/upload/image", { method: "POST", body: form });
      draft[key] = [...(draft[key] || []), data];
      saveDraft();
      toast("上传成功");
      render();
    } catch (e) { toast(e.message); }
  }
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
    <div class="page-title"><h1>告诉 AI 你想宣传什么</h1><p class="muted">主标题必填，文案越清楚，画面越稳定。</p></div>
    <section class="form-card card">
      <div class="field"><label>主标题 <em>*</em></label><input id="title" maxlength="30" value="${draft.title || ""}" placeholder="例如：好水出好鱼"><small>0/30</small></div>
      <div class="field"><label>副标题</label><input id="subtitle" maxlength="40" value="${draft.subtitle || ""}" placeholder="例如：来自密云水库的鲜活鱼"><small>0/40</small></div>
      <div class="field"><label>卖点文案</label><textarea id="selling" maxlength="140" placeholder="输入 1-3 个核心卖点">${draft.selling_points || ""}</textarea><small>0/140</small></div>
    </section>
    <div class="actions bottom-pair"><button class="ghost" onclick="go('reference')">上一步</button><button class="primary" onclick="saveCopy()">下一步</button></div>`);
}

function saveCopy() {
  if (!title.value.trim()) return toast("请填写主标题");
  draft.title = title.value.trim();
  draft.subtitle = subtitle.value.trim();
  draft.selling_points = selling.value.trim();
  saveDraft();
  go("style");
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

function renderConfirm() {
  ensureAuthRoute();
  const style = styles.find(s => s[0] === draft.style)?.[1] || "高级商业广告";
  layout(`${topbar("确认生成")}${progress(5, "确认生成")}
    <div class="page-title"><h1>确认生成内容</h1><p class="muted">确认无误后开始消耗积分生成。</p></div>
    <section class="preview-row">
      <div class="mini-preview card"><b>产品图</b><span>${(draft.productImages || []).length} 张</span></div>
      <div class="mini-preview card"><b>参考图</b><span>${(draft.referenceImages || []).length} 张</span></div>
    </section>
    <section class="panel card summary-list">
      <div><span>生成类型</span><b>${posterTypes.find(t => t[0] === draft.posterType)?.[1] || "产品宣传海报"}</b></div>
      <div><span>主标题</span><b>${draft.title || "-"}</b></div>
      <div><span>风格</span><b>${style}</b></div>
      <div><span>比例</span><b>${draft.ratio || "3:4"}</b></div>
    </section>
    <section class="ai-note card"><span>AI</span><p>将基于你的产品图、参考图和文案生成海报，生成成功后会自动保存到作品库。</p></section>
    <section class="points-card"><span>预计消耗</span><b>10 积分</b></section>
    <button class="primary bottom-action" onclick="createTask()">确认生成</button>`);
}

async function createTask() {
  try {
    const data = await request("/poster/generate", {
      method: "POST",
      body: JSON.stringify({
        product_image_ids: (draft.productImages || []).map(i => i.image_id),
        reference_image_ids: (draft.referenceImages || []).map(i => i.image_id),
        title: draft.title,
        subtitle: draft.subtitle || "",
        selling_points: draft.selling_points || "",
        style: draft.style || "premium_commercial",
        ratio: draft.ratio || "3:4",
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
    <div class="waiting-orbit"><span></span><span></span><span></span><div>AI</div></div>
    <h1>正在生成海报</h1>
    <p class="muted" id="waitText">正在分析产品图</p>
    <p class="muted">可以关闭页面或切到后台，生成成功后会自动出现在作品库。</p>
    <button class="secondary soft-secondary" onclick="go('works')">先去作品库</button>
  </section>`, false);
  pollTask(draft.lastTask);
}

async function pollTask(taskId) {
  const words = ["正在分析产品图", "正在理解宣传文案", "正在匹配海报风格", "正在生成海报", "正在优化画面细节"];
  let i = 0;
  const textTimer = setInterval(() => {
    const el = document.querySelector("#waitText");
    if (el) el.textContent = words[++i % words.length];
  }, 1400);
  const timer = setInterval(async () => {
    try {
      const task = await request(`/poster/task/${taskId}`);
      if (task.status === "success") {
        clearInterval(timer); clearInterval(textTimer);
        draft.currentTask = task; saveDraft(); go("result");
      }
      if (task.status === "failed") {
        clearInterval(timer); clearInterval(textTimer);
        toast(task.error_message || "生成失败，积分已退还"); go("confirm");
      }
    } catch (e) {
      clearInterval(timer); clearInterval(textTimer); toast(e.message); go("home");
    }
  }, 1200);
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
    <button class="primary" onclick="downloadImage('${task.result_image_url || ""}')">下载高清图</button>
    <button class="secondary soft-secondary" onclick="go('edit')">继续修改</button>
    <div class="actions"><button class="ghost" onclick="go('confirm')">重新生成</button><button class="ghost" onclick="go('works')">作品库</button></div>`);
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
      ${data.list.length ? `<section class="masonry-grid">${data.list.map((w, index) => `<article class="plaza-card card" onclick="downloadImage('${asset(w.cover_url)}')">
        <img src="${asset(w.cover_url)}" alt="">
        <div><b>${w.title || "AI 营销海报"}</b><span>V${w.version_no || w.latest_version} · ${index % 3 === 0 ? "精选" : "热门"}</span></div>
      </article>`).join("")}</section>` : `<section class="panel card" style="text-align:center"><h2>还没有公开作品</h2><p class="muted">生成成功的作品会自动进入作品库，后续可在这里展示。</p><button class="primary" onclick="startFlow()">立即生成</button></section>`}`);
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
      <img class="poster-preview" src="${asset(selected.image_url)}">
      <section class="panel card"><b>${work.title}</b><p class="muted">当前查看 V${selected.version_no}，共 ${work.versions.length} 个版本</p>${work.versions.map(v => `<p>V${v.version_no} ${v.edit_instruction || "初次生成"}</p>`).join("")}</section>
      <button class="secondary" onclick="go('edit')">继续修改</button>`);
  } catch (e) { toast(e.message); go("works"); }
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
    const user = await request("/user/profile");
    layout(`${topbar("我的", `<button class="icon-btn" onclick="logout()">⎋</button>`)}
      <section class="profile-card">
        <div class="avatar">${user.username.slice(0, 1).toUpperCase()}</div>
        <div><h1>${user.username}</h1><p>普通用户 · 当前积分 ${user.points_balance}</p></div>
        <span class="member-tag">会员</span>
      </section>
      <section class="mine-stats">
        <button class="stat-card card" onclick="go('works')"><b>我的作品</b><span>查看全部版本</span></button>
        <button class="stat-card card" onclick="go('points')"><b>${user.points_balance}</b><span>积分余额</span></button>
      </section>
      <section class="menu-card card">
        <button onclick="go('works')"><span>▣</span>作品库</button>
        <button onclick="go('points')"><span>◎</span>积分使用情况</button>
        <button onclick="toast('会员功能将在后续版本开放')"><span>◇</span>会员中心</button>
        <button onclick="toast('客服功能将在后续版本开放')"><span>?</span>联系客服</button>
      </section>`);
  } catch (e) { toast(e.message); }
}

function logout() {
  localStorage.removeItem(tokenKey);
  toast("已退出登录");
  go("home");
}

function ensureAuthRoute() {
  if (!token()) go("auth");
}

window.addEventListener("hashchange", () => {
  route = location.hash.replace("#", "") || "home";
  render();
});
render();
