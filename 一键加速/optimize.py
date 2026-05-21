import sys
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QProgressBar,
                             QMessageBox, QTextEdit)
from PyQt6.QtCore import QTimer, Qt

class FakeOptimizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("系统优化器 Pro Max - 纯属放屁版")
        self.setGeometry(400, 300, 500, 300)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # 标题
        title = QLabel("🚀 一键加速 · 垃圾清理 · 智商税 🚀")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # 进度条（永远走不到100%）
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(QLabel("优化进度（假的）："))
        layout.addWidget(self.progress)
        
        # 废话输出区
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("这里会显示一堆废话...")
        layout.addWidget(QLabel("实时日志（编的）："))
        layout.addWidget(self.log)
        
        # 按钮
        self.optimize_btn = QPushButton("⚡ 一键优化 ⚡")
        self.optimize_btn.clicked.connect(self.start_fake_optimization)
        layout.addWidget(self.optimize_btn)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.fake_step)
        self.step = 0
        self.fake_messages = [
            "正在扫描垃圾文件... 发现 1.2TB 无用缓存",
            "清理注册表... 删除了 9999 条无效键值",
            "关闭后台进程... 停止了 Windows 核心服务（开玩笑的）",
            "优化内存... 释放了 32GB RAM（你电脑有那么多吗）",
            "整理磁盘碎片... 把 C 盘整理成了瑞士奶酪",
            "更新驱动程序... 把你的显卡驱动换成了 1995 年版",
            "检测到 847 个病毒，已全部隔离（其实没装杀毒）",
            "清理浏览器历史... 包括你昨晚看的那些",
            "优化启动项... 删除了 bootmgr，下次开机可能蓝屏",
            "深度清理完成！节省了 50GB 空间（实际没动）"
        ]
    
    def start_fake_optimization(self):
        self.optimize_btn.setEnabled(False)
        self.step = 0
        self.progress.setValue(0)
        self.log.clear()
        self.timer.start(300)  # 每0.3秒走一步
    
    def fake_step(self):
        if self.step < len(self.fake_messages):
            msg = self.fake_messages[self.step]
            self.log.append(f"[{self.step+1}] {msg}")
            # 进度条假装增加，但永远不到100%（最大到95%就停）
            val = int((self.step + 1) / len(self.fake_messages) * 95)
            self.progress.setValue(val)
            self.step += 1
        else:
            self.timer.stop()
            # 弹窗说完成了，但进度条永远95%
            self.progress.setValue(95)
            QMessageBox.information(self, "优化完成", 
                "恭喜！你的电脑已经达到巅峰性能！\n"
                "（其实什么都没变，但你觉得快了就是快了）\n"
                "建议每天点一次，智商税续费成功。")
            self.optimize_btn.setEnabled(True)
            # 再加点废话
            self.log.append("\n✨ 优化完成！系统性能提升 999% ✨")
            self.log.append("💸 感谢使用，你的心理作用是最好的优化 💸")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FakeOptimizer()
    win.show()
    sys.exit(app.exec())
