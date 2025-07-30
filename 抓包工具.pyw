import socket
import os
import ctypes
import sys
import time
import threading
import queue
from tkinter import *
from tkinter import scrolledtext, ttk, messagebox
import platform

class NetworkSnifferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("网络流量嗅探器")
        self.root.geometry("800x600")
        self.running = False
        self.packet_count = 0
        self.sniffer = None
        self.packet_queue = queue.Queue()
        self.update_interval = 100  # UI更新间隔(毫秒)
        self.max_packets_per_update = 50  # 每次更新最多处理的数据包数
        
        # 设置UI
        self.setup_ui()
        
        # 检查是否是提权后的实例
        self.elevated = "--elevated" in sys.argv
        
        # 检查管理员权限
        if not self.is_admin():
            self.log_message("[!] 警告: 程序未以管理员权限运行")
            self.log_message("[!] 可能无法捕获所有网络流量")
            self.request_admin()
        else:
            self.log_message("[*] 程序已在管理员权限下运行")
        
        # 启动UI更新定时器
        self.root.after(self.update_interval, self.process_packet_queue)
    
    def setup_ui(self):
        # 顶部状态栏
        status_frame = Frame(self.root, bg="#f0f0f0", padx=10, pady=5)
        status_frame.pack(fill=X)
        
        # IP显示
        self.ip_label = Label(status_frame, text="本机IP: 正在检测...", bg="#f0f0f0")
        self.ip_label.pack(side=LEFT, padx=5)
        
        # 数据包计数器
        self.counter_label = Label(status_frame, text="数据包: 0", bg="#f0f0f0")
        self.counter_label.pack(side=RIGHT, padx=5)
        
        # 权限状态
        self.admin_label = Label(status_frame, text="权限: 未知", bg="#f0f0f0", fg="#cc0000")
        self.admin_label.pack(side=RIGHT, padx=5)
        
        # 控制面板
        control_frame = Frame(self.root, padx=10, pady=10)
        control_frame.pack(fill=X)
        
        # 开始/停止按钮
        self.start_button = Button(control_frame, text="开始捕获", command=self.start_sniffing, 
                                  width=10, bg="#4CAF50", fg="white")
        self.start_button.pack(side=LEFT, padx=5)
        
        self.stop_button = Button(control_frame, text="停止捕获", command=self.stop_sniffing, 
                                 state=DISABLED, width=10, bg="#F44336", fg="white")
        self.stop_button.pack(side=LEFT, padx=5)
        
        # 清空按钮
        Button(control_frame, text="清空日志", command=self.clear_log, width=10).pack(side=LEFT, padx=5)
        
        # 设置按钮
        Button(control_frame, text="设置", command=self.show_settings, width=10).pack(side=RIGHT, padx=5)
        
        # 日志区域
        log_frame = Frame(self.root)
        log_frame.pack(padx=10, pady=(0, 10), fill=BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = Scrollbar(log_frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=WORD, yscrollcommand=scrollbar.set)
        self.log_area.pack(fill=BOTH, expand=True)
        scrollbar.config(command=self.log_area.yview)
        
        # 设置日志区域字体
        self.log_area.config(font=("Consolas", 10))
        
        # 获取本机IP
        self.update_local_ip()
        
        # 更新权限状态显示
        self.update_admin_status()
    
    def update_admin_status(self):
        if self.is_admin():
            self.admin_label.config(text="权限: 管理员", fg="#2E7D32")
        else:
            self.admin_label.config(text="权限: 标准用户", fg="#D32F2F")
    
    def log_message(self, message):
        self.log_area.insert(END, message + "\n")
        self.log_area.see(END)
    
    def clear_log(self):
        self.log_area.delete(1.0, END)
        self.packet_count = 0
        self.update_counter()
    
    def update_counter(self):
        self.counter_label.config(text=f"数据包: {self.packet_count}")
    
    def process_packet_queue(self):
        """从队列中取出数据包并更新UI，避免频繁更新导致卡顿"""
        try:
            processed = 0
            while not self.packet_queue.empty() and processed < self.max_packets_per_update:
                packet_info = self.packet_queue.get_nowait()
                self.log_area.insert(END, packet_info + "\n")
                processed += 1
            
            # 如果队列中还有数据，滚动到底部
            if processed > 0:
                self.log_area.see(END)
                self.root.update_idletasks()
        
        except queue.Empty:
            pass
        
        # 继续安排下一次处理
        self.root.after(self.update_interval, self.process_packet_queue)
    
    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def request_admin(self):
        if self.elevated:
            return  # 已经是提权后的实例
        
        if messagebox.askyesno("权限请求", "此程序需要管理员权限才能捕获网络流量。是否立即提权？"):
            # 创建提权参数
            params = " ".join([sys.argv[0], "--elevated"])
            
            # 关闭当前窗口
            self.root.destroy()
            
            # 请求提权
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, params, None, 1)
            
            # 退出当前实例
            sys.exit(0)
    
    def get_local_ip(self):
        try:
            # 尝试获取真实IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            try:
                # 回退方法：获取主机名对应的IP
                hostname = socket.gethostname()
                return socket.gethostbyname(hostname)
            except:
                return "0.0.0.0"
    
    def update_local_ip(self):
        ip = self.get_local_ip()
        self.ip_label.config(text=f"本机IP: {ip}")
    
    def show_settings(self):
        # 创建设置窗口
        settings = Toplevel(self.root)
        settings.title("设置")
        settings.geometry("400x300")
        settings.transient(self.root)
        settings.grab_set()
        
        # 添加设置选项
        Label(settings, text="高级设置", font=("Arial", 14)).pack(pady=10)
        
        # 更新间隔设置
        frame = Frame(settings, padx=10, pady=5)
        frame.pack(fill=X)
        Label(frame, text="UI更新间隔(ms):").pack(side=LEFT)
        interval_var = StringVar(value=str(self.update_interval))
        Entry(frame, textvariable=interval_var, width=10).pack(side=LEFT, padx=5)
        
        # 最大包数设置
        frame = Frame(settings, padx=10, pady=5)
        frame.pack(fill=X)
        Label(frame, text="每次更新最大包数:").pack(side=LEFT)
        max_packets_var = StringVar(value=str(self.max_packets_per_update))
        Entry(frame, textvariable=max_packets_var, width=10).pack(side=LEFT, padx=5)
        
        # 保存按钮
        def save_settings():
            try:
                new_interval = int(interval_var.get())
                new_max = int(max_packets_var.get())
                
                if 10 <= new_interval <= 1000 and 10 <= new_max <= 200:
                    self.update_interval = new_interval
                    self.max_packets_per_update = new_max
                    messagebox.showinfo("设置", "设置已保存")
                else:
                    messagebox.showerror("错误", "无效的值范围 (10-1000ms, 10-200包)")
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
        
        Button(settings, text="保存", command=save_settings, width=10).pack(pady=20)
    
    def start_sniffing(self):
        if self.running:
            return
            
        if not self.is_admin():
            messagebox.showerror("权限错误", "需要管理员权限才能捕获网络流量")
            self.request_admin()
            return
        
        self.running = True
        self.start_button.config(state=DISABLED)
        self.stop_button.config(state=NORMAL)
        
        self.log_message("[*] 开始捕获网络流量...")
        
        # 在后台线程中运行嗅探器
        self.sniff_thread = threading.Thread(target=self.sniff_packets, daemon=True)
        self.sniff_thread.start()
    
    def stop_sniffing(self):
        if not self.running:
            return
        
        self.running = False
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        
        if self.sniffer:
            if os.name == 'nt':
                try:
                    self.sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
                except:
                    pass
            self.sniffer.close()
            self.sniffer = None
        
        self.log_message("[*] 已停止捕获网络流量")
    
    def sniff_packets(self):
        local_ip = self.get_local_ip()
        
        # 根据操作系统选择合适的协议
        if os.name == 'nt':
            socket_protocol = socket.IPPROTO_IP
        else:
            socket_protocol = socket.IPPROTO_ICMP

        try:
            # 创建原始套接字
            self.sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket_protocol)
            self.sniffer.bind((local_ip, 0))
            self.sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            
            # Windows系统需要启用混杂模式
            if os.name == 'nt':
                self.sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
                self.packet_queue.put("[*] 已启用网络接口的混杂模式")
            
            self.packet_queue.put("[*] 开始捕获网络流量 (按停止按钮结束)...")
            
            while self.running:
                try:
                    # 接收数据包
                    raw_data, addr = self.sniffer.recvfrom(65535)
                    self.packet_count += 1
                    
                    # 更新计数器
                    self.root.after(0, self.update_counter)
                    
                    # 将数据包信息放入队列
                    src_ip = addr[0]
                    packet_size = len(raw_data)
                    
                    # 提取协议信息（简化版本）
                    protocol = "未知"
                    if len(raw_data) >= 20:
                        ip_header = raw_data[0:20]
                        protocol_byte = ip_header[9]
                        if protocol_byte == 1:
                            protocol = "ICMP"
                        elif protocol_byte == 6:
                            protocol = "TCP"
                        elif protocol_byte == 17:
                            protocol = "UDP"
                    
                    packet_info = f"[{self.packet_count}] {src_ip} -> {local_ip} | {packet_size}字节 | {protocol}"
                    self.packet_queue.put(packet_info)
                    
                except socket.error as e:
                    # 检查是否应该退出
                    if not self.running:
                        break
                    
                    # 处理特定错误
                    if e.errno == 10004:  # WSAEINTR
                        continue  # 被中断的操作，可以继续
                    
                    self.packet_queue.put(f"[!] 套接字错误: {str(e)}")
                    break
                except Exception as e:
                    if not self.running:
                        break
                    self.packet_queue.put(f"[!] 错误: {str(e)}")
                    break
            
        except Exception as e:
            self.packet_queue.put(f"[!] 初始化错误: {str(e)}")
        finally:
            if self.sniffer:
                if os.name == 'nt':
                    try:
                        self.sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
                    except:
                        pass
                self.sniffer.close()
                self.sniffer = None

def main():
    root = Tk()
    
    # Windows系统设置任务栏图标
    if platform.system() == 'Windows':
        try:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID("NetworkSniffer.1.0")
        except:
            pass
    
    app = NetworkSnifferApp(root)
    
    # 设置窗口图标
    try:
        root.iconbitmap(default='icon.ico')  # 如果有图标文件
    except:
        pass
    
    # 窗口关闭事件处理
    def on_closing():
        app.stop_sniffing()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
