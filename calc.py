import sys
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QLabel,
                             QMessageBox)

class DumbCalcLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("废物计算器")
        self.setGeometry(400, 300, 400, 120)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # 输入算式（仅供娱乐）
        layout.addWidget(QLabel("输入算式："))
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("")
        layout.addWidget(self.input_edit)
        
        # 按钮：打开系统计算器
        self.btn = QPushButton("计算（别指望算）")
        self.btn.clicked.connect(self.open_calc)
        layout.addWidget(self.btn)
    
    def open_calc(self):
        expr = self.input_edit.text().strip()
        if expr:
            # 嘲讽一下：你输了算式但老子不算
            print(f"你输了：{expr}，但老子就是不算，气不气？")
        try:
            subprocess.Popen("calc.exe")
        except Exception as e:
            QMessageBox.critical(self, "操", f"打不开计算器，你系统烂了\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DumbCalcLauncher()
    win.show()
    sys.exit(app.exec())
