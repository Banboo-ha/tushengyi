const api = "/api/admin";
const tokenKey = "haibao_admin_token";
const app = document.querySelector("#app");
const toastEl = document.querySelector("#toast");
let page = location.hash.replace("#", "") || "users";
let cache = {};

function token() { return localStorage.getItem(tokenKey); }
function toast(message) {
  toastEl.textContent = message;
  toastEl.classList.add("show");
  setTimeout(() => toastEl.classList.remove("show"), 2400);
}
function authHeaders() { return token() ? { Authorization: `Bearer ${token()}` } : {}; }
async function request(path, options = {}) {
  const headers = { ...(options.headers || {}), ...authHeaders() };
  if (options.body) headers["Content-Type"] = "application/json";
  const res = await fetch(api + path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "请求失败");
  return data;
}
function go(name) { page = name; location.hash = name; render(); }

function layout(content) {
  app.innerHTML = `<div class="shell">
    <aside class="side">
      <div class="brand">海报快生 Admin</div>
      ${["users:用户管理", "tasks:生成任务", "works:作品管理", "points:积分流水", "settings:系统设置"].map(item => {
        const [key, label] = item.split(":");
        return `<button class="${page === key ? "active" : ""}" onclick="go('${key}')">${label}</button>`;
      }).join("")}
      <button onclick="logout()">退出登录</button>
    </aside>
    <main class="main">${content}</main>
  </div>`;
}

function renderLogin() {
  app.innerHTML = `<section class="login">
    <h1>管理后台</h1>
    <p>默认账号：admin / admin123</p>
    <div class="field"><label>账号</label><input id="username" value="admin"></div>
    <div class="field"><label>密码</label><input id="password" type="password" value="admin123"></div>
    <button style="width:100%" onclick="login()">登录</button>
  </section>`;
}

async function login() {
  try {
    const data = await request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: username.value, password: password.value }),
    });
    localStorage.setItem(tokenKey, data.token);
    toast("登录成功");
    render();
  } catch (e) { toast(e.message); }
}

function logout() {
  localStorage.removeItem(tokenKey);
  renderLogin();
}

async function render() {
  if (!token()) return renderLogin();
  try {
    if (page === "tasks") return renderTasks();
    if (page === "works") return renderWorks();
    if (page === "points") return renderPoints();
    if (page === "settings") return renderSettings();
    return renderUsers();
  } catch (e) {
    toast(e.message);
    if (String(e.message).includes("登录")) logout();
  }
}

function pageHeader(title, action = "") {
  return `<div class="top"><div><h1>${title}</h1><p>H5 用户端与管理端完全独立</p></div><div>${action}</div></div>`;
}

async function renderUsers() {
  const data = await request("/users");
  cache.users = data.list;
  layout(`${pageHeader("用户管理", `<button onclick="renderUsers()">刷新</button>`)}
    <section class="cards">
      <div class="card"><span>用户数</span><b>${data.list.length}</b></div>
      <div class="card"><span>总积分余额</span><b>${data.list.reduce((n, u) => n + u.points_balance, 0)}</b></div>
      <div class="card"><span>正常用户</span><b>${data.list.filter(u => u.status === "normal").length}</b></div>
      <div class="card"><span>禁用用户</span><b>${data.list.filter(u => u.status !== "normal").length}</b></div>
    </section>
    <section class="table-wrap"><table><thead><tr><th>用户</th><th>积分</th><th>状态</th><th>注册时间</th><th>生成次数</th><th>操作</th></tr></thead><tbody>
      ${data.list.map(u => `<tr><td>${u.username}<br><small>${u.user_id}</small></td><td>${u.points_balance}</td><td><span class="status">${u.status}</span></td><td>${format(u.created_at)}</td><td>${u.generate_count}</td><td><button class="secondary" onclick="addPoints('${u.user_id}')">补积分</button> <button class="danger" onclick="disableUser('${u.user_id}')">禁用</button></td></tr>`).join("")}
    </tbody></table></section>`);
}

async function addPoints(userId) {
  const amount = Number(prompt("补发积分数量", "50"));
  if (!amount) return;
  try {
    await request(`/users/${userId}/points`, { method: "POST", body: JSON.stringify({ amount, reason: "管理员补发" }) });
    toast("积分已补发");
    renderUsers();
  } catch (e) { toast(e.message); }
}

async function disableUser(userId) {
  if (!confirm("确认禁用该用户？")) return;
  try {
    await request(`/users/${userId}/disable`, { method: "POST" });
    toast("用户已禁用");
    renderUsers();
  } catch (e) { toast(e.message); }
}

async function renderTasks() {
  const data = await request("/tasks");
  layout(`${pageHeader("生成任务", `<button onclick="renderTasks()">刷新</button>`)}
    <section class="table-wrap"><table><thead><tr><th>任务</th><th>状态</th><th>标题</th><th>积分</th><th>结果</th><th>失败原因</th><th>时间</th></tr></thead><tbody>
      ${data.list.map(t => `<tr><td>${t.task_type}<br><small>${t.task_id}</small></td><td><span class="status">${t.status}</span></td><td>${t.title || "-"}</td><td>${t.points_cost}</td><td>${t.result_image_url ? `<img class="thumb" src="${t.result_image_url}">` : "-"}</td><td class="danger-text">${t.error_message || ""}</td><td>${format(t.created_at)}</td></tr>`).join("")}
    </tbody></table></section>`);
}

async function renderWorks() {
  const data = await request("/works");
  layout(`${pageHeader("作品管理", `<button onclick="renderWorks()">刷新</button>`)}
    <section class="table-wrap"><table><thead><tr><th>作品</th><th>封面</th><th>版本</th><th>保存</th><th>删除</th><th>操作</th></tr></thead><tbody>
      ${data.list.map(w => `<tr><td>${w.title}<br><small>${w.work_id}</small></td><td>${w.cover_url ? `<img class="thumb" src="${w.cover_url}">` : "-"}</td><td>V${w.latest_version}</td><td>${w.is_saved ? "是" : "否"}</td><td>${w.is_deleted ? "是" : "否"}</td><td><button class="danger" onclick="deleteWork('${w.work_id}')">软删除</button></td></tr>`).join("")}
    </tbody></table></section>`);
}

async function deleteWork(workId) {
  if (!confirm("确认软删除该作品？")) return;
  try {
    await request(`/works/${workId}/delete`, { method: "POST" });
    toast("已软删除");
    renderWorks();
  } catch (e) { toast(e.message); }
}

async function renderPoints() {
  const data = await request("/points/records");
  layout(`${pageHeader("积分流水", `<button onclick="renderPoints()">刷新</button>`)}
    <section class="table-wrap"><table><thead><tr><th>用户</th><th>类型</th><th>变动</th><th>场景</th><th>关联</th><th>时间</th></tr></thead><tbody>
      ${data.records.map(r => `<tr><td>${r.user_id}</td><td>${r.type}</td><td class="${r.amount > 0 ? "ok-text" : "danger-text"}">${r.amount > 0 ? "+" : ""}${r.amount}</td><td>${r.scene}</td><td>${r.related_id || "-"}</td><td>${format(r.created_at)}</td></tr>`).join("")}
    </tbody></table></section>`);
}

async function renderSettings() {
  const s = await request("/settings");
  layout(`${pageHeader("系统设置")}
    <section class="card settings">
      <div class="wide section-title"><h2>图片模型</h2><p>H5 生成海报实际调用这里。502 多数来自接口类型、模型名、尺寸或上游服务错误。</p></div>
      ${field("image_base_url", "图片 Base URL", s.image_base_url || s.model_base_url, "wide")}
      ${field("image_api_key", "图片 API Key", s.image_api_key || s.model_api_key, "wide", "password")}
      ${field("image_model_name", "图片模型名称", s.image_model_name || s.model_name)}
      <div class="field"><label>图片接口类型</label><select id="image_api_type">
        <option value="images_edits" ${s.image_api_type === "images_edits" ? "selected" : ""}>Images Edits: /images/edits（图生图，推荐）</option>
        <option value="images_generations" ${s.image_api_type === "images_generations" ? "selected" : ""}>Images: /images/generations</option>
        <option value="responses" ${s.image_api_type === "responses" ? "selected" : ""}>Responses: /responses + image_generation</option>
      </select></div>
      <div class="field"><label>图片尺寸策略</label><select id="image_size_mode">
        <option value="ratio_standard" ${s.image_size_mode === "ratio_standard" ? "selected" : ""}>按比例映射 OpenAI 标准尺寸</option>
        <option value="auto" ${s.image_size_mode === "auto" ? "selected" : ""}>auto</option>
        <option value="1024x1024" ${s.image_size_mode === "1024x1024" ? "selected" : ""}>1024x1024</option>
        <option value="1024x1536" ${s.image_size_mode === "1024x1536" ? "selected" : ""}>1024x1536</option>
        <option value="1536x1024" ${s.image_size_mode === "1536x1024" ? "selected" : ""}>1536x1024</option>
      </select></div>
      ${field("image_file_field", "图生图文件字段名", s.image_file_field || "image")}
      ${field("image_response_format", "图片 response_format（可空）", s.image_response_format)}
      ${field("image_quality", "图片 quality（可空）", s.image_quality)}
      <div class="field wide"><button class="secondary" onclick="testModel('image')">测试真实图片接口</button></div>

      <div class="wide section-title"><h2>对话模型</h2><p>用于后续 AI 文案辅助、Prompt 优化等文本任务；不直接生成海报图片。</p></div>
      ${field("chat_base_url", "对话 Base URL", s.chat_base_url || s.model_base_url, "wide")}
      ${field("chat_api_key", "对话 API Key", s.chat_api_key || s.model_api_key, "wide", "password")}
      ${field("chat_model_name", "对话模型名称", s.chat_model_name)}
      <div class="field"><label>对话接口类型</label><select id="chat_api_type">
        <option value="chat_completions" ${s.chat_api_type === "chat_completions" ? "selected" : ""}>Chat Completions: /chat/completions</option>
        <option value="responses" ${s.chat_api_type === "responses" ? "selected" : ""}>Responses: /responses</option>
      </select></div>
      <div class="field"><label>Mock 模式</label><select id="mock_mode"><option value="true" ${s.mock_mode === "true" ? "selected" : ""}>开启，H5 不调用真实图片接口</option><option value="false" ${s.mock_mode === "false" ? "selected" : ""}>关闭，H5 调用真实图片接口</option></select></div>
      <div class="field wide"><button class="secondary" onclick="testModel('chat')">测试对话接口</button></div>

      <div class="wide section-title"><h2>积分规则</h2></div>
      ${field("signup_points", "注册赠送积分", s.signup_points)}
      ${field("generate_cost", "生成消耗积分", s.generate_cost)}
      ${field("modify_cost", "修改消耗积分", s.modify_cost)}
      <div class="field wide"><button onclick="saveSettings()">保存设置</button></div>
    </section>`);
  renderSpecs(s.model_specs || []);
}

function field(id, label, value, cls = "", type = "text") {
  return `<div class="field ${cls}"><label>${label}</label><input id="${id}" type="${type}" value="${String(value || "").replaceAll('"', "&quot;")}"></div>`;
}

async function saveSettings() {
  const payload = {
    model_base_url: image_base_url.value,
    model_api_key: image_api_key.value,
    model_name: image_model_name.value,
    image_base_url: image_base_url.value,
    image_api_key: image_api_key.value,
    image_model_name: image_model_name.value,
    image_api_type: image_api_type.value,
    image_size_mode: image_size_mode.value,
    image_file_field: image_file_field.value,
    image_response_format: image_response_format.value,
    image_quality: image_quality.value,
    chat_base_url: chat_base_url.value,
    chat_api_key: chat_api_key.value,
    chat_model_name: chat_model_name.value,
    chat_api_type: chat_api_type.value,
    mock_mode: mock_mode.value,
    signup_points: Number(signup_points.value),
    generate_cost: Number(generate_cost.value),
    modify_cost: Number(modify_cost.value),
  };
  try {
    await request("/settings", { method: "PUT", body: JSON.stringify(payload) });
    toast("设置已保存");
  } catch (e) { toast(e.message); }
}

async function testModel(target) {
  const label = target === "image" ? "图片" : "对话";
  if (target === "image" && !confirm("测试真实图片接口会调用上游模型服务，可能产生一次图片生成费用。确认测试？")) return;
  try {
    await saveSettings();
    const data = await request("/settings/test", { method: "POST", body: JSON.stringify({ target }) });
    const result = document.querySelector("#testResult");
    if (result) {
      result.innerHTML = `<b>${label}接口测试成功</b><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>${data.image_url ? `<img class="test-image" src="${data.image_url}">` : ""}`;
    }
    toast(`${label}接口测试成功`);
  } catch (e) {
    const result = document.querySelector("#testResult");
    if (result) result.innerHTML = `<b class="danger-text">${label}接口测试失败</b><pre>${escapeHtml(e.message)}</pre>`;
    toast(e.message);
  }
}

function renderSpecs(specs) {
  const main = document.querySelector(".main");
  if (!main) return;
  main.insertAdjacentHTML("beforeend", `
    <section class="card spec-wrap">
      <h2>OpenAI 兼容接口规范</h2>
      <div class="spec-grid">${specs.map(spec => `<article class="spec">
        <b>${spec.title}</b>
        <code>${spec.endpoint}</code>
        <p>${spec.note}</p>
        <small>请求示例</small><pre>${escapeHtml(spec.request)}</pre>
        <small>响应读取</small><pre>${escapeHtml(spec.response)}</pre>
      </article>`).join("")}</div>
      <div id="testResult" class="test-result"></div>
    </section>
  `);
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function format(value) {
  return value ? new Date(value).toLocaleString() : "-";
}

window.addEventListener("hashchange", () => {
  page = location.hash.replace("#", "") || "users";
  render();
});
render();
