@echo off
chcp 65001 >nul
color 0A
title MemoraOS——端侧记忆认知系统
cd /d "%~dp0"
echo =======================================================
echo       MemoraOS——端侧记忆认知系统
echo =======================================================
echo.
:: 检查虚拟环境是否已由deploy.bat创建
if not exist "pss_env\Scripts\activate.bat" (
    color 0C
    echo [错误] 未找到虚拟环境！
    echo 请先双击运行本目录下的 deploy.bat 进行环境一键安装。
    pause
    exit /b 1
)
echo [1/3] 正在自检Python运行环境与依赖库...
call pss_env\Scripts\activate.bat
echo.
echo[2/3] 正在启动多源异构自动化转换后台引擎...
:: 使用后台启动转换监控脚本
start /b python core/convert.py
echo.
echo [3/3] 正在唤醒端侧 RAG 架构与 Web 面板...
python main.py web
pause