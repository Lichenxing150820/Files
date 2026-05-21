import os
import ctypes
import win32security
import win32con
import win32api
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import shutil
from datetime import datetime

class PrivilegedFileBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("文件浏览器")
        self.root.geometry("1000x700")
        
        # 初始化变量
        self.selected_path = None
        self.clipboard = None
        self.clipboard_operation = None
        
        # 检查并获取管理员权限
        self.ensure_admin_privileges()
        
        # 设置UI
        self.setup_ui()
        self.setup_context_menu()
        
        # 初始加载C盘
        self.load_directory("C:\\")
    
    def ensure_admin_privileges(self):
        """确保以管理员权限运行"""
        try:
            if not ctypes.windll.shell32.IsUserAnAdmin():
                if messagebox.askyesno(
                    "需要管理员权限", 
                    "需要管理员权限才能访问系统文件。是否现在提升权限?"):
                    
                    # 以管理员权限重新启动
                    ctypes.windll.shell32.ShellExecuteW(
                        None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                    sys.exit()
        except Exception as e:
            messagebox.showerror("错误", f"权限检查失败: {str(e)}")
            sys.exit(1)
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=2)
        
        # 导航按钮
        ttk.Button(toolbar, text="←", command=self.go_up).pack(side=tk.LEFT, padx=2)
        
        # 地址栏
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(toolbar, textvariable=self.path_var, width=70)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        path_entry.bind("<Return>", lambda e: self.load_directory(self.path_var.get()))
        
        # 功能按钮
        ttk.Button(toolbar, text="刷新", command=self.refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="获取权限", command=self.grant_access_to_current).pack(side=tk.LEFT, padx=2)
        
        # 文件列表
        self.tree = ttk.Treeview(
            main_frame, 
            columns=("size", "type", "modified", "owner", "perms"),
            selectmode="browse"
        )
        
        # 设置列
        self.tree.heading("#0", text="名称", anchor=tk.W)
        self.tree.heading("size", text="大小", anchor=tk.W)
        self.tree.heading("type", text="类型", anchor=tk.W)
        self.tree.heading("modified", text="修改日期", anchor=tk.W)
        self.tree.heading("owner", text="所有者", anchor=tk.W)
        self.tree.heading("perms", text="权限", anchor=tk.W)
        
        # 列宽
        self.tree.column("#0", width=300, stretch=tk.YES)
        self.tree.column("size", width=80, stretch=tk.NO)
        self.tree.column("type", width=80, stretch=tk.NO)
        self.tree.column("modified", width=120, stretch=tk.NO)
        self.tree.column("owner", width=150, stretch=tk.NO)
        self.tree.column("perms", width=100, stretch=tk.NO)
        
        # 滚动条
        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 布局
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 绑定事件
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
    
    def setup_context_menu(self):
        """设置右键菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        
        # 菜单项
        self.context_menu.add_command(label="打开", command=self.open_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="复制", command=self.copy_selected)
        self.context_menu.add_command(label="剪切", command=self.cut_selected)
        self.context_menu.add_command(label="粘贴", command=self.paste_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="删除", command=self.delete_selected)
        self.context_menu.add_command(label="重命名", command=self.rename_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="新建文件夹", command=self.create_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="属性", command=self.show_properties)
        self.context_menu.add_command(label="获取完全控制权", command=self.take_ownership)
    
    def take_ownership(self):
        """获取文件/文件夹的所有权"""
        if not self.selected_path:
            return
            
        try:
            # 获取当前用户的SID
            user_sid = win32security.LookupAccountName(None, win32api.GetUserName())[0]
            
            # 获取安全描述符
            sd = win32security.GetNamedSecurityInfo(
                self.selected_path,
                win32security.SE_FILE_OBJECT,
                win32security.OWNER_SECURITY_INFORMATION | 
                win32security.DACL_SECURITY_INFORMATION
            )
            
            # 设置新的所有者
            win32security.SetNamedSecurityInfo(
                self.selected_path,
                win32security.SE_FILE_OBJECT,
                win32security.OWNER_SECURITY_INFORMATION,
                user_sid,
                None, None, None
            )
            
            # 设置完全控制权限
            dacl = win32security.ACL()
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                win32con.FILE_ALL_ACCESS,
                user_sid
            )
            
            win32security.SetNamedSecurityInfo(
                self.selected_path,
                win32security.SE_FILE_OBJECT,
                win32security.DACL_SECURITY_INFORMATION,
                None, None, dacl, None
            )
            
            messagebox.showinfo("成功", "已获取所有权和完全控制权限")
            self.refresh()
            
        except Exception as e:
            messagebox.showerror("错误", f"获取所有权失败: {str(e)}")
    
    def load_directory(self, path):
        """加载目录内容"""
        if not os.path.exists(path):
            messagebox.showerror("错误", "路径不存在")
            return
            
        try:
            self.tree.delete(*self.tree.get_children())
            self.path_var.set(path)
            
            # 添加上级目录项
            if path != os.path.splitdrive(path)[0] + "\\":
                self.tree.insert("", "end", text="..", values=("", "上级目录", "", "", ""))
            
            # 尝试读取目录内容
            try:
                entries = os.listdir(path)
            except PermissionError:
                if messagebox.askyesno("权限不足", f"无法访问 {path}。是否尝试获取权限?"):
                    if self.grant_access(path):
                        entries = os.listdir(path)
                    else:
                        return
                else:
                    return
            
            # 先添加目录
            for entry in entries:
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    try:
                        self.add_tree_item(full_path, entry, is_dir=True)
                    except:
                        continue
            
            # 再添加文件
            for entry in entries:
                full_path = os.path.join(path, entry)
                if os.path.isfile(full_path):
                    try:
                        self.add_tree_item(full_path, entry, is_dir=False)
                    except:
                        continue
                        
        except Exception as e:
            messagebox.showerror("错误", f"加载目录失败: {str(e)}")
    
    def add_tree_item(self, full_path, name, is_dir):
        """添加项目到树视图"""
        try:
            # 获取文件信息
            stat = os.stat(full_path)
            size = "" if is_dir else self.format_size(stat.st_size)
            ftype = "文件夹" if is_dir else "文件"
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            # 获取所有者和权限
            try:
                sd = win32security.GetNamedSecurityInfo(
                    full_path, win32security.SE_FILE_OBJECT,
                    win32security.OWNER_SECURITY_INFORMATION)
                owner = win32security.LookupAccountSid(None, sd.GetSecurityDescriptorOwner())[0]
            except:
                owner = "N/A"
            
            perms = self.get_permissions_string(full_path)
            
            # 添加到树视图
            self.tree.insert(
                "", "end", text=name,
                values=(size, ftype, modified, owner, perms))
        except Exception as e:
            print(f"无法添加 {full_path}: {str(e)}")
    
    def get_permissions_string(self, path):
        """获取权限字符串表示"""
        try:
            sd = win32security.GetNamedSecurityInfo(
                path, win32security.SE_FILE_OBJECT,
                win32security.DACL_SECURITY_INFORMATION)
            dacl = sd.GetSecurityDescriptorDacl()
            
            if dacl is None:
                return "无限制"
                
            # 检查常见权限
            user_flags = {
                "R": win32con.FILE_GENERIC_READ,
                "W": win32con.FILE_GENERIC_WRITE,
                "X": win32con.FILE_GENERIC_EXECUTE,
                "D": win32con.DELETE
            }
            
            perms = []
            for flag, val in user_flags.items():
                if dacl.CheckAccess(win32security.ACTRL_FILE_READ):
                    perms.append(flag)
                else:
                    perms.append("-")
                    
            return "".join(perms)
        except:
            return "N/A"
    
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def refresh(self):
        """刷新当前目录"""
        self.load_directory(self.path_var.get())
    
    def on_double_click(self, event):
        """双击事件处理"""
        item = self.tree.selection()[0]
        text = self.tree.item(item, "text")
        current_path = self.path_var.get()
        
        if text == "..":
            new_path = os.path.dirname(current_path)
        else:
            new_path = os.path.join(current_path, text)
        
        if os.path.isdir(new_path):
            self.load_directory(new_path)
        else:
            try:
                os.startfile(new_path)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件: {str(e)}")
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            text = self.tree.item(item, "text")
            current_path = self.path_var.get()
            
            if text == "..":
                self.selected_path = os.path.dirname(current_path)
            else:
                self.selected_path = os.path.join(current_path, text)
            
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
    def open_selected(self):
        if self.selected_path:
            if os.path.isdir(self.selected_path):
                self.load_directory(self.selected_path)
            else:
                try:
                    os.startfile(self.selected_path)
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开文件: {str(e)}")
    
    def copy_selected(self):
        if self.selected_path:
            self.clipboard = self.selected_path
            self.clipboard_operation = 'copy'
            messagebox.showinfo("复制", f"已复制: {os.path.basename(self.selected_path)}")
    
    def cut_selected(self):
        if self.selected_path:
            self.clipboard = self.selected_path
            self.clipboard_operation = 'cut'
            messagebox.showinfo("剪切", f"已剪切: {os.path.basename(self.selected_path)}")
    
    def paste_selected(self):
        if self.clipboard and self.clipboard_operation:
            dest_dir = self.path_var.get()
            try:
                if self.clipboard_operation == 'copy':
                    if os.path.isdir(self.clipboard):
                        shutil.copytree(self.clipboard, 
                                      os.path.join(dest_dir, os.path.basename(self.clipboard)))
                    else:
                        shutil.copy2(self.clipboard, dest_dir)
                    messagebox.showinfo("粘贴", "复制完成")
                elif self.clipboard_operation == 'cut':
                    shutil.move(self.clipboard, dest_dir)
                    self.clipboard = None
                    messagebox.showinfo("粘贴", "移动完成")
                
                self.refresh()
            except Exception as e:
                messagebox.showerror("错误", f"操作失败: {str(e)}")
    
    def delete_selected(self):
        if self.selected_path and messagebox.askyesno(
            "确认删除", 
            f"确定要永久删除 '{os.path.basename(self.selected_path)}' 吗?"):
            
            try:
                if os.path.isdir(self.selected_path):
                    shutil.rmtree(self.selected_path)
                else:
                    os.remove(self.selected_path)
                messagebox.showinfo("删除", "删除成功")
                self.refresh()
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {str(e)}")
    
    def rename_selected(self):
        if self.selected_path:
            new_name = simpledialog.askstring(
                "重命名", 
                f"为 '{os.path.basename(self.selected_path)}' 输入新名称:",
                initialvalue=os.path.basename(self.selected_path))
            
            if new_name and new_name != os.path.basename(self.selected_path):
                try:
                    os.rename(
                        self.selected_path,
                        os.path.join(os.path.dirname(self.selected_path), new_name)
                    )
                    messagebox.showinfo("重命名", "重命名成功")
                    self.refresh()
                except Exception as e:
                    messagebox.showerror("错误", f"重命名失败: {str(e)}")
    
    def create_folder(self):
        """创建新文件夹"""
        current_dir = self.path_var.get()
        folder_name = simpledialog.askstring("新建文件夹", "输入文件夹名称:")
        if folder_name:
            try:
                os.mkdir(os.path.join(current_dir, folder_name))
                self.refresh()
            except Exception as e:
                messagebox.showerror("错误", f"创建文件夹失败: {str(e)}")
    
    def show_properties(self):
        """显示属性对话框"""
        if not self.selected_path:
            return
            
        prop_text = f"名称: {os.path.basename(self.selected_path)}\n"
        prop_text += f"路径: {self.selected_path}\n"
        prop_text += f"类型: {'文件夹' if os.path.isdir(self.selected_path) else '文件'}\n"
        
        try:
            stat = os.stat(self.selected_path)
            prop_text += f"大小: {self.format_size(stat.st_size)}\n"
            prop_text += f"创建时间: {datetime.fromtimestamp(stat.st_ctime)}\n"
            prop_text += f"修改时间: {datetime.fromtimestamp(stat.st_mtime)}\n"
            
            # 获取所有者信息
            sd = win32security.GetNamedSecurityInfo(
                self.selected_path, win32security.SE_FILE_OBJECT,
                win32security.OWNER_SECURITY_INFORMATION)
            owner_sid = sd.GetSecurityDescriptorOwner()
            owner_name, domain, _ = win32security.LookupAccountSid(None, owner_sid)
            prop_text += f"所有者: {domain}\\{owner_name}\n"
            
            # 获取权限信息
            dacl = sd.GetSecurityDescriptorDacl()
            if dacl:
                prop_text += "\n权限:\n"
                for i in range(dacl.GetAceCount()):
                    ace = dacl.GetAce(i)
                    sid = ace[2]
                    name, domain, _ = win32security.LookupAccountSid(None, sid)
                    mask = ace[1]
                    
                    perms = []
                    if mask & win32con.FILE_READ_DATA:
                        perms.append("读取")
                    if mask & win32con.FILE_WRITE_DATA:
                        perms.append("写入")
                    if mask & win32con.FILE_EXECUTE:
                        perms.append("执行")
                    if mask & win32con.DELETE:
                        perms.append("删除")
                    
                    prop_text += f"{domain}\\{name}: {', '.join(perms)}\n"
            
        except Exception as e:
            prop_text += f"\n无法获取完整属性: {str(e)}\n"
        
        messagebox.showinfo("属性", prop_text)
    
    def go_up(self):
        """导航到上级目录"""
        current_path = self.path_var.get()
        if current_path != os.path.splitdrive(current_path)[0] + "\\":
            self.load_directory(os.path.dirname(current_path))
    
    def grant_access_to_current(self):
        """为当前目录获取权限"""
        path = self.path_var.get()
        if self.grant_access(path):
            messagebox.showinfo("成功", "权限已获取")
            self.refresh()
        else:
            messagebox.showerror("错误", "获取权限失败")
    
    def grant_access(self, path):
        """获取对路径的访问权限"""
        try:
            # 获取当前用户的SID
            user_sid = win32security.LookupAccountName(None, win32api.GetUserName())[0]
            
            # 获取安全描述符
            sd = win32security.GetNamedSecurityInfo(
                path, win32security.SE_FILE_OBJECT,
                win32security.DACL_SECURITY_INFORMATION)
            
            # 创建新的ACL
            dacl = win32security.ACL()
            
            # 添加完全控制权限
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                win32con.FILE_ALL_ACCESS,
                user_sid)
            
            # 设置新的安全描述符
            win32security.SetNamedSecurityInfo(
                path, win32security.SE_FILE_OBJECT,
                win32security.DACL_SECURITY_INFORMATION,
                None, None, dacl, None)
            
            return True
        except Exception as e:
            messagebox.showerror("错误", f"权限设置失败: {str(e)}")
            return False

if __name__ == "__main__":
    # 检查并请求管理员权限
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit()
    except:
        pass
    
    root = tk.Tk()
    app = PrivilegedFileBrowser(root)
    root.mainloop()
