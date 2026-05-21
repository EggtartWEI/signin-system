# 多阶段构建 Dockerfile
# 阶段1：基础依赖
FROM python:3.9-slim as base

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 阶段2：认证服务依赖
FROM base as auth-deps

WORKDIR /app/login

COPY login/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 阶段3：签到系统依赖
FROM base as signin-deps

WORKDIR /app

# 创建 requirements.txt
RUN echo "requests>=2.31.0" > requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt

# 阶段4：最终镜像
FROM python:3.9-slim as production

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 从构建阶段复制 Python 包
COPY --from=auth-deps /root/.local /root/.local
COPY --from=signin-deps /root/.local /root/.local

# 确保使用本地安装的包
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/root/.local/lib/python3.9/site-packages:$PYTHONPATH

# 创建必要的目录
RUN mkdir -p /app/data /app/logs /app/backup /app/login/data

# 复制应用代码
COPY . .

# 设置数据卷
VOLUME ["/app/data", "/app/logs", "/app/backup"]

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
