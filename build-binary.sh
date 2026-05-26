#!/bin/bash
# 打包签到系统为二进制可执行文件
# 在 Linux 环境下执行（可用 WSL 或虚拟机）

set -e

echo "=== 打包签到系统为二进制文件 ==="

# 安装依赖
pip install pyinstaller

# 创建临时目录
mkdir -p build
cd build

# 复制必要文件
cp -r ../login .
cp ../server_with_auth.py .
cp ../data.json .
cp ../mode.json .
cp ../index.html .
cp ../script.js .
cp ../styles.css .
cp ../logo.png .

# 打包签到系统主程序
echo "打包签到系统..."
pyinstaller \
    --onefile \
    --name signin-server \
    --add-data "index.html:." \
    --add-data "script.js:." \
    --add-data "styles.css:." \
    --add-data "logo.png:." \
    --add-data "data.json:." \
    --add-data "mode.json:." \
    --hidden-import http.server \
    --hidden-import socketserver \
    server_with_auth.py

# 打包认证服务
echo "打包认证服务..."
cd login
pyinstaller \
    --onefile \
    --name signin-auth \
    --add-data "external_users.json:." \
    --add-data "login_page.html:." \
    --hidden-import fastapi \
    --hidden-import uvicorn \
    --hidden-import pydantic \
    --hidden-import Crypto \
    attendance_login_only.py

cd ..

# 整理输出
echo "整理输出文件..."
mkdir -p ../dist/signin-system-binary
cp dist/signin-server ../dist/signin-system-binary/
cp login/dist/signin-auth ../dist/signin-system-binary/
cp data.json ../dist/signin-system-binary/
cp mode.json ../dist/signin-system-binary/
cp -r login ../dist/signin-system-binary/

echo "=== 打包完成 ==="
echo "输出目录: dist/signin-system-binary/"
echo ""
echo "文件列表:"
ls -lh ../dist/signin-system-binary/
