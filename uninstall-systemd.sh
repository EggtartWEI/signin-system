#!/bin/bash
# 卸载签到系统

INSTALL_DIR="/opt/signin-system"

echo "=== 卸载值班签到系统 ==="

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 权限运行"
    exit 1
fi

# 确认
read -p "确定要卸载吗？数据将保留在 $INSTALL_DIR/backup (y/N) " confirm
if [[ $confirm != [yY] ]]; then
    echo "取消卸载"
    exit 0
fi

# 停止并禁用服务
echo "停止服务..."
systemctl stop signin-app signin-auth 2>/dev/null || true
systemctl disable signin-app signin-auth 2>/dev/null || true

# 删除服务文件
rm -f /etc/systemd/system/signin-auth.service
rm -f /etc/systemd/system/signin-app.service
systemctl daemon-reload

# 备份数据
echo "备份数据..."
mkdir -p "$INSTALL_DIR/backup"
cp "$INSTALL_DIR/data.json" "$INSTALL_DIR/backup/data-final.json" 2>/dev/null || true

# 删除安装目录
echo "删除安装文件..."
rm -rf "$INSTALL_DIR"

echo "卸载完成！"
echo "数据备份在: $INSTALL_DIR/backup/"
