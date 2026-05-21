@echo off
chcp 65001 >nul
title 签到数据云同步 - 定时任务
echo.
echo ============================================
echo   签到数据云同步 - 定时任务
echo   执行时间: %date% %time%
echo ============================================
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未安装 Python
    exit /b 1
)

echo 正在执行同步...
echo.

REM 执行同步脚本（使用新的模块）
python -c "from sync_module import sync_all_data; sync_all_data()"

REM 记录执行结果
if errorlevel 1 (
    echo.
    echo ============================================
    echo   同步失败 - %date% %time%
    echo ============================================
    exit /b 1
) else (
    echo.
    echo ============================================
    echo   同步成功 - %date% %time%
    echo ============================================
    exit /b 0
)
