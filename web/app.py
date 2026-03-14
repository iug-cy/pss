# web/app.py
import streamlit as st
import sys
import os
import re
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.rag_core import PrivateMemoryAssistant
from config import BASE_DIR

st.set_page_config(page_title="私人数字记忆助理", page_icon="🧠", layout="wide")


@st.cache_resource
def get_assistant():
    return PrivateMemoryAssistant()


assistant = get_assistant()

if "messages" not in st.session_state:
    st.session_state.messages = []


def parse_intent(text: str):
    """NLP 意图识别引擎"""
    cmd_match = re.match(r"^(同步|拉取|找找|导入)\s+(.+)$", text.strip())
    if cmd_match:
        return cmd_match.group(2).strip()

    nlp_match = re.search(r"(同步|拉取|获取|找找).*?(与|和|跟)\s*([a-zA-Z0-9_\u4e00-\u9fa5]+)\s*的?聊天", text)
    if nlp_match:
        return nlp_match.group(3).strip()
    return None


# ================= 侧边栏布局 =================
with st.sidebar:
    st.title("🧠 私人数字记忆助理")
    st.caption("基于本地文档的跨会话知识检索系统")

    st.markdown("---")
    st.subheader("⚙️ 自动化配置")
    # 🌟 默认填入你截图里的导出路径
    default_dir = r"D:\pss\data\texts"
    export_dir = st.text_input("WeFlow 本地批量导出目录:", value=default_dir)
    st.caption("请先在 WeFlow 中将聊天批量导出至此文件夹。")

    st.markdown("---")
    st.subheader("📊 记忆库状态")
    db_count = assistant.get_db_stats()
    st.metric(label="当前记忆碎片数量", value=f"{db_count} 块")

    if st.button("🧹 一键清空记忆库", use_container_width=True):
        res = assistant.clear_memory()
        st.session_state.messages = []
        st.success(res)
        st.rerun()

    st.markdown("---")
    st.subheader("📁 手动补充文件")
    uploaded_file = st.file_uploader("支持零散上传", type=['json', 'csv', 'txt', 'docx'])
    if uploaded_file:
        alias = st.text_input("请输入此人的备注名（必填）：")
        if st.button("开始向量化导入", use_container_width=True) and alias:
            with st.spinner("正在处理..."):
                temp_path = os.path.join(BASE_DIR, "temp", uploaded_file.name)
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                res = assistant.import_local_file(temp_path, alias=alias)
                os.remove(temp_path)
                st.success(res)
                time.sleep(1)
                st.rerun()

# ================= 主聊天区域 =================
st.header("💬 记忆检索引擎")

if not st.session_state.messages:
    st.info("""
    **💡 智能体工作流指南：**
    1. 请先在 WeFlow 软件中，将需要的联系人**批量导出**（选择 Arkme JSON 格式）到左侧配置的文件夹中。
    2. 在下方直接对我说：**`同步 程锦`** 或 **`找找和谭启翔的聊天`**。
    3. 系统将自动在后台扫描该文件夹、解析多模态数据并构建记忆！
    """)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sources" in msg and msg["sources"]:
            with st.expander("📚 查看参考片段"):
                for src in msg["sources"]:
                    st.write(f"- {src}")
                if "raw_context" in msg:
                    st.code(msg["raw_context"], language="text")

if prompt := st.chat_input("输入你的问题，或输入『同步 某人』..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 🌟 触发本地文件扫描智能体
    target_name = parse_intent(prompt)
    if target_name:
        with st.chat_message("assistant"):
            with st.status(f"🤖 识别到知识聚合意图，正在扫描本地目录寻找【{target_name}】...") as status:

                # 调用本地目录扫描引擎
                success, result_msg = assistant.import_from_export_dir(target_name, export_dir)

                if success:
                    status.update(label="同步与向量化完成！", state="complete", expanded=False)
                    reply = f"✅ 已成功为您就绪！\n{result_msg}\n\n**现在您可以直接向我提问了。**"
                else:
                    status.update(label="扫描失败", state="error")
                    reply = result_msg

            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

    # 走正常的 RAG 语义搜索流程
    else:
        with st.chat_message("assistant"):
            with st.spinner("🧠 正在深潜记忆海并进行逻辑推理..."):
                response_dict = assistant.ask(prompt)

                raw_answer = response_dict.get('answer', '获取回答失败')
                sources = response_dict.get('sources','获取来源失败')
                raw_context = response_dict['raw_context']

                thought_match = re.search(r'🧠【AI 逻辑分析】:\n(.*?)\n\n🤖【最终结论】:\n(.*)', raw_answer, re.DOTALL)
                if thought_match:
                    thought_process = thought_match.group(1).strip()
                    final_answer = thought_match.group(2).strip()
                    with st.expander("🧠 查看 AI 推理思维链 (CoT)"):
                        st.write(thought_process)
                    st.markdown(final_answer)
                    display_content = f"*(已折叠思维链)*\n\n{final_answer}"
                else:
                    st.markdown(raw_answer)
                    display_content = raw_answer

                if sources:
                    with st.expander("📚 查看参考片段"):
                        for src in sources:
                            st.write(f"- {src}")
                        st.code(raw_context, language="text")

            st.session_state.messages.append({
                "role": "assistant",
                "content": display_content,
                "sources": sources,
                "raw_context": raw_context
            })