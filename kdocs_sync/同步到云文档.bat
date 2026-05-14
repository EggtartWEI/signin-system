@echo off
chcp 65001 >nul
title 签到数据同步到金山云文档
echo.
echo ============================================
echo   签到数据同步到金山云文档
echo ============================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未安装 Python
    echo 请先安装 Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo 正在运行同步脚本...
echo.

REM 运行同步脚本
python sync_via_webhook.py

if errorlevel 1 (
    echo.
    echo ============================================
    echo   同步失败
    echo ============================================
    pause
    exit /b 1
) else (
    echo.
    echo ============================================
    echo   同步完成
    echo ============================================
    echo.
    echo 正在打开云文档...
    start https://www.kdocs.cn/l/cqrKey08JOk2
    timeout /t 3 >nul
    exit /b 0
)
