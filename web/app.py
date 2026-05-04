import streamlit as st
import sys
import os
import re
import time
import pandas as pd
import glob
import base64

BASE_DIR_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR_PATH)

if not os.path.exists(os.path.join(BASE_DIR_PATH, 'core')):
    st.error("Engine Error: 核心模块未能在路径中定位，请检查项目结构。")
    st.stop()

from bootstrap import init_environment
init_environment()
from core.rag_core import PrivateMemoryAssistant
from config import BASE_DIR, WEFLOW_EXPORT_DIR, TEMP_DIR

st.set_page_config(
    page_title="MemoraOS——端侧记忆认知系统",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def get_bg_image_css():
    web_dir = os.path.join(BASE_DIR_PATH, "web")
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.webp'):
        files = glob.glob(os.path.join(web_dir, ext))
        if files:
            try:
                with open(files[0], 'rb') as f:
                    data = f.read()
                b64_str = base64.b64encode(data).decode('utf-8')
                mime_type = "image/png" if ext.endswith("png") else "image/jpeg"
                return f'background-image: url("data:{mime_type};base64,{b64_str}"); background-size: cover; background-position: center; background-attachment: fixed;'
            except Exception:
                pass
    return ''

bg_css = get_bg_image_css()

USER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><linearGradient id="userGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ff9a9e" /><stop offset="100%" stop-color="#fecfef" /></linearGradient></defs><circle cx="50" cy="50" r="50" fill="url(#userGrad)"/><path d="M50 45c-11 0-20-9-20-20s9-20 20-20 20 9 20 20-9 20-20 20zm0 10c-22 0-40 13.4-40 30v15h80V85c0-16.6-18-30-40-30z" fill="#ffffff" opacity="0.9"/></svg>"""
AI_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><linearGradient id="aiGrad" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="#4BDEFF" /><stop offset="100%" stop-color="#00D0FF" /></linearGradient></defs><polygon points="50,5 89,27 89,73 50,95 11,73 11,27" fill="url(#aiGrad)"/><line x1="50" y1="26" x2="50" y2="14" stroke="#ffffff" stroke-width="4" stroke-linecap="round"/><line x1="50" y1="74" x2="50" y2="86" stroke="#ffffff" stroke-width="4" stroke-linecap="round"/><line x1="26" y1="50" x2="14" y2="50" stroke="#ffffff" stroke-width="4" stroke-linecap="round"/><line x1="74" y1="50" x2="86" y2="50" stroke="#ffffff" stroke-width="4" stroke-linecap="round"/><circle cx="50" cy="50" r="20" fill="#ffffff"/><circle cx="50" cy="50" r="10" fill="#4B4F5E"/></svg>"""
USER_AVATAR = f"data:image/svg+xml;base64,{base64.b64encode(USER_SVG.encode('utf-8')).decode('utf-8')}"
AI_AVATAR = f"data:image/svg+xml;base64,{base64.b64encode(AI_SVG.encode('utf-8')).decode('utf-8')}"

if "theme" not in st.session_state:
    st.session_state.theme = "light" # 默认亮色/暖色

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

if st.session_state.theme == "light":
    custom_css = f"""
    <style>
    .stApp {{
        {bg_css}
        background-color: #fffaf0; 
    }}
    /* 调整主体文字颜色以防背景干扰 */
    .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown li {{ color: #2d3436 !important; }}
    /* 侧边栏样式：半透明毛玻璃 */
    [data-testid="stAlert"] {{
        background-color: rgba(20, 65, 125, 0.85) !important;
        border: 1px solid rgba(79, 172, 254, 0.8) !important;
        backdrop-filter: blur(12px);
    }}
    [data-testid="stAlert"] p, [data-testid="stAlert"] strong, [data-testid="stAlert"] div {{
        color: #ffffff !important;
    }}
    /* 标题文字增加发光/阴影层，无视任何浅色背景干扰 */
    .stMarkdown h2 {{
        color: #1a1c2c !important;
        text-shadow: 2px 2px 10px rgba(255,255,255,0.9), -2px -2px 10px rgba(255,255,255,0.9) !important;
        font-weight: 900 !important;
    }}
    /* 侧边栏样式：提高透明度以融合全局背景 */
    [data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.35) !important;
        backdrop-filter: blur(15px);
    }}
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] .stMarkdown h1, [data-testid="stSidebar"] .stMarkdown h2,[data-testid="stSidebar"] .stMarkdown h3 {{ color: #2d3436 !important; }}
    [data-testid="stMetricValue"] {{ color: #ff7675 !important; font-weight: 800 !important; }}
    /* 侧边栏按钮美化 */[data-testid="stSidebar"] .stButton > button {{
        background-color: rgba(255, 255, 255, 0.5) !important;
        border: 1px solid #ff7675 !important; color: #ff7675 !important;
        border-radius: 8px; transition: all 0.3s ease;
    }}[data-testid="stSidebar"] .stButton > button:hover {{ background-color: #ff7675 !important; color: white !important; }}
    /* 气泡输入框 */[data-testid="stChatInput"] {{
        border-radius: 20px !important; border: 1px solid #ff7675 !important;
        background-color: rgba(255,255,255,0.85) !important; color: #2d3436 !important;
        backdrop-filter: blur(10px);
    }}
    /* 聊天消息气泡 */
    .stChatMessage {{
        background-color: rgba(255,255,255,0.75); backdrop-filter: blur(12px);
        border-radius: 12px; padding: 10px; margin-bottom: 10px;
        border: 1px solid rgba(0,0,0,0.05); box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    }}[data-testid="stChatMessageContent"] p, [data-testid="stChatMessageContent"] span,[data-testid="stChatMessageContent"] li, [data-testid="stChatMessageContent"] a {{ color: #2d3436 !important; font-size: 15px !important; line-height: 1.6 !important; }}
    .st-emotion-cache-1vt4ygl p {{ color: #636e72 !important; }}
    #MainMenu, footer {{visibility: hidden;}} header {{background: transparent !important;}}
    </style>
    """
else:
    custom_css = f"""
    <style>
    .stApp {{
        {bg_css}
        background-color: #0f111a; 
    }}
    .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown li {{ color: #e0e0e0 !important; }}
    [data-testid="stAlert"] {{
        background-color: rgba(5, 15, 30, 0.90) !important;
        border: 1px solid rgba(79, 172, 254, 0.6) !important;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }}
    [data-testid="stAlert"] p,[data-testid="stAlert"] strong, [data-testid="stAlert"] div {{
        color: #ffffff !important;
    }}
    /* 标题文字增加深色辉光，无视任何深色背景干扰 */
    .stMarkdown h2 {{
        color: #ffffff !important;
        text-shadow: 2px 2px 12px rgba(0,0,0,1), -2px -2px 12px rgba(0,0,0,1) !important;
        font-weight: 900 !important;
    }}
    /* 侧边栏样式：提高透明度以融合全局背景 */[data-testid="stSidebar"] {{
        background-color: rgba(13, 17, 23, 0.40) !important;
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255,255,255,0.1);
    }}
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] .stMarkdown h1, [data-testid="stSidebar"] .stMarkdown h2, [data-testid="stSidebar"] .stMarkdown h3 {{ color: #e6edf3 !important; }}[data-testid="stMetricValue"] {{ color: #4facfe !important; font-weight: 800 !important; }}
    [data-testid="stSidebar"] .stButton > button {{
        background-color: rgba(0,0,0,0.3) !important;
        border: 1px solid #4facfe !important; color: #4facfe !important;
        border-radius: 8px; transition: all 0.3s ease;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{ background-color: #4facfe !important; color: white !important; }}
    [data-testid="stChatInput"] {{
        border-radius: 20px !important; border: 1px solid #4facfe !important;
        background-color: rgba(15, 17, 26, 0.85) !important; color: white !important;
        backdrop-filter: blur(10px);
    }}
    .stChatMessage {{
        background-color: rgba(15, 17, 26, 0.75); backdrop-filter: blur(12px);
        border-radius: 12px; padding: 10px; margin-bottom: 10px;
        border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }}[data-testid="stChatMessageContent"] p, [data-testid="stChatMessageContent"] span,[data-testid="stChatMessageContent"] li, [data-testid="stChatMessageContent"] a {{ color: #f0f6fc !important; font-size: 15px !important; line-height: 1.6 !important; }}
    .st-emotion-cache-1vt4ygl p {{ color: #8b949e !important; }}
    #MainMenu, footer {{visibility: hidden;}} header {{background: transparent !important;}}
    </style>
    """
st.markdown(custom_css, unsafe_allow_html=True)


@st.cache_resource
def get_assistant():
    return PrivateMemoryAssistant()

assistant = get_assistant()

# 初始化状态变量
if "messages" not in st.session_state:
    st.session_state.messages =[]
if "current_target" not in st.session_state:
    st.session_state.current_target = None  # 记录当前正在互动的对象

def parse_intent(text: str):
    """
    NLP 意图识别引擎
    """
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


# 侧边栏：数字记忆大屏
with st.sidebar:
    st.title("🧠 MemoraOS")
    st.caption("端侧记忆认知系统")
    st.markdown("---")
    st.subheader("⚙️ 自动化配置")
    export_dir_str = str(WEFLOW_EXPORT_DIR)
    export_dir = st.text_input("WeFlow本地导出目录:", value=export_dir_str)
    st.caption("请先在WeFlow中导出Arkme JSON至此。")

    # 模块1：数据可视化看板
    st.markdown("---")
    st.subheader("📈 记忆库分布")
    dist_data = assistant.get_dashboard_data()
    if dist_data:
        df = pd.DataFrame(list(dist_data.items()), columns=['联系人', '记忆块数'])
        st.bar_chart(df.set_index('联系人'), color="#4facfe" if st.session_state.theme == "dark" else "#ff7675", height=200)
        st.caption(f"总脑容量: {assistant.get_db_stats()} 块记忆")
    else:
        st.info("记忆库暂无数据，请先同步。")

    # 模块2：结构化知识提炼
    st.markdown("---")
    st.subheader("💡 知识提炼与重构")
    if dist_data:
        available_targets = list(dist_data.keys())
        default_idx = 0
        if st.session_state.current_target in available_targets:
            default_idx = available_targets.index(st.session_state.current_target)
        selected_target = st.selectbox("选择目标对象：", available_targets, index=default_idx)
        template_options =[
            "法务审前事实梳理/电子证据链提炼",
            "科研协作知识管理",
            "日常脉络与待办梳理"
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

    # 模块3：系统维护与零散上传
    st.markdown("---")
    st.subheader("🛠️ 系统维护")
    if st.button("🧹 一键清空记忆库", use_container_width=True):
        res = assistant.clear_memory()
        st.session_state.messages =[]
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

# 在主界面右上方渲染主题切换按钮
col_space, col_toggle = st.columns([8.5, 1.5])
with col_toggle:
    st.toggle("🌙 暗色主题" if st.session_state.theme == "light" else "☀️ 亮色主题",
              value=(st.session_state.theme == "dark"),
              on_change=toggle_theme,
              key="theme_toggle")

# 主聊天区域
st.header("💬 跨模态语义检索引擎")
if not st.session_state.messages:
    st.info("""
    **快速上手：**
    1. **建立连接：** 在下方输入 `同步 XX`，系统将自动挂载数据。
    2. **跨模态寻物：** 提问 `张三发给我的图片叫什么名字？`，系统将**直接渲染该图片**！
    3. **知识提炼：** 同步完成后，点击左侧边栏的 `⚡ 一键生成待办大纲`，体验杂乱聊天化为结构化脉络的震撼。
    """)

# 渲染历史消息
for msg in st.session_state.messages:
    avatar_svg = USER_AVATAR if msg["role"] == "user" else AI_AVATAR
    with st.chat_message(msg["role"], avatar=avatar_svg):
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
            with st.expander("📚 查看RAG底层参考片段"):
                for src in msg["sources"]:
                    st.write(f"- {src}")
                if "raw_context" in msg:
                    st.code(msg.get("raw_context", ""), language="text")

# 用户输入处理
if prompt := st.chat_input("输入指令或问题 (如: 同步 张三)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    target_name = parse_intent(prompt)
    if target_name:
        with st.chat_message("assistant", avatar=AI_AVATAR):
            with st.status(f"🤖 正在底层目录扫描【{target_name}】的数据...", expanded=True) as status:
                success, result_msg = assistant.import_from_export_dir(target_name, export_dir)
                if success:
                    st.session_state.current_target = target_name
                    status.update(label="同步与向量化完成！", state="complete", expanded=False)
                    reply = f"✅ 已成功为您挂载！\n\n**现在您可以直接向我提问，或点击左侧提炼知识大纲。**"
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    time.sleep(1)
                    st.rerun()
                else:
                    status.update(label="扫描失败", state="error")
                    reply = result_msg
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
    else:
        with st.chat_message("assistant", avatar=AI_AVATAR):
            with st.spinner("🧠 正在深潜记忆海并进行逻辑推理..."):
                response_dict = assistant.ask(prompt)

                raw_answer = response_dict.get('answer', '获取回答失败')
                sources = response_dict.get('sources',[])
                raw_context = response_dict.get('raw_context', '')

                # 提取思维链
                thought_match = re.search(r'🧠【AI逻辑分析】:\n(.*?)\n\n🤖【最终结论】:\n(.*)', raw_answer, re.DOTALL)
                if thought_match:
                    thought_process = thought_match.group(1).strip()
                    final_answer = thought_match.group(2).strip()
                    with st.expander("🧠 查看AI推理思维链 (CoT)"):
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