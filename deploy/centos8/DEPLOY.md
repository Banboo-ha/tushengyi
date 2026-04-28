# CentOS 8.5 部署说明

目标服务器：`111.229.56.14`  
推荐部署目录：`/opt/haibaokuaisheng`  
推荐运行用户：`haibao`

## 1. 系统依赖

CentOS 8.5 默认 Python 可能偏旧，项目建议 Python 3.9+。

```bash
sudo dnf install -y nginx git gcc openssl-devel bzip2-devel libffi-devel zlib-devel sqlite
sudo dnf install -y python39 python39-devel python39-pip
```

如果 CentOS 8.5 的 dnf 源已经 EOL，需要先切换到 vault 源或用你服务器现有的软件源安装 Python 3.9+。

## 2. 创建运行用户和目录

```bash
sudo useradd --system --create-home --shell /sbin/nologin haibao
sudo mkdir -p /opt/haibaokuaisheng /etc/haibaokuaisheng
sudo chown -R haibao:haibao /opt/haibaokuaisheng
```

把项目代码上传到：

```text
/opt/haibaokuaisheng
```

## 3. 安装 Python 依赖

```bash
cd /opt/haibaokuaisheng
sudo -u haibao python3.9 -m venv .venv
sudo -u haibao .venv/bin/pip install --upgrade pip
sudo -u haibao .venv/bin/pip install -r requirements.txt
```

## 4. 配置环境变量

```bash
sudo cp deploy/centos8/haibaokuaisheng.env.example /etc/haibaokuaisheng/haibaokuaisheng.env
sudo vi /etc/haibaokuaisheng/haibaokuaisheng.env
sudo chmod 600 /etc/haibaokuaisheng/haibaokuaisheng.env
sudo chown root:root /etc/haibaokuaisheng/haibaokuaisheng.env
```

必须修改：

```text
HAIBAO_SECRET_KEY
```

首次启动后，后台默认管理员仍是：

```text
admin / admin123
```

上线后请尽快在后续管理功能中改造管理员密码修改能力，或临时通过数据库更新密码。

## 5. 安装 systemd 服务

```bash
sudo cp deploy/centos8/haibaokuaisheng-web.service /etc/systemd/system/
sudo cp deploy/centos8/haibaokuaisheng-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now haibaokuaisheng-web
sudo systemctl enable --now haibaokuaisheng-worker
```

检查状态：

```bash
sudo systemctl status haibaokuaisheng-web
sudo systemctl status haibaokuaisheng-worker
curl http://127.0.0.1:8000/healthz
```

## 6. 配置 nginx

```bash
sudo cp deploy/centos8/nginx-haibaokuaisheng.conf /etc/nginx/conf.d/haibaokuaisheng.conf
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

访问：

```text
http://111.229.56.14/h5
http://111.229.56.14/admin
```

## 7. 防火墙

如果服务器启用了 firewalld：

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
```

## 8. 任务模型

Web 服务只负责创建任务和提供 API；Worker 服务独立轮询数据库里的 `pending` 任务并生成图片。

这意味着：

- 用户点击确认生成后可以关闭页面或切后台。
- 生成成功后作品会自动进入作品库。
- 如果 worker 重启，超过 `HAIBAO_TASK_STALE_SECONDS` 的 running 任务会被重新排队。
- SQLite 部署建议只跑 1 个 worker；后续上量后建议迁移 PostgreSQL，再增加 worker 数。

## 9. 日志

```bash
sudo journalctl -u haibaokuaisheng-web -f
sudo journalctl -u haibaokuaisheng-worker -f
sudo tail -f /var/log/nginx/haibaokuaisheng.error.log
```

