import tkinter as tk
from datetime import datetime

class RealTimeClock:
    def __init__(self, master):
        self.master = master
        master.title("时间显示器")
        
        # 创建时间显示标签
        self.time_label = tk.Label(master, 
                                 font=('Arial', 48, 'bold'), 
                                 fg='#2E86C1',
                                 bg='#FDFEFE')
        self.time_label.pack(pady=40, padx=20)
        
        # 立即启动时间更新
        self.update_time()

    def update_time(self):
        # 使用datetime获取系统时间（替代os.time的底层实现）
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 带样式的动态文本更新
        self.time_label.config(text=current_time,
                             fg=self._get_color_by_second())
        
        # 设置1000ms后再次更新（精确到秒）
        self.master.after(1000, self.update_time)

    def _get_color_by_second(self):
        """ 动态颜色生成器：根据秒数变化颜色 """
        second = datetime.now().second
        return f'#{second%7 * 30:02x}{second%13 * 15:02x}{second%11 * 20:02x}'

if __name__ == "__main__":
    root = tk.Tk()
    app = RealTimeClock(root)
    root.configure(bg='#17202A')  # 深色背景增强对比度
    root.mainloop()
