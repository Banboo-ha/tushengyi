const { asset, request, ensureLogin, toast } = require("../../utils/api");

function dateText(value) {
  if (!value) return "";
  return String(value).slice(0, 10);
}

Page({
  data: {
    workId: "",
    publicMode: false,
    title: "",
    authorName: "",
    imageUrl: "",
    likesCount: 0,
    current: {},
    versions: [],
    showVersions: false,
    canModify: false,
    editing: false,
    editInstruction: ""
  },
  async onLoad(query) {
    await ensureLogin();
    if (query.public) {
      this.loadPublic(query.version_id);
      return;
    }
    this.loadWork(query.work_id, query.version_id);
  },
  async loadPublic(versionId) {
    try {
      const item = await request(`/works/public/${versionId}`);
      this.setData({
        publicMode: true,
        workId: item.work_id,
        title: item.title,
        authorName: item.author_name,
        imageUrl: asset(item.cover_url),
        likesCount: item.likes_count,
        current: item,
        versions: [],
        canModify: false
      });
    } catch (e) {
      toast(e.message);
    }
  },
  async loadWork(workId, versionId) {
    try {
      const data = await request(`/works/${workId}`);
      const versions = (data.versions || []).map(item => ({
        ...item,
        image: asset(item.image_url),
        created_at_text: dateText(item.created_at)
      }));
      const current = versions.find(item => item.version_id === versionId) || versions[versions.length - 1] || {};
      this.setData({
        workId,
        title: data.title,
        authorName: "我",
        imageUrl: current.image || asset(data.cover_url),
        likesCount: current.likes_count || 0,
        current,
        versions,
        canModify: true
      });
    } catch (e) {
      toast(e.message);
    }
  },
  preview() {
    if (this.data.imageUrl) wx.previewImage({ urls: [this.data.imageUrl] });
  },
  saveImage() {
    if (!this.data.imageUrl) return;
    wx.downloadFile({
      url: this.data.imageUrl,
      success: res => wx.saveImageToPhotosAlbum({
        filePath: res.tempFilePath,
        success: () => toast("已保存到相册"),
        fail: err => toast(err.errMsg || "保存失败")
      }),
      fail: err => toast(err.errMsg || "下载失败")
    });
  },
  toggleEdit() {
    this.setData({ editing: !this.data.editing });
  },
  onEditInput(event) {
    this.setData({ editInstruction: event.detail.value });
  },
  async submitModify() {
    const text = String(this.data.editInstruction || "").trim();
    if (!text) {
      toast("请填写修改要求");
      return;
    }
    try {
      const data = await request("/poster/modify", {
        method: "POST",
        data: {
          work_id: this.data.workId,
          version_id: this.data.current.version_id,
          edit_instruction: text
        }
      });
      wx.redirectTo({ url: `/pages/waiting/waiting?task_id=${data.task_id}` });
    } catch (e) {
      toast(e.message);
    }
  },
  toggleVersions() {
    this.setData({ showVersions: !this.data.showVersions });
  },
  selectVersion(event) {
    const item = event.currentTarget.dataset.item;
    this.setData({
      current: item,
      imageUrl: item.image,
      likesCount: item.likes_count || 0
    });
  }
});
