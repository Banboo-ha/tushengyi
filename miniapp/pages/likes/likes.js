const { asset, request, ensureLogin, toast } = require("../../utils/api");

Page({
  data: { works: [], loading: true },
  onShow() { this.load(); },
  async load() {
    this.setData({ loading: true });
    try {
      await ensureLogin();
      const data = await request("/works/liked?limit=80");
      this.setData({
        works: (data.list || []).map(item => ({ ...item, cover: asset(item.cover_url) })),
        loading: false
      });
    } catch (e) {
      this.setData({ loading: false });
      toast(e.message);
    }
  },
  openWork(event) {
    const item = event.currentTarget.dataset.item;
    wx.navigateTo({ url: `/pages/work-detail/work-detail?version_id=${item.version_id}&public=1` });
  }
});
