const { request, ensureLogin, toast } = require("../../utils/api");

Page({
  data: {
    profile: {},
    avatarText: "图"
  },
  onShow() { this.refresh(); },
  async refresh() {
    try {
      await ensureLogin();
      const profile = await request("/user/profile");
      this.setData({
        profile,
        avatarText: (profile.username || "图").slice(0, 1).toUpperCase()
      });
    } catch (e) {
      toast(e.message);
    }
  },
  goWorks() { wx.navigateTo({ url: "/pages/works/works" }); },
  goLikes() { wx.navigateTo({ url: "/pages/likes/likes" }); },
  goRecharge() { wx.navigateTo({ url: "/pages/recharge/recharge" }); }
});
