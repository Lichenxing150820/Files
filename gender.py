import sys
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QPushButton, 
                             QMessageBox, QGroupBox, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt

class ParentGenderPredictor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("父母性别预测器™ - 科学废柴版")
        self.setGeometry(300, 200, 500, 400)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # 标题
        title = QLabel("⚛️ 父母性别预测器 ⚛️")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        subtitle = QLabel("基于量子伪随机算法 + 你无聊的回答")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # 测试题1
        q1_group = QGroupBox("问题1：你早上更喜欢哪种声音？")
        q1_layout = QVBoxLayout()
        self.q1_buttons = QButtonGroup()
        q1_opts = ["公鸡打鸣", "闹钟狂响", "老妈怒吼", "什么都不喜欢"]
        self.q1_radios = []
        for i, text in enumerate(q1_opts):
            rb = QRadioButton(text)
            q1_layout.addWidget(rb)
            self.q1_radios.append(rb)
            self.q1_buttons.addButton(rb, i)
        q1_group.setLayout(q1_layout)
        layout.addWidget(q1_group)
        
        # 测试题2
        q2_group = QGroupBox("问题2：你选数字的偏好？")
        q2_layout = QHBoxLayout()
        self.q2_combo = QComboBox()
        self.q2_combo.addItems(["7（幸运）", "42（宇宙答案）", "3（三体）", "0（虚无）"])
        q2_layout.addWidget(QLabel("你的数字："))
        q2_layout.addWidget(self.q2_combo)
        q2_group.setLayout(q2_layout)
        layout.addWidget(q2_group)
        
        # 测试题3
        q3_group = QGroupBox("问题3：你觉得哪种动物最聪明？")
        q3_layout = QVBoxLayout()
        self.q3_buttons = QButtonGroup()
        q3_opts = ["海豚", "章鱼", "乌鸦", "你家的猫（其实懒得理你）"]
        self.q3_radios = []
        for i, text in enumerate(q3_opts):
            rb = QRadioButton(text)
            q3_layout.addWidget(rb)
            self.q3_radios.append(rb)
            self.q3_buttons.addButton(rb, i)
        q3_group.setLayout(q3_layout)
        layout.addWidget(q3_group)
        
        # 预测按钮
        self.predict_btn = QPushButton("🔮 科学预测父母性别 🔮")
        self.predict_btn.clicked.connect(self.predict)
        layout.addWidget(self.predict_btn)
        
        # 结果展示区（废话）
        self.result_label = QLabel("点击按钮，见证科学奇迹")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("border: 1px solid gray; padding: 10px;")
        layout.addWidget(self.result_label)
        
        # 随机种子初始化
        random.seed()
    
    def predict(self):
        # 检查是否回答了所有问题（其实没答也能预测，但装个样子）
        if not any(rb.isChecked() for rb in self.q1_radios):
            QMessageBox.warning(self, "操", "问题1好歹选一个，你他妈犹豫啥？")
            return
        if not any(rb.isChecked() for rb in self.q3_radios):
            QMessageBox.warning(self, "操", "问题3选个动物会死？")
            return
        
        # 收集用户选择作为“算法输入”（其实卵用没有）
        q1_val = next(i for i, rb in enumerate(self.q1_radios) if rb.isChecked())
        q2_val = self.q2_combo.currentIndex()
        q3_val = next(i for i, rb in enumerate(self.q3_radios) if rb.isChecked())
        
        # 伪科学加权和（看起来像回事）
        score = (q1_val * 7 + q2_val * 13 + q3_val * 19) % 100
        
        # 随机扰动 + 基于系统时间（真科学是假科学）
        r = random.Random()
        r.seed(score + int(__import__('time').time() * 1000) % 1000)
        
        # 预测父亲性别（选项：男、女、武装直升机、沃尔玛购物袋）
        father_options = ["男", "女", "武装直升机", "沃尔玛购物袋", "蟑螂", "AI生成的幻觉"]
        father_gender = r.choice(father_options)
        
        # 预测母亲性别（独立随机）
        mother_options = ["女", "男", "亚马逊纸箱", "WiFi信号", "你妈是你妈（废话）", "薛定谔的猫（同时是男女）"]
        mother_gender = r.choice(mother_options)
        
        # 额外“科学解释”
        explanations = [
            "基于你选择的数字频率与太阳黑子活动相关性分析得出。",
            "经过1024次神经网络迭代（其实是掷骰子）。",
            "量子纠缠告诉你：别当真。",
            "大数据显示，你的答案与南极企鹅迁徙路线吻合。",
            "算法来自斯坦福废柴实验室，准确率约0%。"
        ]
        explanation = r.choice(explanations)
        
        result_text = f"【科学预测结果】\n\n👨 父亲性别：{father_gender}\n👩 母亲性别：{mother_gender}\n\n🔬 科学依据：{explanation}\n\n⚠️ 警告：本结果纯属扯淡，如有雷同纯属你瞎。"
        self.result_label.setText(result_text)
        
        # 额外弹窗嘲讽
        if father_gender == "男" and mother_gender == "女":
            QMessageBox.information(self, "恭喜", "卧槽，居然预测对了？其实蒙的，别得意。")
        else:
            QMessageBox.information(self, "科学已死", f"看到了吗？你爸是{father_gender}，你妈是{mother_gender}。满意了？")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ParentGenderPredictor()
    win.show()
    sys.exit(app.exec())
