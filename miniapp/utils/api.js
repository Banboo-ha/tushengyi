function appRef() {
  return getApp();
}

function asset(url) {
  if (!url) return "";
  if (/^https?:\/\//.test(url)) return url;
  return appRef().globalData.assetBase + url;
}

function request(path, options = {}) {
  const app = appRef();
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.apiBase + path,
      method: options.method || "GET",
      data: options.data || {},
      header: {
        "content-type": "application/json",
        ...(app.globalData.token ? { Authorization: `Bearer ${app.globalData.token}` } : {}),
        ...(options.header || {})
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) return resolve(res.data);
        const detail = res.data && (res.data.detail || res.data.message);
        reject(new Error(typeof detail === "string" ? detail : JSON.stringify(detail || res.data || "请求失败")));
      },
      fail(err) {
        reject(new Error(err.errMsg || "网络请求失败"));
      }
    });
  });
}

function login() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: ({ code }) => {
        request("/auth/login", { method: "POST", data: { code } })
          .then(data => {
            appRef().globalData.token = data.token;
            appRef().globalData.user = data;
            wx.setStorageSync("token", data.token);
            resolve(data);
          })
          .catch(reject);
      },
      fail: reject
    });
  });
}

async function ensureLogin() {
  if (appRef().globalData.token || wx.getStorageSync("token")) {
    appRef().globalData.token = appRef().globalData.token || wx.getStorageSync("token");
    return appRef().globalData.token;
  }
  const data = await login();
  return data.token;
}

function uploadImage(filePath, imageType, referenceType = "") {
  const app = appRef();
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: app.globalData.apiBase + "/upload/image",
      filePath,
      name: "file",
      formData: { image_type: imageType, reference_type: referenceType },
      header: app.globalData.token ? { Authorization: `Bearer ${app.globalData.token}` } : {},
      success(res) {
        let data = {};
        try { data = JSON.parse(res.data || "{}"); } catch (e) {}
        if (res.statusCode >= 200 && res.statusCode < 300) return resolve(data);
        reject(new Error(data.detail || "上传失败"));
      },
      fail: err => reject(new Error(err.errMsg || "上传失败"))
    });
  });
}

function toast(message) {
  wx.showToast({ title: String(message || "请求失败").slice(0, 28), icon: "none" });
}

module.exports = { asset, request, login, ensureLogin, uploadImage, toast };
