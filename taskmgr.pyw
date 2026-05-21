#pip install psutil GPUtil matplotlib
import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import GPUtil
import platform
import socket
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import threading
from collections import deque
import matplotlib.pyplot as plt
from matplotlib import font_manager

class SystemMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("系统任务管理器")
        self.root.geometry("1000x700")
        
        # 设置字体
        plt.rcParams['font.family'] = 'Arial'
        plt.rcParams['font.size'] = 10
        
        # 设置主题样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 创建标签页
        self.tab_control = ttk.Notebook(root)
        
        # 添加各个标签页
        self.create_system_tab()
        self.create_cpu_tab()
        self.create_memory_tab()
        self.create_gpu_tab()
        self.create_network_tab()
        self.create_process_tab()
        
        self.tab_control.pack(expand=1, fill="both")
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X)
        self.update_status("就绪")
        
        # 存储历史数据用于绘图
        self.cpu_history = deque(maxlen=30)
        self.memory_history = deque(maxlen=30)
        
        # 启动自动更新线程
        self.running = True
        self.update_thread = threading.Thread(target=self.auto_update_data, daemon=True)
        self.update_thread.start()
        
        # 窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def update_status(self, message):
        """更新状态栏"""
        current_time = time.strftime("%H:%M:%S")
        self.status_var.set(f"{current_time} - {message}")
    
    def on_close(self):
        """窗口关闭时清理资源"""
        self.running = False
        if self.update_thread.is_alive():
            self.update_thread.join(timeout=1)
        self.root.destroy()
    
    def auto_update_data(self):
        """自动更新CPU和内存数据"""
        while self.running:
            try:
                self.update_cpu_info()
                self.update_memory_info()
                self.update_charts()
                time.sleep(0.5)  # 0.5秒刷新一次
            except Exception as e:
                self.update_status(f"自动更新出错: {str(e)}")
                time.sleep(1)
    
    def manual_refresh(self):
        """手动刷新进程和网络数据"""
        try:
            self.update_processes()
            self.update_network_info()
            self.update_gpu_info()
            self.update_system_info()
            self.update_status("手动刷新完成")
        except Exception as e:
            self.update_status(f"刷新出错: {str(e)}")
            messagebox.showerror("错误", f"刷新数据时出错: {str(e)}")
    
    def create_system_tab(self):
        """系统信息标签页"""
        self.system_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.system_tab, text="系统信息")
        
        # 系统信息框架
        sys_frame = ttk.LabelFrame(self.system_tab, text="系统概览")
        sys_frame.pack(pady=10, padx=10, fill="x")
        
        # 系统信息标签
        self.os_label = ttk.Label(sys_frame, text="操作系统: ")
        self.os_label.pack(anchor="w", padx=5, pady=2)
        
        self.host_label = ttk.Label(sys_frame, text="主机名: ")
        self.host_label.pack(anchor="w", padx=5, pady=2)
        
        self.cpu_label = ttk.Label(sys_frame, text="处理器: ")
        self.cpu_label.pack(anchor="w", padx=5, pady=2)
        
        self.boot_label = ttk.Label(sys_frame, text="启动时间: ")
        self.boot_label.pack(anchor="w", padx=5, pady=2)
        
        # 磁盘信息框架
        disk_frame = ttk.LabelFrame(self.system_tab, text="磁盘信息")
        disk_frame.pack(pady=10, padx=10, fill="x")
        
        self.disk_tree = ttk.Treeview(disk_frame, columns=("Device", "Mount", "Total", "Used", "Free", "Percent"), show="headings")
        self.disk_tree.heading("Device", text="设备")
        self.disk_tree.heading("Mount", text="挂载点")
        self.disk_tree.heading("Total", text="总空间")
        self.disk_tree.heading("Used", text="已用")
        self.disk_tree.heading("Free", text="可用")
        self.disk_tree.heading("Percent", text="使用率")
        
        self.disk_tree.column("Device", width=100)
        self.disk_tree.column("Mount", width=150)
        self.disk_tree.column("Total", width=100)
        self.disk_tree.column("Used", width=100)
        self.disk_tree.column("Free", width=100)
        self.disk_tree.column("Percent", width=80)
        
        self.disk_tree.pack(fill="both", expand=True)
        
        # 刷新按钮
        refresh_btn = ttk.Button(self.system_tab, text="刷新系统信息", command=self.update_system_info)
        refresh_btn.pack(pady=5)
    
    def create_cpu_tab(self):
        """CPU标签页"""
        self.cpu_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.cpu_tab, text="CPU")
        
        # CPU使用率框架
        cpu_frame = ttk.LabelFrame(self.cpu_tab, text="CPU使用率")
        cpu_frame.pack(pady=10, padx=10, fill="x")
        
        # CPU总使用率
        self.cpu_total_label = ttk.Label(cpu_frame, text="总使用率: 0%")
        self.cpu_total_label.pack(anchor="w", padx=5, pady=2)
        
        # 每个核心的使用率
        self.cpu_core_labels = []
        core_frame = ttk.Frame(cpu_frame)
        core_frame.pack(fill="x", padx=5, pady=5)
        
        # 创建CPU核心使用率进度条
        for i in range(psutil.cpu_count(logical=True)):
            frame = ttk.Frame(core_frame)
            frame.pack(fill="x", padx=5, pady=2)
            
            label = ttk.Label(frame, text=f"核心 {i}:", width=8)
            label.pack(side="left")
            
            progress = ttk.Progressbar(frame, orient="horizontal", length=200, mode="determinate")
            progress.pack(side="left", fill="x", expand=True)
            
            percent_label = ttk.Label(frame, text="0%", width=5)
            percent_label.pack(side="left")
            
            self.cpu_core_labels.append((progress, percent_label))
        
        # CPU使用率图表
        fig = Figure(figsize=(6, 3), dpi=100)
        self.cpu_plot = fig.add_subplot(111)
        self.cpu_plot.set_title("CPU Usage History", fontname='Arial')
        self.cpu_plot.set_ylim(0, 100)
        self.cpu_plot.set_xlabel("Time", fontname='Arial')
        self.cpu_plot.set_ylabel("Usage (%)", fontname='Arial')
        self.cpu_line, = self.cpu_plot.plot([], [], 'r-')
        
        self.cpu_canvas = FigureCanvasTkAgg(fig, master=self.cpu_tab)
        self.cpu_canvas.draw()
        self.cpu_canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def create_memory_tab(self):
        """内存标签页"""
        self.memory_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.memory_tab, text="内存")
        
        # 内存使用信息框架
        mem_frame = ttk.LabelFrame(self.memory_tab, text="内存使用情况")
        mem_frame.pack(pady=10, padx=10, fill="x")
        
        # 内存信息标签
        self.mem_total_label = ttk.Label(mem_frame, text="总内存: ")
        self.mem_total_label.pack(anchor="w", padx=5, pady=2)
        
        self.mem_used_label = ttk.Label(mem_frame, text="已使用: ")
        self.mem_used_label.pack(anchor="w", padx=5, pady=2)
        
        self.mem_free_label = ttk.Label(mem_frame, text="可用: ")
        self.mem_free_label.pack(anchor="w", padx=5, pady=2)
        
        self.mem_percent_label = ttk.Label(mem_frame, text="使用率: ")
        self.mem_percent_label.pack(anchor="w", padx=5, pady=2)
        
        # 内存进度条
        self.mem_progress = ttk.Progressbar(mem_frame, orient="horizontal", length=300, mode="determinate")
        self.mem_progress.pack(fill="x", padx=5, pady=5)
        
        # 交换内存信息
        swap_frame = ttk.LabelFrame(self.memory_tab, text="交换内存")
        swap_frame.pack(pady=10, padx=10, fill="x")
        
        self.swap_total_label = ttk.Label(swap_frame, text="总交换内存: ")
        self.swap_total_label.pack(anchor="w", padx=5, pady=2)
        
        self.swap_used_label = ttk.Label(swap_frame, text="已使用: ")
        self.swap_used_label.pack(anchor="w", padx=5, pady=2)
        
        self.swap_percent_label = ttk.Label(swap_frame, text="使用率: ")
        self.swap_percent_label.pack(anchor="w", padx=5, pady=2)
        
        # 交换内存进度条
        self.swap_progress = ttk.Progressbar(swap_frame, orient="horizontal", length=300, mode="determinate")
        self.swap_progress.pack(fill="x", padx=5, pady=5)
        
        # 内存使用率图表
        fig = Figure(figsize=(6, 3), dpi=100)
        self.mem_plot = fig.add_subplot(111)
        self.mem_plot.set_title("Memory Usage History", fontname='Arial')
        self.mem_plot.set_ylim(0, 100)
        self.mem_plot.set_xlabel("Time", fontname='Arial')
        self.mem_plot.set_ylabel("Usage (%)", fontname='Arial')
        self.mem_line, = self.mem_plot.plot([], [], 'b-')
        
        self.mem_canvas = FigureCanvasTkAgg(fig, master=self.memory_tab)
        self.mem_canvas.draw()
        self.mem_canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def create_gpu_tab(self):
        """GPU标签页"""
        self.gpu_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.gpu_tab, text="GPU")
        
        # GPU信息框架
        gpu_frame = ttk.LabelFrame(self.gpu_tab, text="GPU信息")
        gpu_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # 创建Treeview显示GPU信息
        self.gpu_tree = ttk.Treeview(gpu_frame, columns=("ID", "Name", "Load", "Memory", "Temp"), show="headings")
        self.gpu_tree.heading("ID", text="ID")
        self.gpu_tree.heading("Name", text="名称")
        self.gpu_tree.heading("Load", text="负载")
        self.gpu_tree.heading("Memory", text="显存")
        self.gpu_tree.heading("Temp", text="温度")
        
        self.gpu_tree.column("ID", width=50)
        self.gpu_tree.column("Name", width=150)
        self.gpu_tree.column("Load", width=100)
        self.gpu_tree.column("Memory", width=150)
        self.gpu_tree.column("Temp", width=80)
        
        self.gpu_tree.pack(fill="both", expand=True)
        
        # 刷新按钮
        refresh_btn = ttk.Button(self.gpu_tab, text="刷新GPU信息", command=self.update_gpu_info)
        refresh_btn.pack(pady=5)
        
        # 如果没有GPU设备
        self.no_gpu_label = ttk.Label(gpu_frame, text="未检测到GPU设备")
    
    def create_network_tab(self):
        """网络标签页"""
        self.network_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.network_tab, text="网络")
        
        # 网络IO框架
        io_frame = ttk.LabelFrame(self.network_tab, text="网络流量")
        io_frame.pack(pady=10, padx=10, fill="x")
        
        # 网络IO信息
        self.net_sent_label = ttk.Label(io_frame, text="发送: ")
        self.net_sent_label.pack(anchor="w", padx=5, pady=2)
        
        self.net_recv_label = ttk.Label(io_frame, text="接收: ")
        self.net_recv_label.pack(anchor="w", padx=5, pady=2)
        
        self.net_packets_sent_label = ttk.Label(io_frame, text="发送包数: ")
        self.net_packets_sent_label.pack(anchor="w", padx=5, pady=2)
        
        self.net_packets_recv_label = ttk.Label(io_frame, text="接收包数: ")
        self.net_packets_recv_label.pack(anchor="w", padx=5, pady=2)
        
        # 网络连接框架
        conn_frame = ttk.LabelFrame(self.network_tab, text="网络连接")
        conn_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # 创建Treeview显示网络连接
        self.conn_tree = ttk.Treeview(conn_frame, columns=("LIP", "LPort", "RIP", "RPort", "Status", "PID"), show="headings")
        self.conn_tree.heading("LIP", text="本地IP")
        self.conn_tree.heading("LPort", text="本地端口")
        self.conn_tree.heading("RIP", text="远程IP")
        self.conn_tree.heading("RPort", text="远程端口")
        self.conn_tree.heading("Status", text="状态")
        self.conn_tree.heading("PID", text="PID")
        
        self.conn_tree.column("LIP", width=120)
        self.conn_tree.column("LPort", width=80)
        self.conn_tree.column("RIP", width=120)
        self.conn_tree.column("RPort", width=80)
        self.conn_tree.column("Status", width=80)
        self.conn_tree.column("PID", width=60)
        
        self.conn_tree.pack(fill="both", expand=True)
        
        # 刷新按钮
        refresh_btn = ttk.Button(self.network_tab, text="刷新网络信息", command=self.update_network_info)
        refresh_btn.pack(pady=5)
    
    def create_process_tab(self):
        """进程标签页"""
        self.process_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.process_tab, text="进程")
        
        # 进程信息框架
        proc_frame = ttk.LabelFrame(self.process_tab, text="进程列表")
        proc_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # 创建Treeview显示进程信息
        self.proc_tree = ttk.Treeview(proc_frame, columns=("PID", "Name", "User", "CPU", "Memory"), show="headings")
        self.proc_tree.heading("PID", text="PID")
        self.proc_tree.heading("Name", text="名称")
        self.proc_tree.heading("User", text="用户")
        self.proc_tree.heading("CPU", text="CPU%")
        self.proc_tree.heading("Memory", text="内存%")
        
        self.proc_tree.column("PID", width=60)
        self.proc_tree.column("Name", width=150)
        self.proc_tree.column("User", width=100)
        self.proc_tree.column("CPU", width=80)
        self.proc_tree.column("Memory", width=80)
        
        self.proc_tree.pack(fill="both", expand=True)
        
        # 添加排序功能
        for col in ("PID", "Name", "User", "CPU", "Memory"):
            self.proc_tree.heading(col, command=lambda c=col: self.sort_processes(c))
        
        # 进程操作按钮
        btn_frame = ttk.Frame(self.process_tab)
        btn_frame.pack(pady=5, fill="x")
        
        self.refresh_btn = ttk.Button(btn_frame, text="刷新进程列表", command=self.update_processes)
        self.refresh_btn.pack(side="left", padx=5)
        
        self.kill_btn = ttk.Button(btn_frame, text="结束进程", command=self.kill_process)
        self.kill_btn.pack(side="left", padx=5)
        
        # 全局刷新按钮
        global_refresh_btn = ttk.Button(self.process_tab, text="全局刷新", command=self.manual_refresh)
        global_refresh_btn.pack(pady=5)
    
    def sort_processes(self, col):
        """进程列表排序"""
        items = [(self.proc_tree.set(child, col), child) for child in self.proc_tree.get_children('')]
        
        # 尝试转换为数字排序
        try:
            items.sort(key=lambda t: float(t[0]), reverse=True)
        except ValueError:
            items.sort(reverse=True)
        
        for index, (val, child) in enumerate(items):
            self.proc_tree.move(child, '', index)
    
    def kill_process(self):
        """结束选中的进程"""
        selected = self.proc_tree.selection()
        if not selected:
            return
        
        item = self.proc_tree.item(selected[0])
        pid = int(item['values'][0])
        name = item['values'][1]
        
        try:
            if messagebox.askyesno("确认", f"确定要结束进程 {name} (PID: {pid}) 吗?"):
                p = psutil.Process(pid)
                p.terminate()
                self.update_status(f"已结束进程: {name} (PID: {pid})")
                self.update_processes()
        except Exception as e:
            messagebox.showerror("错误", f"无法结束进程: {e}")
    
    def update_system_info(self):
        """更新系统信息"""
        try:
            # 操作系统信息
            os_info = f"{platform.system()} {platform.release()} {platform.version()}"
            self.os_label.config(text=f"操作系统: {os_info}")
            
            # 主机名
            self.host_label.config(text=f"主机名: {socket.gethostname()}")
            
            # CPU信息
            cpu_info = f"{platform.processor()} ({psutil.cpu_count(logical=True)} 逻辑核心)"
            self.cpu_label.config(text=f"处理器: {cpu_info}")
            
            # 启动时间
            boot_time = psutil.boot_time()
            from datetime import datetime
            self.boot_label.config(text=f"启动时间: {datetime.fromtimestamp(boot_time).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 磁盘信息
            for item in self.disk_tree.get_children():
                self.disk_tree.delete(item)
                
            for part in psutil.disk_partitions(all=False):
                if part.fstype:
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        self.disk_tree.insert("", "end", values=(
                            part.device,
                            part.mountpoint,
                            f"{usage.total/(1024**3):.1f} GB",
                            f"{usage.used/(1024**3):.1f} GB",
                            f"{usage.free/(1024**3):.1f} GB",
                            f"{usage.percent}%"
                        ))
                    except Exception:
                        continue
        except Exception as e:
            self.update_status(f"更新系统信息出错: {str(e)}")
    
    def update_cpu_info(self):
        """更新CPU信息"""
        try:
            # 获取CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
            total_percent = sum(cpu_percent) / len(cpu_percent)
            
            # 更新总使用率
            self.cpu_total_label.config(text=f"总使用率: {total_percent:.1f}%")
            
            # 更新每个核心的使用率
            for i, (progress, label) in enumerate(self.cpu_core_labels):
                percent = cpu_percent[i] if i < len(cpu_percent) else 0
                progress['value'] = percent
                label.config(text=f"{percent:.1f}%")
            
            # 记录历史数据
            self.cpu_history.append(total_percent)
        except Exception as e:
            self.update_status(f"更新CPU信息出错: {str(e)}")
    
    def update_memory_info(self):
        """更新内存信息"""
        try:
            # 物理内存
            mem = psutil.virtual_memory()
            self.mem_total_label.config(text=f"总内存: {mem.total/(1024**3):.2f} GB")
            self.mem_used_label.config(text=f"已使用: {mem.used/(1024**3):.2f} GB")
            self.mem_free_label.config(text=f"可用: {mem.available/(1024**3):.2f} GB")
            self.mem_percent_label.config(text=f"使用率: {mem.percent}%")
            self.mem_progress['value'] = mem.percent
            
            # 交换内存
            swap = psutil.swap_memory()
            self.swap_total_label.config(text=f"总交换内存: {swap.total/(1024**3):.2f} GB")
            self.swap_used_label.config(text=f"已使用: {swap.used/(1024**3):.2f} GB")
            self.swap_percent_label.config(text=f"使用率: {swap.percent}%")
            self.swap_progress['value'] = swap.percent
            
            # 记录历史数据
            self.memory_history.append(mem.percent)
        except Exception as e:
            self.update_status(f"更新内存信息出错: {str(e)}")
    
    def update_gpu_info(self):
        """更新GPU信息"""
        try:
            gpus = GPUtil.getGPUs()
            
            # 清除旧数据
            for item in self.gpu_tree.get_children():
                self.gpu_tree.delete(item)
            
            if not gpus:
                self.no_gpu_label.pack()
                return
            
            self.no_gpu_label.pack_forget()
            
            # 添加新数据
            for i, gpu in enumerate(gpus):
                self.gpu_tree.insert("", "end", values=(
                    i,
                    gpu.name,
                    f"{gpu.load*100:.1f}%",
                    f"{gpu.memoryUsed:.1f}/{gpu.memoryTotal:.1f} MB",
                    f"{gpu.temperature}°C"
                ))
        except Exception as e:
            self.update_status(f"更新GPU信息出错: {str(e)}")
    
    def update_network_info(self):
        """更新网络信息"""
        try:
            # 网络IO统计
            net_io = psutil.net_io_counters()
            self.net_sent_label.config(text=f"发送: {net_io.bytes_sent/(1024**2):.2f} MB")
            self.net_recv_label.config(text=f"接收: {net_io.bytes_recv/(1024**2):.2f} MB")
            self.net_packets_sent_label.config(text=f"发送包数: {net_io.packets_sent}")
            self.net_packets_recv_label.config(text=f"接收包数: {net_io.packets_recv}")
            
            # 网络连接
            for item in self.conn_tree.get_children():
                self.conn_tree.delete(item)
                
            connections = psutil.net_connections(kind='inet')
            for conn in connections[:100]:  # 只显示前100个连接
                self.conn_tree.insert("", "end", values=(
                    conn.laddr.ip if conn.laddr else "-",
                    conn.laddr.port if conn.laddr else "-",
                    conn.raddr.ip if conn.raddr else "-",
                    conn.raddr.port if conn.raddr else "-",
                    conn.status,
                    conn.pid
                ))
        except Exception as e:
            self.update_status(f"更新网络信息出错: {str(e)}")
    
    def update_processes(self):
        """更新进程列表"""
        try:
            # 获取进程信息
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # 按CPU使用率排序
            processes = sorted(processes, key=lambda p: p['cpu_percent'], reverse=True)[:100]  # 只显示前100个
            
            # 更新Treeview
            for item in self.proc_tree.get_children():
                self.proc_tree.delete(item)
                
            for proc in processes:
                self.proc_tree.insert("", "end", values=(
                    proc['pid'],
                    proc['name'],
                    proc['username'],
                    f"{proc['cpu_percent']:.1f}",
                    f"{proc['memory_percent']:.1f}"
                ))
        except Exception as e:
            self.update_status(f"更新进程信息出错: {str(e)}")
    
    def update_charts(self):
        """更新图表数据"""
        try:
            # 更新CPU图表
            self.cpu_line.set_data(range(len(self.cpu_history)), self.cpu_history)
            self.cpu_plot.set_xlim(0, len(self.cpu_history))
            self.cpu_canvas.draw()
            
            # 更新内存图表
            self.mem_line.set_data(range(len(self.memory_history)), self.memory_history)
            self.mem_plot.set_xlim(0, len(self.memory_history))
            self.mem_canvas.draw()
        except Exception as e:
            self.update_status(f"更新图表出错: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SystemMonitorApp(root)
    root.mainloop()
