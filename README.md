# 私人微信聊天记录搜索引擎
基于 RAG 技术的本地微信聊天记录语义检索引擎，支持微信聊天记录导入、自然语言问答、时间范围精准过滤。

## 功能特性
- ✅ 支持 WeFlow API 自动拉取微信聊天记录
- ✅ 支持本地 JSON/CSV/TXT/DOCX 文件导入
- ✅ 基于 bge-m3 本地 Embedding 模型，语义检索精准
- ✅ 支持 Ollama 大模型问答，适配 qwen2.5 等开源模型
- ✅ 支持按时间范围过滤查询，精准定位历史对话
- ✅ Streamlit 可视化 Web 前端，开箱即用

## 环境要求
1.  **Python 版本**：3.10
2.  **Ollama**：用于大模型推理（必须安装）
3.  **WeFlow**：可选，用于自动拉取微信聊天记录


## 一键部署（Windows）
1.  克隆本仓库
    ```bash
    git clone https://github.com/iug-cy/pss.git
    cd pss 
2.  双击运行 setup.bat，脚本会自动验证 Python 版本并完成部署
3.  双击 run_web.bat 启动 Web 前端，浏览器会自动打开