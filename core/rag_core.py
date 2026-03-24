import os
import re


import json
import time
import datetime
import pandas as pd
from docx import Document as DocxDocument
import ollama

from core.weflow_client import WeFlowAPIClient
from core.process import ChatRecordProcessor
from config import LLM_MODEL_DEFAULT, SEARCH_TOP_K, CHAT_HISTORY_MAX_LEN

class PrivateMemoryAssistant:
    def __init__(self, llm_model: str = 'qwen2.5:7b'):
        self.llm_model = llm_model
        self.processor = ChatRecordProcessor()
        self.api_client = WeFlowAPIClient()
        self.chat_history = []

    def import_from_export_dir(self, target_name: str, export_dir: str) -> tuple:
        """
        自动扫描 WeFlow 的导出目录，寻找目标人物的文件并导入
        """
        self.chat_history.clear()
        os.makedirs(export_dir, exist_ok=True)
        if not os.path.exists(export_dir):
            return False, f"❌ 导出目录不存在，且自动创建失败: {export_dir}，请在左侧侧边栏配置正确的路径。"

        # 1. 在目录中进行模糊搜索
        matched_files = []
        for file_name in os.listdir(export_dir):
            # 只要文件名包含目标人物的名字，且是json文件，就抓取
            if target_name in file_name and file_name.endswith('.json'):
                matched_files.append(os.path.join(export_dir, file_name))

        if not matched_files:
            return False, f"❌ 未在导出目录中找到包含【{target_name}】的聊天记录。\n请确认您是否已在 WeFlow 软件中将其导出。"

        # 2. 如果找到多个，默认取第一个
        target_file = matched_files[0]

        try:
            import_msg = self.import_local_file(target_file, alias=target_name)
            return True, f"📁 自动定位到文件：`{os.path.basename(target_file)}`\n\n{import_msg}"
        except Exception as e:
            return False, f"❌ 自动导入失败: {e}"

    def import_local_file(self, file_path: str, alias: str = None) -> str:
        self.chat_history.clear()
        if not os.path.exists(file_path): return f"❌ 找不到文件: {file_path}"

        target_name = alias or os.path.basename(file_path).split('.')[0].replace("私聊_", "")

        # 执行覆盖清理
        self._delete_old_records(target_name)

        ext = os.path.splitext(file_path)[-1].lower()
        if ext == '.json':
            result = self.processor.full_process(chat_file_path=file_path, time_window=30, target_name=target_name)
            return f"✅ 成功覆盖更新微信 JSON！生成了 {result['split_doc_count']} 个记忆块。本机主人被识别为：【{result.get('owner_name')}】"

        # 2. 如果是其他普通文档，走基础读取通道
        docs_content = []
        try:
            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    docs_content = [line.strip() for line in f if line.strip()]
            elif ext in ['.csv', '.xlsx', '.xls']:
                df = pd.read_csv(file_path) if ext == '.csv' else pd.read_excel(file_path)
                docs_content = df.astype(str).fillna('').agg(' '.join, axis=1).tolist()
            elif ext == '.docx':
                doc = DocxDocument(file_path)
                docs_content = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            else:
                return f"❌ 不支持的文件格式: {ext}"

            if not docs_content:
                return "⚠️ 文件为空或读取失败。"

            # 生成向量并存入数据库(复用 processor的Chroma客户端)
            current_time = int(time.time())
            ids = [f"file_{current_time}_{i}" for i in range(len(docs_content))]
            embeddings = self.processor.embed_model.encode(docs_content).tolist()

            # 这里补充一点元数据
            metadatas = [{"source": os.path.basename(file_path)} for _ in range(len(docs_content))]

            self.processor.collection.add(
                ids=ids,
                documents=docs_content,
                embeddings=embeddings,
                metadatas=metadatas
            )
            return f"✅ 成功导入补充文档！共 {len(docs_content)} 条数据。"

        except Exception as e:
            return f"❌ 导入文件出错: {e}"

    def import_from_weflow_api(self, wxid: str, alias: str = None, limit: int = 5000) -> str:
        """通过 API 自动获取并入库"""
        self.chat_history.clear()
        api_name, owner_name, data_list = self.api_client.fetch_messages(wxid, limit)

        if not data_list:
            return "❌ 未获取到有效数据，请检查 wxid 或 WeFlow API 状态。"

        final_target_name = alias or api_name
        self._delete_old_records(final_target_name)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        temp_dir = os.path.join(base_dir, "..", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, f"temp_api_{wxid}.json")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data_list, f, ensure_ascii=False)

            result = self.processor.full_process(chat_file_path=temp_file, time_window=30, target_name=final_target_name, owner_name=owner_name)
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return f"✅ API 同步成功！微信对话已拆分为 {result['split_doc_count']} 个语义块入库。"
        except Exception as e:
            return f"❌ API 数据处理失败: {e}"

    def resolve_name_to_wxid(self, name: str) -> str:
        """供前端 Agent 调用的接口：人名转 WXID"""
        return self.api_client.find_wxid_by_name(name)

    def clear_memory(self) -> str:
        """清空向量库和当前对话记忆"""
        try:
            self.processor.chroma_client.delete_collection(self.processor.collection_name)
            self.processor._collection = None
            self.chat_history =[] # 同时清空多轮对话记忆
            return "✅ 记忆库与对话上下文已彻底清空！"
        except Exception as e:
            return f"❌ 清空失败/已经是空的: {e}"

    def _delete_old_records(self, target_name: str):
        try:
            self.processor.collection.delete(where={"target_name": target_name})
            print(f"♻️ 已自动清理【{target_name}】的历史旧数据，准备覆写新记忆...")
        except Exception:
            pass

    def _parse_time_intent(self, query: str) -> list:
        """
        精确时间信息，强化搜索
        """
        current_time = datetime.datetime.now()
        target_dates = []
        base_year = current_time.year
        if re.search(r'(去年)', query):
            base_year -= 1
        elif re.search(r'(前年)', query):
            base_year -= 2

        # 1. 相对天数
        if re.search(r'(今天|今日)', query):
            target_dates.append(current_time.strftime("%Y-%m-%d"))
        if re.search(r'(昨天|昨日)', query):
            target_dates.append((current_time - datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
        if re.search(r'(前天)', query):
            target_dates.append((current_time - datetime.timedelta(days=2)).strftime("%Y-%m-%d"))

        # 2. 相对周数
        if re.search(r'(上周|最近一周|这几天|这周|本周)', query):
            for i in range(0, 8):
                target_dates.append((current_time - datetime.timedelta(days=i)).strftime("%Y-%m-%d"))

        # 3. 绝对具体日期 (例如：3月10日, 2026年3月10号)
        date_pattern = r'(?:(\d{2,4})年)?(\d{1,2})月(\d{1,2})[日号]?'
        for match in re.finditer(date_pattern, query):
            y = int(match.group(1)) if match.group(1) else base_year
            m = int(match.group(2))
            d = int(match.group(3))
            try:
                target_dates.append(f"{y:04d}-{m:02d}-{d:02d}")
            except ValueError:
                pass

        # 4. 绝对月份 (例如：去年3月, 3月份)
        if not target_dates:
            month_pattern = r'(?:(\d{2,4})年)?(\d{1,2})月份?'
            for match in re.finditer(month_pattern, query):
                y = int(match.group(1)) if match.group(1) else base_year
                m = int(match.group(2))
                for d in range(1, 32):
                    try:
                        datetime.datetime(y, m, d)
                        target_dates.append(f"{y:04d}-{m:02d}-{d:02d}")
                    except ValueError:
                        pass

        return list(set(target_dates))

    def ask(self, question: str) -> dict:
        """
        核心问答接口：返回字典，包含大模型的回答和参考来源。
        """
        current_time = datetime.datetime.now()
        current_date_str = current_time.strftime("%Y-%m-%d")
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

        # NLP 提取时间
        target_dates = self._parse_time_intent(question)

        where_clauses = []
        if len(target_dates) == 1:
            where_clauses.append({"date": target_dates[0]})
        elif len(target_dates) > 1:
            where_clauses.append({"date": {"$in": target_dates}})

        # 提取群聊/私聊意图
        if "私聊" in question:
            where_clauses.append({"chat_type": "私聊"})
        elif "群聊" in question:
            where_clauses.append({"chat_type": "群聊"})

        filter_dict = None
        if len(where_clauses) == 1:
            filter_dict = where_clauses[0]
        elif len(where_clauses) > 1:
            filter_dict = {"$and": where_clauses}
        fallback_warning = ""

        if target_dates:
            target_dates.sort()
            date_range_str = f"[{target_dates[0]}]" if len(
                target_dates) == 1 else f"[{target_dates[0]} 至 {target_dates[-1]}]"
            print(f"💡 NLP 解析成功！已启动强制时间结界，锁定查询范围: {date_range_str}")

        try:
            # 第一次检索（带严格过滤条件）
            search_results = self.processor.search(
                query=question,
                top_k=SEARCH_TOP_K,
                where_filter=filter_dict
            )
            # 降级搜索
            if not search_results and filter_dict:
                print("💡 严格条件未命中，启动全库降级检索...")
                search_results = self.processor.search(query=question, top_k=SEARCH_TOP_K, where_filter=None)
                fallback_warning = f"\n【系统重要警告】：主人询问了特定的时间（如今天、3月10日），但在该限定条件内没有找到任何聊天记录！以下提供的记录是我在**全库其他历史时间**中找到的。请在回答开头明确告知主人：在指定时间没有记录，但在历史时间(说出具体日期)找到了以下线索！\n"
        except Exception as e:
            print(f"检索出错: {e}")
            search_results = []

        if not search_results:
            time_tip = "在该特定时间段内" if target_dates else ""
            return {
                "answer": f"记忆库中未找到相关的线索。{time_tip}没有发生相关的聊天。",
                "sources": [],
                "raw_context": ""
            }

        dynamic_owner_name = search_results[0]['metadata'].get('owner_name', '本机主人')

        context_parts = []
        sources = []
        for i, res in enumerate(search_results):
            content = res['content']
            meta = res['metadata']
            time_range = f"{meta.get('start_time', '')} - {meta.get('end_time', '')}"
            c_type = meta.get('chat_type', '私聊')
            src_str = f"来源 {i + 1}: 【{c_type}】与 {meta.get('target_name', '未知')} ({time_range})"
            sources.append(src_str)
            context_parts.append(f"--- 片段 {i + 1} ---\n{content}")

        context_text = "\n\n".join(context_parts)

        system_prompt = f"""
        你是一个逻辑极其严密的私人记忆助理。请仔细阅读【参考聊天记录】并回答。
        {fallback_warning}
        【核心推理法则（必须严格遵守）】：
        1. 🕵️ 跨会话第三方情报捕捉（极度重要！）：当用户询问“某人（如胡老师）的事”时，答案不仅可能在与该人的直接对话中，还极有可能隐藏在与“其他人”的聊天讨论中！
        - 你必须仔细阅读所有片段的【内容】，绝不能因为片段头部是“与A的聊天”就忽略里面关于B的线索！
        2. 🎭 角色代入：片段中出现的“我”代表用户本人。每段开头的【这是你与 XXX 的聊天片段】说明了当前对话的另一方是谁。
        
        【极度重要法则】：
        1. 身份绑定：“{dynamic_owner_name}” 是向你提问的主人。
        2. 场景隔离：仔细阅读片段开头的【对话场景】。如果主人问“私聊里发的”，你绝不能拿“群聊”的记录去充数！
        3. 绝对真实：如果你提供的【参考聊天片段】里没有回答用户问题的证据，绝对禁止编造！直接回答“在这段时间内，聊天记录未提及...”。
        4. 📁 文件与多模态寻回（重要）：如果主人在寻找某个文件、安装包、图片或视频（如“他发给我的安装包叫什么”、“上次那张图片在哪”），你必须在记录中仔细寻找包含【发送了一份文件/链接，文件名称为：...】或【本地存储路径或标识:...】的内容，并**在回答中明确写出该文件的准确名称或路径**！
        5. 严格遵循以下 XML 格式进行思考和作答。
        
        <thought>
        - 主人问的是私聊还是群聊？问的是什么时间？有没有触发【系统重要警告】？
        - 如果是寻物，提取出对应的文件名或路径。
        - 区分“{dynamic_owner_name}”说了什么，对方说了什么。
        - 分析参考片段中的场景和时间是否吻合。
        - 提取有效结论。
        </thought>
        <answer>
        直接回答主人的问题，如果是找文件请务必提供文件名或路径。
        </answer>

        【参考聊天记录】：
        {context_text}
        """
        messages_for_llm = [{'role': 'system', 'content': system_prompt}]
        messages_for_llm.extend(self.chat_history)
        messages_for_llm.append({'role': 'user', 'content': question})

        try:
            response = ollama.chat(
                model=self.llm_model,
                messages=messages_for_llm
            )
            raw_answer = response['message']['content']

            # 解析结构化输出
            thought_match = re.search(r'<thought>(.*?)</thought>', raw_answer, re.DOTALL)
            answer_match = re.search(r'<answer>(.*?)</answer>', raw_answer, re.DOTALL)

            if answer_match:
                final_answer = answer_match.group(1).strip()
                if thought_match:
                    thought_process = thought_match.group(1).strip()
                    answer = f"🧠【AI 逻辑分析】:\n{thought_process}\n\n🤖【最终结论】:\n{final_answer}"
                else:
                    answer = f"🤖【最终结论】:\n{final_answer}"
            else:
                # 兜底：抹除可能残留的标签
                final_answer = raw_answer.replace('<answer>', '').replace('</answer>', '').replace('<thought>','').replace(
'</thought>', '').strip()
                answer = final_answer

            self.chat_history.append({'role': 'user', 'content': question})
            self.chat_history.append({'role': 'assistant', 'content': final_answer})

            if len(self.chat_history) > CHAT_HISTORY_MAX_LEN:
                self.chat_history = self.chat_history[-CHAT_HISTORY_MAX_LEN:]

        except Exception as e:
            answer = f"⚠️ 模型调用失败: {e}"

        return {
            "answer": answer,
            "sources": sources,
            "raw_context": context_text
        }

    def get_db_stats(self):
        return self.processor.collection.count()