const { asset, request, ensureLogin, toast } = require("../../utils/api");

function shortDate(value) {
  if (!value) return "";
  return String(value).slice(5, 10).replace("-", ".");
}

Page({
  data: { works: [], loading: true },
  onShow() { this.load(); },
  async load() {
    this.setData({ loading: true });
    try {
      await ensureLogin();
      const data = await request("/works");
      this.setData({
        works: (data.list || []).map(item => ({
          ...item,
          cover: asset(item.cover_url),
          created_at_text: shortDate(item.created_at)
        })),
        loading: false
      });
    } catch (e) {
      this.setData({ loading: false });
      toast(e.message);
    }
  },
  openWork(event) {
    const item = event.currentTarget.dataset.item;
    wx.navigateTo({ url: `/pages/work-detail/work-detail?work_id=${item.work_id}&version_id=${item.version_id}` });
  },
  create() {
    wx.switchTab({ url: "/pages/type/type" });
  }
});
