#!/bin/bash
# 更新签到系统脚本

set -e

INSTALL_DIR="/opt/signin-system"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== 更新值班签到系统 ===${NC}"

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 权限运行"
    exit 1
fi

# 备份数据
echo -e "${YELLOW}备份数据...${NC}"
mkdir -p "$INSTALL_DIR/backup"
cp "$INSTALL_DIR/data.json" "$INSTALL_DIR/backup/data-$(date +%Y%m%d-%H%M%S).json" 2>/dev/null || true
cp "$INSTALL_DIR/login/external_users.json" "$INSTALL_DIR/backup/external_users-$(date +%Y%m%d-%H%M%S).json" 2>/dev/null || true

# 停止服务
echo -e "${YELLOW}停止服务...${NC}"
systemctl stop signin-app signin-auth

# 更新代码
echo -e "${YELLOW}更新代码...${NC}"
cd "$INSTALL_DIR"
git pull

# 更新依赖
echo -e "${YELLOW}更新依赖...${NC}"
source "$INSTALL_DIR/venv/bin/activate"
pip install -r "$INSTALL_DIR/login/requirements.txt"

# 启动服务
echo -e "${YELLOW}启动服务...${NC}"
systemctl start signin-auth
sleep 3
systemctl start signin-app

# 检查状态
echo ""
echo -e "${GREEN}更新完成！${NC}"
systemctl status signin-auth --no-pager
systemctl status signin-app --no-pager
