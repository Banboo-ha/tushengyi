const { ensureLogin } = require("../../utils/api");
const { resetDraft } = require("../../utils/draft");

const styleMap = { product: "premium_commercial", xiaohongshu: "xiaohongshu", main_image: "ecommerce", promotion: "premium_commercial" };

Page({
  data: {
    types: [
      {
        id: "product",
        key: "blue",
        icon: "/assets/ui_v1/common/icon_01_product_bag.png",
        visual: "/assets/ui_v1/type/type-product-poster.png",
        name: "产品宣传海报",
        desc: "适合新品、食品、设备、日用品推广"
      },
      {
        id: "xiaohongshu",
        key: "pink",
        icon: "/assets/ui_v1/common/icon_02_heart.png",
        visual: "/assets/ui_v1/type/type-xiaohongshu.png",
        name: "小红书种草图",
        desc: "适合民宿、美妆、生活方式内容"
      },
      {
        id: "main_image",
        key: "orange",
        icon: "/assets/ui_v1/common/icon_03_cart.png",
        visual: "/assets/ui_v1/type/type-ecommerce-main.png",
        name: "电商主图",
        desc: "适合商品销售和平台展示"
      },
      {
        id: "promotion",
        key: "purple",
        icon: "/assets/ui_v1/common/icon_04_megaphone.png",
        visual: "/assets/ui_v1/type/type-promotion.png",
        name: "活动促销海报",
        desc: "适合门店活动、节日促销"
      }
    ]
  },
  onShow() { ensureLogin().catch(() => {}); },
  choose(e) {
    const posterType = e.currentTarget.dataset.id;
    resetDraft({ posterType, style: styleMap[posterType] || "premium_commercial" });
    wx.navigateTo({ url: "/pages/upload-product/upload-product" });
  }
});
