# main.py 统一启动入口
import sys
import os
import platform
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

if not os.path.exists(os.path.join(BASE_DIR, 'core')):
    print(f"错误：未找到 core 目录，请检查项目结构")
    print(f"当前工作目录: {BASE_DIR}")
    sys.exit(1)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        print("\n🚀 启动 Web 界面...")
        try:
            # 启动Streamlit前端
            os.system("streamlit run web/app.py")
        except Exception as e:
            print(f"错误：启动 Web 界面失败: {e}")
            sys.exit(1)
    else:
        print("\n🚀 启动命令行界面...")
        try:
            from core.cli import main as cli_main
            cli_main()
        except ImportError as e:
            print(f"错误：无法导入 CLI 模块: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"错误：启动命令行界面失败: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()