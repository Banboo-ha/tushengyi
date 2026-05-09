const { ensureLogin, uploadImage, asset, toast } = require("../../utils/api");
const { getDraft, setDraft } = require("../../utils/draft");

Page({
  data: { images: [] },
  onShow() {
    ensureLogin().catch(() => {});
    this.sync();
  },
  sync() {
    this.setData({ images: (getDraft().productImages || []).map(i => ({ ...i, url: asset(i.image_url) })) });
  },
  choose() {
    if (this.data.images.length >= 4) return toast("最多上传 4 张产品图");
    wx.chooseMedia({
      count: 4 - this.data.images.length,
      mediaType: ["image"],
      success: async res => {
        wx.showLoading({ title: "上传中" });
        try {
          await ensureLogin();
          const uploaded = [];
          for (const file of res.tempFiles) uploaded.push(await uploadImage(file.tempFilePath, "product"));
          const draft = getDraft();
          setDraft({ productImages: [...(draft.productImages || []), ...uploaded].slice(0, 4) });
          this.sync();
        } catch (e) { toast(e.message); }
        wx.hideLoading();
      }
    });
  },
  remove(e) {
    const images = getDraft().productImages || [];
    images.splice(e.currentTarget.dataset.index, 1);
    setDraft({ productImages: images });
    this.sync();
  },
  next() {
    if (!this.data.images.length) return toast("请至少上传 1 张产品图");
    wx.navigateTo({ url: "/pages/upload-reference/upload-reference" });
  }
});
