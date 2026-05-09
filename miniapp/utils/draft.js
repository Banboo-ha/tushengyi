const key = "poster_draft";

function getDraft() {
  return wx.getStorageSync(key) || {
    productImages: [],
    referenceImages: [],
    posterType: "product",
    style: "premium_commercial",
    ratio: "9:16",
    imageQuality: "high",
    title: "",
    subtitle: "",
    selling_points: ""
  };
}

function setDraft(data) {
  wx.setStorageSync(key, { ...getDraft(), ...data });
}

function resetDraft(data = {}) {
  wx.setStorageSync(key, {
    productImages: [],
    referenceImages: [],
    posterType: "product",
    style: "premium_commercial",
    ratio: "9:16",
    imageQuality: "high",
    title: "",
    subtitle: "",
    selling_points: "",
    ...data
  });
}

module.exports = { getDraft, setDraft, resetDraft };
