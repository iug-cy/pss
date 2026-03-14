@echo off

echo ===============================
echo PSS 环境自动安装
echo ===============================

echo 检查 Python
python --version

echo.
echo 创建虚拟环境
python -m venv pss_env

echo.
echo 激活虚拟环境
call pss_env\Scripts\activate

echo.
echo 升级 pip
python -m pip install --upgrade pip

echo.
echo 安装依赖
pip install -r requirements.txt

echo.
echo ===============================
echo 安装完成
echo ===============================

pause