# src/platforms/win32/hotkey_manager.py

import ctypes
import logging
from typing import Dict, Tuple

from PySide6.QtCore import QObject, Signal, QAbstractNativeEventFilter
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

# Win32 Constants
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# VK Codes Mapping (Simplified)
VK_MAPPING = {
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "PAUSE": 0x13,
    "CAPS LOCK": 0x14,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "PAGE UP": 0x21,
    "PAGE DOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "PRINT SCREEN": 0x2C,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
    "0": 0x30,
    "1": 0x31,
    "2": 0x32,
    "3": 0x33,
    "4": 0x34,
    "5": 0x35,
    "6": 0x36,
    "7": 0x37,
    "8": 0x38,
    "9": 0x39,
    "A": 0x41,
    "B": 0x42,
    "C": 0x43,
    "D": 0x44,
    "E": 0x45,
    "F": 0x46,
    "G": 0x47,
    "H": 0x48,
    "I": 0x49,
    "J": 0x4A,
    "K": 0x4B,
    "L": 0x4C,
    "M": 0x4D,
    "N": 0x4E,
    "O": 0x4F,
    "P": 0x50,
    "Q": 0x51,
    "R": 0x52,
    "S": 0x53,
    "T": 0x54,
    "U": 0x55,
    "V": 0x56,
    "W": 0x57,
    "X": 0x58,
    "Y": 0x59,
    "Z": 0x5A,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
}


class WinEventFilter(QAbstractNativeEventFilter):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def nativeEventFilter(self, eventType, message):
        if eventType == "windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                hotkey_id = msg.wParam
                self.manager._on_hotkey_triggered(hotkey_id)
        return False, 0


class HotkeyManager(QObject):
    hotkey_triggered = Signal(str)  # action_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._action_map: Dict[int, str] = {}  # id -> action_name
        self._id_map: Dict[str, int] = {}  # action_name -> id
        self._next_id = 1
        self._filter = WinEventFilter(self)
        self._is_started = False

        # 加载 user32
        try:
            self.user32 = ctypes.windll.user32
        except Exception as e:
            logger.error(f"无法加载 user32.dll: {e}")
            self.user32 = None

    def start(self):
        if not self._is_started and self.user32:
            QApplication.instance().installNativeEventFilter(self._filter)
            self._is_started = True
            logger.info("全局热键管理器已启动")

    def stop(self):
        if self._is_started:
            self.unregister_all()
            QApplication.instance().removeNativeEventFilter(self._filter)
            self._is_started = False
            logger.info("全局热键管理器已停止")

    def register_hotkey(self, action_name: str, key_sequence_str: str) -> bool:
        """
        注册全局热键

        Args:
            action_name: 动作名称（如 "screenshot"）
            key_sequence_str: 快捷键字符串（如 "Ctrl+Shift+A"）

        Returns:
            bool: 是否注册成功
        """
        if not key_sequence_str or not self.user32:
            return False

        # 如果已经注册了该动作，先注销
        if action_name in self._id_map:
            self.unregister_hotkey(action_name)

        # 解析快捷键
        modifiers, vk_code = self._parse_key_sequence(key_sequence_str)
        if vk_code == 0:
            logger.error(f"无法解析快捷键: {key_sequence_str}")
            return False

        # 生成 ID
        hotkey_id = self._next_id
        self._next_id += 1

        # 注册
        # RegisterHotKey(hWnd, id, fsModifiers, vk)
        # hWnd=None means thread message queue
        success = self.user32.RegisterHotKey(
            None, hotkey_id, modifiers | MOD_NOREPEAT, vk_code
        )

        if success:
            self._action_map[hotkey_id] = action_name
            self._id_map[action_name] = hotkey_id
            logger.info(
                f"注册热键成功: {action_name} -> {key_sequence_str} (id={hotkey_id})"
            )
            return True
        else:
            err_code = ctypes.get_last_error()
            logger.error(
                f"注册热键失败: {action_name} -> {key_sequence_str} (ErrorCode={err_code})"
            )
            return False

    def unregister_hotkey(self, action_name: str):
        if not self.user32:
            return

        if action_name in self._id_map:
            hotkey_id = self._id_map[action_name]
            self.user32.UnregisterHotKey(None, hotkey_id)
            del self._id_map[action_name]
            del self._action_map[hotkey_id]
            logger.info(f"注销热键: {action_name}")

    def unregister_all(self):
        if not self.user32:
            return

        for hotkey_id in list(self._action_map.keys()):
            self.user32.UnregisterHotKey(None, hotkey_id)
        self._action_map.clear()
        self._id_map.clear()
        logger.info("已注销所有热键")

    def _on_hotkey_triggered(self, hotkey_id: int):
        if hotkey_id in self._action_map:
            action_name = self._action_map[hotkey_id]
            logger.debug(f"热键触发: {action_name} (id={hotkey_id})")
            self.hotkey_triggered.emit(action_name)

    def _parse_key_sequence(self, key_str: str) -> Tuple[int, int]:
        """解析 Qt 风格的快捷键字符串为 Win32 Modifiers 和 VK Code"""
        parts = key_str.upper().split("+")
        modifiers = 0
        vk_code = 0

        for part in parts:
            part = part.strip()
            if part in ["CTRL", "CONTROL"]:
                modifiers |= MOD_CONTROL
            elif part == "SHIFT":
                modifiers |= MOD_SHIFT
            elif part == "ALT":
                modifiers |= MOD_ALT
            elif part in ["WIN", "META", "WINDOWS"]:
                modifiers |= MOD_WIN
            else:
                # Key
                if part in VK_MAPPING:
                    vk_code = VK_MAPPING[part]
                elif len(part) == 1:
                    # ASCII char, try to map to VK
                    # A-Z is same as ASCII
                    # 0-9 is same as ASCII
                    ord_val = ord(part)
                    if (ord_val >= 48 and ord_val <= 57) or (
                        ord_val >= 65 and ord_val <= 90
                    ):
                        vk_code = ord_val
                    else:
                        logger.warning(f"未知按键: {part}")
                else:
                    logger.warning(f"未知按键: {part}")

        return modifiers, vk_code
