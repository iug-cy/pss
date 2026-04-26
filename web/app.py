# web/app.py
import streamlit as st
import sys
import os
import re
import time
import pandas as pd

# 确保能导入 core 模块
BASE_DIR_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR_PATH)

if not os.path.exists(os.path.join(BASE_DIR_PATH, 'core')):
    st.error("Engine Error: 核心模块未能在路径中定位，请检查项目结构。")
    st.stop()

from bootstrap import init_environment

init_environment()

from core.rag_core import PrivateMemoryAssistant
from config import BASE_DIR, WEFLOW_EXPORT_DIR, TEMP_DIR

# ================= 页面初始化配置 =================
st.set_page_config(
    page_title="MemoryOS 个人知识引擎",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 极致 UI 优化 =================
st.markdown("""
    <style>
    /* 全局背景优化 */
    .stApp {
        background: linear-gradient(135deg, #0f111a 0%, #1a1c2c 100%);
        color: #e0e0e0;
    }

    /* 侧边栏整体样式 */[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95) !important;
        border-right: 1px solid rgba(255,255,255,0.1);
    }

    /* 🌟 核心修复：强制提亮侧边栏里的所有普通文字、标签和副标题 */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] .stMarkdown h1, 
    [data-testid="stSidebar"] .stMarkdown h2, 
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #e6edf3 !important; 
    }

    /* 让数据大屏的数字更醒目 */
    [data-testid="stMetricValue"] {
        color: #4facfe !important;
        font-weight: 800 !important;
    }

    /* 侧边栏按钮美化 */[data-testid="stSidebar"] .stButton > button {
        background-color: transparent !important;
        border: 1px solid #4facfe !important;
        color: #4facfe !important;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #4facfe !important;
        color: white !important;
    }

    /* 气泡输入框优化 */
    [data-testid="stChatInput"] {
        border-radius: 20px !important;
        border: 1px solid #4facfe !important;
        background-color: rgba(255,255,255,0.05) !important;
        color: white !important;
    }

    /* 聊天消息气泡优化 */
    .stChatMessage {
        background-color: rgba(255,255,255,0.02);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    
    /* 🌟 终极提亮：强制主聊天区域的所有文字变为高亮白/浅灰 */
    [data-testid="stChatMessageContent"] p,[data-testid="stChatMessageContent"] span, 
    [data-testid="stChatMessageContent"] li,[data-testid="stChatMessageContent"] a {
        color: #f0f6fc !important; 
        font-size: 15px !important;
        line-height: 1.6 !important;
    }

    /* 思维链折叠框的文字稍微暗一点，形成层级感 */
    .st-emotion-cache-1vt4ygl p {
        color: #8b949e !important; 
    }

    #MainMenu, footer {visibility: hidden;}
    header {background: transparent !important;}
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_assistant():
    return PrivateMemoryAssistant()


assistant = get_assistant()

# 初始化状态变量
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_target" not in st.session_state:
    st.session_state.current_target = None  # 记录当前正在互动的对象


def parse_intent(text: str):
    """NLP 意图识别引擎"""
    text = text.strip()
    nlp_match = re.search(
        r"(?:同步|拉取|获取|找|看).*?(?:与|和|跟)\s*([a-zA-Z0-9_\u4e00-\u9fa5]+?)\s*(?:的聊天|的记录|的对话|的数据)",
        text)
    if nlp_match:
        return nlp_match.group(1).strip()
    cmd_match = re.match(r"^(?:同步|拉取|导入|更新|查找)\s*([a-zA-Z0-9_\u4e00-\u9fa5]+)$", text)
    if cmd_match:
        return cmd_match.group(1).strip()
    return None


# ================= 📊 侧边栏：数字记忆大屏 (Dashboard) =================
with st.sidebar:
    st.title("🧠 MemoryOS")
    st.caption("面向法务取证与商业机密的端侧AI审计中枢")

    st.markdown("---")
    st.subheader("⚙️ 自动化配置")
    export_dir_str = str(WEFLOW_EXPORT_DIR)
    export_dir = st.text_input("WeFlow 本地导出目录:", value=export_dir_str)
    st.caption("请先在 WeFlow 中导出 Arkme JSON 至此。")

    # --- 模块 1：数据可视化看板 ---
    st.markdown("---")
    st.subheader("📈 记忆库分布")
    dist_data = assistant.get_dashboard_data()
    if dist_data:
        df = pd.DataFrame(list(dist_data.items()), columns=['联系人', '记忆块数'])
        st.bar_chart(df.set_index('联系人'), color="#4facfe", height=200)
        st.caption(f"总脑容量: {assistant.get_db_stats()} 块记忆")
    else:
        st.info("记忆库暂无数据，请先同步。")

    # --- 模块 2：结构化知识提炼 ---
    st.markdown("---")
    st.subheader("💡 知识提炼与重构")

    if dist_data:
        # 直接从数据库的统计结果中拿到所有已存在的联系人名单
        available_targets = list(dist_data.keys())

        # 如果当前有刚刚同步的焦点，将其设为默认选项；否则默认选列表第一个
        default_idx = 0
        if st.session_state.current_target in available_targets:
            default_idx = available_targets.index(st.session_state.current_target)

        selected_target = st.selectbox("选择目标对象：", available_targets, index=default_idx)

        template_options = [
            "电子证据链提炼 (Evidence Chain)",
            "企业合规风险审计 (Audit)",
            "日常脉络与待办梳理 (Daily Routine)"
        ]
        selected_template = st.selectbox("请选择输出模板：", template_options)

        if st.button(f"⚡ 一键提炼", use_container_width=True):
            with st.spinner("大模型正在进行多文档知识蒸馏..."):
                knowledge_md = assistant.generate_structured_knowledge(selected_target, selected_template)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"**已为您提炼与【{selected_target}】的结构化知识脉络：**\n\n" + knowledge_md
                })
                st.rerun()
    else:
        st.warning("记忆库为空，请先导入数据。")

    # --- 模块 3：系统维护与零散上传 ---
    st.markdown("---")
    st.subheader("🛠️ 系统维护")
    if st.button("🧹 一键清空记忆库", use_container_width=True):
        res = assistant.clear_memory()
        st.session_state.messages = []
        st.session_state.current_target = None
        st.success(res)
        time.sleep(1)
        st.rerun()

    with st.expander("📁 手动补充零散文件"):
        uploaded_file = st.file_uploader("支持 Arkme JSON, CSV, DOCX", type=['json', 'csv', 'txt', 'docx'])
        if uploaded_file:
            alias = st.text_input("联系人备注名(必填)：")
            if st.button("向量化导入") and alias:
                with st.spinner("正在处理..."):
                    temp_path = os.path.join(str(TEMP_DIR), uploaded_file.name)
                    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    res = assistant.import_local_file(temp_path, alias=alias)
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    st.success(res)
                    time.sleep(1)
                    st.rerun()

# ================= 💬 主聊天区域 =================
st.header("💬 跨模态检索引擎")

if not st.session_state.messages:
    st.info("""
    **🚀 计设演示快速通道：**
    1. **建立连接：** 在下方输入 `同步 谭启翔`，系统将自动挂载数据。
    2. **跨模态寻物：** 提问 `他发给我的图片叫什么名字？`，系统将**直接渲染该图片**！
    3. **知识提炼：** 同步完成后，点击左侧边栏的 `⚡ 一键生成待办大纲`，体验杂乱聊天化为结构化脉络的震撼。
    """)

# 渲染历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # 跨模态图片渲染引擎
        img_paths = re.findall(
            r'([a-zA-Z]:\\[^\s*?<>"|]*?\.(?:png|jpg|jpeg|gif)|\.\./[^\s*?<>"|]*?\.(?:png|jpg|jpeg|gif))',
            msg["content"], re.IGNORECASE)
        for img_path in set(img_paths):
            if img_path.startswith("../") or img_path.startswith("..\\"):
                actual_path = os.path.normpath(os.path.join(str(WEFLOW_EXPORT_DIR), img_path))
            else:
                actual_path = img_path

            if os.path.exists(actual_path):
                st.image(actual_path, caption=f"🖼️ 跨模态召回: {os.path.basename(actual_path)}")

        if "sources" in msg and msg.get("sources"):
            with st.expander("📚 查看 RAG 底层参考片段"):
                for src in msg["sources"]:
                    st.write(f"- {src}")
                if "raw_context" in msg:
                    st.code(msg.get("raw_context", ""), language="text")

# 用户输入处理
if prompt := st.chat_input("输入指令或问题 (如: 同步 米毛火)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    target_name = parse_intent(prompt)
    if target_name:
        with st.chat_message("assistant"):
            with st.status(f"🤖 正在底层目录扫描【{target_name}】的数据...", expanded=True) as status:
                success, result_msg = assistant.import_from_export_dir(target_name, export_dir)

                if success:
                    st.session_state.current_target = target_name
                    status.update(label="同步与向量化完成！", state="complete", expanded=False)
                    reply = f"✅ 已成功为您挂载！\n\n**现在您可以直接向我提问，或点击左侧提炼知识大纲。**"
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

                    # 🌟 核心修复2：同步成功后，强制刷新整个网页！
                    # 这样左侧栏就会从上到下重新加载一遍，瞬间渲染出“生成待办大纲”的高级按钮
                    time.sleep(1)
                    st.rerun()

                else:
                    status.update(label="扫描失败", state="error")
                    reply = result_msg
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
    else:
        with st.chat_message("assistant"):
            with st.spinner("🧠 正在深潜记忆海并进行逻辑推理..."):
                response_dict = assistant.ask(prompt)

                raw_answer = response_dict.get('answer', '获取回答失败')
                sources = response_dict.get('sources', [])
                raw_context = response_dict.get('raw_context', '')

                # 提取思维链
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

                # 图片渲染
                img_paths = re.findall(
                    r'([a-zA-Z]:\\[^\s*?<>"|]*?\.(?:png|jpg|jpeg|gif)|\.\./[^\s*?<>"|]*?\.(?:png|jpg|jpeg|gif))',
                    display_content, re.IGNORECASE)
                for img_path in set(img_paths):
                    if img_path.startswith("../") or img_path.startswith("..\\"):
                        actual_path = os.path.normpath(os.path.join(str(WEFLOW_EXPORT_DIR), img_path))
                    else:
                        actual_path = img_path
                    if os.path.exists(actual_path):
                        st.image(actual_path, caption=f"🖼️ 跨模态召回: {os.path.basename(actual_path)}")

                file_paths = re.findall(r'([a-zA-Z]:\\[^\s*?<>"|]*?\.(?:pdf|docx|xlsx|csv|txt))', display_content,
                                        re.IGNORECASE)
                for fp in set(file_paths):
                    if os.path.exists(fp):
                        if st.button(f"📂 在资源管理器中显示：{os.path.basename(fp)}", key=fp):
                            import platform

                            # 仅限 Windows 系统
                            if platform.system() == "Windows":
                                os.system(f'explorer /select,"{fp}"')

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