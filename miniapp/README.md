# 图生意微信小程序

这是图生意的原生微信小程序前端，复用 FastAPI 后端的生成、上传、作品、点赞、积分和充值订单能力。

## 本地开发

1. 启动后端：

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. 用微信开发者工具导入 `miniapp/`。
3. 开发阶段在微信开发者工具中勾选“不校验合法域名”。
4. 默认接口地址在 `app.js`：

```js
apiBase: "http://127.0.0.1:8000/api/mp",
assetBase: "http://127.0.0.1:8000"
```

## 正式环境

备案和 HTTPS 完成后，将 `app.js` 改成正式域名，例如：

```js
apiBase: "https://api.huituke.top/api/mp",
assetBase: "https://api.huituke.top"
```

并在微信小程序后台配置：

- request 合法域名
- uploadFile 合法域名
- downloadFile 合法域名

## 支付

首版已完成微信支付订单、查询、回调和后台配置骨架。商户号、API v3 key、证书和回调域名配置完成后，再接入真实 JSAPI 下单和验签。
