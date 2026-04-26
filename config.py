# pss/config.py
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

# WeFlow 默认批量导出目录
WEFLOW_EXPORT_DIR = BASE_DIR / "data" / "texts"

# 临时文件目录（用于上传、API缓存等，阅后即焚）
TEMP_DIR = BASE_DIR / "temp"

# 模型配置
MODEL_ID = "BAAI/bge-m3"                # 要下载的模型ID
LOCAL_MODEL_DIR = BASE_DIR / "pss_md" / "models"  # 本地模型存放路径
LLM_MODEL_DEFAULT = "qwen2.5:7b"        # 默认大模型（ollama）
WEFLOW_API_URL = "http://127.0.0.1:5031" # WeFlow 后台 API 服务地址

# 向量库配置（对应根目录的chroma_db）
DB_PATH = BASE_DIR / "chroma_db"        # 向量库路径
COLLECTION_NAME = "chat_history"        # 向量库集合名

# 业务参数配置
TIME_WINDOW_DEFAULT = 30    # 聊天分组时间窗口（分钟）
SEARCH_TOP_K = 5            # RAG检索条数
CHAT_HISTORY_MAX_LEN = 4    # 多轮对话记忆长度