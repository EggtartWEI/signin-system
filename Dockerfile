# 值班签到系统 Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 复制并安装依赖
COPY login/requirements.txt /app/login/
RUN pip install --no-cache-dir -r /app/login/requirements.txt

# 复制应用代码
COPY . /app/

# 创建必要的目录
RUN mkdir -p /app/data /app/logs /app/backup /app/login/data /app/login/logs

# 暴露端口
EXPOSE 3000 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000 && curl -f http://localhost:8001/health || exit 1

# 启动脚本
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["all"]
