#!/bin/bash
# 服务器部署脚本

set -e

# 配置
# GitHub Container Registry 配置
GITHUB_OWNER=${GITHUB_OWNER:-"your-github-username"}
IMAGE_NAME="ghcr.io/${GITHUB_OWNER}/signin-system"
VERSION=${VERSION:-"latest"}
DEPLOY_DIR=${DEPLOY_DIR:-"/opt/signin-system"}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== 值班签到系统部署脚本 ===${NC}"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# 创建部署目录
echo -e "${YELLOW}创建部署目录...${NC}"
mkdir -p $DEPLOY_DIR
cd $DEPLOY_DIR

# 登录 GitHub Container Registry（如果需要）
if [ -n "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}登录 GitHub Container Registry...${NC}"
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_OWNER" --password-stdin
fi

# 拉取最新镜像
echo -e "${YELLOW}拉取最新镜像...${NC}"
docker pull $IMAGE_NAME:$VERSION

# 创建 docker-compose.yml（如果不存在）
if [ ! -f docker-compose.yml ]; then
    echo -e "${YELLOW}创建 docker-compose.yml...${NC}"
    cat > docker-compose.yml << EOF
version: '3.8'

services:
  auth-service:
    image: $DOCKER_USERNAME/signin-auth:$VERSION
    container_name: signin-auth
    ports:
      - "8001:8001"
    volumes:
      - ./data/external_users.json:/app/external_users.json
      - ./data:/app/data
      - ./logs/auth:/app/logs
    environment:
      - LOG_DIR=/app/logs
      - TZ=Asia/Shanghai
    restart: unless-stopped

  signin-service:
    image: $DOCKER_USERNAME/signin-app:$VERSION
    container_name: signin-app
    ports:
      - "3000:3000"
    volumes:
      - ./data/data.json:/app/data.json
      - ./data/mode.json:/app/mode.json
    environment:
      - TZ=Asia/Shanghai
      - AUTH_SERVICE_URL=http://auth-service:8001
    depends_on:
      - auth-service
    restart: unless-stopped

  sync-service:
    image: $DOCKER_USERNAME/signin-sync:$VERSION
    container_name: signin-sync
    volumes:
      - ./data/data.json:/app/data.json
    environment:
      - TZ=Asia/Shanghai
    depends_on:
      - signin-service
    restart: unless-stopped
EOF
fi

# 创建数据目录
echo -e "${YELLOW}创建数据目录...${NC}"
mkdir -p data logs/auth logs/app logs/sync

# 初始化数据文件（如果不存在）
if [ ! -f data/data.json ]; then
    echo '{}' > data/data.json
fi

if [ ! -f data/mode.json ]; then
    echo '{"mode": "open", "allowedIPs": []}' > data/mode.json
fi

if [ ! -f data/external_users.json ]; then
    echo '{}' > data/external_users.json
fi

# 停止旧容器
echo -e "${YELLOW}停止旧容器...${NC}"
docker-compose down --remove-orphans 2>/dev/null || true

# 启动新容器
echo -e "${YELLOW}启动新容器...${NC}"
docker-compose up -d

# 等待服务启动
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 5

# 检查服务状态
echo -e "${YELLOW}检查服务状态...${NC}"
docker-compose ps

# 健康检查
echo -e "${YELLOW}健康检查...${NC}"
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 认证服务运行正常${NC}"
else
    echo -e "${RED}✗ 认证服务未响应${NC}"
fi

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 签到系统运行正常${NC}"
else
    echo -e "${RED}✗ 签到系统未响应${NC}"
fi

# 清理旧镜像
echo -e "${YELLOW}清理旧镜像...${NC}"
docker system prune -f

echo -e "${GREEN}=== 部署完成 ===${NC}"
echo -e "访问地址:"
echo -e "  签到系统: http://localhost:3000"
echo -e "  认证服务: http://localhost:8001"
echo ""
echo -e "查看日志:"
echo -e "  docker-compose logs -f"
