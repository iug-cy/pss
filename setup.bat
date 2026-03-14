```bat
@echo off
chcp 65001 >nul
echo ========================================
echo  私人微信聊天记录搜索引擎 一键部署
echo ========================================

echo.
echo [1/5] 严格验证 Python 版本...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到 Python，请先安装 Python 3.10.x
    echo 下载地址：https://www.python.org/downloads/release/python-31011/
    pause
    exit
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo 当前 Python 版本：%PYTHON_VERSION%

echo %PYTHON_VERSION% | findstr /b "3.10" >nul
if errorlevel 1 (
    echo ❌ Python 版本不兼容！
    echo 当前版本：%PYTHON_VERSION%
    echo 要求版本：Python 3.10.x
    echo.
    echo 请卸载当前 Python，安装 Python 3.10.x
    echo 下载地址：https://www.python.org/downloads/release/python-31011/
    pause
    exit
)
echo ✅ Python 3.10 版本验证通过

echo.
echo [2/5] 创建虚拟环境...
if not exist "pss_env" (
    python -m venv pss_env
)
echo ✅ 虚拟环境就绪

echo.
echo [3/5] 安装依赖（需要几分钟，请耐心等待）...
call pss_env\Scripts\activate.bat
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ✅ 依赖安装完成

echo.
echo [4/5] 初始化运行环境（自动下载模型）...
python bootstrap.py
echo ✅ 环境初始化完成

echo.
echo ========================================
echo  🎉 部署完成！
echo ========================================
echo.
echo  🚀 启动方式：
echo  1. Web 前端：双击 run_web.bat
echo  2. 命令行：双击 run_cli.bat
echo.
pause