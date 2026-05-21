import tkinter as tk
from tkinter import scrolledtext

class CalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("计算机")

        self.prompt_label = tk.Label(root, text="请输入算式")
        self.prompt_label.pack(pady=10)

        self.entry = tk.Entry(root, width=40)
        self.entry.pack(pady=10)

        # 绑定回车键事件
        self.entry.bind("<Return>", lambda event: self.calculate())

        self.calculate_button = tk.Button(root, text="计算", command=self.calculate)
        self.calculate_button.pack(pady=10)

        # 使用 ScrolledText 组件来显示结果，并带有滚动条
        self.result_text = scrolledtext.ScrolledText(root, width=40, height=10, wrap=tk.WORD)
        self.result_text.pack(pady=10)

        self.exit_button = tk.Button(root, text="退出", command=root.quit)
        self.exit_button.pack(pady=10)

    def safe_eval(self, expression):
        allowed_chars = set("0123456789+-*/%(). ")
        if all(char in allowed_chars for char in expression):
            try:
                result = eval(expression)
                return result
            except Exception as e:
                return f"Error in expression: {e}"
        else:
            return "Invalid characters in expression."

    def calculate(self):
        expression = self.entry.get()
        result = self.safe_eval(expression)
        
        # 清空之前的结果
        self.result_text.delete(1.0, tk.END)
        
        # 在 Text 组件中插入新结果
        self.result_text.insert(tk.END, f"表达式: {expression}\n结果: {result}\n\n")
        
        # 自动滚动到最底部
        self.result_text.yview(tk.END)

def main():
    root = tk.Tk()
    app = CalculatorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
