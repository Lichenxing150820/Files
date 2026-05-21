import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from threading import Thread
import time
import ctypes
from ctypes import wintypes
import io
import psutil


class CombinedFileGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件与内存数据生成工具")
        self.root.geometry("700x650")  # 加大窗口以适应新功能

        # 完整的单位分类和换算表
        self.unit_categories = {
            "基本单位": {
                "bit": 0.125,
                "nibble": 0.5,
                "B": 1,
                "KB": 1024,
                "MB": 1024 ** 2,
                "GB": 1024 ** 3,
                "TB": 1024 ** 4,
                "PB": 1024 ** 5,
                "EB": 1024 ** 6,
                "ZB": 1024 ** 7,
                "YB": 1024 ** 8,
                "BB": 1024 ** 9,   # Brontobyte
                "NB": 1024 ** 10,  # Nonabyte
                "DB": 1024 ** 11,  # Doggabyte
                "CB": 1024 ** 12,  # Corybyte
            },
            "二进制单位(IEC)": {
                "KiB": 1024,
                "MiB": 1024 ** 2,
                "GiB": 1024 ** 3,
                "TiB": 1024 ** 4,
                "PiB": 1024 ** 5,
                "EiB": 1024 ** 6,
                "ZiB": 1024 ** 7,
                "YiB": 1024 ** 8,
            },
            "十进制单位(SI)": {
                "kB": 1000,
                "MB (SI)": 1000 ** 2,
                "GB (SI)": 1000 ** 3,
                "TB (SI)": 1000 ** 4,
                "PB (SI)": 1000 ** 5,
                "EB (SI)": 1000 ** 6,
                "ZB (SI)": 1000 ** 7,
                "YB (SI)": 1000 ** 8,
            },
            "计算机单位": {
                "word": 2,
                "dword": 4,
                "qword": 8,
                "block": 512,
                "sector": 4096,
                "page": 4096,
                "cluster": 4096,
            },
            "存储介质": {
                "Floppy": 1474560,
                "CD": 737280000,
                "DVD": 4707319808,
                "BD": 25025314816,
                "HDD (1TB)": 1024 ** 4,
                "SSD (512GB)": 512 * 1024 ** 3,
            },
            "趣味单位": {
                "Human Genome": 3 * 1024 ** 3,
                "Library of Congress": 20 * 1024 ** 3,
                "All Printed Books": 200 * 1024 ** 3,
                "Internet Archive": 50 * 1024 ** 6,
            }
        }

        # 合并所有单位到一个字典
        self.unit_map = {}
        for category in self.unit_categories.values():
            self.unit_map.update(category)

        # 控件变量
        self.size_var = tk.DoubleVar(value=1)
        self.unit_var = tk.StringVar(value="MB")
        self.unit_category_var = tk.StringVar(value="基本单位")
        self.path_var = tk.StringVar()
        self.path_var.set(self.get_desktop_path())
        self.progress_var = tk.DoubleVar()
        self.remaining_time_var = tk.StringVar(value="预计剩余时间: --")
        self.running = False
        self.paused = False
        self.bytes_written = 0
        self.total_bytes = 0
        self.start_time = 0
        self.memory_file = None
        self.operation_var = tk.StringVar(value="文件生成")

        # 任务栏进度支持
        self.taskbar_supported = False
        self.setup_taskbar_support()

        # 布局
        self.setup_ui()

    def setup_taskbar_support(self):
        """初始化任务栏进度支持"""
        try:
            if hasattr(ctypes.windll.shell32, 'SetCurrentProcessExplicitAppUserModelID'):
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CombinedFileGenerator.Python")
                self.taskbar_supported = True
        except:
            self.taskbar_supported = False

    def update_taskbar_progress(self, progress):
        """更新任务栏进度"""
        if not self.taskbar_supported:
            return

        try:
            progress = max(0, min(100, int(progress)))
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if self.paused:
                ctypes.windll.shell32.SetProgressState(hwnd, 2)  # 暂停(黄色)
            else:
                ctypes.windll.shell32.SetProgressState(hwnd, 1)  # 正常(绿色)
            ctypes.windll.shell32.SetProgressValue(hwnd, progress, 100)
        except Exception as e:
            print(f"更新任务栏进度失败: {e}")
            self.taskbar_supported = False

    def get_desktop_path(self):
        """获取桌面路径"""
        try:
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(0, 0x0010, 0, 0, buf)
            return os.path.join(buf.value, "generated_file.dat")
        except:
            return os.path.join(os.path.expanduser("~"), "Desktop", "generated_file.dat")

    def setup_ui(self):
        # 操作选择
        operation_frame = ttk.Frame(self.root)
        operation_frame.pack(fill=tk.X, pady=10)
        tk.Label(operation_frame, text="选择操作:").pack(side=tk.LEFT)
        operation_options = ["文件生成", "内存数据生成"]
        operation_menu = ttk.Combobox(
            operation_frame,
            textvariable=self.operation_var,
            values=operation_options,
            state="readonly"
        )
        operation_menu.pack(side=tk.LEFT)
        operation_menu.bind("<<ComboboxSelected>>", self.update_path_visibility)

        # 单位类型选择
        category_frame = ttk.Frame(self.root)
        category_frame.pack(fill=tk.X, pady=5)
        tk.Label(category_frame, text="单位类型:").pack(side=tk.LEFT)
        category_combo = ttk.Combobox(
            category_frame,
            textvariable=self.unit_category_var,
            values=list(self.unit_categories.keys()),
            state="readonly",
            width=15
        )
        category_combo.pack(side=tk.LEFT, padx=5)
        category_combo.bind("<<ComboboxSelected>>", self.update_unit_options)

        # 文件大小设置
        size_frame = ttk.Frame(self.root)
        size_frame.pack(fill=tk.X, pady=5)
        tk.Label(size_frame, text="数据大小:").pack(side=tk.LEFT)
        size_entry = ttk.Entry(size_frame, textvariable=self.size_var, width=10)
        size_entry.pack(side=tk.LEFT, padx=5)
        size_entry.bind('<KeyRelease>', lambda e: self.validate_size())
        
        # 单位选择框
        self.unit_combo = ttk.Combobox(
            size_frame,
            textvariable=self.unit_var,
            values=self.get_current_category_units(),
            width=12,
            state="readonly"
        )
        self.unit_combo.pack(side=tk.LEFT, padx=5)
        
        # 添加单位转换表按钮
        tk.Button(size_frame, text="单位转换表", command=self.show_conversion_table).pack(side=tk.LEFT, padx=10)

        # 存储路径选择
        self.path_frame = ttk.Frame(self.root)
        self.path_frame.pack(fill=tk.X, pady=5)
        tk.Label(self.path_frame, text="存储路径:").pack(side=tk.LEFT)
        path_entry = tk.Entry(self.path_frame, textvariable=self.path_var, width=50)
        path_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(self.path_frame, text="浏览...", command=self.select_path).pack(side=tk.LEFT, padx=5)

        # 进度条
        ttk.Progressbar(self.root, variable=self.progress_var, maximum=100).pack(
            fill=tk.X, padx=10, pady=10)

        # 状态信息
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=10)
        self.status_label = tk.Label(progress_frame, text="就绪", fg="blue", anchor="w")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(progress_frame, textvariable=self.remaining_time_var, anchor="e").pack(side=tk.RIGHT)

        # 操作按钮
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        self.start_btn = tk.Button(button_frame, text="开始生成", command=self.start_generation)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.pause_btn = tk.Button(button_frame, text="暂停", command=self.pause_generation, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        self.resume_btn = tk.Button(button_frame, text="继续生成", command=self.resume_generation, state=tk.DISABLED)
        self.resume_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="退出", command=self.safe_exit).pack(side=tk.LEFT, padx=5)

        # 详细信息
        info_frame = tk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        self.speed_label = tk.Label(info_frame, text="速度: --", anchor="w")
        self.speed_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.bytes_label = tk.Label(info_frame, text="已写入: 0 / 0", anchor="e")
        self.bytes_label.pack(side=tk.RIGHT)

        # 初始根据选择设置路径框显示
        self.update_path_visibility()

    def get_current_category_units(self):
        """获取当前分类下的所有单位"""
        return list(self.unit_categories[self.unit_category_var.get()].keys())

    def update_unit_options(self, event=None):
        """更新单位选择框的选项"""
        current_category = self.unit_category_var.get()
        units = self.get_current_category_units()
        self.unit_combo['values'] = units
        if self.unit_var.get() not in units:
            self.unit_var.set(units[0])  # 如果当前单位不在新分类中，设置为第一个单位

    def show_conversion_table(self):
        """显示单位转换表"""
        size = self.size_var.get()
        selected_unit = self.unit_var.get()
        
        if size <= 0:
            messagebox.showerror("错误", "请输入有效的正数大小")
            return
        
        try:
            bytes_value = size * self.unit_map[selected_unit]
        except KeyError:
            messagebox.showerror("错误", f"无效的单位: {selected_unit}")
            return
        
        # 创建新窗口
        table_window = tk.Toplevel(self.root)
        table_window.title(f"{size} {selected_unit} 单位转换表")
        table_window.geometry("550x450")
        
        # 创建文本框
        text_frame = tk.Frame(table_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar = tk.Scrollbar(text_frame, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加单位转换信息
        text.insert(tk.END, f"{size} {selected_unit} 等于:\n\n")
        text.insert(tk.END, "="*60 + "\n")
        
        # 按分类显示单位转换
        for category, units in self.unit_categories.items():
            text.insert(tk.END, f"\n【{category}】\n")
            for unit, value in units.items():
                converted = bytes_value / value
                text.insert(tk.END, f"{converted:,.15f} {unit}\n")  # 显示所有单位，包括小于1的值
        
        text.insert(tk.END, "\n" + "="*60 + "\n")
        
        # 禁用编辑
        text.config(state=tk.DISABLED)
        
        # 添加关闭按钮
        button_frame = tk.Frame(table_window)
        button_frame.pack(fill=tk.X, pady=5)
        tk.Button(button_frame, text="关闭", command=table_window.destroy).pack()

    def update_path_visibility(self, event=None):
        if self.operation_var.get() == "内存数据生成":
            self.path_frame.pack_forget()
        else:
            self.path_frame.pack(fill=tk.X, pady=5)

    def validate_size(self):
        """验证文件大小输入"""
        if self.size_var.get():
            try:
                size = float(self.size_var.get())
                if size <= 0:
                    raise ValueError
            except:
                self.size_var.set(1)
                messagebox.showerror("错误", "请输入有效的正数")

    def select_path(self):
        """选择保存路径"""
        initial_dir = os.path.dirname(self.path_var.get()) if self.path_var.get() else None
        path = filedialog.asksaveasfilename(
            title="选择保存位置",
            filetypes=[("All Files", "*.*")],
            defaultextension=".dat",
            initialdir=initial_dir
        )
        if path:
            self.path_var.set(path)

    def check_disk_space(self, path, required_bytes):
        """检查磁盘空间"""
        try:
            # Windows系统
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(os.path.dirname(path)),
                None, None, ctypes.pointer(free_bytes))
            if free_bytes.value < required_bytes:
                needed = (required_bytes - free_bytes.value) / self.unit_map["GB"]
                messagebox.showerror("错误", f"磁盘空间不足！还需要 {needed:.2f} GB")
                return False
            return True
        except:
            try:
                # Unix系统
                stat = os.statvfs(os.path.dirname(path))
                free_space = stat.f_frsize * stat.f_bavail
                if free_space < required_bytes:
                    needed = (required_bytes - free_space) / self.unit_map["GB"]
                    messagebox.showerror("错误", f"磁盘空间不足！还需要 {needed:.2f} GB")
                    return False
                return True
            except:
                return True

    def check_memory_space(self, required_bytes):
        """检查系统内存是否足够"""
        virtual_memory = psutil.virtual_memory()
        available_memory = virtual_memory.available
        if available_memory < required_bytes:
            needed = (required_bytes - available_memory) / self.unit_map["GB"]
            messagebox.showerror("错误", f"内存不足！还需要 {needed:.2f} GB")
            return False
        return True

    def start_generation(self):
        """开始生成文件或内存数据"""
        if self.running:
            return
        size = self.size_var.get()
        unit = self.unit_var.get()
        path = self.path_var.get()
        operation = self.operation_var.get()

        # 验证输入
        if size <= 0:
            messagebox.showerror("错误", "数据大小必须大于0！")
            return
        if unit not in self.unit_map:
            messagebox.showerror("错误", f"无效的单位: {unit}")
            return

        # 计算总字节数
        try:
            self.total_bytes = int(size * self.unit_map[unit])
        except OverflowError:
            messagebox.showerror("错误", "数据大小超出系统限制！")
            return

        if operation == "文件生成":
            if not path:
                messagebox.showerror("错误", "请选择存储路径！")
                return
            if not self.check_disk_space(path, self.total_bytes):
                return
            confirm_msg = f"将生成 {size} {unit} ({self.total_bytes / self.unit_map['GB']:.2f}GB) 的文件到:\n{path}"
        else:
            if not self.check_memory_space(self.total_bytes):
                return
            confirm_msg = f"将生成 {size} {unit} ({self.total_bytes / self.unit_map['GB']:.2f}GB) 的数据到内存。"

        if not messagebox.askyesno("确认", confirm_msg + "\n\n继续吗？"):
            return

        # 重置状态
        self.bytes_written = 0
        self.progress_var.set(0)
        self.start_time = time.time()
        self.update_taskbar_progress(0)

        # 启动生成线程
        self.running = True
        self.paused = False
        self.update_button_states()
        if operation == "文件生成":
            Thread(target=self.generate_file, args=(path, self.total_bytes), daemon=True).start()
        else:
            self.memory_file = io.BytesIO()
            Thread(target=self.generate_data, args=(self.total_bytes,), daemon=True).start()

    def pause_generation(self):
        """暂停生成"""
        if self.running and not self.paused:
            self.paused = True
            self.running = False
            self.update_button_states()
            self.status_label.config(text="已暂停", fg="orange")
            self.update_taskbar_progress(self.progress_var.get())

    def resume_generation(self):
        """继续生成"""
        if not self.paused:
            return
        operation = self.operation_var.get()
        if operation == "文件生成":
            path = self.path_var.get()
            if not os.path.exists(path):
                messagebox.showerror("错误", "目标文件不存在，无法继续生成！")
                return
            try:
                current_size = os.path.getsize(path)
                if current_size > self.total_bytes:
                    messagebox.showerror("错误", "文件已超过目标大小，无法继续生成！")
                    return
                self.bytes_written = current_size
            except Exception as e:
                messagebox.showerror("错误", f"无法获取文件信息:\n{str(e)}")
                return
        else:
            if self.memory_file is None:
                messagebox.showerror("错误", "内存数据文件不存在，无法继续生成！")
                return
            self.bytes_written = len(self.memory_file.getvalue())
        self.running = True
        self.paused = False
        self.start_time = time.time()
        self.bytes_written / (self.total_bytes / (time.time() - self.start_time)) if self.bytes_written > 0 else 0
        self.update_button_states()
        if operation == "文件生成":
            Thread(target=self.generate_file, args=(self.path_var.get(), self.total_bytes), daemon=True).start()
        else:
            Thread(target=self.generate_data, args=(self.total_bytes,), daemon=True).start()

    def update_button_states(self):
        """更新按钮状态"""
        if self.running:
            self.start_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            self.resume_btn.config(state=tk.DISABLED)
        elif self.paused:
            self.start_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.DISABLED)
            self.resume_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
            self.resume_btn.config(state=tk.DISABLED)

    def calculate_remaining_time(self):
        """计算剩余时间"""
        if self.bytes_written <= 0 or self.bytes_written >= self.total_bytes:
            return "--"
        elapsed_time = time.time() - self.start_time
        if elapsed_time <= 0:
            return "--"
        speed = self.bytes_written / elapsed_time
        remaining_bytes = self.total_bytes - self.bytes_written
        remaining_seconds = remaining_bytes / speed if speed > 0 else 0

        if remaining_seconds < 60:
            return f"{int(remaining_seconds)}秒"
        elif remaining_seconds < 3600:
            return f"{int(remaining_seconds / 60)}分{int(remaining_seconds % 60)}秒"
        else:
            hours = int(remaining_seconds / 3600)
            minutes = int((remaining_seconds % 3600) / 60)
            return f"{hours}小时{minutes}分"

    def format_speed(self, speed):
        """格式化速度显示"""
        # 找出最适合的单位
        sorted_units = sorted(self.unit_map.items(), key=lambda x: x[1], reverse=True)
        for unit, value in sorted_units:
            if speed >= value:
                return f"{speed / value:.2f} {unit}/s"
        return f"{speed:.2f} B/s"

    def generate_file(self, path, total_bytes):
        """生成文件"""
        chunk_size = 1024 * 1024 * 10  # 10MB每次
        chunk = os.urandom(chunk_size)
        try:
            mode = 'ab' if self.bytes_written > 0 else 'wb'
            with open(path, mode) as f:
                while self.bytes_written < total_bytes and self.running:
                    write_size = min(chunk_size, total_bytes - self.bytes_written)
                    f.write(chunk[:write_size])
                    self.bytes_written += write_size
                    # 更新进度
                    progress = (self.bytes_written / total_bytes) * 100
                    elapsed_time = time.time() - self.start_time
                    speed = self.bytes_written / elapsed_time if elapsed_time > 0 else 0
                    remaining_time = self.calculate_remaining_time()

                    self.root.after(0, lambda: self.update_progress(progress, speed, remaining_time))
        except Exception as e:
            messagebox.showerror("错误", f"生成文件时出错: {str(e)}")
        finally:
            self.running = False
            self.paused = False
            self.update_button_states()
            if self.bytes_written >= total_bytes:
                self.root.after(0, lambda: self.update_progress(100, 0, "--"))
                messagebox.showinfo("完成", "文件生成完成！")

    def generate_data(self, total_bytes):
        """生成内存数据"""
        chunk_size = 1024 * 1024 * 10  # 10MB每次
        chunk = os.urandom(chunk_size)
        try:
            while self.bytes_written < total_bytes and self.running:
                write_size = min(chunk_size, total_bytes - self.bytes_written)
                self.memory_file.write(chunk[:write_size])
                self.bytes_written += write_size
                # 更新进度
                progress = (self.bytes_written / total_bytes) * 100
                elapsed_time = time.time() - self.start_time
                speed = self.bytes_written / elapsed_time if elapsed_time > 0 else 0
                remaining_time = self.calculate_remaining_time()

                self.root.after(0, lambda: self.update_progress(progress, speed, remaining_time))
        except Exception as e:
            messagebox.showerror("错误", f"生成内存数据时出错: {str(e)}")
        finally:
            self.running = False
            self.paused = False
            self.update_button_states()
            if self.bytes_written >= total_bytes:
                self.root.after(0, lambda: self.update_progress(100, 0, "--"))
                messagebox.showinfo("完成", "内存数据生成完成！")

    def update_progress(self, progress, speed, remaining_time):
        """更新进度信息"""
        self.progress_var.set(progress)
        self.remaining_time_var.set(f"预计剩余时间: {remaining_time}")
        self.speed_label.config(text=f"速度: {self.format_speed(speed)}")
        self.bytes_label.config(text=f"已写入: {self.bytes_written} / {self.total_bytes}")
        self.update_taskbar_progress(progress)
        if progress >= 100:
            self.status_label.config(text="完成", fg="green")
        elif self.paused:
            self.status_label.config(text="已暂停", fg="orange")
        else:
            self.status_label.config(text="正在生成...", fg="blue")

    def safe_exit(self):
        """安全退出程序"""
        if self.running:
            if not messagebox.askyesno("确认", "生成任务正在进行中，确定要退出吗？"):
                return
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CombinedFileGeneratorApp(root)
    root.mainloop()