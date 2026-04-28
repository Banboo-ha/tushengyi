# 海报快生 MVP

一个基于 FastAPI 的单仓分离 MVP：同一 Python 服务内提供 H5 用户端、PC 管理端和两套独立 API。

## 快速启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

另开一个终端启动生成 worker：

```bash
source .venv/bin/activate
python scripts/worker.py
```

访问：

- H5 用户端：http://127.0.0.1:8000/h5
- 管理后台：http://127.0.0.1:8000/admin
- 健康检查：http://127.0.0.1:8000/healthz
- 就绪检查：http://127.0.0.1:8000/readyz

默认管理员：

```text
账号：admin
密码：admin123
```

## 默认模型配置

首次启动会从 `PRD/APIkey.md` 读取 `model_base_url` 与 `model_api_key`，写入 `system_settings` 表。为了方便本地闭环验证，默认 `mock_mode=true`，生成海报会保存一张本地 SVG 占位图。

在管理后台的「系统设置」中可以分别配置：

- 图片模型：H5 海报生成实际调用的模型。
- 对话模型：后续 AI 文案辅助、Prompt 优化等文本任务使用的模型。
- Mock 模式：开启时 H5 不调用真实图片接口；关闭时调用真实图片接口。
- 测试接口：后台可单独测试对话模型或真实图片模型。

图片模型默认接口类型为 `Images Edits: /images/edits`，会把用户上传的产品图、参考图作为 multipart 图片文件一起传给模型。把 Mock 模式改为关闭后，后端主流程会调用：

```text
{model_base_url}/images/edits
```

请求体采用 OpenAI 图片编辑 / 图生图风格：

```text
multipart/form-data
model=gpt-image-1
prompt=...
n=1
size=1024x1536
image=<产品图文件，可重复>
image=<参考图文件，可重复>
```

如果选择 `Images: /images/generations`，则是纯文生图，不会携带产品图/参考图，不建议用于当前 H5 主流程。

实际请求尺寸默认使用 OpenAI 标准尺寸映射：

```text
1:1  -> 1024x1024
3:4  -> 1024x1536
4:5  -> 1024x1536
9:16 -> 1024x1536
16:9 -> 1536x1024
```

如果海外模型服务响应格式不同，只需要调整 `app/services/ai_client.py`。

## 已实现范围

- H5 用户注册、登录、退出、个人中心
- 注册赠送积分、积分流水、积分不足拦截
- 产品图上传 1-4 张、参考图上传 0-4 张
- 文案填写、风格选择、比例选择、确认生成
- 数据库持久任务队列、独立 worker 生成、生成成功/失败、失败退还积分
- 作品自动创建并自动进入作品库、作品详情
- 基于作品版本的二次修改
- PC 管理端用户管理、补积分、禁用用户
- 任务管理、作品软删除、积分流水、模型/API 设置

## 目录

```text
app/api/h5/        H5 用户端 API
app/api/admin/     PC 管理端 API
app/models/        SQLAlchemy 数据模型
app/services/      业务服务与模型适配器
app/static/h5/     H5 单页应用
app/static/admin/  管理端单页应用
data/app.db        SQLite 数据库，首次启动自动创建
uploads/           上传图与生成图
scripts/worker.py  后台生成 worker
deploy/centos8/    CentOS 8.5 systemd/nginx 部署材料
```

## 冒烟测试

```bash
python scripts/smoke_test.py
```

脚本会用 FastAPI TestClient 跑通注册、上传、生成、自动入库、二次修改、管理员登录和补积分。

## 服务器部署

CentOS 8.5 服务器部署材料见：

```text
deploy/centos8/DEPLOY.md
```

默认按 `111.229.56.14` 准备了 nginx 反向代理配置。生产环境会运行两个 systemd 服务：

- `haibaokuaisheng-web`：FastAPI Web/API 服务。
- `haibaokuaisheng-worker`：独立生成 worker，负责处理 `pending` 任务。
