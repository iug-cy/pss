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
            from bootstrap import auto_install_model
            auto_install_model()
            print(f"🚀 正在从本地路径[{self.model_path}] 加载 Embedding 模型...")
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
        msg_type = msg.get('type', '')
        raw_content = str(msg.get('content', '')).strip()
        if msg_type == "文本消息":
            return raw_content
        elif msg_type in["图片消息", "视频消息", "语音消息"]:
            return f"[发送了一份{msg_type}，本地存储路径或标识:{raw_content}]"
        elif msg_type in ["其他消息", "引用消息"]:
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
        chat_type = "私聊"  # 默认会话类型

        if isinstance(chat_data, dict) and "messages" in chat_data:
            if "session" in chat_data:
                chat_type = chat_data["session"].get("type", "私聊")

            sender_map = {
                s.get('senderID'): s.get('displayName', s.get('nickname', '未知'))
                for s in chat_data.get('senders', [])
            }

            for msg in chat_data.get("messages", []):
                if msg.get("isSend", 0) in [1, True]:
                    owner_name = sender_map.get(msg.get("senderID"), owner_name)
                    break

            for msg in chat_data.get("messages", []):
                content = self._extract_arkme_content(msg)
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
            return [], owner_name, chat_type

        def get_time(record):
            try:
                return datetime.strptime(record["time"], "%Y-%m-%d %H:%M:%S").timestamp()
            except:
                return 0

        messages_to_process.sort(key=get_time)

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

        return grouped_records, owner_name, chat_type

    def convert_groups_to_docs(self, grouped_records: List[Dict], target_name: str = "未知", owner_name: str = "本机主人", chat_type: str = "私聊") -> List[Document]:
        docs = []
        for group_idx, group in enumerate(grouped_records):
            lines = [f"【对话场景：这是提问的主人({owner_name}) 参与的 {chat_type}({target_name}) 的聊天片段】"]
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
                "target_name": target_name,
                "chat_type": chat_type,
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
        grouped_records, parsed_owner, chat_type = self.load_and_group_chat_records(chat_file_path, time_window, target_name=target_name, fallback_owner=owner_name)
        print(f"✅ 完成分组：共{len(grouped_records)}个聊天分组")

        docs = self.convert_groups_to_docs(grouped_records, target_name=target_name, owner_name=parsed_owner, chat_type=chat_type)
        split_docs = self.split_docs(docs)
        collection = self.vectorize_and_store(split_docs, overwrite)

        return {
            "group_count": len(grouped_records),
            "split_doc_count": len(split_docs),
            "vector_count": collection.count(),
            "owner_name": parsed_owner
        }

    def search(self, query: str, top_k: int = 5, where_filter: dict = None) -> List[Dict]:
        query_embedding = self.embed_model.encode(query).tolist()
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": top_k
        }

        if where_filter:
            query_params["where"] = where_filter

        results = self.collection.query(**query_params)

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


