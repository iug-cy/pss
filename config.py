# pss/config.py
from pathlib import Path

# ===================== 基础路径配置（适配你的目录） =====================
# 自动计算项目根目录（指向pss/，无需手动改）
BASE_DIR = Path(__file__).parent.resolve()

# 模型配置（对应你download_model里的./pss_env/models）
MODEL_ID = "BAAI/bge-m3"                # 要下载的模型ID
LOCAL_MODEL_DIR = BASE_DIR / "pss_md" / "models"  # 本地模型存放路径
LLM_MODEL_DEFAULT = "qwen2.5:7b"        # 默认大模型（ollama）

# 向量库配置（对应根目录的chroma_db）
DB_PATH = BASE_DIR / "chroma_db"        # 向量库路径
COLLECTION_NAME = "chat_history"        # 向量库集合名

# ===================== 业务参数配置 =====================
TIME_WINDOW_DEFAULT = 30    # 聊天分组时间窗口（分钟）
SEARCH_TOP_K = 8            # RAG检索条数
CHAT_HISTORY_MAX_LEN = 4    # 多轮对话记忆长度