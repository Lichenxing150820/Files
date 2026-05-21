import tkinter as tk
from tkinter import scrolledtext

# 转换函数
def convert_to_binary():
    # 获取输入框的内容
    input_str = entry.get()
    
    # 将每个字符转换为8位二进制，并拼接结果
    binary_code = ''.join(format(ord(char), '08b') for char in input_str)
    
    # 清空文本框并插入新的二进制机器码
    result_text.delete(1.0, tk.END)  # 清空内容
    result_text.insert(tk.END, f"二进制机器码:\n{binary_code}")  # 插入新内容

# 创建主窗口
root = tk.Tk()
root.title("字符转二进制机器码")
root.geometry("500x300")

# 创建输入框
entry = tk.Entry(root, width=50)
entry.pack(pady=10)

# 创建转换按钮
convert_button = tk.Button(root, text="转换", command=convert_to_binary)
convert_button.pack(pady=10)

# 创建可滚动的文本框
result_text = scrolledtext.ScrolledText(root, width=60, height=10, wrap=tk.WORD)
result_text.pack(pady=10)

# 运行主循环
root.mainloop()
