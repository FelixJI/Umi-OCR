# src/ui/settings/hotkey_settings.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QHBoxLayout, QLabel, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence

from src.utils.config_manager import ConfigManager
from src.controllers.settings_controller import SettingsController

class HotkeyRecorder(QLineEdit):
    hotkeyChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("请按下快捷键...")
        self._key_sequence = ""

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()
        
        # 忽略单纯的修饰键按下
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return
            
        # Backspace/Delete 清除快捷键
        if key in (Qt.Key_Backspace, Qt.Key_Delete):
            self.setText("")
            self._key_sequence = ""
            self.hotkeyChanged.emit("")
            return

        # 构建快捷键字符串
        # Qt 的修饰符处理
        qt_modifiers = Qt.NoModifier
        if modifiers & Qt.ShiftModifier: qt_modifiers |= Qt.ShiftModifier
        if modifiers & Qt.ControlModifier: qt_modifiers |= Qt.ControlModifier
        if modifiers & Qt.AltModifier: qt_modifiers |= Qt.AltModifier
        if modifiers & Qt.MetaModifier: qt_modifiers |= Qt.MetaModifier
        
        # 组合
        key_combine = qt_modifiers | key
        sequence = QKeySequence(key_combine)
        # 使用 PortableText 以保证跨平台兼容性，并且与我们的解析器匹配 (Ctrl+Shift+A)
        key_str = sequence.toString(QKeySequence.PortableText)
        
        self.setText(key_str)
        self._key_sequence = key_str
        self.hotkeyChanged.emit(key_str)
        
    def setHotkey(self, hotkey: str):
        self._key_sequence = hotkey
        self.setText(hotkey)

class HotkeySettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = SettingsController()
        self.config_manager = ConfigManager.get_instance()
        self._init_ui()
        self._load_data()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        group = QGroupBox("全局快捷键")
        form = QFormLayout(group)
        
        self.recorders = {}
        
        # 定义快捷键项
        self.hotkey_items = [
            ("screenshot", "截图 OCR"),
            ("clipboard", "剪贴板 OCR"),
            ("show_hide", "显示/隐藏主窗口"), # 预留
        ]
        
        for action, label in self.hotkey_items:
            recorder = HotkeyRecorder()
            form.addRow(label + ":", recorder)
            self.recorders[action] = recorder
            
        layout.addWidget(group)
        
        # 说明
        info_label = QLabel("提示：点击输入框并按下组合键即可设置。按 Backspace 或 Delete 可清除。")
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        # 保存按钮
        save_btn = QPushButton("保存快捷键配置")
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)
        
    def _load_data(self):
        for action, _ in self.hotkey_items:
            val = self.config_manager.get(f"hotkeys.{action}", "")
            if val:
                self.recorders[action].setHotkey(val)
                
    def _on_save(self):
        try:
            for action, recorder in self.recorders.items():
                val = recorder.text()
                self.config_manager.set(f"hotkeys.{action}", val)
                
            self.config_manager.save()
            QMessageBox.information(self, "成功", "快捷键配置已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")
