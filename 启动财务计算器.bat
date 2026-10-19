@echo off
chcp 65001 >nul
title 财务管理综合计算器
cd /d "%~dp0"

echo ==================================================
echo   财务管理综合计算器
echo   正在启动本地图形界面，请稍候...
echo   浏览器未自动打开时，请访问 http://localhost:8501
echo ==================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python。请先安装 Python 3.9 或更高版本。
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import streamlit" >nul 2>nul
if errorlevel 1 (
    echo [提示] 首次运行，正在安装依赖库...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络后重试。
        pause
        exit /b 1
    )
)

echo [提示] 浏览器将自动打开。关闭此窗口即可停止程序。
echo.
python -m streamlit run app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false

if errorlevel 1 (
    echo.
    echo [错误] 启动失败。请检查端口 8501 是否被占用，或运行 python selftest.py 检查环境。
    pause
)
