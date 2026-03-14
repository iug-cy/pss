# cli.py
import os

from core.rag_core import PrivateMemoryAssistant
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ========== 导入初始化函数+config ==========
from bootstrap import init_environment
from config import LLM_MODEL_DEFAULT

def main():
    init_environment()
    print("=" * 60)
    print("🤖 初始化私人记忆引擎中...")
    # 实例化核心引擎
    assistant = PrivateMemoryAssistant(llm_model=LLM_MODEL_DEFAULT)
    print(f"✅ 引擎就绪！当前记忆库知识块数量: {assistant.get_db_stats()}")
    print("=" * 60)

    print("\n【操作指南】")
    print("1. 输入 'api <wxid>' : 通过 WeFlow API 自动抓取指定好友记录入库")
    print("   (例如: api wxid_rx37zsnsox6f22)")
    print("2. 输入 'import <文件路径>' : 手动导入本地 JSON/CSV/TXT/DOCX 文件")
    print("   (例如: import 私聊_Arkme.json)")
    print("3. 输入 'clear' : 🧹 彻底清空当前记忆库 (避免占空间/回答混乱)")
    print("4. 输入 'quit' : 退出程序")
    print("5. 直接输入其他内容 : 进行语义问答")
    print("-" * 60)

    while True:
        user_input = input("\n📝 请输入指令或问题：").strip()

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("再见！")
            break

        # 【关键修复】：严格拦截 clear，并使用 continue 阻断向下执行
        if user_input.lower() == "clear":
            print("⏳ 正在执行大脑和数据库格式化...")
            msg = assistant.clear_memory()
            print(msg)
            continue  # 这个 continue 极其重要，没有它指令就会发给 AI

        if user_input.startswith("api "):
            # 支持格式: api wxid_xxxx 备注名
            parts = user_input.split()
            if len(parts) < 2:
                print("❌ 格式错误！请输入: api <wxid> [备注名]")
                continue

            wxid = parts[1].strip()
            alias = parts[2].strip() if len(parts) > 2 else None

            print(f"⏳ 正在联系 API 服务器 (目标: {alias or wxid})...")
            result_msg = assistant.import_from_weflow_api(wxid, alias)
            print(result_msg)
            continue

        if user_input.startswith("import "):
                parts = user_input.split()
                file_path = parts[1].strip().replace('"', '').replace("'", "")
                alias = parts[2].strip() if len(parts) > 2 else None
                print(f"⏳ 正在解析并向量化文件 (备注: {alias or '无'})...")
                result_msg = assistant.import_local_file(file_path, alias)
                print(result_msg)
                continue

        # 只有上面的指令都没命中，才会进入大模型问答
        print("🧠 AI 正在检索记忆并思考...")
        result_dict = assistant.ask(user_input)

        print("\n" + "=" * 40)
        print("💬 【AI 回答】:\n" + result_dict['answer'])
        print("\n📚 【参考来源】:")
        if result_dict['sources']:
            for src in result_dict['sources']:
                print("  - " + src)
        else:
            print("  - 无参考来源")
        print("=" * 40)


if __name__ == "__main__":
    main()