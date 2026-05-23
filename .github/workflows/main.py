import sys
import os
import time
import secrets
import string
import hashlib
import zlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFileDialog, QMessageBox, QCheckBox, QInputDialog,
                             QProgressDialog, QProgressBar)
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt6.QtGui import QDesktopServices


class CryptoWorker(QThread):
    progress = pyqtSignal(int)          # 进度百分比 0-100
    status_msg = pyqtSignal(str)        # 状态文本（速度、剩余时间）
    finished = pyqtSignal(bool, str)    # 成功标志，结果消息或错误信息
    canceled = False
    
    def __init__(self, mode, in_path, password, del_original=False):
        super().__init__()
        self.mode = mode                # 'encrypt' or 'decrypt'
        self.in_path = in_path
        self.password = password
        self.del_original = del_original
        self.out_path = ""
    
    def cancel(self):
        self.canceled = True
    
    def derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode())
    
    def run(self):
        try:
            if self.mode == 'encrypt':
                self.do_encrypt()
            else:
                self.do_decrypt()
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def do_encrypt(self):
        total = os.path.getsize(self.in_path)
        # 大文件优化：动态块大小
        chunk_size = 128 * 1024
        if total > 100 * 1024 * 1024:
            chunk_size = 4 * 1024 * 1024      # 大于100MB用4MB块
        elif total > 500 * 1024 * 1024:
            chunk_size = 8 * 1024 * 1024      # 大于500MB用8MB块
            
        processed = 0
        start_time = time.time()
        last_update_time = start_time
        
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = self.derive_key(self.password, salt)
        
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        
        out_path = self.in_path + ".enc"
        self.out_path = out_path
        
        with open(self.in_path, 'rb') as f_in, open(out_path, 'wb') as f_out:
            f_out.write(salt + nonce)
            while True:
                if self.canceled:
                    f_out.close()
                    os.remove(out_path)
                    self.finished.emit(False, "用户取消")
                    return
                chunk = f_in.read(chunk_size)
                if not chunk:
                    break
                encrypted_chunk = encryptor.update(chunk)
                f_out.write(encrypted_chunk)
                processed += len(chunk)
                percent = int(processed * 100 / total)
                self.progress.emit(percent)
                
                # 估算速度和剩余时间（每秒最多更新10次）
                now = time.time()
                if now - last_update_time >= 0.1 or processed == total:
                    elapsed = now - start_time
                    if elapsed > 0 and processed > 0:
                        speed = processed / elapsed / 1024 / 1024   # MB/s
                        remaining_sec = (total - processed) / (processed / elapsed)
                        if remaining_sec < 60:
                            time_str = f"{remaining_sec:.0f}秒"
                        elif remaining_sec < 3600:
                            time_str = f"{int(remaining_sec//60)}分{int(remaining_sec%60)}秒"
                        else:
                            time_str = f"{remaining_sec/3600:.1f}小时"
                        status = f"已处理 {processed/1024/1024:.1f} MB，速度 {speed:.1f} MB/s，剩余 {time_str}"
                        self.status_msg.emit(status)
                    last_update_time = now
            
            encryptor.finalize()
            tag = encryptor.tag
            f_out.write(tag)
        
        self.finished.emit(True, out_path)
    
    def do_decrypt(self):
        total = os.path.getsize(self.in_path)
        chunk_size = 128 * 1024
        if total > 100 * 1024 * 1024:
            chunk_size = 4 * 1024 * 1024
        
        start_time = time.time()
        last_update_time = start_time
        
        with open(self.in_path, 'rb') as f_in:
            salt = f_in.read(16)
            if len(salt) != 16:
                raise ValueError("文件头损坏，不是加密格式")
            nonce = f_in.read(12)
            if len(nonce) != 12:
                raise ValueError("文件头损坏，不是加密格式")
            
            remaining = total - 28
            if remaining < 16:
                raise ValueError("文件太短")
            tag_start = total - 16
            f_in.seek(28)
            ciphertext_len = tag_start - 28
            
            key = self.derive_key(self.password, salt)
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
            decryptor = cipher.decryptor()
            
            out_path = self.in_path
            if out_path.endswith('.enc'):
                out_path = out_path[:-4] + "_decrypted"
            else:
                out_path = out_path + ".dec"
            self.out_path = out_path
            
            with open(out_path, 'wb') as f_out:
                processed = 0
                remaining_cipher = ciphertext_len
                while remaining_cipher > 0:
                    if self.canceled:
                        f_out.close()
                        os.remove(out_path)
                        self.finished.emit(False, "用户取消")
                        return
                    read_size = min(chunk_size, remaining_cipher)
                    chunk = f_in.read(read_size)
                    if not chunk:
                        break
                    decrypted_chunk = decryptor.update(chunk)
                    f_out.write(decrypted_chunk)
                    processed += len(chunk)
                    percent = int(processed * 100 / ciphertext_len) if ciphertext_len else 0
                    self.progress.emit(percent)
                    
                    now = time.time()
                    if now - last_update_time >= 0.1 or processed == ciphertext_len:
                        elapsed = now - start_time
                        if elapsed > 0 and processed > 0:
                            speed = processed / elapsed / 1024 / 1024
                            remaining_sec = (ciphertext_len - processed) / (processed / elapsed)
                            if remaining_sec < 60:
                                time_str = f"{remaining_sec:.0f}秒"
                            elif remaining_sec < 3600:
                                time_str = f"{int(remaining_sec//60)}分{int(remaining_sec%60)}秒"
                            else:
                                time_str = f"{remaining_sec/3600:.1f}小时"
                            status = f"已处理 {processed/1024/1024:.1f} MB，速度 {speed:.1f} MB/s，剩余 {time_str}"
                            self.status_msg.emit(status)
                        last_update_time = now
                    
                    remaining_cipher -= read_size
                
                f_in.seek(tag_start)
                tag = f_in.read(16)
                if len(tag) != 16:
                    raise ValueError("缺少认证标签")
                decryptor.finalize_with_tag(tag)
        
        self.finished.emit(True, out_path)


class FileCrypto(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件加密器 - GCM + 多线程 + 增强功能")
        self.setGeometry(300, 300, 600, 280)
        self.setAcceptDrops(True)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # 文件选择行
        file_layout = QHBoxLayout()
        self.file_label = QLabel("没选文件，你瞎啊？\n(也可以直接把文件拖进来)")
        self.file_label.setWordWrap(True)
        self.select_btn = QPushButton("点这儿选文件")
        self.select_btn.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_label, 3)
        file_layout.addWidget(self.select_btn, 1)
        layout.addLayout(file_layout)
        
        # 密钥输入行 + 眼睛按钮 + 随机密码按钮
        pwd_layout = QHBoxLayout()
        pwd_layout.addWidget(QLabel("密钥："))
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_edit.textChanged.connect(self.check_password_strength)
        pwd_layout.addWidget(self.pwd_edit)
        
        self.show_pwd_btn = QPushButton("👁")
        self.show_pwd_btn.setCheckable(True)
        self.show_pwd_btn.setFixedWidth(30)
        self.show_pwd_btn.toggled.connect(self.toggle_password_visibility)
        pwd_layout.addWidget(self.show_pwd_btn)
        
        self.gen_pwd_btn = QPushButton("🎲")
        self.gen_pwd_btn.setFixedWidth(30)
        self.gen_pwd_btn.setToolTip("生成随机强密码")
        self.gen_pwd_btn.clicked.connect(self.generate_random_password)
        pwd_layout.addWidget(self.gen_pwd_btn)
        
        layout.addLayout(pwd_layout)
        
        # 密码强度显示
        self.strength_bar = QProgressBar()
        self.strength_bar.setRange(0, 100)
        self.strength_bar.setFixedHeight(8)
        self.strength_bar.setTextVisible(False)
        self.strength_label = QLabel("密码强度：未输入")
        self.strength_label.setFixedHeight(20)
        layout.addWidget(self.strength_bar)
        layout.addWidget(self.strength_label)
        
        # 选项行：删除原文件复选框
        option_layout = QHBoxLayout()
        self.del_check = QCheckBox("操作后删除原文件（加密删明文，解密删.enc）")
        self.del_check.setChecked(False)
        option_layout.addWidget(self.del_check)
        option_layout.addStretch()
        layout.addLayout(option_layout)
        
        # 按钮行（增加了哈希校验按钮）
        btn_layout = QHBoxLayout()
        self.encrypt_btn = QPushButton("加密")
        self.decrypt_btn = QPushButton("解密")
        self.open_btn = QPushButton("打开文件")
        self.hash_btn = QPushButton("📋 校验哈希")
        self.encrypt_btn.clicked.connect(self.encrypt)
        self.decrypt_btn.clicked.connect(self.decrypt)
        self.open_btn.clicked.connect(self.open_file)
        self.hash_btn.clicked.connect(self.show_file_hash)
        btn_layout.addWidget(self.encrypt_btn)
        btn_layout.addWidget(self.decrypt_btn)
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.hash_btn)
        layout.addLayout(btn_layout)
        
        self.current_file = ""
        self.worker = None
        self.progress_dlg = None
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self.current_file = path
                self.file_label.setText(path)
                break
        else:
            QMessageBox.warning(self, "眼瞎了？", "拖进来的是个啥？我要文件！")
    
    def toggle_password_visibility(self, checked):
        if checked:
            self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_pwd_btn.setText("🙈")
        else:
            self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_pwd_btn.setText("👁")
    
    def check_password_strength(self):
        pwd = self.pwd_edit.text()
        if not pwd:
            self.strength_bar.setValue(0)
            self.strength_label.setText("密码强度：未输入")
            return
        
        score = 0
        if len(pwd) >= 8:
            score += 20
        if len(pwd) >= 12:
            score += 20
        if any(c.isdigit() for c in pwd):
            score += 20
        if any(c.islower() for c in pwd):
            score += 10
        if any(c.isupper() for c in pwd):
            score += 15
        if any(not c.isalnum() for c in pwd):
            score += 15
        
        types = sum([
            any(c.islower() for c in pwd),
            any(c.isupper() for c in pwd),
            any(c.isdigit() for c in pwd),
            any(not c.isalnum() for c in pwd)
        ])
        if types >= 3:
            score = min(100, score + 10)
        if types == 4:
            score = min(100, score + 5)
        
        self.strength_bar.setValue(score)
        if score < 40:
            self.strength_label.setText("密码强度：弱 💀")
            self.strength_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        elif score < 70:
            self.strength_label.setText("密码强度：中 ⚠️")
            self.strength_bar.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
        else:
            self.strength_label.setText("密码强度：强 ✅")
            self.strength_bar.setStyleSheet("QProgressBar::chunk { background-color: green; }")
    
    def generate_random_password(self):
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(16))
        self.pwd_edit.setText(password)
        if not self.show_pwd_btn.isChecked():
            self.show_pwd_btn.toggle()
    
    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选个文件")
        if path:
            self.current_file = path
            self.file_label.setText(path)
    
    def compute_file_hash(self, filepath, algo='sha256'):
        """计算文件的哈希值（SHA256或MD5）"""
        hash_obj = hashlib.sha256() if algo == 'sha256' else hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    
    def compute_crc32(self, filepath):
        """计算文件的CRC32校验值"""
        crc = 0
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                crc = zlib.crc32(chunk, crc)
        return format(crc & 0xFFFFFFFF, '08x')
    
    def show_file_hash(self):
        if not self.current_file or not os.path.exists(self.current_file):
            QMessageBox.warning(self, "错误", "没有有效文件，先选一个或拖一个进来。")
            return
        try:
            sha256 = self.compute_file_hash(self.current_file, 'sha256')
            crc32 = self.compute_crc32(self.current_file)
            size = os.path.getsize(self.current_file)
            size_str = f"{size} bytes ({size/1024:.2f} KB)"
            msg = (f"文件：{os.path.basename(self.current_file)}\n"
                   f"大小：{size_str}\n"
                   f"SHA-256：{sha256}\n"
                   f"CRC32：{crc32}")
            QMessageBox.information(self, "文件哈希校验", msg)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"计算失败：{str(e)}")
    
    def confirm_password(self, password: str) -> bool:
        confirm, ok = QInputDialog.getText(
            self, 
            "确认密码", 
            "再输一遍密钥，错了别怪我：",
            QLineEdit.EchoMode.Password
        )
        if not ok:
            return False
        if confirm != password:
            QMessageBox.warning(self, "脑子呢？", "两次密码不一样，自己好好想想！")
            return False
        return True
    
    def start_operation(self, mode):
        if not self.current_file:
            QMessageBox.warning(self, "", "文件都没选")
            return
        password = self.pwd_edit.text()
        if not password:
            QMessageBox.warning(self, "", "密钥是空的")
            return
        if mode == 'encrypt' and not self.confirm_password(password):
            return
        if self.del_check.isChecked():
            reply = QMessageBox.question(self, "确认删除", 
                                         f"操作完成后将删除原文件：\n{self.current_file}\n\n确定继续？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.progress_dlg = QProgressDialog(f"{'加密' if mode=='encrypt' else '解密'}中...", "取消", 0, 100, self)
        self.progress_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dlg.setAutoClose(False)
        self.progress_dlg.setAutoReset(False)
        self.progress_dlg.show()
        
        self.worker = CryptoWorker(mode, self.current_file, password, self.del_check.isChecked())
        self.worker.progress.connect(self.update_progress)
        self.worker.status_msg.connect(self.update_status_text)
        self.worker.finished.connect(lambda success, msg: self.operation_finished(success, msg, mode))
        self.progress_dlg.canceled.connect(self.cancel_operation)
        self.worker.start()
    
    def update_progress(self, value):
        if self.progress_dlg:
            self.progress_dlg.setValue(value)
    
    def update_status_text(self, text):
        if self.progress_dlg:
            self.progress_dlg.setLabelText(text)
    
    def cancel_operation(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.progress_dlg.setLabelText("正在取消...")
            self.progress_dlg.setCancelButton(None)
    
    def operation_finished(self, success, msg, mode):
        self.progress_dlg.close()
        if success:
            if self.del_check.isChecked():
                try:
                    os.remove(self.current_file)
                    self.file_label.setText("原文件已删，别后悔")
                    self.current_file = ""
                except Exception as e:
                    QMessageBox.warning(self, "删不掉", f"原文件删不了：{str(e)}")
            if mode == 'encrypt':
                self.current_file = msg
                self.file_label.setText(msg)
            else:
                self.current_file = msg
                self.file_label.setText(msg)
            QMessageBox.information(self, "成了", f"{'加密' if mode=='encrypt' else '解密'}完成\n{msg}")
        else:
            QMessageBox.critical(self, "失败", f"操作失败：{msg}")
        self.worker = None
    
    def encrypt(self):
        self.start_operation('encrypt')
    
    def decrypt(self):
        self.start_operation('decrypt')
    
    def open_file(self):
        if not self.current_file:
            QMessageBox.warning(self, "", "文件呢？")
            return
        if not os.path.exists(self.current_file):
            QMessageBox.warning(self, "", "文件不存在")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_file))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FileCrypto()
    win.show()
    sys.exit(app.exec())
