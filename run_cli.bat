@echo off
chcp 65001 >nul
call pss_env\Scripts\activate.bat
echo 🚀 正在启动命令行版本...
echo.
python main.py
pause