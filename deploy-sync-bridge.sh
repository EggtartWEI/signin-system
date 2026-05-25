#!/bin/bash
# 同步桥接服务部署脚本
# 在有网络的服务器上执行

set -e

INSTALL_DIR="/opt/signin-sync-bridge"
SERVICE_USER="www-data"

echo "=== 部署签到系统同步桥接服务 ==="

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 权限运行"
    exit 1
fi

# 1. 安装依赖
echo "[1/6] 安装系统依赖..."
apt update
apt install -y python3 python3-pip python3-venv git

# 2. 创建用户
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false "$SERVICE_USER"
fi

# 3. 创建目录
echo "[2/6] 创建安装目录..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/backup"

# 4. 复制文件
echo "[3/6] 复制同步脚本..."
cp kdocs_sync/sync_bridge.py "$INSTALL_DIR/"
cp kdocs_sync/sync-bridge.service /etc/systemd/system/
cp kdocs_sync/sync-bridge.timer /etc/systemd/system/

# 5. 创建虚拟环境并安装依赖
echo "[4/6] 创建虚拟环境..."
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install requests

# 6. 配置环境变量
echo "[5/6] 配置环境变量..."
echo "请配置以下参数："
read -p "生产服务器地址 (默认: http://10.45.140.70:3000): " PROD_URL
PROD_URL=${PROD_URL:-"http://10.45.140.70:3000"}

read -p "AirScript Webhook URL: " WEBHOOK_URL
read -p "AirScript Token: " TOKEN

# 更新 service 文件
sed -i "s|your_webhook_url|$WEBHOOK_URL|g" /etc/systemd/system/sync-bridge.service
sed -i "s|your_token|$TOKEN|g" /etc/systemd/system/sync-bridge.service
sed -i "s|http://10.45.140.70:3000|$PROD_URL|g" /etc/systemd/system/sync-bridge.service

# 7. 启动服务
echo "[6/6] 启动定时任务..."
systemctl daemon-reload
systemctl enable sync-bridge.timer
systemctl start sync-bridge.timer

# 8. 验证
echo ""
echo "=== 部署完成 ==="
echo ""
echo "定时任务状态:"
systemctl status sync-bridge.timer --no-pager

echo ""
echo "查看日志:"
echo "  sudo journalctl -u sync-bridge.service -f"
echo "  sudo tail -f /var/log/signin-sync-bridge.log"

echo ""
echo "手动运行测试:"
echo "  sudo systemctl start sync-bridge.service"

echo ""
echo "修改配置:"
echo "  sudo vim /etc/systemd/system/sync-bridge.service"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl restart sync-bridge.timer"
