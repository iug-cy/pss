# bootstrap.py
import sys
import os
import subprocess
import platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

try:
    from config import LOCAL_MODEL_DIR, MODEL_ID, DB_PATH, TEMP_DIR, WEFLOW_EXPORT_DIR, LLM_MODEL_DEFAULT
except ImportError:
    print("错误：无法导入 config 模块，请检查项目结构")
    sys.exit(1)

def auto_install_model():
    """自动检查并下载模型到 pss_md/models"""
    LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    weight_files = ["pytorch_model.bin", "model.safetensors"]
    has_weight = any((LOCAL_MODEL_DIR / f).exists() for f in weight_files)
    has_config = (LOCAL_MODEL_DIR / "config.json").exists()

    if has_weight and has_config:
        return True

    print(f"\n📥 未检测到完整的本地模型，正在从魔搭社区(ModelScope)自动下载 {MODEL_ID}...")
    print(f"📂 目标路径：{LOCAL_MODEL_DIR}")
    print(f"⏳ 模型大小约 2.2GB，根据网速可能需要几分钟，请耐心等待...\n")

    try:
        try:
            import modelscope
        except ImportError:
            print("⚙️ 正在自动安装下载依赖库 modelscope...")
            os.system(f"{sys.executable} -m pip install modelscope -q")

        from modelscope.hub.snapshot_download import snapshot_download

        # 添加进度显示
        def progress_callback(percentage, downloaded_size, total_size):
            sys.stdout.write(f"\r下载进度: {percentage:.1f}% ({downloaded_size/1024/1024:.1f}MB/{total_size/1024/1024:.1f}MB)")
            sys.stdout.flush()

        snapshot_download(
            model_id=MODEL_ID,
            local_dir=str(LOCAL_MODEL_DIR),
            progress_callback=progress_callback
        )
        print("\n✅ 本地模型下载并部署完成！\n")
        return True

    except Exception as e:
        print(f"\n❌ 模型下载失败，请检查网络是否通畅。")
        print(f"错误详情：{e}")
        sys.exit(1)

def ensure_ollama_model(model):

    try:
        result = subprocess.run(
            ["ollama", "show", model],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"正在下载 Ollama 模型: {model}")
            subprocess.run(["ollama", "pull", model])

    except FileNotFoundError:
        print("未检测到 Ollama，请先安装：https://ollama.com")

def check_ollama():

    try:
        subprocess.run(["ollama","--version"],capture_output=True)

    except:

        print("未检测到 Ollama，请先安装 https://ollama.com")

def init_environment():
    print(f"🔧 正在检查运行环境...")
    check_ollama()
    ensure_ollama_model("qwen2.5:7b")
    auto_install_model()

    DB_PATH.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    WEFLOW_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"✅ 系统目录就绪。")


if __name__ == "__main__":
    init_environment()