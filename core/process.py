import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union
from sentence_transformers import SentenceTransformer
import chromadb
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid

# --- 初始化配置 ---
#DB_PATH = "../chroma_db"
#COLLECTION_NAME = "chat_history"
#MODEL_PATH = "../pss_md/models"

# BASE_DIR = Path(__file__).parent.parent.resolve()
# 基于根目录生成绝对路径，100%适配目录结构
# DB_PATH = str(BASE_DIR / "chroma_db")
# COLLECTION_NAME = "chat_history"
# MODEL_PATH = str(BASE_DIR / "pss_md" / "models")

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ========== 导入config配置（替换原有硬编码） ==========
from config import DB_PATH, COLLECTION_NAME, LOCAL_MODEL_DIR

class ChatRecordProcessor:
    """
    - 支持自动识别并解析 Arkme JSON 格式与基础 JSON 格式
    - 使用 sentence-transformers 直接加载本地模型
    - 使用原生 chromadb 客户端管理向量库
    """

    def __init__(
            self,
            db_path: str = DB_PATH,
            collection_name: str = COLLECTION_NAME,
            model_path: str = str(LOCAL_MODEL_DIR),
            device: str = "cpu"  # 或 "cuda"
    ):
        self.db_path = db_path
        self.collection_name = collection_name
        self.model_path = model_path
        self.device = device

        # 懒加载组件
        self._embed_model = None
        self._chroma_client = None
        self._collection = None
        self._text_splitter = None

        # 确保数据库目录存在
        Path(db_path).mkdir(parents=True, exist_ok=True)

    @property
    def embed_model(self) -> SentenceTransformer:
        """加载本地Embedding模型"""
        if self._embed_model is None:
            # 🌟 绝杀技 1：在真正初始化模型前，拦截并检查是否需要下载
            from bootstrap import auto_install_model
            auto_install_model()

            print(f"🚀 正在从本地路径[{self.model_path}] 加载 Embedding 模型...")

            # 🌟 绝杀技 2：加入 local_files_only=True
            # 这行代码极其重要！它能死死按住 SentenceTransformer，
            # 绝对不允许它在后台偷偷连接 HuggingFace（防止国内网络报错卡死）
            self._embed_model = SentenceTransformer(
                self.model_path,
                device=self.device,
                local_files_only=True
            )
            print("✅ 模型加载完成！")

        return self._embed_model

    @property
    def chroma_client(self) -> chromadb.PersistentClient:
        """ChromaDB客户端"""
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(path=self.db_path)
        return self._chroma_client

    @property
    def collection(self) -> chromadb.Collection:
        """获取或创建集合"""
        if self._collection is None:
            self._collection = self.chroma_client.get_or_create_collection(name=self.collection_name)
        return self._collection

    @property
    def text_splitter(self) -> RecursiveCharacterTextSplitter:
        """中文聊天切分器"""
        if self._text_splitter is None:
            self._text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150,
                separators=["\n", "。", "！", "？", "；", "：", "，", " ", ""],
                length_function=len,
                keep_separator=False
            )
        return self._text_splitter

    def _extract_arkme_content(self, msg: dict) -> str:
        """【核心亮点】深度提取 Arkme 复杂消息格式"""
        msg_type = msg.get('type', '')
        raw_content = msg.get('content', '')

        if msg_type == "文本消息":
            return raw_content
        elif msg_type in ["图片消息", "视频消息", "语音消息"]:
            # WeFlow 导出的多模态，其 raw_content 通常是相对路径，如 ../images/xxx.png
            # 记录下来，方便日后直接溯源
            return f"[发送了一份{msg_type}，本地存储路径或标识:{raw_content}]"
        elif msg_type in ["其他消息", "引用消息"]:
            # 微信的文件名通常藏在 musicTitle 或 title 里
            title = msg.get('musicTitle') or msg.get('finderTitle') or msg.get('title')
            if title:
                return f"[发送了一份文件/链接，文件名称为：{title}]"
            else:
                return f"[{msg_type}：{raw_content}]"
        elif msg_type == "动画表情":
            return "[发送了动画表情]"
        else:
            return f"[{msg_type}]"

    def load_and_group_chat_records(
            self,
            chat_file_path: str,
            time_window: int = 5,
            min_msg_count: int = 1,
            target_name: str = "对方",
            fallback_owner: str = "本机主人"
    ) -> tuple:
        """加载JSON并按时间窗口分组 (自适应 Arkme 格式)"""
        try:
            with open(chat_file_path, "r", encoding="utf-8") as f:
                chat_data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"加载聊天记录失败: {e}")

        messages_to_process = []
        owner_name = fallback_owner

        if isinstance(chat_data, dict) and "messages" in chat_data:
            sender_map = {
                s.get('senderID'): s.get('displayName', s.get('nickname', '未知'))
                for s in chat_data.get('senders', [])
            }
            # 🌟 从本地 Arkme 文件中提取主人的名字
            for msg in chat_data.get("messages", []):
                if msg.get("isSend", 0) in [1, True]:
                    owner_name = sender_map.get(msg.get("senderID"), owner_name)
                    break

            for msg in chat_data.get("messages", []):
                content = self._extract_arkme_content(msg)

                # 彻底抛弃“我”，直接使用真实人名
                is_send = msg.get("isSend", 0)
                if is_send in [1, True]:
                    sender = owner_name
                else:
                    sender_id = msg.get("senderID")
                    sender = sender_map.get(sender_id, target_name)
                    if str(sender).startswith("wxid_"): sender = target_name

                time_str = msg.get("formattedTime", "")
                messages_to_process.append(
                    {"time": time_str, "sender": sender, "content": content, "type": msg.get("type", "text")})
        elif isinstance(chat_data, list):
            messages_to_process = chat_data
        else:
            return [], owner_name

        # ---------------------------------------------------------
        # 🌟 核心修复 1：终极防线 - 强制按时间正序排列
        # 无论 API 还是本地文件，彻底杜绝“时间倒流”现象
        # ---------------------------------------------------------
        def get_time(record):
            try:
                return datetime.strptime(record["time"], "%Y-%m-%d %H:%M:%S").timestamp()
            except:
                return 0

        messages_to_process.sort(key=get_time)

        # ---------------------------------------------------------
        # 2. 核心：基于时间窗口的聚合分组
        # ---------------------------------------------------------
        grouped_records = []
        current_group = None

        for record in messages_to_process:
            content = str(record.get("content") or "").strip()
            sender = str(record.get("sender") or "未知").strip()
            time_str = str(record.get("time") or "")
            msg_type = str(record.get("type") or "text")

            if not content:
                continue

            try:
                current_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            except:
                current_time = datetime.now()
                time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

            if not current_group:
                # 🌟 修复: 必须存入 time_str
                current_group = {"messages": [(time_str, sender, content)], "senders": {sender}, "start_time": time_str,
                                 "end_time": time_str, "type": msg_type, "last_time": current_time, "msg_count": 1}
                continue

            time_diff = abs((current_time - current_group["last_time"]).total_seconds() / 60)

            if time_diff <= time_window:
                current_group["messages"].append((time_str, sender, content))  # 🌟 存入 time_str
                current_group["senders"].add(sender)
                current_group["end_time"] = time_str
                current_group["last_time"] = current_time
                current_group["msg_count"] += 1
            else:
                if current_group["msg_count"] >= min_msg_count:
                    grouped_records.append(current_group)
                current_group = {"messages": [(time_str, sender, content)], "senders": {sender}, "start_time": time_str,
                                 "end_time": time_str, "type": msg_type, "last_time": current_time, "msg_count": 1}

        if current_group and current_group["msg_count"] >= min_msg_count:
            grouped_records.append(current_group)

        for group in grouped_records:
            group["sender"] = ", ".join(sorted(group["senders"]))
            start_dt = datetime.strptime(group["start_time"], "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(group["end_time"], "%Y-%m-%d %H:%M:%S")
            group["duration"] = round((end_dt - start_dt).total_seconds() / 60, 1)

        return grouped_records, owner_name

    # ...[ convert_groups_to_docs, split_docs, vectorize_and_store, full_process, search 均保持原样不变！] ...
    def convert_groups_to_docs(self, grouped_records: List[Dict], target_name: str = "未知", owner_name: str = "本机主人") -> List[Document]:
        docs = []
        for group_idx, group in enumerate(grouped_records):
            # 🌟 上帝视角注入：让向量模型一眼看穿这是谁的聊天！
            lines = [f"【对话场景：这是提问的主人({owner_name}) 与 聊天对象({target_name}) 的微信聊天片段】"]

            for t, s, c in group["messages"]:
                if s in ["我", owner_name]:
                    display_s = f"主人({owner_name})"
                elif s in ["对方", target_name, "未知"]:
                    display_s = f"聊天对象({target_name})"
                else:
                    display_s = s  # 其他群成员

                lines.append(f"[{t}] {display_s}：{c}")

            merged_content = "\n".join(lines)
            metadata = {
                "owner_name": owner_name,
                "target_name": target_name,  # 存入元数据，方便以后做精确过滤
                "start_time": group["start_time"],
                "end_time": group["end_time"],
                "date": group["start_time"].split(" ")[0],
                "msg_count": group["msg_count"],
                "duration": group["duration"],
                "group_idx": group_idx
            }
            docs.append(Document(page_content=merged_content, metadata=metadata))
        return docs

    def split_docs(self, docs: List[Document]) -> List[Document]:
        split_docs = []
        for doc in docs:
            chunks = self.text_splitter.split_documents([doc])
            for chunk_idx, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "chunk_idx": chunk_idx,
                    "total_chunks": len(chunks)
                })
                split_docs.append(chunk)
        return split_docs

    def vectorize_and_store(self, split_docs: List[Document], overwrite: bool = False) -> chromadb.Collection:
        if overwrite:
            try:
                self.chroma_client.delete_collection(self.collection_name)
                self._collection = self.chroma_client.create_collection(self.collection_name)
            except Exception:
                pass

        documents = [doc.page_content for doc in split_docs]
        metadatas = [doc.metadata for doc in split_docs]
        # 🌟 致命 Bug 修复：使用 UUID 生成绝对唯一的 ID，保证每次导入必定成功！
        batch_hash = uuid.uuid4().hex[:6]
        ids = [f"doc_{batch_hash}_{i}" for i in range(len(split_docs))]

        embeddings = self.embed_model.encode(documents, show_progress_bar=True, batch_size=32).tolist()

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )
        return self.collection

    def full_process(self, chat_file_path: str, time_window: int = 5, overwrite: bool = False, target_name: str = "对方", owner_name: str = "本机主人"):
        print(f"开始加载聊天记录：{chat_file_path}")
        grouped_records, parsed_owner = self.load_and_group_chat_records(chat_file_path, time_window, target_name=target_name, fallback_owner=owner_name)
        print(f"✅ 完成分组：共{len(grouped_records)}个聊天分组")

        docs = self.convert_groups_to_docs(grouped_records, target_name=target_name, owner_name=parsed_owner)
        split_docs = self.split_docs(docs)
        collection = self.vectorize_and_store(split_docs, overwrite)

        return {
            "group_count": len(grouped_records),
            "split_doc_count": len(split_docs),
            "vector_count": collection.count(),
            "owner_name": parsed_owner
        }

    def search(self, query: str, top_k: int = 5, where_filter: dict = None) -> List[Dict]:
        """
        高级搜索接口：支持纯向量语义搜索 + 元数据精准过滤
        """
        query_embedding = self.embed_model.encode(query).tolist()
        # 动态构造查询参数
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": top_k
        }

        # 🌟 如果传入了过滤条件，就加上 where 语法
        if where_filter:
            query_params["where"] = where_filter

        # 执行原生查询
        results = self.collection.query(**query_params)

        # 将恶心的原生嵌套结构，清洗为优雅的 List[Dict]
        formatted_results = []
        if results.get("ids") and len(results["ids"]) > 0 and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })
        return formatted_results


# ====================== 测试运行 ======================
if __name__ == "__main__":
    processor = ChatRecordProcessor(
        db_path=DB_PATH,
        collection_name=COLLECTION_NAME,
        model_path=LOCAL_MODEL_DIR,
        device="cpu"
    )

    # 【这里换成你的 Arkme 文件路径】
    test_file = "../data/texts/私聊_谭启翔.json"

    # 扩大 time_window，比如把30分钟内（1800秒）的聊天当成同一个会话
    result = processor.full_process(
        chat_file_path=test_file,
        time_window=30,
        overwrite=True
    )

    print("\n===== 测试搜索 (试试搜图片或文件) =====")
    # 模拟搜索 Arkme 文件中独有的内容
    search_results = processor.search("他的自动控制原理发货了吗", top_k=2)
    for i, res in enumerate(search_results):
        print(f"\n【结果 {i + 1}】")
        print(f"时间范围：{res['metadata']['start_time']} - {res['metadata']['end_time']}")
        print(f"内容：\n{res['content']}")