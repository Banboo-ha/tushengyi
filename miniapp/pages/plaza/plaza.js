const { asset, request, ensureLogin, toast } = require("../../utils/api");

function mapWork(item) {
  return { ...item, cover: asset(item.cover_url) };
}

Page({
  data: { works: [], loading: true },
  onLoad() { this.load(); },
  onPullDownRefresh() {
    this.load().finally(() => wx.stopPullDownRefresh());
  },
  async load() {
    this.setData({ loading: true });
    try {
      const data = await request("/works/plaza?limit=80");
      this.setData({ works: (data.list || []).map(mapWork), loading: false });
    } catch (e) {
      this.setData({ loading: false });
      toast(e.message);
    }
  },
  openWork(event) {
    const item = event.currentTarget.dataset.item;
    wx.navigateTo({ url: `/pages/work-detail/work-detail?version_id=${item.version_id}&public=1` });
  },
  async like(event) {
    const index = event.currentTarget.dataset.index;
    const item = this.data.works[index];
    try {
      await ensureLogin();
      const data = await request(`/works/versions/${item.version_id}/like`, { method: "POST" });
      this.setData({
        [`works[${index}].likes_count`]: data.likes_count,
        [`works[${index}].liked_by_me`]: true
      });
    } catch (e) {
      toast(e.message);
    }
  }
});
