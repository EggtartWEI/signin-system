# 值班签到系统部署指南

## 项目状态

### 已完成 ✅

1. **GitHub 仓库**
   - 地址：https://github.com/EggtartWEI/signin-system
   - 代码已推送，包含完整项目

2. **GitHub Actions 自动化构建**
   - Workflow 文件：`.github/workflows/docker-build.yml`
   - 功能：每次推送代码自动构建 Docker 镜像
   - 状态：✅ 构建成功

3. **Docker 镜像**
   - 镜像地址：`ghcr.io/eggtartwei/signin-system:latest`
   - 存储位置：GitHub Container Registry (ghcr.io)
   - 查看地址：https://github.com/EggtartWEI/signin-system/pkgs/container/signin-system

### 待完成 ⏳

1. **服务器准备**
   - 购买/准备云服务器（推荐阿里云、腾讯云等）
   - 配置安全组（开放 3000、8001 端口）

2. **服务器环境配置**
   - 安装 Docker
   - 安装 Docker Compose
   - 配置 SSH 密钥登录

3. **自动部署配置（可选）**
   - 配置 GitHub Secrets
   - 重新启用 deploy workflow

---

## 快速开始（手动部署）

### 第一步：准备服务器

推荐配置：
- **CPU**：1-2 核
- **内存**：2-4 GB
- **系统**：Ubuntu 20.04/22.04 LTS
- **带宽**：3-5 Mbps
- **域名**：（可选）用于 HTTPS

### 第二步：安装 Docker

在服务器上执行：

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 添加用户到 docker 组
sudo usermod -aG docker $USER

# 验证安装
docker --version
docker-compose --version
```

### 第三步：拉取并运行镜像

```bash
# 创建部署目录
mkdir -p /opt/signin-system
cd /opt/signin-system

# 登录 GitHub Container Registry
# 需要先在 GitHub 生成 Personal Access Token
# https://github.com/settings/tokens
export CR_PAT=你的_GITHUB_TOKEN
echo $CR_PAT | docker login ghcr.io -u EggtartWEI --password-stdin

# 拉取镜像
docker pull ghcr.io/eggtartwei/signin-system:latest

# 创建数据文件
touch data.json mode.json
mkdir -p login
touch login/external_users.json

# 运行容器
docker run -d \
  --name signin-system \
  -p 3000:3000 \
  -p 8001:8001 \
  -v $(pwd)/data.json:/app/data.json \
  -v $(pwd)/mode.json:/app/mode.json \
  -v $(pwd)/login/external_users.json:/app/login/external_users.json \
  --restart unless-stopped \
  ghcr.io/eggtartwei/signin-system:latest
```

### 第四步：验证部署

```bash
# 查看容器状态
docker ps

# 查看日志
docker logs -f signin-system

# 测试访问
curl http://localhost:3000
curl http://localhost:8001/health
```

### 第五步：配置反向代理（推荐）

使用 Nginx 配置域名和 HTTPS：

```bash
# 安装 Nginx
sudo apt install nginx -y

# 创建配置文件
sudo tee /etc/nginx/sites-available/signin-system << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 启用配置
sudo ln -s /etc/nginx/sites-available/signin-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 使用 Docker Compose（推荐）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  signin-system:
    image: ghcr.io/eggtartwei/signin-system:latest
    container_name: signin-system
    restart: unless-stopped
    ports:
      - "3000:3000"
      - "8001:8001"
    volumes:
      - ./data.json:/app/data.json
      - ./mode.json:/app/mode.json
      - ./login/external_users.json:/app/login/external_users.json
      - ./logs:/app/logs
      - ./backup:/app/backup
    environment:
      - TZ=Asia/Shanghai
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  nginx:
    image: nginx:alpine
    container_name: signin-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - signin-system
```

启动：
```bash
docker-compose up -d
```

---

## 自动部署配置（进阶）

如果你想实现推送代码自动部署到服务器，需要：

### 1. 配置 GitHub Secrets

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `SSH_HOST` | 服务器 IP 或域名 | `123.45.67.89` |
| `SSH_USERNAME` | SSH 用户名 | `root` |
| `SSH_PRIVATE_KEY` | SSH 私钥 | `-----BEGIN OPENSSH PRIVATE KEY-----` |
| `SSH_PORT` | SSH 端口 | `22` |

### 2. 重新启用 Deploy Workflow

取消注释或重新添加 `.github/workflows/deploy.yml` 文件。

### 3. 服务器配置 SSH 密钥

```bash
# 在服务器上
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 将 GitHub Actions 的公钥添加到 authorized_keys
echo "你的公钥内容" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

---

## 数据备份

### 自动备份脚本

创建 `backup.sh`：

```bash
#!/bin/bash
BACKUP_DIR="/opt/signin-system/backup"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据
cp /opt/signin-system/data.json $BACKUP_DIR/data-$DATE.json
cp /opt/signin-system/login/external_users.json $BACKUP_DIR/external_users-$DATE.json

# 保留最近 30 个备份
ls -t $BACKUP_DIR/data-*.json | tail -n +31 | xargs rm -f
ls -t $BACKUP_DIR/external_users-*.json | tail -n +31 | xargs rm -f

echo "备份完成: $DATE"
```

添加到定时任务：
```bash
# 每天凌晨 2 点备份
0 2 * * * /opt/signin-system/backup.sh >> /var/log/signin-backup.log 2>&1
```

---

## 常见问题

### Q: 如何更新到最新版本？

```bash
cd /opt/signin-system
docker pull ghcr.io/eggtartwei/signin-system:latest
docker-compose down
docker-compose up -d
```

### Q: 如何查看日志？

```bash
# 实时日志
docker logs -f signin-system

# 最近 100 行
docker logs --tail 100 signin-system
```

### Q: 如何重启服务？

```bash
docker restart signin-system
```

### Q: 数据存储在哪里？

数据存储在服务器的以下文件中：
- `/opt/signin-system/data.json` - 签到数据
- `/opt/signin-system/mode.json` - 系统配置
- `/opt/signin-system/login/external_users.json` - 外委账号

---

## 联系支持

如有问题，请提交 Issue 到：
https://github.com/EggtartWEI/signin-system/issues

---

**最后更新**：2025年
