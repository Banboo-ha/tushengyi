const { request, asset, ensureLogin, toast } = require("../../utils/api");
const { resetDraft } = require("../../utils/draft");

const styleMap = { product: "premium_commercial", xiaohongshu: "xiaohongshu", main_image: "ecommerce", promotion: "premium_commercial" };

Page({
  data: {
    profile: null,
    works: [],
    features: [
      { id: "product", name: "产品海报", desc: "突出卖点", icon: "/assets/ui_v1/home/home-product-icon.png" },
      { id: "xiaohongshu", name: "小红书封面", desc: "种草必备", icon: "/assets/ui_v1/home/home-xiaohongshu-icon.png" },
      { id: "main_image", name: "电商主图", desc: "提升点击", icon: "/assets/ui_v1/home/home-main-image-icon.png" },
      { id: "promotion", name: "活动促销", desc: "吸睛利器", icon: "/assets/ui_v1/home/home-promotion-icon.png" }
    ]
  },
  onShow() {
    this.load();
  },
  async load() {
    try {
      await ensureLogin();
      const [profile, featured] = await Promise.all([
        request("/user/profile"),
        request("/works/featured")
      ]);
      this.setData({
        profile,
        works: (featured.list || []).map(item => ({ ...item, cover: asset(item.cover_url) }))
      });
    } catch (e) { toast(e.message); }
  },
  start() {
    resetDraft();
    wx.switchTab({ url: "/pages/type/type" });
  },
  pickType(event) {
    const posterType = event.currentTarget.dataset.id;
    resetDraft({ posterType, style: styleMap[posterType] || "premium_commercial" });
    wx.navigateTo({ url: "/pages/upload-product/upload-product" });
  },
  goPlaza() {
    wx.navigateTo({ url: "/pages/plaza/plaza" });
  },
  openWork(event) {
    const item = event.currentTarget.dataset.item;
    wx.navigateTo({ url: `/pages/work-detail/work-detail?version_id=${item.version_id}&public=1` });
  },
  goMine() {
    wx.switchTab({ url: "/pages/mine/mine" });
  }
});
