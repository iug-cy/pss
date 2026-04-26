#!/bin/bash

# 获取脚本所在目录
cd "$(dirname "$0")"
echo "当前工作目录: $(pwd)"

# 检查项目结构
if [ ! -d "core" ]; then
    echo -e "${RED}[错误] 未找到 core 目录，请确保此脚本在项目根目录运行${NC}"
    exit 1
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[错误] 未检测到 Python 3.8+${NC}"
    echo ""
    echo "请先安装 Python:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv"
    echo "  macOS: brew install python"
    echo "  或访问: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "[检查] Python ${PYTHON_VERSION} 已安装"

# 检查Ollama
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}[警告] 未检测到 Ollama${NC}"
    echo ""
    echo "请安装 Ollama:"
    echo "  Linux: curl -fsSL https://ollama.com/install.sh | sh"
    echo "  macOS: brew install ollama"
    echo "  或访问: https://ollama.com/download"
    echo ""
    exit 1
fi

OLLAMA_VERSION=$(ollama --version)
echo -e "[检查] Ollama ${OLLAMA_VERSION} 已安装"

# 检查虚拟环境
echo ""
echo "[步骤1/4] 创建虚拟环境..."
if [ -d "pss_env" ]; then
    echo "[跳过] 虚拟环境已存在"
else
    python3 -m venv pss_env
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 创建虚拟环境失败${NC}"
        exit 1
    fi
    echo "[完成] 虚拟环境创建成功"
fi

# 激活虚拟环境并安装依赖
echo ""
echo "[步骤2/4] 安装Python依赖..."
source pss_env/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] 激活虚拟环境失败${NC}"
    exit 1
fi

# 升级pip
python -m pip install --upgrade pip -q
echo "[完成] pip 升级成功"

# 安装依赖
pip install -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] 安装依赖失败${NC}"
    exit 1
fi
echo "[完成] 依赖安装成功"

# 检查Embedding模型
echo ""
echo "[步骤3/4] 检查Embedding模型..."
python3 -c "from config import LOCAL_MODEL_DIR; import os; exit(0 if any(os.path.exists(LOCAL_MODEL_DIR / f) for f in ['pytorch_model.bin', 'model.safetensors']) and (LOCAL_MODEL_DIR / 'config.json').exists() else 1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "[提示] 首次运行将自动下载Embedding模型（约2GB）"
    echo -e "[提示] 模型将保存到 pss_md/models 目录"
fi

# 创建必要的目录
echo ""
echo "[步骤4/4] 初始化系统目录..."
python3 -c "from config import DB_PATH, TEMP_DIR, WEFLOW_EXPORT_DIR; DB_PATH.mkdir(parents=True, exist_ok=True); TEMP_DIR.mkdir(parents=True, exist_ok=True); WEFLOW_EXPORT_DIR.mkdir(parents=True, exist_ok=True)"
echo "[完成] 系统目录初始化成功"

# 部署完成
echo ""
echo "================================================"
echo "  部署完成！"
echo "================================================"
echo ""
echo "请选择启动模式:"
echo "  1 - 命令行界面 (CLI)"
echo "  2 - Web界面"
echo "  3 - 退出"
echo ""

read -p "请输入选项 (1/2/3): " choice

if [ "$choice" = "1" ]; then
    echo ""
    echo "启动命令行界面..."
    python main.py
elif [ "$choice" = "2" ]; then
    echo ""
    echo "启动Web界面..."
    python main.py web
else
    echo ""
    echo "感谢使用！可以随时运行此脚本重新部署。"
fi
