import tkinter as tk
import os
import sys
import ctypes
import subprocess
from tkinter import messagebox

class PersistentWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("你是关不掉的！！！")
        
        # 禁用常规关闭方式
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.bind('<Alt-F4>', self.disable_shortcut)
        self.root.bind('<Control-q>', self.disable_shortcut)
        
        # 创建透明顶层窗口
        self.top = tk.Toplevel(self.root)
        self.top.attributes("-alpha", 0.01)
        self.top.protocol('WM_DELETE_WINDOW', self.on_close)
        
        # 提升权限（需要管理员运行）
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        except Exception:
            pass
        
        # 自保护机制
        self.check_process()
        
        # 窗口内容
        label = tk.Label(self.root, text="你是关不掉的！！！", padx=50, pady=50)
        label.pack()

    def disable_shortcut(self, event):
        return "break"

    def on_close(self):
        messagebox.showinfo("这个窗口是关不掉的！！！")
        self.root.deiconify()
        self.start_new_instance()

    def check_process(self):
        # 进程守护（示例实现）
        if not self.is_process_alive():
            self.start_new_instance()

    def is_process_alive(self):
        # 简单的进程检查（需根据实际情况实现）
        return True

    def start_new_instance(self):
        subprocess.Popen([sys.executable, __file__], creationflags=subprocess.CREATE_NEW_CONSOLE)
        self.root.after(1000, self.root.destroy)

if __name__ == "__main__":
    app = PersistentWindow()
    app.root.mainloop()