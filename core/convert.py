# core/convert.py
import json
import os
import re
import time
import sys
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- 自动定位项目路径 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")  # QQ原始数据监听目录
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "texts")  # 转换后输出的存放目录

# 确保目录存在
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def parse_friend_info_from_filename(filename):
    """从原始文件名解析好友名（最终兜底方案）"""
    base_name = os.path.splitext(os.path.basename(filename))[0]
    name = re.sub(r'^(私聊_|friend_|UID_)', '', base_name)
    name = re.sub(r'_u_[a-zA-Z0-9]+|_\d{8}_\d{6}|\（.*?\）|UID_\w+', '', name)
    return name.strip()


def convert_napcat_to_custom(input_file):
    """执行转换的核心逻辑 (与你原来的一致，略微优化了文件安全检查)"""
    # 为了防止文件被持续写入占用，稍微等一下
    time.sleep(1)

    print(f"\n🔄 [QQ适配器] 察觉原始数据，开始转换: {os.path.basename(input_file)}")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"❌ 读取文件失败: {str(e)}")
        return False

    messages = []
    chat_info = {}
    friend_remark = ""
    friend_name = ""
    friend_uin = ""

    if "messages" in raw_data:
        messages = raw_data["messages"]
        chat_info = raw_data.get("chatInfo", {})
        self_uid = chat_info.get("selfUid", "")
        self_name = chat_info.get("selfName", "我")
        friend_remark = chat_info.get("remark", "") or chat_info.get("remarkName", "")
        friend_name = chat_info.get("friendName", "")
        friend_uin = chat_info.get("friendUin", "")
    elif isinstance(raw_data, list) and len(raw_data) > 0 and "content" in raw_data[0]:
        messages = raw_data
        self_uid = ""
        self_name = "我"

    final_name = ""
    if friend_remark and friend_remark.strip():
        final_name = friend_remark.strip()
        print(f"✅ 提取到对方备注名: {final_name}")
    elif friend_name and friend_name.strip():
        final_name = friend_name.strip()
    else:
        final_name = parse_friend_info_from_filename(input_file)

    safe_name = re.sub(r'[\\/*?:"<>|]', "", final_name)

    # 强制加上“私聊_”前缀，这样你的 RAG 系统能完美复用你的“场景隔离”逻辑！
    if friend_uin and friend_uin != "未知QQ" and friend_uin.strip():
        filename = f"私聊_{safe_name}{friend_uin.strip()}.json"
    else:
        filename = f"私聊_{safe_name}.json"

    output_file = os.path.join(OUTPUT_DIR, filename)

    result = []
    for index, msg in enumerate(messages):
        msg_id = msg.get("id", str(index))
        timestamp = msg.get("timestamp", 0)
        time_str = msg.get("time", "")

        create_time = 0
        formatted_time = ""
        if timestamp > 0:
            create_time = int(timestamp / 1000)
            try:
                formatted_time = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S")
            except:
                formatted_time = time_str
        else:
            create_time = int(datetime.now().timestamp())
            formatted_time = time_str or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sender_uid = ""
        sender_name = "未知"
        is_send = 0
        if "sender" in msg:
            sender_obj = msg["sender"]
            sender_uid = sender_obj.get("uid", "")
            sender_name = sender_obj.get("name", "未知")
            if sender_uid == self_uid or sender_name == self_name:
                is_send = 1

        content = ""
        msg_type = "文本消息"
        local_type = 1
        if "content" in msg:
            content_obj = msg["content"]
            if isinstance(content_obj, str):
                content = content_obj
            elif isinstance(content_obj, dict) and "text" in content_obj:
                content = content_obj["text"]

        raw_type = msg.get("type", "")
        if raw_type in ("type_1", "text"):
            msg_type = "文本消息"
            local_type = 1
        elif raw_type in ("type_3", "reply"):
            msg_type = "文本消息"
            local_type = 1
            if content.startswith("[回复"):
                lines = content.split("\n")
                if len(lines) > 1:
                    content = "\n".join(lines[1:])
        elif raw_type == "image":
            msg_type = "图片消息"
            local_type = 3
            content = content or "[图片]"
        elif raw_type == "video":
            msg_type = "视频消息"
            local_type = 4
            content = content or "[视频]"
        elif raw_type in ("voice", "audio"):
            msg_type = "语音消息"
            local_type = 2
            content = content or "[语音]"
        elif raw_type == "file":
            msg_type = "文件消息"
            local_type = 5
            content = content or "[文件]"
        elif raw_type in ("face", "emoji"):
            msg_type = "动画表情"
            local_type = 6
            content = content or "[动画表情]"

        # 最关键的补全：包装成带有 Arkme/WeFlow 标志的格式
        # 注意：这里我们构造一个符合原来 load_and_group_chat_records 期望解析的字典结构
        result.append({
            "localId": index + 1,
            "createTime": create_time,
            "formattedTime": formatted_time,
            "type": msg_type,
            "localType": local_type,
            "content": content,
            "isSend": is_send,
            "senderUsername": sender_uid,
            "senderDisplayName": sender_name,
            "source": "",
            "senderAvatarKey": sender_uid,
            "platformMessageId": str(msg_id)
        })

    # 将内容包装成 WeFlow 格式字典，以兼容原系统自动识别
    final_output = {
        "weflow": {
            "version": "1.0.3",
            "format": "arkme-json",
            "generator": "QQAdapter"  # 标志这是你转码的
        },
        "session": {
            "type": "私聊",
            "remark": friend_remark,
            "displayName": final_name
        },
        "senders": [
            # 建立ID映射表（核心！）
            {"senderID": self_uid, "displayName": self_name, "remark": "本机主人"},
            {"senderID": friend_uin, "displayName": final_name, "remark": friend_remark}
        ],
        "messages": result
    }

    # 修改原 messages 中的 senderID 使其匹配上方的 senders 表
    for m in final_output["messages"]:
        if m["isSend"] == 1:
            m["senderID"] = self_uid
        else:
            m["senderID"] = friend_uin

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 写入文件失败: {str(e)}")
        return False

    print(f"✅ 转换完成！输出为：{filename}")
    return True


# ================= 监听器类 =================
class RawDataHandler(FileSystemEventHandler):
    def __init__(self):
        self.processed_files = {}  # 缓存，防抖

    def process_file(self, file_path):
        if not file_path.endswith('.json'):
            return

        filename = os.path.basename(file_path)
        current_time = time.time()
        # 防抖：同一文件 5 秒内修改不重复触发
        if filename in self.processed_files and (current_time - self.processed_files[filename] < 5):
            return
        self.processed_files[filename] = current_time

        # 执行转换
        convert_napcat_to_custom(file_path)

    def on_created(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)


def start_adapter_daemon():
    print("=" * 60)
    print("🔄 [多源异构转换引擎] 已启动...")
    print(f"📂 正在监听原始目录: {RAW_DIR}")
    print("💡 提示：将QQ导出的 JSON 文件拖入上方目录，系统将全自动完成清洗。")
    print("=" * 60)

    event_handler = RawDataHandler()
    observer = Observer()
    observer.schedule(event_handler, RAW_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    start_adapter_daemon()