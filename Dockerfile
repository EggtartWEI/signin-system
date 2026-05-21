# 值班签到系统 Dockerfile
# 多阶段构建，减小镜像体积

# 阶段1：基础镜像
FROM python:3.9-slim as base

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 阶段2：认证服务
FROM base as auth-service

COPY login/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY login/ .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

EXPOSE 8001

CMD ["python", "attendance_login_only.py"]

# 阶段3：签到系统
FROM base as signin-service

# 创建数据目录
RUN mkdir -p /app/data

# 复制签到系统文件
COPY server_with_auth.py .
COPY index.html .
COPY script.js .
COPY styles.css .
COPY logo.png .
COPY data.json ./data.json
COPY mode.json ./mode.json

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

EXPOSE 3000

CMD ["python", "server_with_auth.py"]

# 阶段4：同步服务
FROM base as sync-service

COPY kdocs_sync/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kdocs_sync/ .
COPY data.json /app/data.json

# 定时任务使用 cron
RUN apt-get update && apt-get install -y cron

# 添加定时任务
RUN echo "0 20 * * * cd /app && python sync_via_webhook.py >> /var/log/sync.log 2>&1" | crontab -

CMD ["cron", "-f"]
