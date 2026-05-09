const { login } = require("./utils/api");

App({
  globalData: {
    apiBase: "http://127.0.0.1:8000/api/mp",
    assetBase: "http://127.0.0.1:8000",
    token: "",
    user: null
  },
  onLaunch() {
    const token = wx.getStorageSync("token");
    if (token) this.globalData.token = token;
    login().catch(() => {});
  }
});
