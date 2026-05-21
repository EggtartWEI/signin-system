# Docker 部署指南

## 方案概述

使用 GitHub Actions 自动构建 Docker 镜像，推送到 Docker Hub，服务器自动拉取部署。

```
GitHub Push → GitHub Actions 构建 → Docker Hub → 服务器拉取部署
```

## 前置准备

### 1. Docker Hub 账号

1. 注册 [Docker Hub](https://hub.docker.com/)
2. 创建仓库（如 `signin-system`）

### 2. GitHub Secrets 配置

在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `DOCKER_USERNAME` | Docker Hub 用户名 | yourusername |
| `DOCKER_PASSWORD` | Docker Hub 密码或 Token | yourpassword |
| `SSH_HOST` | 服务器 IP 或域名 | 192.168.1.100 |
| `SSH_USERNAME` | SSH 用户名 | root |
| `SSH_PRIVATE_KEY` | SSH 私钥 | -----BEGIN... |
| `SSH_PORT` | SSH 端口（可选） | 22 |

### 3. 服务器准备

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 创建部署目录
sudo mkdir -p /opt/signin-system
sudo chown $USER:$USER /opt/signin-system
```

## 部署步骤

### 方式一：自动部署（推荐）

1. **推送代码到 GitHub**
   ```bash
   git add .
   git commit -m "update: xxx"
   git push origin master
   ```

2. **GitHub Actions 自动执行**
   - 构建 Docker 镜像
   - 推送到 Docker Hub
   - 自动部署到服务器

3. **查看部署状态**
   - 在 GitHub 仓库 Actions 标签页查看

### 方式二：手动部署

```bash
# 1. 登录 Docker Hub
docker login

# 2. 拉取镜像
docker pull yourusername/signin-system:latest

# 3. 进入部署目录
cd /opt/signin-system

# 4. 下载 docker-compose.yml
wget https://raw.githubusercontent.com/yourusername/signin-system/master/docker-compose.yml

# 5. 创建数据文件
touch data.json mode.json
mkdir -p login
touch login/external_users.json

# 6. 启动服务
docker-compose up -d

# 7. 查看日志
docker-compose logs -f
```

## 使用部署脚本

```bash
# 下载部署脚本
wget https://raw.githubusercontent.com/yourusername/signin-system/master/scripts/deploy.sh
chmod +x deploy.sh

# 完整部署
./deploy.sh deploy

# 查看状态
./deploy.sh status

# 查看日志
./deploy.sh logs

# 备份数据
./deploy.sh backup

# 重启服务
./deploy.sh restart
```

## 本地测试

```bash
# 构建镜像
docker build -t signin-system:test .

# 运行容器
docker run -d \
  -p 3000:3000 \
  -p 8001:8001 \
  -v $(pwd)/data.json:/app/data.json \
  -v $(pwd)/mode.json:/app/mode.json \
  -v $(pwd)/login/external_users.json:/app/login/external_users.json \
  signin-system:test

# 查看日志
docker logs -f <container_id>
```

## 数据备份

### 自动备份

部署脚本会在每次部署前自动备份数据到 `/opt/signin-system/backup/`

### 手动备份

```bash
# 备份数据
docker cp signin-system:/app/data.json ./backup/data-$(date +%Y%m%d).json
docker cp signin-system:/app/login/external_users.json ./backup/external_users-$(date +%Y%m%d).json

# 或使用部署脚本
./deploy.sh backup
```

### 恢复数据

```bash
# 停止服务
docker-compose down

# 恢复数据文件
cp backup/data-20250115.json data.json
cp backup/external_users-20250115.json login/external_users.json

# 启动服务
docker-compose up -d
```

## 更新升级

### 自动更新

推送代码到 GitHub，Actions 会自动构建并部署。

### 手动更新

```bash
# 1. 拉取最新镜像
docker pull yourusername/signin-system:latest

# 2. 备份数据
./deploy.sh backup

# 3. 重启服务
docker-compose down
docker-compose up -d

# 4. 清理旧镜像
docker image prune -f
```

## 故障排查

### 查看容器状态

```bash
docker-compose ps
docker-compose logs -f
```

### 进入容器调试

```bash
docker exec -it signin-system /bin/bash
```

### 检查端口占用

```bash
netstat -tlnp | grep -E '3000|8001'
```

### 重置容器

```bash
# 停止并删除容器
docker-compose down

# 删除数据（谨慎操作）
rm data.json mode.json

# 重新启动
docker-compose up -d
```

## 安全建议

1. **使用非 root 用户运行容器**
   ```dockerfile
   RUN useradd -m -u 1000 appuser
   USER appuser
   ```

2. **限制容器资源**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '1.0'
         memory: 512M
   ```

3. **使用 HTTPS**
   - 配置 SSL 证书
   - 使用 Nginx 反向代理

4. **定期更新镜像**
   ```bash
   docker pull yourusername/signin-system:latest
   docker-compose up -d
   ```

## 性能优化

### 使用多阶段构建

已配置在 Dockerfile 中，减小镜像体积。

### 启用缓存

GitHub Actions 已配置 Docker layer caching。

### 数据库优化（可选）

如果使用外部数据库，配置连接池：

```python
# 在配置中添加
DATABASE_POOL_SIZE = 10
DATABASE_MAX_OVERFLOW = 20
```

## 监控建议

### 使用 Prometheus + Grafana

```yaml
# docker-compose.yml 添加
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

### 使用 Uptime Kuma

```yaml
  uptime-kuma:
    image: louislam/uptime-kuma
    volumes:
      - uptime-data:/app/data
    ports:
      - "3002:3001"
```

## 常见问题

### Q: 容器启动失败？

A: 检查日志 `docker-compose logs`，可能是端口被占用或数据文件权限问题。

### Q: 数据丢失？

A: 确保正确挂载了数据卷，检查 `docker-compose.yml` 中的 volumes 配置。

### Q: 时区不对？

A: 已在 Dockerfile 中设置 `TZ=Asia/Shanghai`，宿主机也需要正确设置时区。

### Q: 如何回滚？

A: 使用备份的数据文件，或拉取指定版本的镜像：
```bash
docker pull yourusername/signin-system:v1.0.0
```

## 联系支持

如有问题，请提交 Issue 或联系管理员。
