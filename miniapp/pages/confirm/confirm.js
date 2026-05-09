const { request, asset, ensureLogin, toast } = require("../../utils/api");
const { getDraft, setDraft } = require("../../utils/draft");

const typeLabels = { product: "产品宣传海报", xiaohongshu: "小红书种草图", main_image: "电商主图", promotion: "活动促销海报" };
const ratios = ["1:1", "3:4", "4:5", "9:16", "16:9"];
const qualities = [{ key: "medium", label: "高清", cost: 8 }, { key: "high", label: "超清", cost: 10 }];

Page({
  data: { ratios, qualityLabels: qualities.map(q => q.label) },
  onShow() { this.sync(); },
  sync() {
    const d = getDraft();
    const quality = d.imageQuality || "high";
    const qIndex = Math.max(0, qualities.findIndex(q => q.key === quality));
    this.setData({
      ...d,
      posterTypeLabel: typeLabels[d.posterType] || "产品宣传海报",
      images: [...(d.productImages || []), ...(d.referenceImages || [])].map(i => ({ ...i, url: asset(i.image_url) })),
      ratio: d.ratio || "9:16",
      ratioIndex: ratios.indexOf(d.ratio || "9:16"),
      qualityIndex: qIndex,
      qualityLabel: qualities[qIndex].label,
      cost: qualities[qIndex].cost
    });
  },
  setRatio(e) {
    const ratio = ratios[Number(e.detail.value)];
    setDraft({ ratio });
    this.sync();
  },
  setQuality(e) {
    const quality = qualities[Number(e.detail.value)];
    setDraft({ imageQuality: quality.key });
    this.sync();
  },
  async create() {
    const d = getDraft();
    try {
      await ensureLogin();
      const task = await request("/poster/generate", {
        method: "POST",
        data: {
          product_image_ids: (d.productImages || []).map(i => i.image_id),
          reference_image_ids: (d.referenceImages || []).map(i => i.image_id),
          title: d.title || "",
          subtitle: d.subtitle || "",
          selling_points: d.selling_points || "",
          style: d.style || "premium_commercial",
          poster_type: d.posterType || "product",
          ratio: d.ratio || "9:16",
          image_quality: d.imageQuality || "high"
        }
      });
      wx.navigateTo({ url: `/pages/waiting/waiting?task_id=${task.task_id}` });
    } catch (e) { toast(e.message); }
  }
});
