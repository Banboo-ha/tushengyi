const { ensureLogin, uploadImage, asset, toast } = require("../../utils/api");
const { getDraft, setDraft } = require("../../utils/draft");

Page({
  data: { images: [] },
  onShow() { this.sync(); },
  sync() { this.setData({ images: (getDraft().referenceImages || []).map(i => ({ ...i, url: asset(i.image_url) })) }); },
  choose() {
    if (this.data.images.length >= 4) return toast("最多上传 4 张参考图");
    wx.chooseMedia({
      count: 4 - this.data.images.length,
      mediaType: ["image"],
      success: async res => {
        wx.showLoading({ title: "上传中" });
        try {
          await ensureLogin();
          const uploaded = [];
          for (const file of res.tempFiles) uploaded.push(await uploadImage(file.tempFilePath, "reference"));
          const draft = getDraft();
          setDraft({ referenceImages: [...(draft.referenceImages || []), ...uploaded].slice(0, 4) });
          this.sync();
        } catch (e) { toast(e.message); }
        wx.hideLoading();
      }
    });
  },
  remove(e) {
    const images = getDraft().referenceImages || [];
    images.splice(e.currentTarget.dataset.index, 1);
    setDraft({ referenceImages: images });
    this.sync();
  },
  skip() { wx.navigateTo({ url: "/pages/copy/copy" }); }
});
