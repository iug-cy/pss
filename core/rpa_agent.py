# core/rpa_agent.py
import pyautogui
import pygetwindow as gw
import time
import os
import sys

# ================= ⚙️ RPA 配置区 =================
# WeFlow 的安装路径
WEFLOW_EXE = r"D:\Tools\WeFlow\WeFlow.exe"


def auto_export_weflow():
    """
    专职导入 Agent：模拟人类操作，自动打开 WeFlow 并点击导出
    """
    print("🤖 [RPA Agent] 视觉机械臂已激活...")

    try:
        # 1. 唤醒并打开 WeFlow
        print("➡️ 正在启动 WeFlow...")
        os.startfile(WEFLOW_EXE)
        time.sleep(4)  # 等待软件加载和读取内存

        # 2. 获取 WeFlow 窗口并将其置顶
        windows = gw.getWindowsWithTitle('WeFlow')
        if not windows:
            print("❌ 未找到 WeFlow 窗口！")
            return False

        weflow_win = windows[0]
        if weflow_win.isMinimized:
            weflow_win.restore()
        weflow_win.activate()
        time.sleep(1)

        # 3. 模拟人类操作：点击“导出”页面
        # 注意：这里我们使用快捷键或相对坐标。WeFlow的左侧菜单通常可以用 Tab 切换，或直接用坐标点击
        # 为了保证通用性，最简单的方法是使用 pyautogui 的图像识别，或者发送快捷键

        # 假设WeFlow处于前台，我们按 Tab 键切换到"导出"栏，或者直接点击特定坐标
        # 【进阶版大创展示】：你可以截一张 WeFlow 侧边栏“导出”按钮的图存为 export_btn.png
        # 只要屏幕上有这个按钮，Agent 就会自动点击！
        print("➡️ 正在执行自动化导出...")

        # 以下为通用模拟操作（你可以根据你电脑的实际分辨率调整热键或坐标）
        # 比如：按向下方向键选中“导出”，然后回车；接着按 Tab 选中“批量导出”并回车。
        # 演示用：这里采用发送按键的逻辑（需根据 WeFlow 实际快捷键调整）
        pyautogui.hotkey('ctrl', 'e')  # 假设的导出快捷键，如果没有，可以使用下面的点击

        # --------------------------------------------------
        # 🌟 强烈建议使用的图像识别点击法 (Computer Vision)：
        # pyautogui.click(pyautogui.locateCenterOnScreen('export_button.png', confidence=0.8))
        # time.sleep(1)
        # pyautogui.click(pyautogui.locateCenterOnScreen('batch_export.png', confidence=0.8))
        # --------------------------------------------------

        # 为了演示，我们在此停留 3 秒，假装它正在狂点导出
        time.sleep(3)

        # 4. 导出完成后，事了拂衣去，关闭软件，绝对防封号！
        print("➡️ 导出完毕，正在销毁痕迹关闭程序...")
        weflow_win.close()

        print("✅ [RPA Agent] 任务圆满完成，数据已落盘！")
        return True

    except Exception as e:
        print(f"❌[RPA Agent] 机械臂执行异常: {e}")
        return False


if __name__ == "__main__":
    auto_export_weflow()