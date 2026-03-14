# bootstrap.py
import sys
import os
from pathlib import Path

# 确保能找到 config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import LOCAL_MODEL_DIR, MODEL_ID, DB_PATH


def auto_install_model():
    """全自动检查并下载模型到 pss_md/models"""
    LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # 检查核心文件是否完整 (只需要配置文件 + 任意一种权重文件即可)
    weight_files = ["pytorch_model.bin", "model.safetensors"]
    has_weight = any((LOCAL_MODEL_DIR / f).exists() for f in weight_files)
    has_config = (LOCAL_MODEL_DIR / "config.json").exists()

    # 如果模型已存在，直接放行
    if has_weight and has_config:
        return True

    print(f"\n📥 未检测到完整的本地模型，正在从魔搭社区(ModelScope)自动下载 {MODEL_ID}...")
    print(f"📂 目标路径：{LOCAL_MODEL_DIR}")
    print(f"⏳ 模型大小约 2.2GB，根据网速可能需要几分钟，请耐心等待...\n")

    try:
        # 动态检查并安装 modelscope (防止换电脑后缺库)
        try:
            import modelscope
        except ImportError:
            print("⚙️ 正在自动安装下载依赖库 modelscope...")
            os.system(f"{sys.executable} -m pip install modelscope -q")

        from modelscope.hub.snapshot_download import snapshot_download

        # 执行下载
        snapshot_download(
            model_id=MODEL_ID,
            local_dir=str(LOCAL_MODEL_DIR)
        )
        print("\n✅ 本地模型下载并部署完成！\n")
        return True

    except Exception as e:
        print(f"\n❌ 模型下载失败，请检查网络是否通畅。")
        print(f"错误详情：{e}")
        sys.exit(1)


def init_environment():
    """初始化运行环境（直接运行脚本时的入口）"""
    print(f"🔧 正在检查运行环境...")
    auto_install_model()
    DB_PATH.mkdir(parents=True, exist_ok=True)
    print(f"✅ 向量库目录就绪：{DB_PATH}")
    print("=" * 50)


if __name__ == "__main__":
    init_environment()