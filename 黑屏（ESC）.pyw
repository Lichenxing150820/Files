import tkinter as tk
import ctypes
import sys
import threading
import time
from ctypes import windll, c_long, c_uint32, c_uint, Structure, byref, c_int

# 定义Windows API常量
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

# 保存原始系统状态
ORIGINAL_EXECUTION_STATE = None
SCREENSAVER_ENABLED = None
SCREENSAVER_TIMEOUT = None

class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]

def get_original_state():
    """获取原始系统状态"""
    global ORIGINAL_EXECUTION_STATE, SCREENSAVER_ENABLED, SCREENSAVER_TIMEOUT
    
    # 获取原始执行状态
    kernel32 = windll.kernel32
    ORIGINAL_EXECUTION_STATE = kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    
    # 获取屏幕保护原始设置
    pvParam = c_int()
    windll.user32.SystemParametersInfoA(0x0070, 0, byref(pvParam), 0)  # SPI_GETSCREENSAVEACTIVE
    SCREENSAVER_ENABLED = pvParam.value
    
    pvParam = c_int()
    windll.user32.SystemParametersInfoA(0x0072, 0, byref(pvParam), 0)  # SPI_GETSCREENSAVETIMEOUT
    SCREENSAVER_TIMEOUT = pvParam.value

def restore_original_state():
    """恢复原始系统状态"""
    global ORIGINAL_EXECUTION_STATE, SCREENSAVER_ENABLED, SCREENSAVER_TIMEOUT
    
    # 恢复执行状态
    if ORIGINAL_EXECUTION_STATE is not None:
        windll.kernel32.SetThreadExecutionState(ORIGINAL_EXECUTION_STATE)
    
    # 恢复屏幕保护设置
    if SCREENSAVER_ENABLED is not None:
        windll.user32.SystemParametersInfoA(0x0071, SCREENSAVER_ENABLED, None, 0)  # SPI_SETSCREENSAVEACTIVE
    
    if SCREENSAVER_TIMEOUT is not None:
        windll.user32.SystemParametersInfoA(0x0073, SCREENSAVER_TIMEOUT, None, 0)  # SPI_SETSCREENSAVETIMEOUT

# 防睡眠线程函数
def prevent_sleep():
    """防止系统睡眠和关闭屏幕"""
    kernel32 = windll.kernel32
    while prevent_sleep.running:
        kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        time.sleep(30)

def create_black_screen():
    """创建全屏黑色窗口"""
    # 获取原始系统状态
    get_original_state()
    
    # 启动防睡眠功能
    prevent_sleep.running = True
    sleep_thread = threading.Thread(target=prevent_sleep)
    sleep_thread.daemon = True
    sleep_thread.start()
    
    # 创建主窗口
    root = tk.Tk()
    root.title("离开模式")
    
    # 获取屏幕尺寸
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # 设置全屏无边框窗口
    root.overrideredirect(True)
    root.geometry(f"{screen_width}x{screen_height}+0+0")
    root.config(bg="black")
    
    # 窗口置顶
    root.attributes("-topmost", True)
    
    # 禁用Alt+F4
    root.protocol("WM_DELETE_WINDOW", lambda: None)
    
    # 绑定ESC键退出 - 退出前恢复原始状态
    def on_escape(event):
        prevent_sleep.running = False
        restore_original_state()
        root.destroy()
        sys.exit()
    root.bind("<Escape>", on_escape)
    
    # 隐藏鼠标光标
    root.config(cursor="none")
    
    # 禁用Windows键
    root.bind("<Super_L>", lambda e: "break")
    root.bind("<Super_R>", lambda e: "break")
    
    # 隐藏任务栏图标
    try:
        hwnd = windll.user32.GetParent(root.winfo_id())
        
        # 获取原始扩展样式
        current_style = windll.user32.GetWindowLongA(hwnd, GWL_EXSTYLE)
        windll.user32.SetWindowLongA(hwnd, GWL_EXSTYLE, current_style | WS_EX_TOOLWINDOW)
    except Exception:
        pass
    
    # 禁用Alt+Tab和任务切换
    def block_alt_tab(e):
        if e.keysym in ('Alt_L', 'Alt_R', 'Tab'):
            return "break"
    root.bind("<Alt-Tab>", block_alt_tab)
    root.bind("<Alt_L>", block_alt_tab)
    root.bind("<Alt_R>", block_alt_tab)
    
    # 禁用Windows+D显示桌面
    def block_win_d(e):
        if e.keysym == 'd' and e.state & 0x4:  # 检查Windows键
            return "break"
    root.bind("<d>", block_win_d)
    
    # 阻止屏幕保护启动
    windll.user32.SystemParametersInfoA(0x0071, 0, None, 0)  # 禁用屏幕保护
    windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_DISPLAY_REQUIRED)
    
    # 设置退出时自动恢复
    root.bind("<Destroy>", lambda e: restore_original_state())
    
    # 进入主循环
    root.mainloop()

if __name__ == "__main__":
    try:
        create_black_screen()
    except Exception as e:
        restore_original_state()
        print(f"Error occurred: {e}")
        sys.exit(1)
