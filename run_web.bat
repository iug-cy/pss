@echo off
chcp 65001 >nul
call pss_env\Scripts\activate.bat
echo 🚀 正在启动 Web 前端...
echo 浏览器会自动打开，如未打开请手动访问：http://localhost:8501
echo.
python -m streamlit run web/app.py
pause