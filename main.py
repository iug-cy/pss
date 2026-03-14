# main.py 统一启动入口
import sys
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        # 启动Streamlit前端
        os.system("streamlit run web/app.py")
    else:
        from core.cli import main as cli_main
        cli_main()

if __name__ == "__main__":
    main()