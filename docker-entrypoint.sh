#!/bin/bash
set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== 值班签到系统启动 ===${NC}"

# 检查数据文件是否存在，不存在则创建
if [ ! -f "/app/data.json" ]; then
    echo -e "${YELLOW}创建初始数据文件...${NC}"
    echo '{}' > /app/data.json
fi

if [ ! -f "/app/mode.json" ]; then
    echo -e "${YELLOW}创建初始模式配置...${NC}"
    echo '{"mode": "open", "allowedIPs": []}' > /app/mode.json
fi

if [ ! -f "/app/login/external_users.json" ]; then
    echo -e "${YELLOW}创建初始外委账号文件...${NC}"
    echo '{}' > /app/login/external_users.json
fi

# 创建日志目录
mkdir -p /app/logs /app/login/logs /app/backup

# 启动服务的函数
start_auth_service() {
    echo -e "${GREEN}启动认证服务...${NC}"
    cd /app/login
    python attendance_login_only.py &
    AUTH_PID=$!
    echo $AUTH_PID > /tmp/auth.pid
}

start_signin_service() {
    echo -e "${GREEN}启动签到系统...${NC}"
    cd /app
    python server_with_auth.py &
    SIGNIN_PID=$!
    echo $SIGNIN_PID > /tmp/signin.pid
}

start_sync_cron() {
    echo -e "${GREEN}配置定时同步任务...${NC}"
    # 创建 cron 任务（每天晚上 20:00 执行同步）
    echo "0 20 * * * cd /app/kdocs_sync && python sync_module.py >> /app/logs/sync.log 2>&1" | crontab -
    # 启动 cron
    cron
    echo -e "${GREEN}定时任务已启动${NC}"
}

# 根据参数启动服务
case "${1:-all}" in
    auth)
        start_auth_service
        ;;
    signin)
        start_signin_service
        ;;
    sync)
        start_sync_cron
        ;;
    all)
        start_auth_service
        sleep 5  # 等待认证服务启动
        start_signin_service
        start_sync_cron
        ;;
    *)
        echo "用法: $0 [auth|signin|sync|all]"
        exit 1
        ;;
esac

# 等待所有后台进程
echo -e "${GREEN}所有服务已启动${NC}"
echo -e "${GREEN}签到系统: http://localhost:3000${NC}"
echo -e "${GREEN}认证服务: http://localhost:8001${NC}"

# 捕获信号并优雅退出
trap 'echo -e "${YELLOW}正在停止服务...${NC}"; kill $(jobs -p) 2>/dev/null; exit 0' SIGTERM SIGINT

# 保持容器运行
wait
