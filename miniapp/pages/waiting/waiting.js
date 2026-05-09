const { request, toast } = require("../../utils/api");

Page({
  data: { taskId: "", percent: 0, message: "正在分析产品图" },
  onLoad(query) {
    this.setData({ taskId: query.task_id || "" });
    this.start();
  },
  onUnload() {
    clearInterval(this.timer);
    clearInterval(this.progressTimer);
  },
  start() {
    const start = Date.now();
    const words = ["正在分析产品图", "正在理解宣传文案", "正在生成海报", "正在优化画面细节"];
    let i = 0;
    this.progressTimer = setInterval(() => {
      const p = Math.min(98, Math.round((Date.now() - start) / 300000 * 100));
      this.setData({ percent: p, message: words[i++ % words.length] });
    }, 1200);
    this.timer = setInterval(() => this.poll(), 1500);
    this.poll();
  },
  async poll() {
    if (!this.data.taskId) return;
    try {
      const task = await request(`/poster/task/${this.data.taskId}`);
      if (task.status === "success") {
        clearInterval(this.timer); clearInterval(this.progressTimer);
        wx.redirectTo({ url: `/pages/result/result?task_id=${task.task_id}` });
      }
      if (task.status === "failed") {
        clearInterval(this.timer); clearInterval(this.progressTimer);
        toast(task.error_message || "生成失败，积分已退还");
        wx.redirectTo({ url: "/pages/confirm/confirm" });
      }
    } catch (e) { toast(e.message); }
  },
  goWorks() { wx.redirectTo({ url: "/pages/works/works" }); }
});
