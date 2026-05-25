#!/bin/bash
# 值班签到系统 Systemd 部署脚本
# 在服务器上执行此脚本

set -e

# 配置
INSTALL_DIR="/opt/signin-system"
SERVICE_USER="www-data"
GITHUB_REPO="https://github.com/EggtartWEI/signin-system.git"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== 值班签到系统 Systemd 部署 ===${NC}"

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用 root 权限运行${NC}"
    exit 1
fi

# 1. 安装依赖
echo -e "${YELLOW}[1/8] 安装系统依赖...${NC}"
apt update
apt install -y python3 python3-pip python3-venv git curl

# 2. 创建用户
echo -e "${YELLOW}[2/8] 创建服务用户...${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false "$SERVICE_USER"
fi

# 3. 下载代码
echo -e "${YELLOW}[3/8] 下载项目代码...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo "目录已存在，更新代码..."
    cd "$INSTALL_DIR"
    git pull
else
    git clone "$GITHUB_REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 设置权限
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# 4. 创建虚拟环境
echo -e "${YELLOW}[4/8] 创建 Python 虚拟环境...${NC}"
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

# 安装依赖
pip install --upgrade pip
pip install -r "$INSTALL_DIR/login/requirements.txt"

# 5. 创建数据目录和文件
echo -e "${YELLOW}[5/8] 准备数据文件...${NC}"
mkdir -p "$INSTALL_DIR/logs" "$INSTALL_DIR/backup"

# 创建空数据文件（如果不存在）
if [ ! -f "$INSTALL_DIR/data.json" ]; then
    echo '{}' > "$INSTALL_DIR/data.json"
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/data.json"
fi

if [ ! -f "$INSTALL_DIR/mode.json" ]; then
    echo '{"mode": "open", "allowedIPs": []}' > "$INSTALL_DIR/mode.json"
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/mode.json"
fi

if [ ! -f "$INSTALL_DIR/login/external_users.json" ]; then
    mkdir -p "$INSTALL_DIR/login"
    echo '{}' > "$INSTALL_DIR/login/external_users.json"
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/login/external_users.json"
fi

# 6. 创建 Systemd 服务文件
echo -e "${YELLOW}[6/8] 创建 Systemd 服务...${NC}"

# 认证服务
cat > /etc/systemd/system/signin-auth.service << EOF
[Unit]
Description=Signin Auth Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/login
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="LOG_DIR=$INSTALL_DIR/logs"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/login/attendance_login_only.py
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 签到系统服务
cat > /etc/systemd/system/signin-app.service << EOF
[Unit]
Description=Signin App Service
After=network.target signin-auth.service
Requires=signin-auth.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/server_with_auth.py
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 7. 启动服务
echo -e "${YELLOW}[7/8] 启动服务...${NC}"
systemctl daemon-reload
systemctl enable signin-auth signin-app
systemctl start signin-auth
sleep 3
systemctl start signin-app

# 8. 检查状态
echo -e "${YELLOW}[8/8] 检查服务状态...${NC}"
sleep 2

echo ""
echo -e "${GREEN}=== 部署完成 ===${NC}"
echo ""
echo "服务状态:"
systemctl is-active signin-auth && echo -e "  ${GREEN}✓${NC} 认证服务运行中" || echo -e "  ${RED}✗${NC} 认证服务未运行"
systemctl is-active signin-app && echo -e "  ${GREEN}✓${NC} 签到系统运行中" || echo -e "  ${RED}✗${NC} 签到系统未运行"

echo ""
echo "访问地址:"
echo "  签到系统: http://服务器IP:3000"
echo "  认证服务: http://服务器IP:8001"

echo ""
echo "常用命令:"
echo "  查看状态: sudo systemctl status signin-auth signin-app"
echo "  查看日志: sudo journalctl -u signin-auth -f"
echo "  重启服务: sudo systemctl restart signin-auth signin-app"
echo "  停止服务: sudo systemctl stop signin-auth signin-app"
