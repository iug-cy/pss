from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
# WeFlow默认批量导出目录
WEFLOW_EXPORT_DIR = BASE_DIR / "data" / "texts"

# 临时文件目录
TEMP_DIR = BASE_DIR / "temp"

# 模型配置
MODEL_ID = "BAAI/bge-m3"
LOCAL_MODEL_DIR = BASE_DIR / "pss_md" / "models"  # 本地模型存放路径
LLM_MODEL_DEFAULT = "qwen2.5:7b"        # 默认大模型
WEFLOW_API_URL = "http://127.0.0.1:5031" # WeFlow后台API服务地址

# 向量库配置
DB_PATH = BASE_DIR / "chroma_db"        # 向量库路径
COLLECTION_NAME = "chat_history"        # 向量库集合名

# 参数配置
TIME_WINDOW_DEFAULT = 30    # 聊天分组时间窗口（分钟）
SEARCH_TOP_K = 5            # RAG检索条数
CHAT_HISTORY_MAX_LEN = 4    # 多轮对话记忆长度