@echo off
setlocal enabledelayedexpansion

:: 获取脚本所在目录
cd /d "%~dp0"
echo 当前工作目录: %CD%

:: 检查项目结构
if not exist "core" (
    echo [错误]未找到core目录，请确保此脚本在项目根目录运行
    pause
    exit /b 1
)
:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 3.8+
    echo.
    echo 请先安装 Python:
    echo 1. 访问 https://www.python.org/downloads/
    echo 2. 下载并安装 Python 3.8 或更高版本
    echo 3. 安装时请勾选 "Add Python to PATH"
    echo 4. 重新运行此脚本
    echo.
    pause
    exit /b 1
)

:: 检查Python版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [检查] Python %PYTHON_VERSION% 已安装

:: 检查Ollama是否安装
ollama.exe --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 未检测到 Ollama
    echo.
    echo 请安装 Ollama:
    echo 1. 访问 https://ollama.com/download
    echo 2. 下载并安装 Windows 版本
    echo 3. 安装完成后，重新运行此脚本
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('ollama.exe --version 2^>^&1') do set OLLAMA_VERSION=%%i
echo [检查] Ollama %OLLAMA_VERSION% 已安装

:: 创建虚拟环境
echo.
echo [步骤1/4] 创建虚拟环境...
if exist "pss_env" (
    echo [跳过] 虚拟环境已存在
) else (
    python -m venv pss_env
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [完成] 虚拟环境创建成功
)

:: 激活虚拟环境并安装依赖
echo.
echo [步骤2/4] 安装Python依赖...
call pss_env\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [错误] 激活虚拟环境失败
    pause
    exit /b 1
)

:: 升级pip并指定国内镜像源
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet
echo [完成] pip 升级成功

:: 安装依赖
echo 正在从国内镜像源极速下载依赖包，请稍候...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [错误] 安装依赖失败，请检查网络连接。
    pause
    exit /b 1
)
echo [完成] 环境依赖安装成功

:: 下载Embedding模型
echo.
echo [步骤3/4] 检查Embedding模型...
python -c "from config import LOCAL_MODEL_DIR; import os; exit(0 if any(os.path.exists(LOCAL_MODEL_DIR / f) for f in ['pytorch_model.bin', 'model.safetensors']) and (LOCAL_MODEL_DIR / 'config.json').exists() else 1)" 2>nul
if %errorlevel% neq 0 (
    echo [提示] 首次运行将自动下载Embedding模型（约2GB）
    echo [提示] 模型将保存到 pss_md\models 目录
)

:: 创建必要的目录
echo.
echo [步骤4/4] 初始化系统目录...
python -c "from config import DB_PATH, TEMP_DIR, WEFLOW_EXPORT_DIR; DB_PATH.mkdir(parents=True, exist_ok=True); TEMP_DIR.mkdir(parents=True, exist_ok=True); WEFLOW_EXPORT_DIR.mkdir(parents=True, exist_ok=True)"
echo [完成] 系统目录初始化成功

:: 部署完成
echo.
echo ================================================
echo   部署完成！
echo ================================================
echo.
echo 请选择启动模式:
echo   1 - 命令行界面 (CLI)
echo   2 - Web界面
echo   3 - 退出
echo.

set /p choice="请输入选项 (1/2/3): "

if "%choice%"=="1" (
    echo.
    echo 启动命令行界面...
    python main.py
) else if "%choice%"=="2" (
    echo.
    echo 启动Web界面...
    python main.py web
) else (
    echo.
    echo 感谢使用！可以随时运行此脚本重新部署。
)

echo.
pause


