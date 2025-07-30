import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, Menu, simpledialog, filedialog
import socket
import threading
import json
import os
import time
from datetime import datetime
import configparser

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("聊天客户端")
        self.root.geometry("800x600")
        
        # 连接状态
        self.connected = False
        self.socket = None
        self.current_file = None
        self.pending_files = {}  # 存储待接收文件的信息
        
        # 创建聊天记录存储目录
        self.log_dir = os.path.join(os.path.expanduser("~"), "Documents", "sheepchatfile")
        os.makedirs(self.log_dir, exist_ok=True)
        self.current_log_file = None  # 当前日志文件路径
        
        # 添加配置文件
        self.config_path = os.path.join(os.path.expanduser("~"), ".sheepchat_client.cfg")
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)
        
        # 如果配置文件不存在，创建默认配置
        if not self.config.has_section('Connection'):
            self.config['Connection'] = {
                'ip': '127.0.0.1',
                'port': '65432',
                'nickname': ''
            }
        
        # 显示登录界面
        self.show_login_ui()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def save_config(self):
        """保存当前配置到文件"""
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
    
    def get_log_file_path(self, nickname):
        """获取当天日志文件路径"""
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.log_dir, f"{nickname}_{today}.log")
    
    def load_chat_history(self):
        """加载当天的聊天记录"""
        if not os.path.exists(self.current_log_file):
            return

        self.msg_text.config(state=tk.NORMAL)
        with open(self.current_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.msg_text.insert(tk.END, content)
            self.msg_text.see(tk.END)
        self.msg_text.config(state=tk.DISABLED)
    
    def show_login_ui(self):
        """显示登录界面"""
        self.login_frame = ttk.Frame(self.root)
        self.login_frame.pack(fill="both", expand=True, padx=50, pady=50)
        
        ttk.Label(self.login_frame, text="IP地址:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.ip_entry = ttk.Entry(self.login_frame)
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.ip_entry.insert(0, self.config['Connection'].get('ip', '127.0.0.1'))
        
        ttk.Label(self.login_frame, text="端口号:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.port_entry = ttk.Entry(self.login_frame)
        self.port_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.port_entry.insert(0, self.config['Connection'].get('port', '65432'))
        
        ttk.Label(self.login_frame, text="昵称:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.nick_entry = ttk.Entry(self.login_frame)
        self.nick_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.nick_entry.insert(0, self.config['Connection'].get('nickname', ''))
        
        login_btn = ttk.Button(self.login_frame, text="连接", command=self.connect_to_server)
        login_btn.grid(row=3, column=0, columnspan=2, padx=5, pady=15, sticky="nsew")
        
        # 配置列权重
        self.login_frame.columnconfigure(1, weight=1)
    
    def connect_to_server(self):
        """连接到服务器"""
        if self.connected:
            return
            
        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()
        nickname = self.nick_entry.get().strip()
        
        if not ip:
            messagebox.showerror("错误", "请输入IP地址")
            return
        if not port.isdigit():
            messagebox.showerror("错误", "端口号必须是数字")
            return
        if not nickname:
            messagebox.showerror("错误", "请输入昵称")
            return
            
        # 检查禁止的昵称
        if nickname.lower() in ["管理", "管理员", "服务器", "系统消息", "系统", "sb", "admin", "administrator", "傻逼", "死", "杀", "傻", "逼", "傻子", "他妈的", "操", "操你妈", "server", "service","错误"]:
            messagebox.showerror("昵称不可用", "此昵称包含敏感词")
            return
            
        # 保存当前配置
        self.config['Connection']['ip'] = ip
        self.config['Connection']['port'] = port
        self.config['Connection']['nickname'] = nickname
        self.save_config()
        
        port = int(port)
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((ip, port))
            
            # 发送登录信息
            login_data = {
                "type": "login",
                "nickname": nickname
            }
            self.socket.send(json.dumps(login_data).encode('utf-8'))
            
            # 接收登录响应
            response = self.socket.recv(1024).decode('utf-8')
            if not response:
                messagebox.showerror("错误", "服务器无响应")
                self.socket.close()
                return
                
            response_data = json.loads(response)
            if response_data.get("status") != "success":
                messagebox.showerror("错误", response_data.get("message", "登录失败"))
                self.socket.close()
                return
                
            # 登录成功
            self.connected = True
            self.nickname = nickname
            self.user_list = response_data.get("user_list", [])
            
            # 设置当前日志文件
            self.current_log_file = self.get_log_file_path(nickname)
            
            # 移除登录界面，显示主界面
            self.login_frame.destroy()
            self.setup_chat_ui()
            
            # 加载聊天记录
            self.load_chat_history()
            
            # 启动接收消息线程
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("错误", f"连接失败: {str(e)}")
            if self.socket:
                self.socket.close()
    
    def setup_chat_ui(self):
        """设置聊天界面"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 用户列表框
        user_frame = ttk.LabelFrame(main_frame, text="在线用户")
        user_frame.pack(side="left", fill="y", padx=5, pady=5)
        
        self.user_listbox = tk.Listbox(user_frame, width=20)
        self.user_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # 刷新用户列表
        self.refresh_user_list()
        
        # 文件传输按钮
        file_frame = ttk.Frame(user_frame)
        file_frame.pack(fill="x", padx=5, pady=5)
        
        self.file_btn = ttk.Button(file_frame, text="发送文件", command=self.send_file_dialog)
        self.file_btn.pack(fill="x", padx=5, pady=2)
        
        # 语音消息按钮
        self.voice_btn = ttk.Button(file_frame, text="语音消息", command=self.send_voice_message)
        self.voice_btn.pack(fill="x", padx=5, pady=2)
        
        # 私聊选择
        self.private_var = tk.BooleanVar()
        private_chk = ttk.Checkbutton(file_frame, text="私聊模式", variable=self.private_var)
        private_chk.pack(fill="x", padx=5, pady=2)
        
        # 右侧消息区域
        msg_frame = ttk.Frame(main_frame)
        msg_frame.pack(side="right", fill="both", expand=True)
        
        # 消息显示区域
        msg_display = ttk.LabelFrame(msg_frame, text="聊天内容")
        msg_display.pack(fill="both", expand=True)
        
        self.msg_text = scrolledtext.ScrolledText(msg_display, state=tk.DISABLED)
        self.msg_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.msg_text.tag_config("system", foreground="blue")
        self.msg_text.tag_config("private", foreground="purple")
        self.msg_text.tag_config("warning", foreground="red")
        self.msg_text.tag_config("file", foreground="green")
        
        # 创建右键菜单
        self.context_menu = Menu(self.msg_text, tearoff=0)
        self.context_menu.add_command(label="复制", command=self.copy_text)
        self.context_menu.add_command(label="保存聊天记录", command=self.save_chat_history)
        self.msg_text.bind("<Button-3>", self.show_context_menu)
        
        # 消息发送区域
        send_frame = ttk.Frame(msg_frame)
        send_frame.pack(fill="x", padx=5, pady=5)
        
        self.msg_entry = ttk.Entry(send_frame)
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.msg_entry.bind("<Return>", self.send_message)
        
        send_btn = ttk.Button(send_frame, text="发送", width=10, command=self.send_message)
        send_btn.pack(side="right", padx=5, pady=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value=f"已连接: {self.nickname}")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")
    
    def refresh_user_list(self):
        """刷新用户列表"""
        self.user_listbox.delete(0, tk.END)
        for user in self.user_list:
            self.user_listbox.insert(tk.END, user)
    
    def receive_messages(self):
        """接收服务器消息"""
        try:
            while self.connected:
                data = self.socket.recv(4096)
                if not data:
                    break
                    
                # 检查是否是文件传输中
                if self.current_file:
                    self.current_file['file'].write(data)
                    self.current_file['received'] += len(data)
                    
                    # 文件传输完成
                    if self.current_file['received'] >= self.current_file['size']:
                        self.current_file['file'].close()
                        self.display_message(
                            "系统", 
                            f"文件 {self.current_file['filename']} 接收完成 (保存在: {self.current_file['filepath']})",
                            "system"
                        )
                        self.current_file = None
                        self.status_var.set(f"已连接: {self.nickname}")
                    else:
                        # 更新进度
                        progress = (self.current_file['received'] / self.current_file['size']) * 100
                        self.status_var.set(f"接收文件中: {progress:.1f}%")
                    continue
                    
                try:
                    # 尝试解码为JSON
                    message = json.loads(data.decode('utf-8'))
                    self.handle_server_message(message)
                except UnicodeDecodeError:
                    # 可能是文件数据，跳过处理
                    continue
                except json.JSONDecodeError:
                    # 处理文件传输开始
                    if data.startswith(b'FILE_START:'):
                        file_info = data[len(b'FILE_START:'):].decode('utf-8')
                        try:
                            file_info = json.loads(file_info)
                        except:
                            self.display_message("错误", "文件信息解析失败", "warning")
                            continue
                        
                        # 检查是否已同意接收该文件
                        if file_info['filename'] in self.pending_files:
                            save_path = self.pending_files[file_info['filename']]
                            del self.pending_files[file_info['filename']]
                            
                            # 创建文件接收
                            try:
                                self.current_file = {
                                    'file': open(save_path, 'wb'),
                                    'filename': file_info['filename'],
                                    'size': file_info['filesize'],
                                    'received': 0,
                                    'filepath': save_path
                                }
                                
                                self.display_message(
                                    "系统", 
                                    f"开始接收文件: {file_info['filename']} (大小: {file_info['filesize']/1024/1024:.2f}MB)", 
                                    "system"
                                )
                            except Exception as e:
                                self.display_message("错误", f"创建文件失败: {str(e)}", "warning")
                                self.send_file_response(file_info.get('from', ''), file_info['filename'], False)
                        else:
                            self.display_message("错误", "未请求接收该文件", "warning")
                    else:
                        self.display_message("错误", "无法解析服务器数据", "warning")
                        
        except Exception as e:
            if self.connected:
                self.display_message("错误", f"连接出错: {str(e)}", "warning")
        finally:
            if self.connected:
                if self.current_file:
                    try:
                        self.current_file['file'].close()
                    except:
                        pass
                    self.current_file = None
                self.disconnect()
    
    def handle_server_message(self, message):
        """处理服务器消息"""
        msg_type = message.get('type')
        
        if msg_type == "message":
            self.display_message(
                message.get('from'), 
                message.get('message', ''),
                "normal"
            )
            
        elif msg_type == "private_message":
            self.display_message(
                message.get('from'), 
                message.get('message', ''),
                "private"
            )
            
        elif msg_type == "system":
            self.display_message(
                "系统", 
                message.get('message', ''),
                "system"
            )
            
            # 更新用户列表
            user_list = message.get('user_list')
            if user_list is not None:
                self.user_list = user_list
                self.refresh_user_list()
                
        elif msg_type == "file_request":
            # 接收文件请求
            filename = message.get('filename')
            filesize = message.get('filesize')
            sender = message.get('from')
            
            if not filename or not filesize or not sender:
                self.display_message("错误", "文件请求信息不完整", "warning")
                return
                
            # 询问用户是否接收
            if messagebox.askyesno("文件传输", 
                                 f"用户 {sender} 向你发送文件: {filename} ({(filesize/1024/1024):.2f}MB)\n是否接收?"):
                # 用户选择保存路径
                save_path = filedialog.asksaveasfilename(
                    initialfile=filename,
                    title="保存文件"
                )
                if not save_path:
                    # 用户取消了保存路径，视为拒绝
                    self.send_file_response(sender, filename, False)
                else:
                    # 同意接收，并保存路径
                    self.send_file_response(sender, filename, True)
                    # 记录待接收文件
                    self.pending_files[filename] = save_path
            else:
                # 拒绝接收
                self.send_file_response(sender, filename, False)
    
    def display_message(self, sender, content, msg_type="normal"):
        """显示消息到聊天窗口，并记录到日志文件"""
        self.msg_text.config(state=tk.NORMAL)
        
        # 构建显示的消息字符串
        if sender == "系统":
            display_msg = f"[系统] {content}\n"
            log_msg = f"[系统] {content}\n"
        elif msg_type == "private":
            display_msg = f"[{sender} 私聊]: {content}\n"
            log_msg = f"[{sender} 私聊]: {content}\n"
        else:
            display_msg = f"[{sender}]: {content}\n"
            log_msg = f"[{sender}]: {content}\n"

        # 显示消息
        if sender == "系统":
            self.msg_text.insert(tk.END, f"[系统] ", "system")
            self.msg_text.insert(tk.END, content + "\n")
        elif msg_type == "private":
            self.msg_text.insert(tk.END, f"[{sender} 私聊]: ", "private")
            self.msg_text.insert(tk.END, content + "\n")
        else:
            self.msg_text.insert(tk.END, f"[{sender}]: ")
            self.msg_text.insert(tk.END, content + "\n")

        self.msg_text.see(tk.END)
        self.msg_text.config(state=tk.DISABLED)

        # 写入日志文件
        if self.current_log_file:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write(log_msg)
    
    def send_message(self, event=None):
        """发送消息"""
        if not self.connected:
            return
            
        message = self.msg_entry.get().strip()
        if not message:
            return
            
        self.msg_entry.delete(0, tk.END)
        
        send_data = {
            "type": "message",
            "message": message
        }
        
        # 检查是否是私聊模式
        if self.private_var.get():
            selected = self.user_listbox.curselection()
            if not selected:
                self.display_message("错误", "请选择私聊对象", "warning")
                return
                
            to_user = self.user_listbox.get(selected[0])
            send_data['to'] = to_user
            self.display_message("你", f"【私聊给 {to_user}】{message}")
        else:
            self.display_message("你", message)
        
        try:
            self.socket.send(json.dumps(send_data).encode('utf-8'))
        except:
            self.display_message("错误", "发送消息失败", "warning")
    
    def send_file_dialog(self):
        """发送文件对话框"""
        if not self.connected:
            return
            
        filename = filedialog.askopenfilename(
            title="选择要发送的文件",
            filetypes=[("所有文件", "*.*")]
        )
        
        if not filename:
            return
            
        # 检查文件大小 (50MB限制)
        try:
            filesize = os.path.getsize(filename)
        except:
            self.display_message("错误", "无法获取文件大小", "warning")
            return
            
        if filesize > 50 * 1024 * 1024:  # 50MB
            self.display_message("错误", "文件过大(>50MB)，无法发送", "warning")
            return
            
        # 获取接收方
        to_user = None
        if self.private_var.get():
            selected = self.user_listbox.curselection()
            if selected:
                to_user = self.user_listbox.get(selected[0])
    
        try:
            # 发送文件信息
            file_info = {
                "type": "file_info",
                "filename": os.path.basename(filename),
                "filesize": filesize
            }
            if to_user:
                file_info['to'] = to_user
                self.display_message("你", f"【私聊】发送文件给 {to_user}: {os.path.basename(filename)} ({(filesize/1024/1024):.2f}MB)")
            else:
                self.display_message("你", f"发送文件: {os.path.basename(filename)} ({(filesize/1024/1024):.2f}MB)")
                
            self.socket.send(json.dumps(file_info).encode('utf-8'))
            
            # 发送文件内容
            threading.Thread(
                target=self.send_file,
                args=(filename, to_user)
            ).start()
            
        except Exception as e:
            self.display_message("错误", f"发送文件失败: {str(e)}", "warning")
    
    def send_file(self, filename, to_user=None):
        """发送文件内容"""
        try:
            with open(filename, 'rb') as f:
                self.display_message("系统", "开始传输文件...", "system")
                
                # 发送文件开始标志
                start_info = {
                    "filename": os.path.basename(filename),
                    "filesize": os.path.getsize(filename)
                }
                if to_user:
                    start_info['to'] = to_user
                    
                self.socket.send(b'FILE_START:' + json.dumps(start_info).encode('utf-8'))
                
                # 发送文件内容
                total_sent = 0
                total_size = os.path.getsize(filename)
                while total_sent < total_size:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.socket.send(chunk)
                    total_sent += len(chunk)
                    # 显示进度
                    progress = (total_sent / total_size) * 100
                    self.status_var.set(f"发送文件中: {progress:.1f}%")
                    
            self.status_var.set(f"已连接: {self.nickname}")
            self.display_message("系统", "文件传输完成", "system")
        except Exception as e:
            self.status_var.set(f"已连接: {self.nickname}")
            self.display_message("错误", f"文件传输出错: {str(e)}", "warning")
    
    def send_file_response(self, sender, filename, accepted):
        """发送文件响应"""
        if not sender:
            return
            
        try:
            response = {
                "type": "file_response",
                "to": sender,
                "filename": filename,
                "accepted": accepted
            }
            self.socket.send(json.dumps(response).encode('utf-8'))
        except:
            self.display_message("错误", "发送文件响应失败", "warning")
    
    def send_voice_message(self):
        """发送语音消息（模拟功能）"""
        if not self.connected:
            return
            
        duration = simpledialog.askinteger(
            "语音消息", 
            "输入语音时长(秒):", 
            minvalue=1, 
            maxvalue=60
        )
        if not duration:
            return
            
        # 模拟语音消息功能
        message = f"【语音消息】({duration}秒)"
        
        send_data = {
            "type": "message",
            "message": message
        }
        
        # 检查是否是私聊模式
        if self.private_var.get():
            selected = self.user_listbox.curselection()
            if not selected:
                self.display_message("错误", "请选择私聊对象", "warning")
                return
                
            to_user = self.user_listbox.get(selected[0])
            send_data['to'] = to_user
            self.display_message("你", f"【私聊给 {to_user}】{message}")
        else:
            self.display_message("你", message)
        
        try:
            self.socket.send(json.dumps(send_data).encode('utf-8'))
        except:
            self.display_message("错误", "发送语音消息失败", "warning")
    
    def copy_text(self):
        """复制选中的文本"""
        try:
            if self.msg_text.tag_ranges(tk.SEL):
                selected = self.msg_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                if selected:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(selected)
        except:
            pass
    
    def save_chat_history(self):
        """保存聊天历史记录"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if not filepath:
            return
            
        try:
            content = self.msg_text.get(1.0, tk.END)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self.display_message("系统", f"聊天记录已保存到: {filepath}", "system")
        except Exception as e:
            self.display_message("错误", f"保存聊天记录失败: {str(e)}", "warning")
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        self.context_menu.post(event.x_root, event.y_root)
    
    def disconnect(self):
        """断开服务器连接"""
        if self.connected:
            try:
                # 发送退出消息
                quit_data = {
                    "type": "quit"
                }
                self.socket.send(json.dumps(quit_data).encode('utf-8'))
                self.socket.close()
            except:
                pass
            self.connected = False
            self.status_var.set("已断开连接")
            self.display_message("系统", "与服务器断开连接", "system")
    
    def on_closing(self):
        """窗口关闭事件处理"""
        if self.connected:
            self.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    client = ChatClient(root)
    root.mainloop()