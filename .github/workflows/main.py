import sys
import base64
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

SALT_SIZE = 16          # 盐长度（字节）
ITERATIONS = 600_000    # PBKDF2 迭代次数
KEY_LENGTH = 32         # Fernet 密钥长度（字节）


def derive_key(password: str, salt: bytes) -> bytes:
    """使用 PBKDF2 从密码和盐派生 32 字节密钥，并编码为 Fernet 可用的 URL-safe base64"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend()
    )
    key = kdf.derive(password.encode('utf-8'))
    return base64.urlsafe_b64encode(key)


def encrypt_text(plaintext: str, password: str) -> str:
    """加密文本，返回包含盐和密文的字符串（格式：salt_b64:token）"""
    salt = os.urandom(SALT_SIZE)
    key = derive_key(password, salt)
    fernet = Fernet(key)
    token = fernet.encrypt(plaintext.encode('utf-8'))
    salt_b64 = base64.urlsafe_b64encode(salt).decode('ascii')
    token_b64 = token.decode('ascii')
    return f"{salt_b64}:{token_b64}"


def decrypt_text(ciphertext: str, password: str) -> str:
    """解密文本，从密文中提取盐，派生密钥并解密"""
    try:
        salt_b64, token_b64 = ciphertext.split(':', 1)
    except ValueError:
        raise ValueError("密文格式错误，缺少盐分隔符 ':'")

    try:
        salt = base64.urlsafe_b64decode(salt_b64.encode('ascii'))
    except Exception:
        raise ValueError("密文中的盐编码无效")

    if len(salt) != SALT_SIZE:
        raise ValueError("盐长度不匹配")

    key = derive_key(password, salt)
    fernet = Fernet(key)
    try:
        plaintext = fernet.decrypt(token_b64.encode('ascii'))
    except Exception:
        raise ValueError("解密失败，密码错误或密文已损坏")
    return plaintext.decode('utf-8')


class CryptoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文本加密解密器")
        self.setMinimumSize(600, 450)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # 密码输入
        pwd_layout = QHBoxLayout()
        pwd_layout.addWidget(QLabel("密码："))
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText("输入加密/解密密码")
        pwd_layout.addWidget(self.pwd_input)

        # 显示/隐藏密码按钮
        self.show_pwd_btn = QPushButton("显示")
        self.show_pwd_btn.setCheckable(True)
        self.show_pwd_btn.toggled.connect(self.toggle_password_visibility)
        pwd_layout.addWidget(self.show_pwd_btn)
        main_layout.addLayout(pwd_layout)

        # 明文/密文输入区
        input_group = QGroupBox("输入文本 / 密文")
        input_layout = QVBoxLayout(input_group)
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("在此输入要加密的文本，或要解密的密文...")
        input_layout.addWidget(self.input_text)
        main_layout.addWidget(input_group)

        # 按钮区
        btn_layout = QHBoxLayout()
        self.encrypt_btn = QPushButton("🔒 加密")
        self.encrypt_btn.clicked.connect(self.do_encrypt)
        self.decrypt_btn = QPushButton("🔓 解密")
        self.decrypt_btn.clicked.connect(self.do_decrypt)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(self.encrypt_btn)
        btn_layout.addWidget(self.decrypt_btn)
        btn_layout.addWidget(self.clear_btn)
        main_layout.addLayout(btn_layout)

        # 输出区
        output_group = QGroupBox("输出结果")
        output_layout = QVBoxLayout(output_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("加密或解密结果将显示在这里...")
        output_layout.addWidget(self.output_text)

        copy_layout = QHBoxLayout()
        self.copy_btn = QPushButton("📋 复制结果")
        self.copy_btn.clicked.connect(self.copy_output)
        copy_layout.addStretch()
        copy_layout.addWidget(self.copy_btn)
        output_layout.addLayout(copy_layout)
        main_layout.addWidget(output_group)

    def toggle_password_visibility(self, checked):
        if checked:
            self.pwd_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_pwd_btn.setText("隐藏")
        else:
            self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_pwd_btn.setText("显示")

    def get_password(self):
        pwd = self.pwd_input.text()
        if not pwd:
            QMessageBox.warning(self, "警告", "请输入密码")
            return None
        return pwd

    def do_encrypt(self):
        password = self.get_password()
        if password is None:
            return
        plaintext = self.input_text.toPlainText().strip()
        if not plaintext:
            QMessageBox.warning(self, "警告", "请输入要加密的文本")
            return
        try:
            cipher = encrypt_text(plaintext, password)
            self.output_text.setPlainText(cipher)
        except Exception as e:
            QMessageBox.critical(self, "加密失败", str(e))

    def do_decrypt(self):
        password = self.get_password()
        if password is None:
            return
        ciphertext = self.input_text.toPlainText().strip()
        if not ciphertext:
            QMessageBox.warning(self, "警告", "请输入要解密的密文")
            return
        try:
            plain = decrypt_text(ciphertext, password)
            self.output_text.setPlainText(plain)
        except Exception as e:
            QMessageBox.critical(self, "解密失败", str(e))

    def copy_output(self):
        text = self.output_text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "已复制", "结果已复制到剪贴板")
        else:
            QMessageBox.information(self, "无内容", "没有可复制的结果")

    def clear_all(self):
        self.input_text.clear()
        self.output_text.clear()
        self.pwd_input.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CryptoApp()
    window.show()
    sys.exit(app.exec())