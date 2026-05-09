const { request, ensureLogin, toast } = require("../../utils/api");

Page({
  data: { packages: [] },
  onLoad() { this.load(); },
  async load() {
    try {
      const data = await request("/pay/packages");
      this.setData({
        packages: (data.list || []).map(item => ({
          ...item,
          price: (Number(item.amount_cents || 0) / 100).toFixed(2)
        }))
      });
    } catch (e) {
      toast(e.message);
    }
  },
  async buy(event) {
    try {
      await ensureLogin();
      const data = await request("/pay/orders", {
        method: "POST",
        data: { package_id: event.currentTarget.dataset.id }
      });
      if (!data.payment_available) {
        toast(data.message || "支付能力配置中");
        return;
      }
      const params = data.payment_params || {};
      wx.requestPayment({
        ...params,
        success: () => toast("支付成功，积分稍后到账"),
        fail: err => toast(err.errMsg || "支付已取消")
      });
    } catch (e) {
      toast(e.message);
    }
  }
});
