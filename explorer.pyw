import os
import shutil
import tkinter as tk
from tkinter import ttk, Menu, messagebox, simpledialog, scrolledtext
import win32api
import win32file
import win32con
from win32com.shell import shell, shellcon
import psutil
import threading
import fnmatch
from PIL import Image, ImageTk
import datetime
import subprocess
import sys

class FileExplorer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("高级文件资源管理器")
        self.geometry("1200x800")
        self.is_admin = self.check_admin()
        self.clipboard = {"operation": None, "path": None}
        self.current_dir = os.path.abspath(os.sep)
        self.search_thread = None
        self.preview_image = None
        self.select_rect = None
        self.start_x = None
        self.start_y = None
        self.dragging = False
        self.history = []
        self.history_index = -1
        
        # 创建界面
        self.create_widgets()
        
        # 加载初始目录
        self.load_directory(self.current_dir)
        
        # 绑定快捷键
        self.bind_keys()

    def check_admin(self):
        try:
            return shell.IsUserAnAdmin()
        except:
            return False

    def create_widgets(self):
        # 状态栏
        self.status_bar = tk.Label(self, text=f"管理员权限: {'已获取' if self.is_admin else '未获取'}", 
                                bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 主框架
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧文件浏览区
        self.create_browser_frame(main_frame)
        
        # 添加分割线
        sep = ttk.Separator(main_frame, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 右侧预览区
        self.create_preview_frame(main_frame)

    def create_browser_frame(self, parent):
        # 文件浏览区框架
        browser_frame = ttk.Frame(parent)
        browser_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 工具栏
        toolbar = ttk.Frame(browser_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="上一级", command=self.go_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新", command=self.refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="新建文件夹", command=self.create_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="主页", command=self.go_home).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="此电脑", command=self.show_computer_view).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="全选", command=self.select_all).pack(side=tk.LEFT, padx=2)  # 添加全选按钮
    
        # 地址栏
        address_frame = ttk.Frame(browser_frame)
        address_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(address_frame, text="地址:").pack(side=tk.LEFT)
        self.address_var = tk.StringVar()
        address_entry = ttk.Entry(address_frame, textvariable=self.address_var, width=60)
        address_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        address_entry.bind("<Return>", lambda e: self.navigate_to_path(self.address_var.get()))
        
        # 搜索框
        search_frame = ttk.Frame(browser_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind("<Return>", self.start_search)
        
        ttk.Button(search_frame, text="搜索", command=self.start_search).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text="清空", command=self.clear_search).pack(side=tk.LEFT)
        
        # 树视图框架
        tree_frame = ttk.Frame(browser_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建选择画布用于拖拽多选
        self.select_canvas = tk.Canvas(tree_frame, highlightthickness=0, bg='white', bd=0)
        self.select_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 文件树视图
        columns = ("name", "size", "type", "modified")
        self.tree = ttk.Treeview(self.select_canvas, columns=columns, show="headings")
        
        # 配置树视图滚动条
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=tree_scroll.set)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 将树视图放入画布窗口
        self.tree_window = self.select_canvas.create_window(0, 0, anchor="nw", window=self.tree)
        
        # 调整树视图大小以填充画布
        self.tree.bind("<Configure>", self.on_tree_configure)
        self.select_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # 定义列和标题
        self.tree.heading("name", text="名称", command=lambda: self.sort_column("name"))
        self.tree.heading("size", text="大小", command=lambda: self.sort_column("size"))
        self.tree.heading("type", text="类型", command=lambda: self.sort_column("type"))
        self.tree.heading("modified", text="修改日期", command=lambda: self.sort_column("modified"))
        
        # 设置列宽
        self.tree.column("name", width=300, anchor=tk.W)
        self.tree.column("size", width=100, anchor=tk.E)
        self.tree.column("type", width=150, anchor=tk.W)
        self.tree.column("modified", width=150, anchor=tk.W)
        
        # 绑定事件 - 拖拽选择
        self.select_canvas.bind("<ButtonPress-1>", self.on_select_press)
        self.select_canvas.bind("<B1-Motion>", self.on_select_drag)
        self.select_canvas.bind("<ButtonRelease-1>", self.on_select_release)
        
        # 绑定其他事件
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # 绑定鼠标滚轮事件用于滚动
        self.select_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.tree.bind("<MouseWheel>", self.on_mouse_wheel)

    def select_all(self, event=None):
        """全选当前目录下的所有项目"""
        # 获取树视图中的所有可见项目
        all_items = self.tree.get_children()
        
        # 过滤掉特殊项目（如".."、"返回文件浏览"等）
        valid_items = []
        for item in all_items:
            values = self.tree.item(item, "values")
            tags = self.tree.item(item, "tags")
            
            # 排除特殊项目
            if values and (values[0] == ".." or values[0] == "返回文件浏览" or "computer" in tags):
                continue
            valid_items.append(item)
        
        # 设置选择
        self.tree.selection_set(valid_items)
        
        # 更新状态栏
        self.update_status_bar(f"已全选 {len(valid_items)} 个项目")

    def bind_keys(self):
        """绑定键盘快捷键"""
        # F2 - 重命名
        self.bind("<F2>", self.rename_selected)
        # Delete - 移动到回收站
        self.bind("<Delete>", self.delete_selected_to_recycle)
        # Shift+Delete - 永久删除
        self.bind("<Shift-Delete>", self.permanent_delete_selected)
        # Ctrl+Shift+N - 新建文件夹
        self.bind("<Control-Shift-N>", self.create_folder)
        # F5 - 刷新
        self.bind("<F5>", lambda e: self.refresh())
        # Ctrl+A - 全选
        self.bind("<Control-a>", self.select_all)
        self.bind("<Control-A>", self.select_all)  # 处理大写锁定情况

    def on_tree_configure(self, event):
        """当树视图大小改变时调整画布滚动区域"""
        self.select_canvas.configure(scrollregion=self.select_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """当画布大小改变时调整树视图大小"""
        self.select_canvas.itemconfig(self.tree_window, width=event.width, height=event.height)

    def on_mouse_wheel(self, event):
        """处理鼠标滚轮事件以滚动视图"""
        scroll = -1 * (event.delta // 120)  # Windows系统
        self.tree.yview_scroll(scroll, "units")
        return "break"

    def create_preview_frame(self, parent):
        # 预览区框架
        preview_frame = ttk.Frame(parent)
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5, ipadx=5, ipady=5)
        
        # 预览标题
        ttk.Label(preview_frame, text="预览:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=5)
        
        # 图像预览
        self.image_preview = ttk.Label(preview_frame, borderwidth=2, relief="solid")
        self.image_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.image_preview.configure(anchor=tk.CENTER)
        
        # 文本预览
        self.text_preview = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD, height=10)
        self.text_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text_preview.config(state=tk.DISABLED)
        
        # 属性预览
        ttk.Label(preview_frame, text="属性:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=5)
        self.properties_text = tk.Text(preview_frame, height=10, wrap=tk.NONE)
        self.properties_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.properties_text.config(state=tk.DISABLED)

    def load_directory(self, path):
        # 清理现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # 更新当前目录
        self.current_dir = os.path.normpath(path)
        self.address_var.set(self.current_dir)
        
        try:
            # 如果是磁盘根目录，添加父目录项为"此电脑"
            if self.is_root_directory(self.current_dir):
                self.tree.insert("", "end", values=("..", "", "此电脑", ""), 
                                tags=("parent", "computer"), iid="__computer")
            
            # 添加父目录项
            elif self.current_dir != os.path.abspath(os.sep):
                parent_dir = os.path.dirname(self.current_dir)
                self.tree.insert("", "end", values=("..", "", "父目录", ""), 
                                tags=("parent",), iid=f"__parent_{parent_dir}")
            
            # 列出目录内容
            items = os.listdir(self.current_dir)
            for item in items:
                full_path = os.path.join(self.current_dir, item)
                
                try:
                    if os.path.isdir(full_path):
                        self.add_directory_item(item, full_path)
                    else:
                        self.add_file_item(item, full_path)
                except PermissionError:
                    self.add_system_item(item, full_path)
                except Exception as e:
                    self.add_error_item(item, full_path, str(e))
        
        except Exception as e:
            messagebox.showerror("错误", f"无法访问目录: {str(e)}")
        
        # 更新状态栏
        self.update_status_bar()

    def is_root_directory(self, path):
        """检查是否是磁盘根目录"""
        return os.path.isdir(path) and os.path.basename(path) == "" and len(path) == 3 and path[1:3] == ":\\"

    def add_directory_item(self, name, path):
        try:
            size = ""
            item_type = "文件夹"
            modified = os.path.getmtime(path)
            self.tree.insert("", "end", values=(name, size, item_type, modified), 
                            tags=("folder",), iid=path)
        except Exception as e:
            self.tree.insert("", "end", values=(name, "错误", "文件夹", ""), 
                            tags=("error",), iid=path)

    def add_file_item(self, name, path):
        try:
            size = os.path.getsize(path)
            size_text = self.format_size(size)
            item_type = os.path.splitext(name)[1][1:] + "文件" if '.' in name else "文件"
            modified = os.path.getmtime(path)
            self.tree.insert("", "end", values=(name, size_text, item_type, modified), 
                            tags=("file",), iid=path)
        except Exception as e:
            self.tree.insert("", "end", values=(name, "错误", "文件", ""), 
                            tags=("error",), iid=path)

    def add_system_item(self, name, path):
        self.tree.insert("", "end", values=(f"{name} [系统文件]", "受限", "系统文件", ""), 
                        tags=("system",), iid=path)

    def add_error_item(self, name, path, error):
        self.tree.insert("", "end", values=(f"{name} [错误]", "受限", "错误", error), 
                        tags=("error",), iid=path)

    def format_size(self, size):
        # 格式化文件大小
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def format_time(self, timestamp):
        # 格式化时间戳
        return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def navigate_to_path(self, path):
        if os.path.exists(path):
            self.load_directory(path)
        else:
            messagebox.showerror("错误", "路径不存在")

    def on_double_click(self, event):
        item = self.tree.focus()
        if item:
            values = self.tree.item(item, "values")
            tags = self.tree.item(item, "tags")
            
            if values and values[0] == "..":
                if "computer" in tags:
                    self.show_computer_view()
                else:
                    self.go_up()
            elif "folder" in tags:
                self.load_directory(item)
            else:
                self.open_file(item)

    def go_up(self):
        parent = os.path.dirname(self.current_dir)
        if os.path.exists(parent):
            self.load_directory(parent)
        else:
            self.show_computer_view()
            
    def show_computer_view(self):
        """显示'此电脑'视图，列出所有磁盘驱动器"""
        # 清理现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # 更新当前目录
        self.current_dir = "此电脑"
        self.address_var.set(self.current_dir)
        
        # 获取所有磁盘驱动器
        drives = self.get_logical_drives()
        
        for drive in drives:
            try:
                # 获取驱动器类型
                drive_type = self.get_drive_type(drive)
                type_map = {
                    win32file.DRIVE_UNKNOWN: "未知类型",
                    win32file.DRIVE_NO_ROOT_DIR: "无效路径",
                    win32file.DRIVE_REMOVABLE: "可移动磁盘",
                    win32file.DRIVE_FIXED: "本地磁盘",
                    win32file.DRIVE_REMOTE: "网络驱动器",
                    win32file.DRIVE_CDROM: "CD-ROM",
                    win32file.DRIVE_RAMDISK: "RAM磁盘"
                }
                type_str = type_map.get(drive_type, "未知类型")
                
                # 获取磁盘空间信息
                free_bytes, total_bytes, used_bytes = self.get_disk_space(drive)
                if free_bytes is not None and total_bytes is not None:
                    free_gb = free_bytes / (1024**3)
                    total_gb = total_bytes / (1024**3)
                    size_text = f"{free_gb:.1f} GB 可用 / {total_gb:.1f} GB"
                else:
                    size_text = "无法获取空间信息"
                
                self.tree.insert("", "end", values=(drive, size_text, type_str, ""), 
                                tags=("drive",), iid=drive)
            except Exception as e:
                self.tree.insert("", "end", values=(drive, "无法访问", "驱动器", str(e)), 
                                tags=("drive", "error"), iid=drive)
        
        # 更新状态栏
        self.update_status_bar()

    def get_logical_drives(self):
        """获取所有逻辑驱动器"""
        return win32api.GetLogicalDriveStrings().split('\x00')[:-1]

    def get_drive_type(self, drive):
        """获取驱动器类型"""
        return win32file.GetDriveType(drive)

    def get_disk_space(self, drive):
        """获取磁盘空间信息"""
        try:
            _, total_bytes, free_bytes = win32file.GetDiskFreeSpaceEx(drive)
            used_bytes = total_bytes - free_bytes
            return free_bytes, total_bytes, used_bytes
        except:
            return None, None, None
            
    def go_home(self):
        """返回用户主目录"""
        home_dir = os.path.expanduser("~")
        if os.path.exists(home_dir):
            self.load_directory(home_dir)

    def open_file(self, path):
        try:
            os.startfile(path)
        except:
            try:
                subprocess.Popen(["start", "", path], shell=True)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件: {str(e)}")

    def on_select(self, event):
        item = self.tree.focus()
        if item:
            path = item
            if self.tree.item(item, "values")[0] == "..":
                if "computer" in self.tree.item(item, "tags"):
                    path = "此电脑"
                else:
                    path = os.path.dirname(self.current_dir)
            
            self.update_preview(path)
            self.show_properties(path)

    def update_preview(self, path):
        # 清除现有预览
        self.image_preview.configure(image='')
        self.text_preview.config(state=tk.NORMAL)
        self.text_preview.delete(1.0, tk.END)
        self.text_preview.config(state=tk.DISABLED)
        
        # 如果是文件夹或驱动器则不需要预览
        if os.path.isdir(path) or (hasattr(self, 'tree') and "drive" in self.tree.item(path, "tags")):
            self.image_preview.configure(text="文件夹预览不可用")
            return
        
        # 获取文件扩展名
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        
        # 图片预览
        if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
            self.preview_image_file(path)
        # 文本预览
        elif ext in [".txt", ".log", ".csv", ".py", ".js", ".html", ".css", ".xml", ".json"]:
            self.preview_text_file(path)
        else:
            self.image_preview.configure(text="此文件类型不支持预览")

    def preview_image_file(self, path):
        try:
            img = Image.open(path)
            max_width, max_height = 400, 400
            width, height = img.size
            
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            
            self.preview_image = ImageTk.PhotoImage(img)
            self.image_preview.configure(image=self.preview_image)
        except Exception as e:
            self.image_preview.configure(text=f"无法预览图片: {str(e)}")

    def preview_text_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(2000)  # 读取前2000个字符
                if len(content) == 2000:
                    content += "\n...(预览截断)"
            
            self.text_preview.config(state=tk.NORMAL)
            self.text_preview.delete(1.0, tk.END)
            self.text_preview.insert(tk.END, content)
            self.text_preview.config(state=tk.DISABLED)
        except Exception as e:
            self.text_preview.config(state=tk.NORMAL)
            self.text_preview.delete(1.0, tk.END)
            self.text_preview.insert(tk.END, f"无法预览文件: {str(e)}")
            self.text_preview.config(state=tk.DISABLED)

    def show_properties(self, path):
        self.properties_text.config(state=tk.NORMAL)
        self.properties_text.delete(1.0, tk.END)
        
        if not os.path.exists(path) and path != "此电脑":
            self.properties_text.insert(tk.END, "文件不存在")
            self.properties_text.config(state=tk.DISABLED)
            return
        
        if path == "此电脑":
            self.properties_text.insert(tk.END, "名称: 此电脑\n类型: 系统文件夹")
            self.properties_text.config(state=tk.DISABLED)
            return
            
        name = os.path.basename(path)
        dir_name = os.path.dirname(path)
        
        try:
            stat = os.stat(path)
            size = stat.st_size
            created = stat.st_ctime
            modified = stat.st_mtime
            accessed = stat.st_atime
            
            if os.path.isdir(path):
                item_type = "文件夹"
                try:
                    num_items = len(os.listdir(path))
                    type_info = f"{num_items} 个项目"
                except:
                    type_info = "受限访问"
            else:
                item_type = "文件"
                type_info = os.path.splitext(name)[1].upper() + "文件" if '.' in name else "文件"
            
            properties = [
                f"名称: {name}",
                f"类型: {item_type}",
                f"位置: {dir_name}",
                f"大小: {self.format_size(size)}",
                f"创建时间: {self.format_time(created)}",
                f"修改时间: {self.format_time(modified)}",
                f"访问时间: {self.format_time(accessed)}",
            ]
            
            try:
                attr = win32file.GetFileAttributes(path)
                hidden = "是" if attr & win32con.FILE_ATTRIBUTE_HIDDEN else "否"
                system = "是" if attr & win32con.FILE_ATTRIBUTE_SYSTEM else "否"
                properties.extend([
                    f"隐藏: {hidden}",
                    f"系统文件: {system}"
                ])
            except:
                pass
            
            self.properties_text.insert(tk.END, "\n".join(properties))
        
        except Exception as e:
            self.properties_text.insert(tk.END, f"无法获取属性: {str(e)}")
        
        self.properties_text.config(state=tk.DISABLED)

    def start_search(self, event=None):
        search_term = self.search_var.get().strip()
        if not search_term:
            return
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.tree.insert("", "end", values=("正在搜索...", "", "", ""))
        self.update_status_bar(f"正在搜索 '{search_term}'...")
        
        if self.search_thread and self.search_thread.is_alive():
            return
            
        self.search_thread = threading.Thread(
            target=self.search_files, 
            args=(self.current_dir, search_term),
            daemon=True
        )
        self.search_thread.start()

    def search_files(self, directory, pattern):
        results = []
        self.search_var.set(pattern)  # 确保搜索框显示当前搜索内容
        
        # 在目录中搜索匹配的文件和文件夹
        for root, dirs, files in os.walk(directory):
            if self.search_var.get() != pattern:
                return
                
            for name in files:
                if fnmatch.fnmatch(name.lower(), pattern.lower()):
                    results.append(os.path.join(root, name))
            
            for name in dirs:
                if fnmatch.fnmatch(name.lower(), pattern.lower()):
                    results.append(os.path.join(root, name))
        
        self.after(0, self.display_search_results, results, pattern)

    def display_search_results(self, results, pattern):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not results:
            self.tree.insert("", "end", values=(f"未找到匹配 '{pattern}' 的结果", "", "", ""))
            self.update_status_bar(f"搜索完成，未找到结果")
            return
        
        self.tree.insert("", "end", values=("返回文件浏览", "", "", ""), tags=("back",))
        
        for path in results:
            name = os.path.basename(path)
            if os.path.isdir(path):
                self.tree.insert("", "end", values=(name, "", "文件夹", path), iid=path, tags=("folder",))
            else:
                try:
                    size = self.format_size(os.path.getsize(path))
                    item_type = os.path.splitext(name)[1][1:] + "文件" if '.' in name else "文件"
                    self.tree.insert("", "end", values=(name, size, item_type, path), iid=path, tags=("file",))
                except:
                    self.tree.insert("", "end", values=(f"{name} [访问受限]", "", "", path), iid=path, tags=("system",))
        
        self.update_status_bar(f"找到 {len(results)} 个匹配 '{pattern}' 的结果")

    def clear_search(self):
        self.search_var.set("")
        self.load_directory(self.current_dir)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
            
        self.tree.selection_set(item)
        path = item
        name = self.tree.item(item, "values")[0] if self.tree.item(item, "values") else ""
        tags = self.tree.item(item, "tags")
        
        menu = Menu(self, tearoff=0)
        
        # 特殊项处理
        if name == ".." or "parent" in tags:
            pass
        elif name == "返回文件浏览":
            menu.add_command(label="返回文件浏览", command=self.go_to_browse)
        elif "computer" in tags:
            menu.add_command(label="刷新", command=self.refresh)
        elif "drive" in tags:
            menu.add_command(label="打开", command=lambda: self.load_directory(path))
            menu.add_separator()
            menu.add_command(label="属性", command=lambda: self.show_properties(path))
        else:
            # 通用菜单项
            if os.path.isdir(path):
                menu.add_command(label="打开", command=lambda: self.load_directory(path))
            else:
                menu.add_command(label="打开", command=lambda: self.open_file(path))
            
            menu.add_separator()
            menu.add_command(label="打开所在位置", command=lambda: self.open_file_location(path))
            menu.add_separator()
            menu.add_command(label="剪切", command=lambda: self.cut_item(path))
            menu.add_command(label="复制", command=lambda: self.copy_item(path))
            menu.add_command(label="粘贴", command=self.paste_item)
            menu.add_separator()
            menu.add_command(label="全选", command=self.select_all)
            menu.add_separator()
            # 添加移动到回收站选项
            menu.add_command(label="移动到回收站", command=lambda: self.move_to_recycle_bin(path))
            
            # 添加永久删除选项（需要确认）
            menu.add_command(label="永久删除", command=lambda: self.permanent_delete(path))
            
            menu.add_separator()
            menu.add_command(label="重命名", command=lambda: self.rename_item(path))
            menu.add_separator()
            menu.add_command(label="属性", command=lambda: self.show_properties(path))
        
        menu.add_separator()

        
        if name != "返回文件浏览" and "drive" not in tags and "computer" not in tags:
            menu.add_separator()
            menu.add_command(label="新建文件夹", command=self.create_folder)
            
        menu.add_command(label="刷新", command=self.refresh, accelerator="F5")
        
        menu.post(event.x_root, event.y_root)

    def move_to_recycle_bin(self, path):
        name = os.path.basename(path)
        try:
            # 使用pywin32的SHFileOperation移动到回收站
            result = shell.SHFileOperation((
                0, 
                shellcon.FO_DELETE, 
                path, 
                None, 
                shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION | shellcon.FOF_NOERRORUI
            ))
            
            self.add_to_history("move_to_recycle", path, None)
            self.refresh()
        except Exception as e:
            self.show_delete_error(e, path, move_to_recycle=True)

    def add_to_history(self, action, path, backup_path):
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        
        self.history.append({
            "action": action,
            "path": path,
            "backup_path": backup_path,
            "timestamp": datetime.datetime.now()
        })
        self.history_index = len(self.history) - 1
        
        if len(self.history) > 50:
            self.history.pop(0)
            self.history_index -= 1

    def undo(self):
        if self.history_index < 0:
            return
            
        action = self.history[self.history_index]
        
        try:
            if action["action"] == "move_to_recycle":
                self.restore_from_recycle(action["path"])
            elif action["action"] == "permanent_delete":
                if action["backup_path"] and os.path.exists(action["backup_path"]):
                    shutil.copy2(action["backup_path"], action["path"])
                    os.remove(action["backup_path"])
            
            self.history_index -= 1
            self.refresh()
        except Exception as e:
            self.show_delete_error(e, action["path"], move_to_recycle=False)

    def redo(self):
        if self.history_index >= len(self.history) - 1:
            return
            
        self.history_index += 1
        action = self.history[self.history_index]
        
        try:
            if action["action"] == "move_to_recycle":
                self.move_to_recycle_bin(action["path"])
            elif action["action"] == "permanent_delete":
                self.permanent_delete(action["path"])
            
            self.refresh()
        except Exception as e:
            self.show_delete_error(e, action["path"], move_to_recycle=False)

    def restore_from_recycle(self, path):
        try:
            # 使用pywin32的SHFileOperation恢复文件
            result = shell.SHFileOperation((
                0,
                shellcon.FO_MOVE,
                "回收站\\" + os.path.basename(path),
                os.path.dirname(path),
                shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION | shellcon.FOF_NOERRORUI
            ))
        except Exception as e:
            self.show_delete_error(e, path, move_to_recycle=True)

    def go_to_browse(self):
        self.load_directory(self.current_dir)

    def open_file_location(self, path):
        try:
            subprocess.Popen(f'explorer /select,"{path}"', shell=True)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开位置: {str(e)}")

    def cut_item(self, path):
        self.clipboard = {"operation": "cut", "path": path}

    def copy_item(self, path):
        self.clipboard = {"operation": "copy", "path": path}

    def paste_item(self):
        if not self.clipboard.get("path"):
            return
            
        source = self.clipboard["path"]
        base_name = os.path.basename(source)
        dest = os.path.join(self.current_dir, base_name)
        
        try:
            if self.clipboard["operation"] == "copy":
                if os.path.isdir(source):
                    shutil.copytree(source, dest)
                else:
                    shutil.copy2(source, dest)
            elif self.clipboard["operation"] == "cut":
                if os.path.isdir(source):
                    shutil.move(source, dest)
                else:
                    self.force_move(source, dest)
                self.clipboard = {"operation": None, "path": None}
            
            self.refresh()
        except Exception as e:
            self.show_delete_error(e, source, move_to_recycle=False)

    def force_move(self, source, dest):
        try:
            os.rename(source, dest)
        except PermissionError:
            self.kill_processes_using_file(source)
            try:
                os.rename(source, dest)
            except:
                shutil.copy2(source, dest)
                self.delete_item(source)

    def kill_processes_using_file(self, file_path):
        for proc in psutil.process_iter(['pid', 'name', 'open_files']):
            try:
                for f in proc.open_files():
                    if f.path.lower() == file_path.lower():
                        proc.kill()
            except:
                continue

    def rename_selected(self, event=None):
        """重命名选中的项目（快捷键F2）"""
        selected = self.tree.selection()
        if selected:
            self.rename_item(selected[0])

    def delete_selected_to_recycle(self, event=None):
        """将选中的项目移动到回收站（快捷键Delete）"""
        selected = self.tree.selection()
        if selected:
            for item in selected:
                self.move_to_recycle_bin(item)

    def permanent_delete_selected(self, event=None):
        """永久删除选中的项目（快捷键Shift+Delete）"""
        selected = self.tree.selection()
        if selected:
            for item in selected:
                self.permanent_delete(item)

    def permanent_delete(self, path):
        name = os.path.basename(path)
        if not messagebox.askyesno("确认永久删除", f"确定要永久删除 '{name}' 吗？此操作不可恢复！"):
            return
        
        try:
            # 尝试获取文件所有权
            self.take_ownership(path)
            
            # 如果是文件夹
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    os.remove(path)
                except PermissionError:
                    self.kill_processes_using_file(path)
                    os.remove(path)
            
            self.add_to_history("permanent_delete", path, None)
            self.refresh()
        except Exception as e:
            self.show_delete_error(e, path, move_to_recycle=False)

    def take_ownership(self, path):
        """尝试获取文件所有权"""
        try:
            cmd = f'takeown /f "{path}"'
            if os.system(cmd) != 0:
                raise PermissionError("获取所有权失败")
        except Exception as e:
            pass  # 即使无法获取所有权，仍然继续尝试删除

    def show_delete_error(self, error, path, move_to_recycle=False):
        """显示与用户图片完全相同的错误对话框"""
        action = "移动到回收站" if move_to_recycle else "永久删除"
        
        error_dialog = tk.Toplevel(self)
        error_dialog.title("错误")
        error_dialog.geometry("500x200")
        error_dialog.resizable(False, False)
        error_dialog.transient(self)
        error_dialog.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(error_dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 左侧图标
        icon_frame = ttk.Frame(main_frame)
        icon_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        # 绘制红色圆形背景和白色叉号
        canvas = tk.Canvas(icon_frame, width=40, height=40, highlightthickness=0, bg='white')
        canvas.pack()
        canvas.create_oval(2, 2, 38, 38, fill='red', outline='')
        canvas.create_line(10, 10, 30, 30, fill='white', width=3)
        canvas.create_line(30, 10, 10, 30, fill='white', width=3)
        
        # 右侧文本
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 错误标题
        error_title = ttk.Label(text_frame, text=f"{action}失败:", font=("Arial", 11, "bold"))
        error_title.pack(anchor=tk.W, pady=(0, 5))
        
        # 错误详情
        if isinstance(error, PermissionError):
            err_text = f"[Errno 13] Permission denied: '{path}'"
        else:
            err_text = str(error)
        error_label = ttk.Label(text_frame, text=err_text, font=("Arial", 9))
        error_label.pack(anchor=tk.W)
        
        # 按钮框架
        button_frame = ttk.Frame(error_dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 确定按钮（带蓝色边框）
        style = ttk.Style()
        style.configure('Blue.TButton', foreground='#004080', borderwidth=2, relief='solid')
        ok_button = ttk.Button(button_frame, text="确定", command=error_dialog.destroy, style='Blue.TButton', width=10)
        ok_button.pack(side=tk.RIGHT)

    def rename_item(self, path):
        name = os.path.basename(path)
        parent = os.path.dirname(path)
        
        new_name = simpledialog.askstring("重命名", "输入新名称:", initialvalue=name)
        if new_name and new_name != name:
            new_path = os.path.join(parent, new_name)
            try:
                os.rename(path, new_path)
                self.refresh()
            except Exception as e:
                self.show_delete_error(e, path, move_to_recycle=False)

    def create_folder(self, event=None):
        """创建新文件夹"""
        folder_name = simpledialog.askstring("新建文件夹", "输入文件夹名称:", 
                                            initialvalue="新建文件夹")
        if not folder_name:
            return
            
        folder_path = os.path.join(self.current_dir, folder_name)
        
        # 检查是否已存在
        if os.path.exists(folder_path):
            messagebox.showerror("错误", f"'{folder_name}' 已存在")
            return
            
        try:
            os.makedirs(folder_path)
            self.add_to_history("create_folder", folder_path, None)
            self.refresh()
            # 高亮显示新创建的文件夹
            if os.path.exists(folder_path):
                self.tree.selection_set(folder_path)
                self.tree.focus(folder_path)
                self.tree.see(folder_path)
        except Exception as e:
            self.show_delete_error(e, folder_path, move_to_recycle=False)

    def refresh(self, event=None):
        if self.current_dir == "此电脑":
            self.show_computer_view()
        else:
            self.load_directory(self.current_dir)

    def update_status_bar(self, message=None):
        if message:
            self.status_bar.config(text=message)
        else:
            items = len(self.tree.get_children())
            folder = os.path.basename(self.current_dir) if self.current_dir != os.path.abspath(os.sep) else "根目录"
            selected = len(self.tree.selection())
            status = f"位置: {folder} | 项目数: {items}"
            if selected > 0:
                status += f" | 已选: {selected}"
            status += f" | 管理员权限: {'已获取' if self.is_admin else '未获取'}"
            self.status_bar.config(text=status)

    def on_select_press(self, event):
        """鼠标按下时开始选择"""
        self.start_x = event.x
        self.start_y = event.y
        self.dragging = True
        
        # 如果没有按下Shift或Control键，清除当前选择
        if not event.state & (0x0001 | 0x0004):  # Shift或Control键
            self.tree.selection_remove(self.tree.selection())
        
        # 创建选择矩形
        self.select_rect = self.select_canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            dash=(2,2), fill="", outline="blue", width=1, tags="selection_rect"
        )
    
    def on_select_drag(self, event):
        """鼠标拖动时更新选择"""
        if not self.dragging or self.select_rect is None:
            return
            
        cur_x = event.x
        cur_y = event.y
        
        # 更新选择矩形
        self.select_canvas.coords(self.select_rect, self.start_x, self.start_y, cur_x, cur_y)
        
        # 获取矩形内的项目
        rect_coords = (self.start_x, self.start_y, cur_x, cur_y)
        items_in_rect = self.get_items_in_rectangle(rect_coords)
        
        # 设置选择（添加而不是清除）
        self.tree.selection_set(items_in_rect)
        
        # 更新状态栏显示所选数量
        selected = len(items_in_rect)
        self.status_bar.config(text=f"已选择 {selected} 个项目")

    def on_select_release(self, event):
        """鼠标释放时结束选择"""
        if self.select_rect:
            self.select_canvas.delete(self.select_rect)
            self.select_rect = None
            self.dragging = False
        
        # 更新状态栏
        self.update_status_bar()

    def get_items_in_rectangle(self, coords):
        """获取选择矩形内的项目"""
        x1, y1, x2, y2 = coords
        if x1 > x2: x1, x2 = x2, x1
        if y1 > y2: y1, y2 = y2, y1
        
        items_in_rect = []
        
        # 获取所有可视项目
        children = self.tree.get_children()
        
        # 获取每个项目的边界框
        for item in children:
            bbox = self.tree.bbox(item)
            if bbox:
                # 计算项目在画布上的位置
                x, y, width, height = bbox
                
                # 转换为绝对位置
                item_x1 = x
                item_y1 = y
                item_x2 = x + width
                item_y2 = y + height
                
                # 检查项目是否在矩形内
                if (item_x1 < x2 and item_x2 > x1 and
                    item_y1 < y2 and item_y2 > y1):
                    items_in_rect.append(item)
        
        return items_in_rect

    def sort_column(self, column):
        """按列排序"""
        items = [(self.tree.set(child, column), child) for child in self.tree.get_children('')]
        
        # 特殊处理大小列（带单位）
        if column == "size":
            def size_key(item):
                value = item[0]
                if not value: return 0
                units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
                for unit, factor in units.items():
                    if unit in value:
                        num = float(value.split()[0])
                        return num * factor
                return 0
            items.sort(key=size_key)
        # 特殊处理修改日期列
        elif column == "modified":
            items.sort(key=lambda item: float(item[0]) if item[0] else 0)
        else:
            items.sort()
        
        # 重新插入已排序的项目
        for index, (value, child) in enumerate(items):
            self.tree.move(child, '', index)

if __name__ == "__main__":
    try:
        # 尝试以管理员权限运行
        if not shell.IsUserAnAdmin():
            shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=f'"{sys.argv[0]}"')
            sys.exit()
        else:
            app = FileExplorer()
            app.mainloop()
    except Exception as e:
        print(f"启动错误: {str(e)}")