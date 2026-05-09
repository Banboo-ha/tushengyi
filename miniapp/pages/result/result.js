const { request, asset, toast } = require("../../utils/api");

Page({
  data: { task: null, imageUrl: "" },
  async onLoad(query) {
    try {
      const task = await request(`/poster/task/${query.task_id}`);
      this.setData({ task, imageUrl: asset(task.result_image_url) });
    } catch (e) { toast(e.message); }
  },
  preview() { wx.previewImage({ urls: [this.data.imageUrl] }); },
  save() {
    wx.downloadFile({
      url: this.data.imageUrl,
      success: res => wx.saveImageToPhotosAlbum({ filePath: res.tempFilePath, success: () => toast("已保存到相册"), fail: err => toast(err.errMsg) })
    });
  },
  edit() {
    const t = this.data.task || {};
    wx.navigateTo({ url: `/pages/work-detail/work-detail?work_id=${t.work_id}&version_id=${t.version_id}` });
  },
  regenerate() { wx.navigateTo({ url: "/pages/confirm/confirm" }); },
  goWorks() { wx.redirectTo({ url: "/pages/works/works" }); }
});
