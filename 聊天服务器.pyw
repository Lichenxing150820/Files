import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, Listbox, Menu, simpledialog
import socket
import threading
import json
import os
import time
from datetime import datetime, timedelta

class ChatServer:
    def __init__(self, root):
        self.root = root
        self.root.title("聊天服务器")
        self.root.geometry("1200x1000")
        
        # 初始化服务器状态
        self.server = None
        self.server_running = False
        self.clients = {}
        self.banned_users = set()
        self.muted_users = set()
        self.ban_reason = {}
        self.mute_expiry = {}
        
        # 创建UI
        self.setup_ui()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        # 服务器配置区域
        config_frame = ttk.LabelFrame(self.root, text="服务器配置")
        config_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(config_frame, text="端口号:").grid(row=0, column=0, padx=5, pady=5)
        self.port_entry = ttk.Entry(config_frame)
        self.port_entry.grid(row=0, column=1, padx=5, pady=5)
        self.port_entry.insert(0, "65432")
        
        self.start_btn = ttk.Button(config_frame, text="启动服务器", command=self.start_server)
        self.start_btn.grid(row=0, column=2, padx=5, pady=5)
        
        self.stop_btn = ttk.Button(config_frame, text="关闭服务器", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=3, padx=5, pady=5)
        
        # 用户列表区域
        user_frame = ttk.LabelFrame(self.root, text="在线用户")
        user_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.user_list = Listbox(user_frame)
        self.user_list.pack(fill="both", expand=True, padx=5, pady=5)
        self.user_list.bind('<<ListboxSelect>>', self.on_user_select)
        
        # 用户操作按钮
        action_frame = ttk.Frame(user_frame)
        action_frame.pack(fill="x", padx=5, pady=5)
        
        self.kick_btn = ttk.Button(action_frame, text="踢出用户", state=tk.DISABLED, command=self.kick_user)
        self.kick_btn.pack(side=tk.LEFT, padx=5)
        
        self.ban_btn = ttk.Button(action_frame, text="封禁用户", state=tk.DISABLED, command=self.ban_user)
        self.ban_btn.pack(side=tk.LEFT, padx=5)
        
        self.mute_btn = ttk.Button(action_frame, text="禁言用户", state=tk.DISABLED, command=self.mute_user)
        self.mute_btn.pack(side=tk.LEFT, padx=5)
        
        self.unmute_btn = ttk.Button(action_frame, text="解除禁言", state=tk.DISABLED, command=self.unmute_user)
        self.unmute_btn.pack(side=tk.LEFT, padx=5)
        
        # 消息区域
        msg_frame = ttk.LabelFrame(self.root, text="消息和日志")
        msg_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.msg_text = scrolledtext.ScrolledText(msg_frame, state=tk.DISABLED)
        self.msg_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 消息发送区域
        send_frame = ttk.Frame(msg_frame)
        send_frame.pack(fill="x", padx=5, pady=5)
        
        self.msg_entry = ttk.Entry(send_frame)
        self.msg_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5, pady=5)
        self.msg_entry.bind("<Return>", self.send_server_message)
        
        send_btn = ttk.Button(send_frame, text="发送", command=self.send_server_message)
        send_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 配置文本标签
        self.msg_text.tag_config("system", foreground="blue")
        self.msg_text.tag_config("private", foreground="purple")
        self.msg_text.tag_config("warning", foreground="red")
    
    def start_server(self):
        port = self.port_entry.get()
        if not port.isdigit():
            messagebox.showerror("错误", "端口号必须是数字")
            return
            
        port = int(port)
        
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind(('0.0.0.0', port))
            self.server.listen(5)
            self.server_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.DISABLED)
            
            self.display_message("服务器", f"服务器已在端口 {port} 启动")
            
            # 启动监听线程
            threading.Thread(target=self.accept_clients, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("错误", f"无法启动服务器: {str(e)}")
    
    def stop_server(self):
        if not self.server_running:
            return
            
        # 通知所有客户端
        for nickname, client in list(self.clients.items()):
            try:
                client['socket'].send(json.dumps({
                    "type": "system",
                    "message": "服务器即将关闭"
                }).encode('utf-8'))
                client['socket'].close()
            except:
                pass
        
        self.clients = {}
        self.update_user_list()
        
        try:
            self.server.close()
        except:
            pass
            
        self.server_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.NORMAL)
        
        self.display_message("服务器", "服务器已停止")
    
    def accept_clients(self):
        while self.server_running:
            try:
                client_socket, addr = self.server.accept()
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
            except:
                if self.server_running:
                    self.display_message("错误", "接受连接时出错")
    
    def handle_client(self, client_socket):
        nickname = None
        current_file = None
        
        try:
            # 获取客户端信息
            data = client_socket.recv(4096)
            if not data:
                return
                
            try:
                client_data = json.loads(data.decode('utf-8'))
                if client_data.get('type') == 'quit':
                    return
                    
                nickname = client_data.get('nickname', '')
                
                # 验证昵称
                if not nickname or nickname.lower() in ["管理", "管理员", "服务器", "系统消息", "系统", "sb", "admin", "administrator", "傻逼", "死", "杀", "傻", "逼", "傻子", "他妈的", "操", "操你妈", "server", "service","错误"]:
                    client_socket.send(json.dumps({
                        "type": "login_response",
                        "status": "error",
                        "message": "昵称无效或已被禁止"
                    }).encode('utf-8'))
                    client_socket.close()
                    return
                    
                # 检查是否被封禁
                if nickname in self.banned_users:
                    reason = self.ban_reason.get(nickname, "违反服务器规则")
                    client_socket.send(json.dumps({
                        "type": "login_response",
                        "status": "error",
                        "message": f"你已被封禁，原因: {reason}"
                    }).encode('utf-8'))
                    client_socket.close()
                    return
                    
                # 检查昵称是否已存在
                if nickname in self.clients:
                    client_socket.send(json.dumps({
                        "type": "login_response",
                        "status": "error",
                        "message": "该昵称已被占用"
                    }).encode('utf-8'))
                    client_socket.close()
                    return
                    
                # 添加新用户
                self.clients[nickname] = {
                    "socket": client_socket,
                    "address": client_socket.getpeername(),
                    "files": []
                }
                
                # 发送登录成功响应
                client_socket.send(json.dumps({
                    "type": "login_response",
                    "status": "success",
                    "message": f"欢迎 {nickname}",
                    "user_list": list(self.clients.keys())
                }).encode('utf-8'))
                
                # 广播新用户加入
                self.broadcast({
                    "type": "system",
                    "message": f"{nickname} 加入了聊天室",
                    "user_list": list(self.clients.keys())
                })
                
                self.display_message("系统", f"{nickname} 加入了聊天室")
                self.update_user_list()
                
                # 接收客户端消息
                while True:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                        
                    # 检查是否是文件传输中
                    if current_file:
                        current_file['file'].write(data)
                        current_file['received'] += len(data)
                        
                        # 文件传输完成
                        if current_file['received'] >= current_file['size']:
                            current_file['file'].close()
                            self.display_message(
                                "系统", 
                                f"文件 {current_file['filename']} 接收完成", 
                                private=True, 
                                to_user=nickname
                            )
                            current_file = None
                        continue
                        
                    try:
                        # 尝试解码为JSON
                        message = json.loads(data.decode('utf-8'))
                        if message.get('type') == 'quit':
                            break
                        self.handle_client_message(nickname, message)
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
                                self.display_message("错误", "文件信息解析失败", private=True, to_user=nickname)
                                continue
                            
                            # 创建临时文件接收
                            temp_dir = "received_files"
                            os.makedirs(temp_dir, exist_ok=True)
                            filepath = os.path.join(temp_dir, file_info['filename'])
                            
                            # 如果文件存在，则添加时间戳重命名
                            if os.path.exists(filepath):
                                base, ext = os.path.splitext(file_info['filename'])
                                new_filename = f"{base}_{int(time.time())}{ext}"
                                filepath = os.path.join(temp_dir, new_filename)
                            
                            try:
                                current_file = {
                                    'file': open(filepath, 'wb'),
                                    'filename': file_info['filename'],
                                    'size': file_info['filesize'],
                                    'received': 0,
                                    'sender': nickname,
                                    'receiver': file_info.get('to'),
                                    'filepath': filepath
                                }
                                
                                self.display_message(
                                    "系统", 
                                    f"开始接收文件: {file_info['filename']} (来自: {nickname})", 
                                    private=True, 
                                    to_user=nickname
                                )
                            except Exception as e:
                                self.display_message("错误", f"创建文件失败: {str(e)}", private=True, to_user=nickname)
                        else:
                            self.display_message("错误", "无法解析客户端数据", private=True, to_user=nickname)
                    
            except Exception as e:
                self.display_message("错误", f"处理客户端时出错: {str(e)}")
                
        finally:
            if current_file:
                try:
                    current_file['file'].close()
                except:
                    pass
                
            if nickname and nickname in self.clients:
                del self.clients[nickname]
                try:
                    client_socket.close()
                except:
                    pass
                self.broadcast({
                    "type": "system",
                    "message": f"{nickname} 离开了聊天室",
                    "user_list": list(self.clients.keys())
                })
                self.display_message("系统", f"{nickname} 离开了聊天室")
                self.update_user_list()
    
    def handle_client_message(self, nickname, message):
        msg_type = message.get('type')
        
        if msg_type == "file_info":
            # 处理文件传输请求
            filename = message.get('filename')
            filesize = message.get('filesize')
            to_user = message.get('to')
            
            if not filename or not filesize:
                self.send_to_user(nickname, {
                    "type": "system",
                    "message": "文件信息不完整"
                })
                return
                
            # 通知接收方（如果指定了接收方且在线）
            if to_user:
                if to_user in self.clients:
                    self.send_to_user(to_user, {
                        "type": "file_request",
                        "from": nickname,
                        "filename": filename,
                        "filesize": filesize
                    })
                else:
                    # 接收方不在线，通知发送方
                    self.send_to_user(nickname, {
                        "type": "system",
                        "message": f"用户 {to_user} 不在线，无法发送文件"
                    })
                    return
            
            # 广播文件传输消息（让所有客户端都能看到）
            broadcast_msg = f"【文件传输】{nickname} 发送文件: {filename} ({(filesize/1024/1024):.2f}MB)"
            if to_user:
                broadcast_msg += f" 给 {to_user}"
            
            self.broadcast({
                "type": "system",
                "message": broadcast_msg
            })
            
            # 记录文件信息
            self.clients[nickname]['files'].append({
                "filename": filename,
                "size": filesize,
                "receiver": to_user or "所有人"
            })
            
            # 发送文件传输开始标志
            file_start = {
                "filename": filename,
                "filesize": filesize
            }
            if to_user:
                file_start['to'] = to_user
                
            self.clients[nickname]['socket'].send(b'FILE_START:' + json.dumps(file_start).encode('utf-8'))
            
        elif msg_type == "file_response":
            # 处理文件传输响应
            accepted = message.get('accepted')
            filename = message.get('filename')
            sender = message.get('to')  # 注意：这里的to实际上是发送方
            
            if not sender or not filename:
                return
                
            if not accepted:
                # 接收方拒绝接收文件
                self.send_to_user(sender, {
                    "type": "system",
                    "message": f"接收方拒绝了文件 {filename}"
                })
            else:
                # 接收方同意接收，此时发送方开始发送文件数据（已经在file_info中处理了）
                pass
                
        elif msg_type == "message":
            content = message.get('message', '')
            to_user = message.get('to')
            
            if nickname in self.muted_users:
                # 检查禁言是否过期
                expire_time = self.mute_expiry.get(nickname)
                if expire_time and datetime.now() > datetime.fromisoformat(expire_time):
                    self.unmute_user_auto(nickname)
                else:
                    # 用户被禁言，不发送消息
                    self.send_to_user(nickname, {
                        "type": "system",
                        "message": "你已被禁言，无法发送消息"
                    })
                    return
                    
            if to_user:
                # 私聊消息
                if to_user in self.clients:
                    self.send_to_user(to_user, {
                        "type": "private_message",
                        "from": nickname,
                        "message": content
                    })
                    # 同时给发送方发送私聊消息（以便发送方看到）
                    self.send_to_user(nickname, {
                        "type": "private_message",
                        "from": nickname,
                        "to": to_user,
                        "message": content
                    })
                else:
                    self.send_to_user(nickname, {
                        "type": "system",
                        "message": f"用户 {to_user} 不在线，无法发送私聊消息"
                    })
            else:
                # 广播公共消息
                self.broadcast({
                    "type": "message",
                    "from": nickname,
                    "message": content
                })
            
            # 在服务器显示
            self.display_message(nickname, content, private=bool(to_user), to_user=to_user)
    
    def broadcast(self, message):
        """向所有客户端广播消息"""
        data = json.dumps(message).encode('utf-8')
        for client in list(self.clients.values()):
            try:
                client['socket'].send(data)
            except:
                pass
    
    def send_to_user(self, nickname, message):
        """向特定用户发送消息"""
        if nickname in self.clients:
            try:
                data = json.dumps(message).encode('utf-8')
                self.clients[nickname]['socket'].send(data)
                return True
            except:
                self.display_message("错误", f"无法发送消息给 {nickname}")
        return False
    
    def update_user_list(self):
        """更新用户列表"""
        self.user_list.delete(0, tk.END)
        for nickname in self.clients:
            status = " (禁言)" if nickname in self.muted_users else ""
            self.user_list.insert(tk.END, f"{nickname}{status}")
    
    def display_message(self, sender, content, private=False, to_user=None):
        """在消息区域显示消息"""
        self.msg_text.config(state=tk.NORMAL)
        
        if private:
            if sender == "服务器":
                self.msg_text.insert(tk.END, "[系统私聊] ", "system")
            else:
                self.msg_text.insert(tk.END, f"[{sender} → {to_user}]: ", "private")
        else:
            if sender == "系统" or sender == "服务器":
                self.msg_text.insert(tk.END, "[系统] ", "system")
            else:
                self.msg_text.insert(tk.END, f"[{sender}]: ")
        
        self.msg_text.insert(tk.END, content + "\n")
        self.msg_text.see(tk.END)
        self.msg_text.config(state=tk.DISABLED)
    
    def send_server_message(self, event=None):
        """发送服务器消息"""
        message = self.msg_entry.get().strip()
        if not message:
            return
            
        self.msg_entry.delete(0, tk.END)
        
        if message.startswith("/"):
            # 处理服务器命令
            self.handle_server_command(message)
        else:
            self.broadcast({
                "type": "message",
                "from": "服务器",
                "message": message
            })
            self.display_message("服务器", message)
    
    def handle_server_command(self, command):
        """处理服务器命令"""
        parts = command.split()
        cmd = parts[0][1:].lower()
        
        if cmd == "help":
            self.display_message("系统", "可用命令: /list, /kick [用户名], /ban [用户名] [原因], /mute [用户名] [分钟], /unmute [用户名], /clear")
            
        elif cmd == "list":
            self.display_message("系统", f"在线用户: {', '.join(self.clients.keys())}")
            self.display_message("系统", f"被封禁用户: {', '.join(self.banned_users)}")
            self.display_message("系统", f"被禁言用户: {', '.join(self.muted_users)}")
            
        elif cmd == "kick" and len(parts) > 1:
            username = parts[1]
            if username in self.clients:
                self.kick_user_immediate(username)
                self.display_message("系统", f"已踢出用户 {username}")
            else:
                self.display_message("错误", f"用户 {username} 不在线")
                
        elif cmd == "ban" and len(parts) > 1:
            username = parts[1]
            reason = " ".join(parts[2:]) if len(parts) > 2 else "违反服务器规则"
            self.do_ban_user(username, reason)
            self.display_message("系统", f"已封禁用户 {username}, 原因: {reason}")
            
        elif cmd == "mute" and len(parts) > 1:
            username = parts[1]
            minutes = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 30
            self.do_mute_user(username, minutes)
            self.display_message("系统", f"已禁言用户 {username} {minutes} 分钟")
            
        elif cmd == "unmute" and len(parts) > 1:
            username = parts[1]
            self.unmute_user_auto(username)
            self.display_message("系统", f"已解除用户 {username} 的禁言")
            
        elif cmd == "clear":
            self.msg_text.config(state=tk.NORMAL)
            self.msg_text.delete(1.0, tk.END)
            self.msg_text.config(state=tk.DISABLED)
            
        else:
            self.display_message("错误", "未知命令，输入 /help 查看帮助")
    
    def on_user_select(self, event):
        """用户选择事件"""
        if self.user_list.curselection():
            self.kick_btn.config(state=tk.NORMAL)
            self.ban_btn.config(state=tk.NORMAL)
            
            selected_user = self.user_list.get(self.user_list.curselection()[0]).split()[0]
            if selected_user in self.muted_users:
                self.mute_btn.config(state=tk.DISABLED)
                self.unmute_btn.config(state=tk.NORMAL)
            else:
                self.mute_btn.config(state=tk.NORMAL)
                self.unmute_btn.config(state=tk.DISABLED)
        else:
            self.kick_btn.config(state=tk.DISABLED)
            self.ban_btn.config(state=tk.DISABLED)
            self.mute_btn.config(state=tk.DISABLED)
            self.unmute_btn.config(state=tk.DISABLED)
    
    def kick_user(self):
        """踢出用户"""
        if not self.user_list.curselection():
            return
            
        username = self.user_list.get(self.user_list.curselection()[0]).split()[0]
        self.kick_user_immediate(username)
        self.display_message("系统", f"已踢出用户 {username}")
    
    def kick_user_immediate(self, username):
        """立即踢出用户"""
        if username in self.clients:
            try:
                self.clients[username]['socket'].send(json.dumps({
                    "type": "system",
                    "message": "你已被服务器踢出"
                }).encode('utf-8'))
                self.clients[username]['socket'].close()
            except:
                pass
            finally:
                if username in self.clients:
                    del self.clients[username]
                    self.update_user_list()
    
    def ban_user(self):
        """封禁用户"""
        if not self.user_list.curselection():
            return
            
        username = self.user_list.get(self.user_list.curselection()[0]).split()[0]
        reason = simpledialog.askstring("封禁用户", f"输入封禁 {username} 的原因:", parent=self.root)
        if reason is None:  # 用户取消了
            return
            
        if not reason:
            reason = "违反服务器规则"
            
        self.do_ban_user(username, reason)
        self.display_message("系统", f"已封禁用户 {username}, 原因: {reason}")
    
    def do_ban_user(self, username, reason):
        """执行封禁用户"""
        self.banned_users.add(username)
        self.ban_reason[username] = reason
        
        # 如果用户在线，踢出用户
        if username in self.clients:
            try:
                self.clients[username]['socket'].send(json.dumps({
                    "type": "system",
                    "message": f"你已被服务器封禁，原因: {reason}"
                }).encode('utf-8'))
                self.clients[username]['socket'].close()
            except:
                pass
            finally:
                if username in self.clients:
                    del self.clients[username]
                    self.update_user_list()
    
    def mute_user(self):
        """禁言用户"""
        if not self.user_list.curselection():
            return
            
        username = self.user_list.get(self.user_list.curselection()[0]).split()[0]
        minutes = simpledialog.askinteger("禁言用户", f"禁言 {username} 的分钟数:", 
                                        parent=self.root, minvalue=1, maxvalue=1440)
        if minutes is None:  # 用户取消了
            return
            
        self.do_mute_user(username, minutes)
        self.display_message("系统", f"已禁言用户 {username} {minutes} 分钟")
    
    def do_mute_user(self, username, minutes):
        """执行禁言用户"""
        self.muted_users.add(username)
        expiry_time = datetime.now() + timedelta(minutes=minutes)
        self.mute_expiry[username] = expiry_time.isoformat()
        
        # 通知用户
        if username in self.clients:
            try:
                self.clients[username]['socket'].send(json.dumps({
                    "type": "system",
                    "message": f"你已被禁言 {minutes} 分钟"
                }).encode('utf-8'))
            except:
                pass
                
        self.update_user_list()
    
    def unmute_user(self):
        """解除禁言"""
        if not self.user_list.curselection():
            return
            
        username = self.user_list.get(self.user_list.curselection()[0]).split()[0]
        self.unmute_user_auto(username)
        self.display_message("系统", f"已解除用户 {username} 的禁言")
    
    def unmute_user_auto(self, username):
        """自动解除禁言"""
        if username in self.muted_users:
            self.muted_users.remove(username)
        if username in self.mute_expiry:
            del self.mute_expiry[username]
            
        # 通知用户
        if username in self.clients:
            try:
                self.clients[username]['socket'].send(json.dumps({
                    "type": "system",
                    "message": "你的禁言已被解除"
                }).encode('utf-8'))
            except:
                pass
                
        self.update_user_list()
    
    def on_closing(self):
        """窗口关闭事件处理"""
        if self.server_running:
            self.stop_server()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatServer(root)
    root.mainloop()