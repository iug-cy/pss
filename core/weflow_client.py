# core/weflow_client.py
import requests
import time


class WeFlowAPIClient:
    def __init__(self, base_url="http://127.0.0.1:5031"):
        self.base_url = base_url
        self._contacts_cache = []  # 🌟 缓存池：避免每次提问都去轰炸API，提升网页响应速度

    def _load_all_contacts(self):
        """【核弹级数据扫描】拉取所有的联系人和最近会话，破解 API 分页截断"""
        if self._contacts_cache:
            return self._contacts_cache

        # 尝试扫描三个最有可能的接口，并强行拉取最大上限
        endpoints = [
            "/api/v1/sessions?limit=9999",
            "/api/v1/contacts?limit=9999",
            "/api/v1/recent?limit=9999"
        ]

        all_data = []
        for ep in endpoints:
            try:
                res = requests.get(f"{self.base_url}{ep}", timeout=3)
                if res.status_code == 200:
                    data = res.json()

                    # 智能拨洋葱：适配不同版本的 API 嵌套结构
                    item_list = []
                    if 'data' in data:
                        if isinstance(data['data'], list):
                            item_list = data['data']
                        elif isinstance(data['data'], dict) and 'list' in data['data']:
                            item_list = data['data']['list']
                    elif 'messages' in data:
                        item_list = data['messages']

                    all_data.extend(item_list)
            except Exception:
                pass  # 如果某个接口不存在，静默跳过，继续试下一个

        self._contacts_cache = all_data
        return all_data

    def find_wxid_by_name(self, target_name: str) -> str:
        """【智能体前端调用】通过昵称或备注反向超强查找 wxid"""
        all_contacts = self._load_all_contacts()

        if not all_contacts:
            print("⚠️ 警告：未能从任何接口获取到数据，请检查 WeFlow 服务。")
            return None

        # 1. 黄金级别：精准匹配
        for item in all_contacts:
            # WeFlow 数据可能是平铺，也可能包裹在 session 对象里
            c = item.get('session', item) if isinstance(item, dict) else item
            if not isinstance(c, dict): continue

            wxid = c.get('wxid') or c.get('userName') or c.get('id')
            if not wxid: continue

            names = [c.get('remark'), c.get('displayName'), c.get('nickname'), c.get('nickName'), c.get('name')]
            valid_names = [str(n).strip() for n in names if n]

            if target_name in valid_names:
                return wxid

        # 2. 白银级别：模糊包含匹配 (降级容错)
        for item in all_contacts:
            c = item.get('session', item) if isinstance(item, dict) else item
            if not isinstance(c, dict): continue

            wxid = c.get('wxid') or c.get('userName') or c.get('id')
            if not wxid: continue

            names = [c.get('remark'), c.get('displayName'), c.get('nickname')]
            valid_names = [str(n).strip() for n in names if n]

            for n in valid_names:
                if target_name in n or n in target_name:
                    print(f"💡 未精确找到【{target_name}】，但模糊定位到了: 【{n}】 ({wxid})")
                    return wxid

        return None

    def _get_contact_name(self, wxid: str) -> str:
        """通过 wxid 查找真实姓名 (供后端拉取时使用)"""
        all_contacts = self._load_all_contacts()
        for item in all_contacts:
            c = item.get('session', item) if isinstance(item, dict) else item
            if not isinstance(c, dict): continue
            current_wxid = c.get('wxid') or c.get('userName') or c.get('id')
            if current_wxid == wxid:
                return c.get('remark') or c.get('displayName') or c.get('nickname') or "对方"
        return "对方"

    def fetch_messages(self, wxid: str, limit: int = 5000) -> tuple:
        """拉取具体的聊天记录"""
        endpoint = f"{self.base_url}/api/v1/messages"
        params = {"talker": wxid, "limit": limit}

        try:
            print(f"📡 正在请求 WeFlow API 获取 {wxid} 的数据...")

            # 1. 查找对方姓名
            target_name = self._get_contact_name(wxid)
            print(f"👤 解析到聊天对象身份: 【{target_name}】")

            # 2. 获取聊天记录
            response = requests.get(endpoint, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                raw_messages = data.get('data') or data.get('messages') or []
                raw_messages.reverse()  # 倒序转正序

                owner_name = "本机主人"  # 兜底名称
                for msg in raw_messages:
                    if msg.get("isSend", 0) in [1, True]:
                        name = msg.get("senderDisplayName") or msg.get("senderNickname") or msg.get("senderUsername")
                        if name and not str(name).startswith("wxid_"):
                            owner_name = name
                            break
                print(f"👑 自动识别到本机主人身份: 【{owner_name}】")

                formatted_list = []
                for msg in raw_messages:
                    is_send = msg.get("isSend", 0)
                    sender = owner_name if (is_send == 1 or is_send == True) else target_name

                    raw_time = msg.get("formattedTime")
                    if not raw_time:
                        ts = msg.get("timestamp") or msg.get("createTime")
                        if ts:
                            if len(str(int(ts))) == 13: ts = int(ts) / 1000.0
                            raw_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(ts)))
                        else:
                            raw_time = "未知时间"

                    content = msg.get("content")
                    if not content: continue

                    formatted_list.append({
                        "time": raw_time,
                        "sender": str(sender).strip(),
                        "content": str(content).strip(),
                        "type": str(msg.get("type", "文本消息"))
                    })

                print(f"✅ 成功抓取 {len(formatted_list)} 条记录！")
                return target_name, owner_name, formatted_list
            else:
                print(f"❌ API 请求失败，状态码: {response.status_code}")
                return "对方", "本机主人", []
        except Exception as e:
            print(f"❌ 连接 WeFlow API 失败: {e}")
            return "对方", "本机主人",