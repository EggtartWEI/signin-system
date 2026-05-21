# GitHub Secrets 配置说明

## 配置步骤

### 1. 打开 GitHub 仓库设置
1. 进入 GitHub 仓库页面
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**

### 2. 添加 Secrets

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `DOCKER_USERNAME` | Docker Hub 用户名 | yourname |
| `DOCKER_PASSWORD` | Docker Hub 密码或访问令牌 | dckr_pat_xxx |
| `SERVER_HOST` | 服务器 IP 或域名 | 192.168.1.100 |
| `SERVER_USER` | 服务器用户名 | root |
| `SERVER_SSH_KEY` | SSH 私钥 | -----BEGIN OPENSSH PRIVATE KEY----- |

### 3. 获取 Docker Hub 访问令牌

1. 登录 [Docker Hub](https://hub.docker.com)
2. 点击右上角头像 → **Account Settings**
3. 选择 **Security** → **New Access Token**
4. 输入令牌名称，选择权限（**Read, Write, Delete**）
5. 复制生成的令牌

### 4. 生成 SSH 密钥对

在本地执行：
```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions
```

将公钥添加到服务器：
```bash
ssh-copy-id -i ~/.ssh/github_actions.pub root@your-server-ip
```

将私钥内容复制到 GitHub Secrets：
```bash
cat ~/.ssh/github_actions
```

### 5. 配置完成后的效果

每次推送代码到 `main` 或 `master` 分支时：
1. GitHub Actions 自动构建 Docker 镜像
2. 推送镜像到 Docker Hub
3. 自动部署到服务器（如果配置了部署步骤）

## 手动部署到服务器

如果不想自动部署，可以在服务器上手动执行：

```bash
# 1. 登录服务器
ssh root@your-server-ip

# 2. 创建部署目录
mkdir -p /opt/signin-system
cd /opt/signin-system

# 3. 下载部署脚本
curl -O https://raw.githubusercontent.com/yourusername/signin-system/main/deploy.sh
chmod +x deploy.sh

# 4. 设置环境变量
export DOCKER_USERNAME=your-docker-username
export VERSION=latest

# 5. 执行部署
./deploy.sh
```

## 查看构建状态

1. 进入 GitHub 仓库
2. 点击 **Actions** 标签
3. 查看工作流运行状态

## 常见问题

### Q: Docker Hub 推送失败
A: 检查 DOCKER_USERNAME 和 DOCKER_PASSWORD 是否正确，密码应该是访问令牌而不是登录密码。

### Q: SSH 部署失败
A: 检查 SERVER_SSH_KEY 格式是否正确，应该是完整的私钥内容（包含 BEGIN/END 行）。

### Q: 服务器拉取镜像慢
A: 可以配置国内镜像源，修改 `/etc/docker/daemon.json`：
```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
```
