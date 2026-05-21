import sys
from io import BytesIO
from PIL import Image
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap


class LSBSteganography:
    """LSB 隐写工具：将文本隐藏到 PNG 图片的 RGB 像素中，保留透明度"""

    @staticmethod
    def encode(image_path: str, text: str) -> Image.Image:
        """
        将文本嵌入图片的 RGB 通道，保持 Alpha 透明不变。
        返回嵌入后的 PIL Image 对象。
        """
        img = Image.open(image_path)
        has_alpha = (img.mode == 'RGBA')

        if has_alpha:
            # 分离 RGB 和 Alpha 通道
            img_rgb = img.convert('RGB')
            alpha = img.split()[-1]
            pixels = img_rgb.load()
        else:
            img = img.convert('RGB')
            pixels = img.load()
            img_rgb = img

        width, height = img_rgb.size

        # 准备数据：4 字节长度头 (大端序) + UTF-8 文本
        data_bytes = text.encode('utf-8')
        length_bytes = len(data_bytes).to_bytes(4, byteorder='big')
        all_bytes = length_bytes + data_bytes

        # 容量检查 (每个像素3个通道)
        total_pixels = width * height
        needed_bits = len(all_bytes) * 8
        if needed_bits > total_pixels * 3:
            raise ValueError(f"图片容量不足，最多可隐藏 {total_pixels * 3 // 8} 字节，当前需要 {len(all_bytes)} 字节")

        # 将字节串转换为比特流
        bits = ''.join(f'{byte:08b}' for byte in all_bytes)

        # 逐像素嵌入 LSB
        bit_idx = 0
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                if bit_idx < needed_bits:
                    r = (r & 0xFE) | int(bits[bit_idx])
                    bit_idx += 1
                if bit_idx < needed_bits:
                    g = (g & 0xFE) | int(bits[bit_idx])
                    bit_idx += 1
                if bit_idx < needed_bits:
                    b = (b & 0xFE) | int(bits[bit_idx])
                    bit_idx += 1
                pixels[x, y] = (r, g, b)
                if bit_idx >= needed_bits:
                    break
            if bit_idx >= needed_bits:
                break

        # 如果原图有 Alpha 通道，将修改后的 RGB 与原 Alpha 重新合并
        if has_alpha:
            r_ch, g_ch, b_ch = img_rgb.split()
            img = Image.merge('RGBA', (r_ch, g_ch, b_ch, alpha))

        return img

    @staticmethod
    def decode(image_path: str) -> str:
        """从图片的 RGB 通道中提取隐藏文本（忽略 Alpha 通道）"""
        img = Image.open(image_path)

        # 若有透明度，只提取 RGB 部分即可（水印未写入 Alpha）
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        pixels = img.load()
        width, height = img.size

        bits = []
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                bits.append(str(r & 1))
                bits.append(str(g & 1))
                bits.append(str(b & 1))

        # 将比特流还原为字节
        bytes_list = []
        for i in range(0, len(bits), 8):
            byte_bits = ''.join(bits[i:i+8])
            if len(byte_bits) < 8:
                break
            bytes_list.append(int(byte_bits, 2))

        if len(bytes_list) < 4:
            raise ValueError("未找到水印数据（长度头不足）")

        # 解析长度字段
        length = int.from_bytes(bytes_list[:4], byteorder='big')
        if length == 0:
            return ""
        if 4 + length > len(bytes_list):
            raise ValueError("水印数据不完整或已损坏")

        data_bytes = bytes(bytes_list[4:4 + length])
        return data_bytes.decode('utf-8')


class SteganoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片隐写水印工具")
        self.setMinimumSize(700, 600)

        self.current_image_path = None
        self.watermarked_image = None   # 嵌入水印后的 PIL Image
        self.extracted_text = ""

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ---- 图片预览 ----
        img_group = QGroupBox("图片预览")
        img_layout = QVBoxLayout(img_group)
        self.img_label = QLabel()
        self.img_label.setFixedSize(400, 300)
        self.img_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setText("未选择图片")
        img_layout.addWidget(self.img_label, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(img_group)

        # ---- 上传按钮 ----
        self.upload_btn = QPushButton("📁 上传图片")
        self.upload_btn.clicked.connect(self.upload_image)
        main_layout.addWidget(self.upload_btn)

        # ---- 水印操作区 ----
        op_group = QGroupBox("水印操作")
        op_layout = QVBoxLayout(op_group)

        # 水印文字输入
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("水印文字："))
        self.watermark_input = QLineEdit()
        self.watermark_input.setPlaceholderText("输入要隐藏的文字...")
        input_layout.addWidget(self.watermark_input)
        op_layout.addLayout(input_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.encode_btn = QPushButton("🔒 添加隐藏水印")
        self.encode_btn.clicked.connect(self.add_watermark)
        self.decode_btn = QPushButton("🔓 提取隐藏水印")
        self.decode_btn.clicked.connect(self.extract_watermark)
        self.download_btn = QPushButton("💾 下载水印图片")
        self.download_btn.clicked.connect(self.download_image)
        self.download_btn.setEnabled(False)
        btn_layout.addWidget(self.encode_btn)
        btn_layout.addWidget(self.decode_btn)
        btn_layout.addWidget(self.download_btn)
        op_layout.addLayout(btn_layout)
        main_layout.addWidget(op_group)

        # ---- 提取结果显示 ----
        result_group = QGroupBox("提取结果")
        result_layout = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("提取的隐藏水印将显示在这里...")
        result_layout.addWidget(self.result_text)
        main_layout.addWidget(result_group)

    def upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        if not file_path:
            return

        self.current_image_path = file_path
        # 预览
        pixmap = QPixmap(file_path)
        scaled = pixmap.scaled(
            self.img_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.img_label.setPixmap(scaled)

        # 重置状态
        self.watermarked_image = None
        self.download_btn.setEnabled(False)
        self.result_text.clear()
        self.watermark_input.clear()

    def add_watermark(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "警告", "请先上传一张图片")
            return

        text = self.watermark_input.text().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入水印文字")
            return

        try:
            # 嵌入水印
            watermarked_img = LSBSteganography.encode(self.current_image_path, text)
            self.watermarked_image = watermarked_img

            # 更新预览为水印图
            buffer = BytesIO()
            watermarked_img.save(buffer, format='PNG')
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            scaled = pixmap.scaled(
                self.img_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.img_label.setPixmap(scaled)

            self.download_btn.setEnabled(True)
            QMessageBox.information(self, "成功", "水印已嵌入图片！请点击下载按钮保存。")
        except Exception as e:
            QMessageBox.critical(self, "嵌入失败", str(e))

    def extract_watermark(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "警告", "请先上传一张图片")
            return

        try:
            extracted = LSBSteganography.decode(self.current_image_path)
            self.extracted_text = extracted
            self.result_text.setPlainText(extracted if extracted else "（水印为空）")
            if not extracted:
                QMessageBox.information(self, "提取完成", "未检测到水印信息。")
        except Exception as e:
            self.result_text.setPlainText(f"提取失败: {e}")
            QMessageBox.critical(self, "提取失败", str(e))

    def download_image(self):
        if self.watermarked_image is None:
            QMessageBox.warning(self, "警告", "没有可下载的图片，请先添加水印")
            return

        # 根据图片模式推荐保存格式
        default_name = "watermarked.png"
        filters = "PNG 图片 (*.png);;BMP 图片 (*.bmp);;所有文件 (*)"
        if self.watermarked_image.mode == 'RGBA':
            # 透明图片必须保存为 PNG
            default_name = "watermarked.png"
            filters = "PNG 图片 (*.png);;所有文件 (*)"

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "保存水印图片", default_name, filters
        )
        if not file_path:
            return

        try:
            # 如果图片是 RGBA 模式且用户没有输入 .png 后缀，自动补充
            if self.watermarked_image.mode == 'RGBA' and not file_path.lower().endswith('.png'):
                file_path += '.png'

            # 保存
            if file_path.lower().endswith('.bmp'):
                self.watermarked_image.save(file_path, format='BMP')
            else:
                self.watermarked_image.save(file_path, format='PNG')

            QMessageBox.information(self, "成功", f"图片已保存至：\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SteganoApp()
    window.show()
    sys.exit(app.exec())
