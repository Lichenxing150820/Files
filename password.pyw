import os
import json
import base64
import hashlib
import binascii
from tkinter import *
from tkinter import messagebox, simpledialog, filedialog
from tkinter.scrolledtext import ScrolledText
from configparser import ConfigParser
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets
import sys

class FileLocker:
    def __init__(self):
        self.config_file = 'config.ini'
        self.data_file = 'file.dat'
        self.config = ConfigParser()
        
        # 检查状态
        self.is_setup = self.check_initial_setup()
    
    def check_initial_setup(self):
        """检查系统是否已完成初始设置"""
        # 检查配置文件是否存在且有效
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            return self.config.getboolean('DEFAULT', 'is_setup', fallback=False)
        
        # 检查数据文件是否存在
        if os.path.exists(self.data_file):
            return True
            
        return False
    
    def create_config(self, password):
        """创建初始配置文件"""
        # 生成随机盐值
        salt = secrets.token_bytes(16)
        
        # 派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        try:
            key = kdf.derive(password.encode())
        except TypeError:
            # 处理空密码情况
            key = kdf.derive(b'')
            
        fernet_key = base64.urlsafe_b64encode(key)
        
        # 创建密码哈希值
        key_hash = hashlib.sha256(key).hexdigest()
        
        # 保存配置文件
        self.config['DEFAULT'] = {
            'salt': base64.b64encode(salt).decode(),
            'key_hash': key_hash,
            'is_setup': '1'
        }
        with open(self.config_file, 'w') as f:
            self.config.write(f)
        
        # 返回Fernet加密器
        return Fernet(fernet_key)
    
    def verify_password(self, password):
        """验证密码是否正确"""
        # 检查配置文件是否存在
        if not os.path.exists(self.config_file):
            return None
        
        self.config.read(self.config_file)
        
        # 获取盐值
        salt_b64 = self.config['DEFAULT'].get('salt', '')
        if not salt_b64:
            return None
        try:
            salt = base64.b64decode(salt_b64)
        except binascii.Error:
            return None
        
        # 获取存储的哈希值
        stored_hash = self.config['DEFAULT'].get('key_hash', '')
        if not stored_hash:
            return None
        
        # 派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        try:
            key = kdf.derive(password.encode())
        except (TypeError, UnicodeEncodeError):
            # 处理特殊字符和空密码
            try:
                key = kdf.derive(password.encode('utf-8'))
            except:
                return None
        
        # 验证密码哈希
        if hashlib.sha256(key).hexdigest() != stored_hash:
            return None
        
        # 验证通过，初始化Fernet加密器
        fernet_key = base64.urlsafe_b64encode(key)
        return Fernet(fernet_key)
    
    def save_file(self, fernet, filename, content):
        """保存加密文件"""
        # 读取现有数据或创建新结构
        data = self.load_all_files(fernet)
        
        # 添加新文件
        data[filename] = content
        
        # 加密并保存
        return self.save_all_files(fernet, data)
    
    def save_all_files(self, fernet, data):
        """保存所有文件数据"""
        try:
            encrypted = fernet.encrypt(json.dumps(data).encode())
            with open(self.data_file, 'wb') as f:
                f.write(encrypted)
            return True
        except Exception as e:
            print(f"保存文件错误: {e}")
            return False
    
    def load_all_files(self, fernet):
        """加载所有文件数据"""
        try:
            # 文件不存在时返回空字典
            if not os.path.exists(self.data_file):
                return {}
                
            with open(self.data_file, 'rb') as f:
                encrypted_data = f.read()
            return json.loads(fernet.decrypt(encrypted_data).decode())
        except (json.JSONDecodeError, binascii.Error):
            return {}
        except Exception as e:
            print(f"加载文件错误: {e}")
            return {}
    
    def delete_files(self, fernet, filenames):
        """删除指定文件"""
        # 加载现有数据
        data = self.load_all_files(fernet)
        
        # 逐个删除文件
        deleted_count = 0
        for filename in filenames:
            if filename in data:
                del data[filename]
                deleted_count += 1
        
        # 保存更改
        if deleted_count > 0:
            return self.save_all_files(fernet, data) and deleted_count
        return 0
    
    def get_files(self, fernet):
        """获取所有加密文件名"""
        data = self.load_all_files(fernet)
        return list(data.keys())
    
    def get_file_content(self, fernet, filename):
        """获取指定文件的内容"""
        data = self.load_all_files(fernet)
        return data.get(filename, None)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("文件保密柜")
        self.root.geometry("600x400")  # 更大的初始窗口大小
        
        # 设置应用程序图标(替换为实际图标路径)
        if getattr(sys, 'frozen', False):
            # 打包后的路径
            icon_path = os.path.join(sys._MEIPASS, "locker.ico")
        else:
            # 开发环境路径
            icon_path = "locker.ico"
            
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
        
        # 创建主框架
        self.main_frame = Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 创建状态栏(始终存在)
        self.status_bar = Label(self.root, text="就绪", bd=1, relief=SUNKEN, anchor=W)
        self.status_bar.pack(side=BOTTOM, fill=X, padx=5, pady=5)
        
        self.locker = FileLocker()
        self.fernet = None  # 当前Fernet加密器实例
        
        # 根据状态显示不同界面
        if self.locker.is_setup:
            self.show_login()
        else:
            self.show_set_password()
    
    def show_set_password(self):
        """显示设置密码界面 - 完全符合截图样式"""
        self.clear_main_frame()
        
        # 主标题
        Label(self.main_frame, text="文件保密柜", font=("黑体", 16), pady=20).pack()
        
        # 设置面板
        settings_frame = Frame(self.main_frame, padx=20, pady=20)
        settings_frame.pack(pady=10, fill=BOTH, expand=True)
        
        # "首次使用，请设置密码" 标题
        Label(settings_frame, text="首次使用，请设置密码", font=("黑体", 14)).pack(pady=10)
        
        # 密码输入框
        input_frame = Frame(settings_frame)
        input_frame.pack(pady=10)
        
        Label(input_frame, text="输入密码:").grid(row=0, column=0, padx=5, pady=10, sticky="e")
        self.pw_entry = Entry(input_frame, show="*", width=30)
        self.pw_entry.grid(row=0, column=1, padx=5, pady=10)
        
        Label(input_frame, text="确认密码:").grid(row=1, column=0, padx=5, pady=10, sticky="e")
        self.confirm_entry = Entry(input_frame, show="*", width=30)
        self.confirm_entry.grid(row=1, column=1, padx=5, pady=10)
        
        # 设置密码按钮
        Button(settings_frame, text="设置密码", command=self.set_password, 
               width=15, height=1).pack(pady=20)
        
        self.update_status("等待设置密码")
    
    def show_login(self):
        """显示登录界面 - 完全符合截图样式"""
        self.clear_main_frame()
        
        # 主标题
        title_label = Label(self.main_frame, text="文件保密柜", font=("黑体", 16), pady=20)
        title_label.pack()
        
        # 登录面板
        login_frame = Frame(self.main_frame, padx=20, pady=20)
        login_frame.pack(pady=10, fill=BOTH, expand=True)
        
        # "请输入密码解锁" 标题
        Label(login_frame, text="请输入密码解锁", font=("黑体", 14)).pack(pady=10)
        
        # 密码输入框
        password_frame = Frame(login_frame)
        password_frame.pack(pady=10)
        
        Label(password_frame, text="密码:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.login_entry = Entry(password_frame, show="*", width=30)
        self.login_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 登录按钮
        Button(login_frame, text="登录", command=self.login, 
               width=15, height=1).pack(pady=20)
        
        # 只有在配置文件被删除但数据文件存在时才显示提示
        if os.path.exists(self.locker.data_file) and not os.path.exists(self.locker.config_file):
            notice_label = Label(login_frame, text="注意:删除配置文件不会重置系统，请使用原密码登录", 
                  fg="red", font=("宋体", 9))
            notice_label.pack(pady=10)
        
        self.update_status("等待登录")
    
    def show_main(self):
        """显示主界面"""
        self.clear_main_frame()
        
        # 标题栏
        title_frame = Frame(self.main_frame)
        title_frame.pack(fill=X, padx=10, pady=10)
        
        Label(title_frame, text="文件保密柜", font=("黑体", 14, "bold")).pack(side=LEFT)
        
        # 按钮组
        btn_frame = Frame(title_frame)
        btn_frame.pack(side=RIGHT, padx=10)
        
        # 添加删除文件按钮
        Button(btn_frame, text="上传文件", command=self.upload_file, width=10).pack(side=LEFT, padx=2)
        Button(btn_frame, text="下载文件", command=self.download_files, width=10).pack(side=LEFT, padx=2)
        Button(btn_frame, text="删除文件", command=self.delete_files, width=10).pack(side=LEFT, padx=2)
        Button(btn_frame, text="创建文件", command=self.create_file, width=10).pack(side=LEFT, padx=2)
        Button(btn_frame, text="更改密码", command=self.show_change_password, width=10).pack(side=LEFT, padx=2)
        
        # 文件列表区域
        list_frame = Frame(self.main_frame)
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 列表标题和操作按钮
        list_header = Frame(list_frame)
        list_header.pack(fill=X)
        Label(list_header, text="文件列表", font=("黑体", 12)).pack(side=LEFT)
        
        # 列表控件框架
        list_control_frame = Frame(list_frame)
        list_control_frame.pack(fill=BOTH, expand=True)
        
        scrollbar = Scrollbar(list_control_frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        self.file_listbox = Listbox(list_control_frame, yscrollcommand=scrollbar.set, 
                                    width=50, height=15, selectmode=EXTENDED)  # 支持多选
        self.file_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        
        # 绑定双击事件查看文件内容
        self.file_listbox.bind('<Double-Button-1>', self.view_file_content)
        
        scrollbar.config(command=self.file_listbox.yview)
        
        # 刷新文件列表
        self.refresh_file_list()
        
        self.update_status("文件管理就绪")
    
    def show_change_password(self):
        """显示更改密码界面"""
        self.clear_main_frame()
        
        # 主标题
        Label(self.main_frame, text="文件保密柜", font=("黑体", 16), pady=20).pack()
        
        # 更改密码面板
        change_frame = Frame(self.main_frame, padx=20, pady=20)
        change_frame.pack(pady=10, fill=BOTH, expand=True)
        
        Label(change_frame, text="更改密码", font=("黑体", 14)).pack(pady=10)
        
        password_frame = Frame(change_frame)
        password_frame.pack(pady=10)
        
        Label(password_frame, text="旧密码:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.old_pw_entry = Entry(password_frame, show="*", width=30)
        self.old_pw_entry.grid(row=0, column=1, padx=5, pady=5)
        
        Label(password_frame, text="新密码:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.new_pw_entry = Entry(password_frame, show="*", width=30)
        self.new_pw_entry.grid(row=1, column=1, padx=5, pady=5)
        
        Label(password_frame, text="确认新密码:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.confirm_new_entry = Entry(password_frame, show="*", width=30)
        self.confirm_new_entry.grid(row=2, column=1, padx=5, pady=5)
        
        btn_frame = Frame(change_frame)
        btn_frame.pack(pady=20)
        
        Button(btn_frame, text="确认更改", command=self.change_password, width=15).pack(side=LEFT, padx=10)
        Button(btn_frame, text="返回", command=self.show_main, width=15).pack(side=LEFT, padx=10)
        
        self.update_status("更改密码界面")
    
    def clear_main_frame(self):
        """清除主框架内容"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
    
    def update_status(self, text):
        """安全更新状态栏文本"""
        self.status_bar.config(text=text)
    
    def set_password(self):
        """处理设置密码逻辑"""
        pw = self.pw_entry.get()
        confirm = self.confirm_entry.get()
        
        if pw != confirm:
            messagebox.showerror("错误", "两次输入的密码不一致")
            self.update_status("密码设置失败: 两次密码不一致")
            return
        
        try:
            # 创建加密器和配置文件
            self.fernet = self.locker.create_config(pw)
            self.show_main()
            self.update_status("密码设置成功")
        except Exception as e:
            messagebox.showerror("错误", f"设置密码失败: {str(e)}")
            self.update_status(f"密码设置失败: {str(e)}")
    
    def login(self):
        """处理登录逻辑"""
        pw = self.login_entry.get()
        
        self.fernet = self.locker.verify_password(pw)
        if self.fernet:
            self.show_main()
            self.update_status("登录成功")
        else:
            messagebox.showerror("错误", "密码错误")
            self.update_status("登录失败: 密码错误")
    
    def change_password(self):
        """处理更改密码逻辑"""
        old_p极
        old_pw = self.old_pw_entry.get()
        new_pw = self.new_pw_entry.get()
        confirm_pw = self.confirm_new_entry.get()
        
        if new_pw != confirm_pw:
            messagebox.showerror("错误", "新密码不一致")
            self.update_status("密码更改失败: 新密码不一致")
            return
        
        # 验证旧密码
        old_fernet = self.locker.verify_password(old_pw)
        if not old_fernet:
            message极
            messagebox.showerror("错误", "旧密码错误")
            self.update_status("密码更改失败: 旧密码错误")
            return
        
        try:
            # 从数据文件读取所有文件内容
            all_files = self.locker.load_all_files(old_fernet)
            
            # 创建新配置文件
            new_fernet = self.locker.create_config(new_pw)
            
            # 用新密码重新加密所有文件
            if all_files:
                self.locker.save_all_files(new_fernet, all_files)
            
            self.fernet = new_fernet
            self.update_status("密码更改成功")
            self.show_main()
        except Exception as e:
            messagebox.showerror("错误", f"密码更改失败: {str(e)}")
            self.update_status(f"密码更改失败: {str(e)}")
    
    def refresh_file_list(self):
        """刷新文件列表"""
        if not self.fernet:
            self.update_status("无法刷新: 未初始化加密器")
            return
            
        try:
            self.file_listbox.delete(0, END)
            files = self.locker.get_files(self.fernet)
            for file in files:
                self.file_listbox.insert(END, file)
            self.update_status(f"已加载 {len(files)} 个文件")
        except Exception as e:
            self.update_status(f"刷新文件列表失败: {str(e)}")
    
    def create_file(self):
        """创建新文本文件"""
        filename = simpledialog.askstring("创建文件", "输入文件名:")
        if not filename:
            self.update_status("文件创建取消")
            return
        
        # 创建文本编辑器窗口
        self.create_editor_window(filename, "")
        self.update_status(f"创建文件: {filename}")
    
    def view_file_content(self, event=None):
        """查看文件内容"""
        if not self.file_listbox.curselection():
            return
            
        filename = self.file_listbox.get(self.file_listbox.curselection())
        content = self.locker.get_file_content(self.fernet, filename)
        
        if content is None:
            messagebox.showerror("错误", "文件内容获取失败")
            self.update_status(f"错误: 无法获取 {filename} 内容")
            return
        
        # 创建编辑器窗口显示内容
        self.create_editor_window(filename, content)
        self.update_status(f"查看文件: {filename}")
    
    def create_editor_window(self, filename, content):
        """创建文件编辑器窗口"""
        editor = Toplevel(self.root)
        editor.title(f"编辑文件: {filename}")
        editor.geometry("500x400")
        editor.grab_set()  # 模态窗口
        
        # 内容编辑器
        content_frame = Frame(editor)
        content_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        Label(content_frame, text=f"文件名: {filename}").pack(anchor=W)
        
        scroll_text = ScrolledText(content_frame, wrap=WORD, height=20)
        scroll_text.pack(fill=BOTH, expand=True, pady=5)
        scroll_text.insert(END, content)
        
        # 按钮区域
        btn_frame = Frame(editor)
        btn_frame.pack(fill=X, padx=10, pady=10)
        
        def save_file():
            new_content = scroll_text.get("1.0", END).strip()
            if self.locker.save_file(self.fernet, filename, new_content):
                self.update_status(f"文件保存成功: {filename}")
                self.refresh_file_list()
                editor.destroy()
            else:
                messagebox.showerror("错误", "文件保存失败")
                self.update_status(f"错误: 保存文件失败 {filename}")
        
        Button(btn_frame, text="保存", command=save_file, width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="取消", command=editor.destroy, width极
        Button(btn_frame, text="取消", command=editor.destroy, width=10).pack(side=LEFT, padx=5)
    
    def upload_file(self):
        """上传本地文件(支持多选)"""
        filepaths = filedialog.askopenfilenames(
            title="选择要上传的文件",
            filetypes=[("所有文件", "*.*")]
        )
        
        if not filepaths:
            self.update_status("文件上传取消")
            return
        
        success_count = 0
        fail_count = 0
        
        for filepath in filepaths:
            filename = os.path.basename(filepath)
            self.update_status(f"上传中: {filename}")
            
            try:
                # 以二进制方式读取
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                
                # 检查是否为文本文件(UTF-8可解码)
                try:
                    content = file_data.decode('utf-8')
                    # 保存文本文件
                    if self.locker.save_file(self.fernet, filename, content):
                        success_count += 1
                    else:
                        self.update_status(f"错误: 上传失败 {filename}")
                        fail_count += 1
                except UnicodeDecodeError:
                    # 如果是二进制文件，转换为Base64存储
                    # 添加特殊前缀标识
                    content = base64.b64encode(file_data).decode('utf-8')
                    if self.locker.save_file(self.fernet, f"[BINARY]{filename}", content):
                        success_count += 1
                    else:
                        self.update_status(f"错误: 上传失败 {filename}")
                        fail_count += 1
            except Exception as e:
                self.update_status(f"上传失败: {filename} ({str(e)})")
                fail_count += 1
        
        self.update_status(f"上传完成: 成功 {success_count} 个, 失败 {fail_count} 个")
        self.refresh_file_list()
    
    def download_files(self):
        """下载选中的多个文件到本地"""
        selected_indices = self.file_listbox.curselection()
        
        if not selected_indices:
            messagebox.showwarning("警告", "请先选择一个或多个文件")
            return
        
        # 获取选择的多个文件名
        filenames = [self.file_listbox.get(i) for i in selected_indices]
        
        # 选择保存目录
        save_dir = filedialog.askdirectory(
            title="选择保存文件的目录"
        )
        
        if not save_dir:
            self.update_status("下载取消")
            return
        
        success_count = 0
        fail_count = 0
        
        for filename in filenames:
            self.update_status(f"下载中: {filename}")
            
            try:
                content = self.locker.get_file_content(self.fernet, filename)
                if content is None:
                    self.update_status(f"错误: 无法获取 {filename} 内容")
                    fail_count += 1
                    continue
                
                # 构造保存路径
                save_path = os.path.join(save_dir, filename.replace("[BINARY]", ""))
                
                # 处理二进制文件
                if filename.startswith("[BINARY]"):
                    # 将Base64字符串解码为二进制数据
                    try:
                        binary_data = base64.b64decode(content)
                        with open(save_path, 'wb') as f:
                            f.write(binary_data)
                        success_count += 1
                    except Exception as e:
                        self.update_status(f"错误: 下载失败 {filename} ({str(e)})")
                        fail_count += 1
                else:
                    # 保存文本文件
                    try:
                        with open(save_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        success_count += 1
                    except Exception as e:
                        self.update_status(f"错误: 下载失败 {filename} ({str(e)})")
                        fail_count += 1
            except Exception as e:
                self.update_status(f"下载失败: {filename} ({str(e)})")
                fail_count += 1
        
        self.update_status(f"下载完成: 成功 {success_count} 个, 失败 {fail_count} 个")
        messagebox.showinfo("下载完成", f"成功下载 {success_count} 个文件\n失败 {fail_count} 个文件")
    
    def delete_files(self):
        """删除选中的文件"""
        selected_indices = self.file_listbox.curselection()
        
        if not selected_indices:
            messagebox.showwarning("警告", "请先选择一个或多个文件")
            return
        
        # 获取选择的多个文件名
        filenames = [self.file_listbox.get(i) for i in selected_indices]
        
        # 确认删除
        if not messagebox.askyesno("确认删除", f"确定要删除 {len(filenames)} 个文件吗？"):
            return
        
        # 调用文件删除方法
        try:
            deleted_count = self.locker.delete_files(self.fernet, filenames)
            if deleted_count:
                self.update_status(f"成功删除 {deleted_count} 个文件")
                self.refresh_file_list()
                messagebox.showinfo("删除成功", f"已删除 {deleted_count} 个文件")
            else:
                self.update_status("没有文件被删除")
        except Exception as e:
            self.update_status(f"删除失败: {str(e)}")
            messagebox.showerror("删除失败", f"文件删除失败: {str(e)}")

if __name__ == "__main__":
    root = Tk()
    app = App(root)
    root.mainloop()
