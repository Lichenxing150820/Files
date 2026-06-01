import sys
import json
import random
import math
from datetime import datetime
from typing import List, Optional, Tuple

from PyQt6.QtCore import (
    Qt, QTimer, QElapsedTimer, QEasingCurve, QPropertyAnimation, pyqtProperty, QSettings
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, QIcon, QAction, QPixmap, QPalette
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QDialog, QLineEdit, QScrollArea, QMessageBox,
    QFileDialog, QListWidget, QListWidgetItem, QTabWidget, QColorDialog,
    QSizePolicy, QSpacerItem, QFrame, QStyle, QStyleFactory
)

# -------------------- 数据类 --------------------
class Prize:
    def __init__(self, name: str, color: QColor, probability: float):
        self.name = name
        self.color = color
        self.probability = probability  # 0.0 ~ 1.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "color": self.color.name(),  # 如 "#RRGGBB"
            "probability": self.probability
        }

    @staticmethod
    def from_dict(d: dict) -> "Prize":
        return Prize(
            name=d["name"],
            color=QColor(d["color"]),
            probability=float(d["probability"])
        )


class LotteryConfig:
    def __init__(self, name: str, prizes: List[Prize], created_time: str = ""):
        self.name = name
        self.prizes = prizes
        self.created_time = created_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "prizes": [p.to_dict() for p in self.prizes],
            "created_time": self.created_time
        }

    @staticmethod
    def from_dict(d: dict) -> "LotteryConfig":
        prizes = [Prize.from_dict(p) for p in d["prizes"]]
        return LotteryConfig(
            name=d["name"],
            prizes=prizes,
            created_time=d.get("created_time", "")
        )


# -------------------- 全局常量与工具 --------------------
COMMON_COLORS = [
    ("黑色", QColor(0, 0, 0)),
    ("白色", QColor(255, 255, 255)),
    ("红色", QColor(255, 0, 0)),
    ("绿色", QColor(0, 255, 0)),
    ("蓝色", QColor(0, 0, 255)),
    ("黄色", QColor(255, 255, 0)),
    ("青色", QColor(0, 255, 255)),
    ("品红", QColor(255, 0, 255)),
    ("灰色", QColor(128, 128, 128)),
    ("橙色", QColor(255, 165, 0)),
    ("紫色", QColor(128, 0, 128)),
    ("棕色", QColor(165, 42, 42)),
]


def weighted_choice(prizes: List[Prize]) -> Prize:
    """根据概率加权随机选择一个奖品"""
    r = random.random()
    cumulative = 0.0
    for prize in prizes:
        cumulative += prize.probability
        if r <= cumulative:
            return prize
    return prizes[-1]  # 兜底


# -------------------- 设置对话框 --------------------
class SetupDialog(QDialog):
    def __init__(self, config: Optional[LotteryConfig] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("抽奖设置")
        self.resize(550, 500)
        self.current_config = config

        # 动态行控件列表：[(name_edit, color_btn, prob_edit, row_widget)]
        self.rows: List[Tuple[QLineEdit, QPushButton, QLineEdit, QWidget]] = []

        self._init_ui()
        if config:
            self._load_config(config)
        else:
            # 默认添加两个空行
            self._add_row()
            self._add_row()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 方案名称
        name_layout = QHBoxLayout()
        name_label = QLabel("方案名称：")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入抽奖方案名称")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # 奖品列表标题
        header = QHBoxLayout()
        header.addWidget(QLabel("奖品名称"))
        header.addWidget(QLabel("颜色"))
        header.addWidget(QLabel("概率(%)"))
        header.addWidget(QLabel("操作"))
        layout.addLayout(header)

        # 可滚动的奖品区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll)

        # 添加奖品按钮
        add_btn = QPushButton("＋ 添加奖品")
        add_btn.clicked.connect(lambda: self._add_row())
        layout.addWidget(add_btn)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.apply_btn = QPushButton("应用")
        self.cancel_btn = QPushButton("取消")
        self.apply_btn.setFixedWidth(100)
        self.cancel_btn.setFixedWidth(100)
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.apply_btn.clicked.connect(self._on_apply)
        self.cancel_btn.clicked.connect(self.reject)

        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #aaa;
                border-radius: 4px;
                background: #e0e0e0;
            }
            QPushButton:hover {
                background: #d0d0d0;
            }
            QLineEdit {
                padding: 4px;
                border: 1px solid #aaa;
                border-radius: 3px;
            }
        """)

    def _add_row(self, name="", color=QColor(200, 200, 200), prob=""):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 2, 0, 2)

        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("奖品名")
        name_edit.setFixedWidth(120)

        color_btn = QPushButton()
        color_btn.setFixedSize(40, 28)
        color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
        color_btn.clicked.connect(lambda _, b=color_btn: self._pick_color(b))

        prob_edit = QLineEdit(prob)
        prob_edit.setPlaceholderText("自动")
        prob_edit.setFixedWidth(70)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(30, 28)
        del_btn.clicked.connect(lambda _, rw=row_widget: self._remove_row(rw))

        row_layout.addWidget(name_edit)
        row_layout.addWidget(color_btn)
        row_layout.addWidget(prob_edit)
        row_layout.addWidget(del_btn)
        row_layout.addStretch()

        self.scroll_layout.addWidget(row_widget)
        self.rows.append((name_edit, color_btn, prob_edit, row_widget))

        # 默认颜色（如果传入的是默认灰色，可更新）
        if color.isValid():
            color_btn.setProperty("color", color)

    def _remove_row(self, row_widget: QWidget):
        for i, (_, _, _, rw) in enumerate(self.rows):
            if rw is row_widget:
                self.scroll_layout.removeWidget(row_widget)
                row_widget.deleteLater()
                del self.rows[i]
                break

    def _pick_color(self, btn: QPushButton):
        old_color = btn.property("color")
        if isinstance(old_color, QColor):
            initial = old_color
        else:
            initial = QColor(200, 200, 200)
        color = QColorDialog.getColor(initial, self, "选择颜色")
        if color.isValid():
            btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
            btn.setProperty("color", color)

    def _load_config(self, config: LotteryConfig):
        self.name_edit.setText(config.name)
        # 清除现有行
        while self.rows:
            _, _, _, rw = self.rows[0]
            self._remove_row(rw)
        for prize in config.prizes:
            prob_str = f"{prize.probability * 100:.2f}" if prize.probability > 0 else ""
            self._add_row(prize.name, prize.color, prob_str)

    def _collect_data(self) -> Optional[LotteryConfig]:
        """收集并验证数据，返回配置或None"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "方案名称不能为空！")
            return None

        prizes: List[Prize] = []
        filled_sum = 0.0
        unfilled_indices = []

        for idx, (name_edit, color_btn, prob_edit, _) in enumerate(self.rows):
            pname = name_edit.text().strip()
            if not pname:
                QMessageBox.warning(self, "错误", f"第{idx+1}个奖品名称为空！")
                return None
            color = color_btn.property("color")
            if not isinstance(color, QColor) or not color.isValid():
                color = QColor(200, 200, 200)
            prob_text = prob_edit.text().strip()
            if prob_text == "":
                unfilled_indices.append(idx)
                prizes.append(Prize(pname, color, 0.0))
            else:
                try:
                    p = float(prob_text) / 100.0
                    if p < 0 or p > 1:
                        raise ValueError
                    filled_sum += p
                    prizes.append(Prize(pname, color, p))
                except ValueError:
                    QMessageBox.warning(self, "错误", f"第{idx+1}个奖品概率非法（需0-100的数字）！")
                    return None

        if not prizes:
            QMessageBox.warning(self, "错误", "至少需要一个奖品！")
            return None

        # 自动填充或验证总和
        if unfilled_indices:
            remaining = 1.0 - filled_sum
            if remaining < -1e-9:
                QMessageBox.warning(self, "错误",
                                    "已填写概率总和超过100%，无法自动分配！\n请调整概率或减少已填值。")
                return None
            if remaining <= 0:
                # 剩余为0，将所有未填的设为0
                for i in unfilled_indices:
                    prizes[i].probability = 0.0
            else:
                each = remaining / len(unfilled_indices)
                for i in unfilled_indices:
                    prizes[i].probability = each
        else:
            if abs(filled_sum - 1.0) > 1e-6:
                QMessageBox.warning(self, "错误",
                                    f"所有奖品概率总和必须等于100%！当前总和为{filled_sum*100:.2f}%")
                return None

        return LotteryConfig(name=name, prizes=prizes)

    def _on_apply(self):
        config = self._collect_data()
        if config:
            self.result_config = config
            self.accept()

    def reject(self):
        # 取消时确认
        reply = QMessageBox.question(self, "确认取消", "确定要放弃更改吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            super().reject()

    def get_config(self) -> Optional[LotteryConfig]:
        if hasattr(self, 'result_config'):
            return self.result_config
        return None


# -------------------- 转盘绘制部件 --------------------
class WheelWidget(QWidget):
    """自定义抽奖转盘，支持旋转动画"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.prizes: List[Prize] = []
        self.current_angle = 0.0  # 当前旋转角度（度）
        self.target_angle = 0.0
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.elapsed_timer = QElapsedTimer()
        self.duration = 4000  # 动画时长（ms）
        self._animating = False
        self.on_finished = None  # 动画结束回调

        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_prizes(self, prizes: List[Prize]):
        self.prizes = prizes
        self.current_angle = 0.0
        self.update()

    def start_spin(self, target_prize: Prize):
        """启动旋转动画，指针指向目标奖品扇区内的随机位置"""
        if self._animating or not self.prizes:
            return
        # 计算扇区范围（未旋转时的起始角度）
        start_angle = 0
        for prize in self.prizes:
            span = prize.probability * 360.0
            if prize is target_prize:
                # 在该扇区内随机取一个本地角度
                local_angle = start_angle + random.uniform(0, span)
                break
            start_angle += span
        else:
            return  # 未找到

        # 指针方向：固定在正上方（12点钟），在绘图中为90°
        # 转盘旋转 current_angle 后，指针所指的转盘本地角度为 (90 - current_angle) % 360
        # 我们需要 (90 - current_angle) % 360 = local_angle
        # => current_angle = (90 - local_angle) % 360
        final_angle = (90 - local_angle) % 360
        # 加上随机圈数（5~8圈）
        rounds = random.randint(5, 8)
        self.target_angle = rounds * 360 + final_angle

        # 启动动画
        self.elapsed_timer.start()
        self._animating = True
        self.anim_timer.start(16)  # ~60fps

    def _update_animation(self):
        elapsed = self.elapsed_timer.elapsed()
        if elapsed >= self.duration:
            # 动画结束
            self.current_angle = self.target_angle
            self.anim_timer.stop()
            self._animating = False
            self.update()
            if self.on_finished:
                self.on_finished()
            return

        # 缓动函数：OutCubic
        progress = elapsed / self.duration
        eased = 1 - pow(1 - progress, 3)
        self.current_angle = self.target_angle * eased
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h) - 20
        if side < 50:
            return

        cx = w // 2
        cy = h // 2
        r = side // 2
        rect = (cx - r, cy - r, side, side)

        if not self.prizes:
            # 默认灰色圆
            painter.setBrush(QColor(220, 220, 220))
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.drawEllipse(cx - r, cy - r, side, side)
            painter.setFont(QFont("Microsoft YaHei", 12))
            painter.drawText(rect[0], rect[1], rect[2], rect[3], Qt.AlignmentFlag.AlignCenter, "请设置奖品")
            return

        # 绘制扇形
        start_angle = 90 + self.current_angle  # 12点钟方向 + 旋转偏移
        for prize in self.prizes:
            span = prize.probability * 360.0 * 16  # Qt 使用 1/16 度单位
            painter.setBrush(prize.color)
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.drawPie(rect[0], rect[1], rect[2], rect[3], int(start_angle * 16), int(span))
            # 绘制奖品名称
            # 计算扇形中心角度用于放置文字（简化：不绘制文字在扇区内，以免旋转后混乱）
            start_angle += span / 16

        # 绘制中心圆
        painter.setBrush(Qt.GlobalColor.white)
        painter.setPen(QPen(Qt.GlobalColor.gray, 2))
        painter.drawEllipse(cx - 15, cy - 15, 30, 30)

        # 绘制指针（固定不动，位于上方）
        painter.save()
        painter.translate(cx, cy - r - 10)
        painter.setBrush(QColor(220, 50, 50))
        painter.setPen(Qt.GlobalColor.darkRed)
        pointer = [(-8, 0), (8, 0), (0, -20)]
        from PyQt6.QtGui import QPolygonF
        from PyQt6.QtCore import QPointF
        poly = QPolygonF([QPointF(x, y) for x, y in pointer])
        painter.drawPolygon(poly)
        painter.restore()


# -------------------- 抽奖页面 --------------------
class LotteryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config: Optional[LotteryConfig] = None
        self._init_ui()
        self._spin_result = None  # 暂存动画结果

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 转盘
        self.wheel = WheelWidget()
        layout.addWidget(self.wheel, alignment=Qt.AlignmentFlag.AlignCenter)

        # 结果标签
        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self.result_label.setStyleSheet("color: #d63031; margin: 10px;")
        layout.addWidget(self.result_label)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.spin_btn = QPushButton("🎰 开始抽奖")
        self.spin_btn.setFixedSize(140, 45)
        self.setup_btn = QPushButton("⚙ 设置奖品")
        self.setup_btn.setFixedSize(140, 45)
        btn_layout.addWidget(self.spin_btn)
        btn_layout.addWidget(self.setup_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.spin_btn.clicked.connect(self._start_spin)
        self.setup_btn.clicked.connect(self._open_setup)

        # 样式
        self.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                border-radius: 8px;
                background-color: #0984e3;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #0766b3;
            }
            QPushButton:disabled {
                background-color: #b2bec3;
            }
        """)

    def load_config(self, config: LotteryConfig):
        self.config = config
        self.wheel.set_prizes(config.prizes)
        self.result_label.setText("")

    def _open_setup(self):
        dlg = SetupDialog(self.config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_config = dlg.get_config()
            if new_config:
                self.config = new_config
                self.wheel.set_prizes(new_config.prizes)
                self.result_label.setText("")
                # 通知主窗口更新历史
                main_win = self._get_main_window()
                if main_win:
                    main_win.add_to_history(new_config)

    def _start_spin(self):
        if not self.config or not self.config.prizes:
            QMessageBox.information(self, "提示", "请先设置奖品！")
            return
        self.spin_btn.setEnabled(False)
        self.result_label.setText("抽奖中...")
        # 选择中奖奖品
        target = weighted_choice(self.config.prizes)
        self._spin_result = target
        self.wheel.on_finished = self._on_spin_finished
        self.wheel.start_spin(target)

    def _on_spin_finished(self):
        if self._spin_result:
            self.result_label.setText(f"🎉 恭喜：{self._spin_result.name}")
        self.spin_btn.setEnabled(True)
        self.wheel.on_finished = None
        self._spin_result = None

    def _get_main_window(self):
        # 向上查找主窗口
        p = self.parent()
        while p is not None:
            if isinstance(p, MainWindow):
                return p
            p = p.parent()
        return None

    def get_current_config(self) -> Optional[LotteryConfig]:
        return self.config


# -------------------- 历史记录页面 --------------------
class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("MyLotteryApp", "LotteryMachine")
        self._init_ui()
        self._load_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("📋 抽奖方案历史")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("应用选中")
        self.delete_btn = QPushButton("🗑 删除")
        self.clear_all_btn = QPushButton("清空全部")

        self.apply_btn.setFixedHeight(35)
        self.delete_btn.setFixedHeight(35)
        self.clear_all_btn.setFixedHeight(35)

        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.clear_all_btn)
        layout.addLayout(btn_layout)

        self.apply_btn.clicked.connect(self._apply_selected)
        self.delete_btn.clicked.connect(self._delete_selected)
        self.clear_all_btn.clicked.connect(self._clear_all)

        self.setStyleSheet("""
            QListWidget {
                border: 1px solid #b2bec3;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton {
                background: #dfe6e9;
                border: 1px solid #b2bec3;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #b2bec3;
            }
        """)

    def _load_history(self):
        self.list_widget.clear()
        raw = self.settings.value("history", "[]")
        try:
            data = json.loads(raw)
        except Exception:
            data = []
        for item in data:
            config = LotteryConfig.from_dict(item)
            list_item = QListWidgetItem(f"{config.name}    [{config.created_time}]")
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.list_widget.addItem(list_item)

    def _save_history(self, history_list: list):
        self.settings.setValue("history", json.dumps(history_list, ensure_ascii=False))

    def get_all_history(self) -> list:
        raw = self.settings.value("history", "[]")
        try:
            return json.loads(raw)
        except Exception:
            return []

    def add_record(self, config: LotteryConfig):
        """追加一条记录（去重：如果名称和时间完全相同则不重复添加）"""
        history = self.get_all_history()
        d = config.to_dict()
        # 简单去重：同名同时刻不重复
        if not any(h.get("name") == d["name"] and h.get("created_time") == d["created_time"] for h in history):
            history.append(d)
            self._save_history(history)
            self._load_history()

    def _apply_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先选择一个方案")
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        config = LotteryConfig.from_dict(data)
        main_win = self._get_main_window()
        if main_win:
            main_win.lottery_page.load_config(config)
            main_win.tab_widget.setCurrentIndex(0)

    def _delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        reply = QMessageBox.question(self, "确认删除", "确定要删除此方案吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            data = item.data(Qt.ItemDataRole.UserRole)
            history = self.get_all_history()
            history = [h for h in history if not (h.get("name") == data["name"] and h.get("created_time") == data["created_time"])]
            self._save_history(history)
            self._load_history()

    def _clear_all(self):
        reply = QMessageBox.question(self, "确认清空", "确定要删除所有历史记录吗？此操作不可恢复！",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._save_history([])
            self._load_history()

    def _get_main_window(self):
        p = self.parent()
        while p:
            if isinstance(p, MainWindow):
                return p
            p = p.parent()
        return None


# -------------------- 主窗口 --------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎡 抽奖机")
        self.resize(900, 700)

        # 中心Tab
        self.tab_widget = QTabWidget()
        self.lottery_page = LotteryPage()
        self.history_page = HistoryPage()
        self.tab_widget.addTab(self.lottery_page, "🎰 抽奖")
        self.tab_widget.addTab(self.history_page, "📋 历史")
        self.setCentralWidget(self.tab_widget)

        # 菜单栏
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")

        export_action = QAction("导出当前配置", self)
        export_action.triggered.connect(self.export_current)
        file_menu.addAction(export_action)

        import_action = QAction("导入配置", self)
        import_action.triggered.connect(self.import_config)
        file_menu.addAction(import_action)

        # 样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QMenuBar {
                background-color: #dfe6e9;
                border-bottom: 1px solid #b2bec3;
            }
            QMenuBar::item:selected {
                background: #b2bec3;
            }
            QTabWidget::pane {
                border: 1px solid #b2bec3;
                background: white;
            }
            QTabBar::tab {
                background: #dfe6e9;
                padding: 8px 16px;
                border: 1px solid #b2bec3;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 1px solid white;
            }
        """)

    def add_to_history(self, config: LotteryConfig):
        """供抽奖页面在应用设置后调用"""
        self.history_page.add_record(config)

    def export_current(self):
        config = self.lottery_page.get_current_config()
        if not config:
            QMessageBox.warning(self, "提示", "当前没有抽奖配置，请先设置。")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出配置", "", "JSON文件 (*.json)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "成功", f"配置已导出到 {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败：{str(e)}")

    def import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "JSON文件 (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 验证必须字段
            if not all(k in data for k in ("name", "prizes")):
                raise ValueError("JSON缺少必要字段(name, prizes)")
            for p in data["prizes"]:
                if not all(k in p for k in ("name", "color", "probability")):
                    raise ValueError("奖品数据缺少字段")
            config = LotteryConfig.from_dict(data)
            # 询问是否立即应用
            reply = QMessageBox.question(self, "导入成功", f"成功导入方案：{config.name}\n是否立即应用？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.lottery_page.load_config(config)
                self.tab_widget.setCurrentIndex(0)
            # 无论如何都添加到历史
            self.history_page.add_record(config)
        except Exception as e:
            QMessageBox.critical(self, "导入错误", f"无法解析文件：{str(e)}")


# -------------------- 入口 --------------------
def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("MyLotteryApp")
    app.setApplicationName("LotteryMachine")
    # 设置整体字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()