import random
import tkinter as tk

root=tk.Tk()

entry=tk.Entry(root)
label=tk.Label(root,text='输入随机数范围，格式：（起始 结束）如20 100')
button=tk.Button(root,text='随机',command=lambda: label.config(text=random.randint(int(entry.get().split()[0]),int(entry.get().split()[1]))))
button.pack()
entry.pack()
label.pack()

root.mainloop()