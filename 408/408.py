import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QKeyEvent, QCloseEvent


class VideoPlayer(QMainWindow):
    def __init__(self, video_path: str):
        super().__init__()
        self.video_path = video_path
        self.init_ui()

    def init_ui(self):
        # 全屏无边框，黑色背景
        self.setWindowTitle("Video Player")
        self.showFullScreen()
        self.setStyleSheet("background-color: black;")

        # 隐藏鼠标光标
        self.setCursor(Qt.CursorShape.BlankCursor)

        # 中央部件和布局
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # 视频显示控件，禁止获取焦点
        self.video_widget = QVideoWidget()
        self.video_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.video_widget)

        # 音频输出
        self.audio_output = QAudioOutput()

        # 媒体播放器
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setSource(QUrl.fromLocalFile(self.video_path))

        # 连接信号
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.errorOccurred.connect(self.on_error)

        # 确保主窗口能够接收键盘事件
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

        # 开始播放
        self.media_player.play()

    def closeEvent(self, event: QCloseEvent):
        """窗口即将关闭时调用（Alt+F4、任务栏关闭、ESC 都会触发）"""
        # 停止播放，防止声音残留
        self.media_player.stop()
        # 强制终止进程，不执行后续的 Python 退出清理，确保彻底结束
        os._exit(0)
        # 注意：os._exit(0) 会立即结束，所以 event.accept() 可以省略

    def keyPressEvent(self, event: QKeyEvent):
        """只响应 ESC 键，其他按键全部忽略（屏蔽）"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            os._exit(0)
        else:
            # 吞掉其他所有按键，不传递给父类处理
            event.ignore()
            return
        # 仅 ESC 会到达这里，正常传递给父类（可省略）
        # super().keyPressEvent(event)

    def on_media_status_changed(self, status: QMediaPlayer.MediaStatus):
        """播放结束：隐藏视频画面，保持黑屏，等待 ESC 退出"""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.video_widget.hide()
            self.media_player.stop()

    def on_error(self, error, error_string):
        print(f"播放错误: {error_string}")
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # ⚠️ 请将这里的路径替换成你自己的视频文件路径
    video_file = "ree.mp4"
    player = VideoPlayer(video_file)

    sys.exit(app.exec())
