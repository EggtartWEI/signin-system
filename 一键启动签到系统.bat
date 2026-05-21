@echo off
chcp 65001 >nul
title 签到系统一键启动
echo.
echo ============================================
echo   签到系统一键启动
echo ============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未安装 Python
    pause
    exit /b 1
)

echo [1/3] 正在启动认证服务...
echo.
start "认证服务-8001" cmd /k "cd /d "%~dp0login" && python attendance_login_only.py"

echo 等待认证服务启动...
timeout /t 5 /nobreak >nul

echo.
echo [2/3] 检查认证服务状态...
curl -s http://localhost:8001/api/status >nul 2>&1
if errorlevel 1 (
    echo 警告: 认证服务可能未正常启动，继续启动签到系统...
) else (
    echo 认证服务运行正常
)

echo.
echo [3/3] 正在启动签到系统...
echo.
cd /d "%~dp0"
python server_with_auth.py

echo.
echo ============================================
echo 服务器已停止
echo ============================================
pause
