import tkinter as tk
from tkinter import filedialog, messagebox
import sys  # 新增：用于获取命令行参数

class Notepad:
    def __init__(self, root):
        self.root = root
        self.root.title("记事本")
        self.root.geometry("800x600")
        
        self.text_area = tk.Text(self.root, wrap='word', undo=True)
        self.text_area.pack(expand=True, fill='both')
        
        self.create_menu()
        self.bind_shortcuts()
        
        self.current_file = None
        
        # 新增：检查命令行参数
        if len(sys.argv) > 1:  # 如果有命令行参数
            self.open_file_from_path(sys.argv[1])  # 尝试打开第一个参数指定的文件

    def open_file_from_path(self, file_path):  # 新增方法
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(tk.END, file.read())
            self.current_file = file_path
            self.root.title(f"简易记事本 - {file_path}")  # 在标题栏显示文件路径
        except Exception as e:
            messagebox.showerror("错误", f"打开文件失败: {str(e)}")

    # 其他方法保持不变...
    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="新建", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="打开", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="保存", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.exit_app)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="撤销", command=self.text_area.edit_undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="重做", command=self.text_area.edit_redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="剪切", command=self.cut_text, accelerator="Ctrl+X")
        edit_menu.add_command(label="复制", command=self.copy_text, accelerator="Ctrl+C")
        edit_menu.add_command(label="粘贴", command=self.paste_text, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="全选", command=self.select_all, accelerator="Ctrl+A")
        menubar.add_cascade(label="编辑", menu=edit_menu)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        self.root.config(menu=menubar)

    def bind_shortcuts(self):
        self.root.bind('<Control-n>', lambda event: self.new_file())
        self.root.bind('<Control-o>', lambda event: self.open_file())
        self.root.bind('<Control-s>', lambda event: self.save_file())
        self.root.bind('<Control-x>', lambda event: self.cut_text())
        self.root.bind('<Control-c>', lambda event: self.copy_text())
        self.root.bind('<Control-v>', lambda event: self.paste_text())
        self.root.bind('<Control-a>', lambda event: self.select_all())

    def new_file(self):
        self.text_area.delete(1.0, tk.END)
        self.current_file = None
        self.root.title("简易记事本")

    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if file_path:
            self.open_file_from_path(file_path)

    def save_file(self):
        if self.current_file:
            try:
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(self.text_area.get(1.0, tk.END))
            except Exception as e:
                messagebox.showerror("错误", f"保存文件失败: {str(e)}")
        else:
            self.save_as_file()

    def save_as_file(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(self.text_area.get(1.0, tk.END))
                self.current_file = file_path
                self.root.title(f"简易记事本 - {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件失败: {str(e)}")

    def cut_text(self):
        self.text_area.event_generate("<<Cut>>")

    def copy_text(self):
        self.text_area.event_generate("<<Copy>>")

    def paste_text(self):
        self.text_area.event_generate("<<Paste>>")

    def select_all(self):
        self.text_area.tag_add('sel', '1.0', 'end')

    def show_about(self):
        messagebox.showinfo("关于", "简易记事本\n版本 1.0\n2025年")

    def exit_app(self):
        if messagebox.askokcancel("退出", "确定要退出吗？"):
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = Notepad(root)
    root.mainloop()
