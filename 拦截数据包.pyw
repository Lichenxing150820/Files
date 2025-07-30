# -*- coding: utf-8 -*-
# advanced_firewall_fixed.py - 高级网络流量拦截系统（最终修复版）
import os
import sys
import ctypes
import threading
import time
import logging
import subprocess
import socket
from tkinter import *
from tkinter import ttk, messagebox, scrolledtext
from scapy.all import *

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('firewall_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class FirewallMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("高级网络流量拦截系统")
        self.root.geometry("900x650")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 运行状态
        self.is_running = False
        self.sniff_thread = None
        self.block_all = False  # 全局拦截开关
        
        # 初始化UI
        self.setup_ui()
        
        # 检查管理员权限
        if not self.is_admin():
            self.request_uac()
        else:
            # 只有拥有管理员权限后才进行后续操作
            self.post_admin_init()
        
        # 确保只有一个窗口
        self.root.focus_force()

    def post_admin_init(self):
        """获得管理员权限后的初始化"""
        # 检查Npcap
        if not self.check_npcap():
            messagebox.showerror("错误", "请先安装Npcap (https://npcap.com/)")
            self.root.destroy()
            return
        
        # 初始化防火墙
        self.setup_firewall()
        
        # 初始状态
        self.status_var.set("就绪 - 管理员权限")
        logging.info("程序初始化完成")

    def setup_ui(self):
        """设置图形用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=BOTH, expand=True)
        
        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="10")
        control_frame.pack(fill=X, pady=5)
        
        # 拦截模式选择
        mode_frame = ttk.Frame(control_frame)
        mode_frame.grid(row=0, column=0, padx=5, sticky=W)
        
        self.mode_var = IntVar(value=0)
        ttk.Radiobutton(mode_frame, text="智能模式", variable=self.mode_var, value=0,
                       command=lambda: self.toggle_mode(False)).pack(side=LEFT)
        ttk.Radiobutton(mode_frame, text="全局拦截", variable=self.mode_var, value=1, 
                       command=lambda: self.toggle_mode(True)).pack(side=LEFT, padx=10)
        
        # 模式说明标签
        self.mode_desc = ttk.Label(mode_frame, text="(智能模式: 拦截特定目标 | 全局拦截: 拦截所有流量)")
        self.mode_desc.pack(side=LEFT, padx=10)
        
        # 操作按钮
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=0, column=1, padx=5)
        
        self.start_btn = ttk.Button(btn_frame, text="启动监控", command=self.start_monitor)
        self.start_btn.pack(side=LEFT, padx=2)
        self.stop_btn = ttk.Button(btn_frame, text="停止监控", command=self.stop_monitor, state=DISABLED)
        self.stop_btn.pack(side=LEFT, padx=2)
        self.add_btn = ttk.Button(btn_frame, text="添加目标", command=self.add_target)
        self.add_btn.pack(side=LEFT, padx=2)
        self.remove_btn = ttk.Button(btn_frame, text="删除目标", command=self.remove_target)
        self.remove_btn.pack(side=LEFT, padx=2)
        
        # 目标列表
        target_frame = ttk.LabelFrame(main_frame, text="目标列表", padding="10")
        target_frame.pack(fill=BOTH, expand=True, pady=5)
        
        self.target_tree = ttk.Treeview(target_frame, columns=('target', 'type', 'status'), show='headings')
        self.target_tree.heading('target', text='目标IP/域名')
        self.target_tree.heading('type', text='类型')
        self.target_tree.heading('status', text='状态')
        self.target_tree.column('target', width=300)
        self.target_tree.column('type', width=100)
        self.target_tree.column('status', width=100)
        
        vsb = ttk.Scrollbar(target_frame, orient="vertical", command=self.target_tree.yview)
        hsb = ttk.Scrollbar(target_frame, orient="horizontal", command=self.target_tree.xview)
        self.target_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.target_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        target_frame.grid_rowconfigure(0, weight=1)
        target_frame.grid_columnconfigure(0, weight=1)
        
        # 初始目标列表
        self.targets = []
        
        # 日志输出
        log_frame = ttk.LabelFrame(main_frame, text="系统日志", padding="10")
        log_frame.pack(fill=BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, wrap=WORD)
        self.log_text.pack(fill=BOTH, expand=True)
        self.log_text.configure(state='disabled')
        
        # 状态栏
        self.status_var = StringVar()
        self.status_var.set("正在初始化...")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=SUNKEN, anchor=W)
        status_bar.pack(fill=X, pady=(5,0))
        
        # 重定向日志到GUI
        self.log_handler = TextHandler(self.log_text, self.status_var)
        logging.getLogger().addHandler(self.log_handler)

    def update_target_list(self):
        """更新目标列表显示"""
        # 先清空现有列表
        for item in self.target_tree.get_children():
            self.target_tree.delete(item)
        
        # 添加所有目标
        for target in self.targets:
            target_type = "域名" if not target.replace('.', '').isdigit() else "IP"
            status = "待拦截" if not self.block_all else "例外"
            self.target_tree.insert('', 'end', values=(target, target_type, status))

    def suppress_cmd_window(self):
        """隐藏后台命令窗口"""
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # 完全隐藏窗口
            return startupinfo
        return None

    def is_admin(self):
        """检查是否以管理员权限运行"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def request_uac(self):
        """请求UAC提权"""
        try:
            # 先隐藏当前窗口
            self.root.withdraw()
            
            # 请求提权
            script = os.path.abspath(sys.argv[0])
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script}"', None, 0)  # 0表示隐藏窗口
            
            # 关闭当前实例
            self.root.destroy()
            sys.exit(0)
        except Exception as e:
            messagebox.showerror("错误", f"请求管理员权限失败: {str(e)}")
            self.root.destroy()

    def check_npcap(self):
        """检查Npcap是否安装"""
        try:
            from scapy.arch.windows import get_windows_if_list
            if not get_windows_if_list():
                raise ImportError
            return True
        except:
            logging.error("Npcap未安装或配置不正确")
            return False

    def setup_firewall(self):
        """初始化防火墙配置"""
        self.execute_silent('netsh advfirewall set allprofiles state on')
        logging.info("防火墙已初始化")

    def toggle_mode(self, global_block):
        """切换拦截模式"""
        self.block_all = global_block
        
        # 清理旧规则
        self.clean_firewall_rules()
        
        if global_block:
            # 全局拦截模式
            self.execute_silent('netsh advfirewall firewall add rule name="GlobalBlock" dir=out action=block')
            self.execute_silent('netsh advfirewall firewall add rule name="GlobalBlockIn" dir=in action=block')
            logging.info("已启用全局拦截模式 - 所有流量将被拦截")
            self.status_var.set("全局拦截模式已启用")
        else:
            # 智能模式 - 只拦截列表中的目标
            logging.info("已启用智能模式 - 只拦截列表中的目标")
            self.status_var.set("智能模式已启用")
        
        # 重新应用目标规则
        self.apply_target_rules()
        self.update_target_list()

    def execute_silent(self, command):
        """静默执行命令"""
        try:
            startupinfo = self.suppress_cmd_window()
            result = subprocess.run(
                command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                startupinfo=startupinfo,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            if result.returncode != 0:
                logging.warning(f"命令执行可能失败: {command}")
                logging.debug(f"错误输出: {result.stderr.strip()}")
            return result
        except Exception as e:
            logging.error(f"执行命令失败: {command}\n错误: {str(e)}")
            return None

    def apply_target_rules(self):
        """应用目标规则到防火墙"""
        if not hasattr(self, 'target_tree') or not self.targets:
            return
            
        for target in self.targets:
            if self.block_all:
                # 全局模式 - 为每个目标创建允许规则
                self.execute_silent(
                    f'netsh advfirewall firewall add rule '
                    f'name="Allow_{target}" '
                    f'dir=out '
                    f'remoteip={target} '
                    f'action=allow'
                )
                self.execute_silent(
                    f'netsh advfirewall firewall add rule '
                    f'name="AllowIn_{target}" '
                    f'dir=in '
                    f'remoteip={target} '
                    f'action=allow'
                )
            else:
                # 智能模式 - 为每个目标创建拦截规则
                self.execute_silent(
                    f'netsh advfirewall firewall add rule '
                    f'name="Block_{target}" '
                    f'dir=out '
                    f'remoteip={target} '
                    f'action=block'
                )
                self.execute_silent(
                    f'netsh advfirewall firewall add rule '
                    f'name="BlockIn_{target}" '
                    f'dir=in '
                    f'remoteip={target} '
                    f'action=block'
                )
        
        logging.info("防火墙规则已更新")
        self.update_target_list()

    def resolve_domain(self, domain):
        """解析域名到IP地址"""
        try:
            return socket.gethostbyname(domain)
        except:
            return None

    def packet_callback(self, packet):
        """Scapy数据包回调处理函数 - 实际监控逻辑"""
        # 这是一个空实现，因为我们使用防火墙规则进行拦截
        # 在实际使用中，可以添加额外的监控逻辑
        pass

    def start_monitor(self):
        """启动流量监控"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # 应用当前模式规则
        self.toggle_mode(self.block_all)
        
        # 启动监控线程
        self.sniff_thread = threading.Thread(
            target=self.run_sniff,
            daemon=True
        )
        self.sniff_thread.start()
        
        # 更新按钮状态
        self.start_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.add_btn.config(state=NORMAL)
        self.remove_btn.config(state=NORMAL)
        
        logging.info("=== 启动流量监控 ===")
        self.status_var.set("监控运行中...")

    def stop_monitor(self):
        """停止流量监控"""
        if self.is_running:
            self.is_running = False
            if self.sniff_thread and self.sniff_thread.is_alive():
                self.sniff_thread.join(timeout=2.0)
            
            # 更新按钮状态
            self.start_btn.config(state=NORMAL)
            self.stop_btn.config(state=DISABLED)
            
            # 清除防火墙规则
            self.clean_firewall_rules()
            
            logging.info("=== 停止流量监控 ===")
            logging.info("已清除所有防火墙规则，网络连接恢复正常")
            self.status_var.set("监控已停止，网络已恢复")

    def run_sniff(self):
        """运行Scapy嗅探线程"""
        while self.is_running:
            try:
                # 实际监控逻辑
                # 这里我们使用简化的实现，因为防火墙规则已经处理了拦截
                # 可以添加额外的监控或日志记录功能
                time.sleep(1)
                
                # 为了演示目的，保留Scapy调用但使用超时
                sniff(filter="ip", store=0, timeout=1)
                
            except Exception as e:
                logging.error(f"监控错误: {str(e)}")
                time.sleep(1)

    def add_target(self):
        """添加目标"""
        dialog = AddTargetDialog(self.root)
        self.root.wait_window(dialog.top)
        
        if dialog.result:
            target = dialog.result.strip()
            if target not in self.targets:
                self.targets.append(target)
                self.apply_target_rules()
                self.update_target_list()
                logging.info(f"已添加目标: {target}")

    def remove_target(self):
        """删除目标"""
        selected = self.target_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要删除的目标")
            return
            
        for item in selected:
            target = self.target_tree.item(item, 'values')[0]
            if target in self.targets:
                self.targets.remove(target)
                
                # 清理防火墙规则
                self.execute_silent(f'netsh advfirewall firewall delete rule name="Block_{target}" >nul 2>&1')
                self.execute_silent(f'netsh advfirewall firewall delete rule name="BlockIn_{target}" >nul 2>&1')
                self.execute_silent(f'netsh advfirewall firewall delete rule name="Allow_{target}" >nul 2>&1')
                self.execute_silent(f'netsh advfirewall firewall delete rule name="AllowIn_{target}" >nul 2>&1')
                
                logging.info(f"已移除目标: {target}")
        
        self.update_target_list()
        self.apply_target_rules()

    def clean_firewall_rules(self):
        """清理所有防火墙规则"""
        # 删除全局规则
        self.execute_silent('netsh advfirewall firewall delete rule name="GlobalBlock" >nul 2>&1')
        self.execute_silent('netsh advfirewall firewall delete rule name="GlobalBlockIn" >nul 2>&1')
        
        # 删除所有目标规则
        for target in self.targets:
            self.execute_silent(f'netsh advfirewall firewall delete rule name="Block_{target}" >nul 2>&1')
            self.execute_silent(f'netsh advfirewall firewall delete rule name="BlockIn_{target}" >nul 2>&1')
            self.execute_silent(f'netsh advfirewall firewall delete rule name="Allow_{target}" >nul 2>&1')
            self.execute_silent(f'netsh advfirewall firewall delete rule name="AllowIn_{target}" >nul 2>&1')
        
        logging.info("已清除所有防火墙规则")

    def on_close(self):
        """关闭窗口事件处理"""
        # 先移除日志处理器，防止关闭时出错
        logging.getLogger().removeHandler(self.log_handler)
        
        self.stop_monitor()
        self.clean_firewall_rules()
        
        logging.info("程序已退出")
        self.root.destroy()

class AddTargetDialog:
    """添加目标对话框"""
    def __init__(self, parent):
        self.top = Toplevel(parent)
        self.top.title("添加目标")
        self.top.geometry("350x180")
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.focus_force()
        
        self.result = None
        
        ttk.Label(self.top, text="请输入要添加的IP或域名:").pack(pady=10)
        
        self.entry = ttk.Entry(self.top, width=30)
        self.entry.pack(pady=5)
        self.entry.focus()
        
        ttk.Label(self.top, text="(在全局拦截模式下，这些目标将不会被拦截)").pack()
        
        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="确定", command=self.on_ok).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.on_cancel).pack(side=LEFT, padx=5)
        
        self.top.bind('<Return>', lambda e: self.on_ok())
        self.top.bind('<Escape>', lambda e: self.on_cancel())

    def on_ok(self):
        self.result = self.entry.get()
        if not self.result:
            messagebox.showwarning("警告", "请输入有效的IP或域名")
            return
        self.top.destroy()

    def on_cancel(self):
        self.result = None
        self.top.destroy()

class TextHandler(logging.Handler):
    """将日志输出重定向到Tkinter文本框"""
    def __init__(self, text_widget, status_var=None):
        super().__init__()
        self.text_widget = text_widget
        self.status_var = status_var
        
    def emit(self, record):
        try:
            msg = self.format(record)
            
            def append():
                try:
                    if self.text_widget.winfo_exists():
                        self.text_widget.configure(state='normal')
                        self.text_widget.insert(END, msg + '\n')
                        self.text_widget.configure(state='disabled')
                        self.text_widget.see(END)
                        
                        if self.status_var:
                            # 限制状态消息长度
                            status_msg = msg
                            if len(status_msg) > 80:
                                status_msg = status_msg[:77] + "..."
                            self.status_var.set(status_msg)
                except Exception:
                    pass  # 防止在关闭时出错
            
            if self.text_widget.winfo_exists():
                self.text_widget.after(0, append)
        except Exception:
            pass  # 确保不会因日志处理导致程序崩溃

# 主程序入口
if __name__ == "__main__":
    # 确保只运行一个实例
    root = Tk()
    
    # 防止重复创建窗口
    if not getattr(root, '_app_created', False):
        root._app_created = True
        app = FirewallMonitorApp(root)
        root.mainloop()
