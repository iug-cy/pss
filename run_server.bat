@echo off
chcp 65001
color 0A
title MemoryOS 引擎启动序列

echo =======================================================
echo       MemoryOS 端侧跨模态数字记忆引擎 - 计设演示
echo =======================================================
echo.
echo [1/3] 正在自检 Python 运行环境与依赖库...
call D:\Miniconda3\Scripts\activate.bat pss
echo.
echo [2/3] 正在启动多源异构(QQ/微信)自动化转换引擎...
:: 使用 start /b 在后台独立运行你刚写的 convert.py
start /b python core/convert.py

echo.
echo [3/3] 正在唤醒端侧 RAG 架构与 Web 面板...
python main.py web
pause