const { getDraft, setDraft } = require("../../utils/draft");

Page({
  data: { title: "", subtitle: "", selling_points: "" },
  onShow() { this.setData(getDraft()); },
  setTitle(e) { this.setData({ title: e.detail.value }); },
  setSubtitle(e) { this.setData({ subtitle: e.detail.value }); },
  setSelling(e) { this.setData({ selling_points: e.detail.value }); },
  next() {
    setDraft({ title: this.data.title.trim(), subtitle: this.data.subtitle.trim(), selling_points: this.data.selling_points.trim() });
    wx.navigateTo({ url: "/pages/confirm/confirm" });
  }
});
