#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 快捷键输入控件

提供快捷键录入功能，支持组合键捕获和冲突检测。

主要功能:
- 快捷键捕获（Ctrl+Shift+A 格式）
- 组合键解析
- 冲突检测
- 清除/重置功能

Author: Umi-OCR Team
Date: 2026-01-27
"""

from typing import Optional, Set
from PySide6.QtWidgets import QLineEdit, QWidget, QHBoxLayout, QPushButton, QSizePolicy
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence

# =============================================================================
# 快捷键输入控件
# =============================================================================


class HotkeyInput(QLineEdit):
    """
    快捷键输入控件

    用于捕获用户按下的组合键，生成快捷键字符串。

    使用示例:
        hotkey_input = HotkeyInput()
        hotkey_input.hotkey_changed.connect(on_hotkey_changed)
        hotkey_input.set_hotkey("Ctrl+Shift+A")

    信号:
        hotkey_changed(str): 快捷键变更时发射，参数为快捷键字符串
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    # 快捷键变更信号
    # 参数: hotkey_str (str) - 快捷键字符串，如 "Ctrl+Shift+A"
    hotkey_changed = Signal(str)

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化快捷键输入控件

        Args:
            parent: 父控件
        """
        super().__init__(parent)

        # 当前快捷键字符串
        self._hotkey: str = ""

        # 已注册的快捷键集合（用于冲突检测）
        self._registered_hotkeys: Set[str] = set()

        # 初始化UI
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化 UI 设置"""
        self.setReadOnly(True)
        self.setPlaceholderText("点击并按下快捷键...")
        self.setClearButtonEnabled(False)

        # 样式设置
        self.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                font-size: 13px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fafafa;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
                background-color: #fff;
            }
            QLineEdit:hover {
                border-color: #999;
            }
        """)

    # -------------------------------------------------------------------------
    # 事件处理
    # -------------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        按键事件处理

        捕获用户按下的组合键，生成快捷键字符串。

        Args:
            event: 按键事件
        """
        key = event.key()
        modifiers = event.modifiers()

        # 忽略单纯的修饰键按下
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return

        # Backspace/Delete/Escape 清除快捷键
        if key in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Escape):
            self.clear_hotkey()
            return

        # 构建快捷键字符串
        qt_modifiers = Qt.KeyboardModifier(0)
        if modifiers & Qt.ShiftModifier:
            qt_modifiers |= Qt.ShiftModifier
        if modifiers & Qt.ControlModifier:
            qt_modifiers |= Qt.ControlModifier
        if modifiers & Qt.AltModifier:
            qt_modifiers |= Qt.AltModifier
        if modifiers & Qt.MetaModifier:
            qt_modifiers |= Qt.MetaModifier

        # 组合键值
        key_combine = int(qt_modifiers) | key
        sequence = QKeySequence(key_combine)

        # 使用 PortableText 格式（跨平台兼容）
        hotkey_str = sequence.toString(QKeySequence.PortableText)

        # 设置快捷键
        self._set_hotkey_internal(hotkey_str)

    def focusInEvent(self, event) -> None:
        """获得焦点时的处理"""
        super().focusInEvent(event)
        self.setPlaceholderText("按下组合键...")

    def focusOutEvent(self, event) -> None:
        """失去焦点时的处理"""
        super().focusOutEvent(event)
        self.setPlaceholderText("点击并按下快捷键...")

    # -------------------------------------------------------------------------
    # 公共接口
    # -------------------------------------------------------------------------

    def get_hotkey(self) -> str:
        """
        获取当前快捷键

        Returns:
            str: 快捷键字符串，如 "Ctrl+Shift+A"
        """
        return self._hotkey

    def set_hotkey(self, hotkey: str) -> None:
        """
        设置快捷键

        Args:
            hotkey: 快捷键字符串，如 "Ctrl+Shift+A"
        """
        self._hotkey = hotkey
        self.setText(hotkey)

    def clear_hotkey(self) -> None:
        """清除快捷键"""
        self._hotkey = ""
        self.setText("")
        self.hotkey_changed.emit("")

    def set_registered_hotkeys(self, hotkeys: Set[str]) -> None:
        """
        设置已注册的快捷键集合（用于冲突检测）

        Args:
            hotkeys: 已注册的快捷键集合
        """
        self._registered_hotkeys = hotkeys

    def check_conflict(self, hotkey: str) -> bool:
        """
        检查快捷键是否冲突

        Args:
            hotkey: 要检查的快捷键字符串

        Returns:
            bool: 是否冲突
        """
        if not hotkey:
            return False
        return hotkey in self._registered_hotkeys

    # -------------------------------------------------------------------------
    # 私有方法
    # -------------------------------------------------------------------------

    def _set_hotkey_internal(self, hotkey_str: str) -> None:
        """
        内部设置快捷键

        Args:
            hotkey_str: 快捷键字符串
        """
        self._hotkey = hotkey_str
        self.setText(hotkey_str)
        self.hotkey_changed.emit(hotkey_str)


# =============================================================================
# 带清除按钮的快捷键输入控件
# =============================================================================


class HotkeyInputWithClear(QWidget):
    """
    带清除按钮的快捷键输入控件

    包含一个 HotkeyInput 和一个清除按钮。

    使用示例:
        hotkey_widget = HotkeyInputWithClear()
        hotkey_widget.hotkey_changed.connect(on_hotkey_changed)
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    hotkey_changed = Signal(str)

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化控件

        Args:
            parent: 父控件
        """
        super().__init__(parent)

        # 创建子控件
        self._input = HotkeyInput(self)
        self._clear_btn = QPushButton("清除", self)

        # 初始化UI
        self._setup_ui()

        # 连接信号
        self._connect_signals()

    def _setup_ui(self) -> None:
        """初始化 UI 布局"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 输入框
        self._input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self._input)

        # 清除按钮
        self._clear_btn.setFixedWidth(60)
        self._clear_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                font-size: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f5f5f5;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border-color: #999;
            }
            QPushButton:pressed {
                background-color: #ddd;
            }
        """)
        layout.addWidget(self._clear_btn)

    def _connect_signals(self) -> None:
        """连接信号"""
        self._input.hotkey_changed.connect(self.hotkey_changed.emit)
        self._clear_btn.clicked.connect(self._input.clear_hotkey)

    # -------------------------------------------------------------------------
    # 公共接口（代理到 HotkeyInput）
    # -------------------------------------------------------------------------

    def get_hotkey(self) -> str:
        """获取当前快捷键"""
        return self._input.get_hotkey()

    def set_hotkey(self, hotkey: str) -> None:
        """设置快捷键"""
        self._input.set_hotkey(hotkey)

    def clear_hotkey(self) -> None:
        """清除快捷键"""
        self._input.clear_hotkey()

    def set_registered_hotkeys(self, hotkeys: Set[str]) -> None:
        """设置已注册的快捷键集合"""
        self._input.set_registered_hotkeys(hotkeys)

    def check_conflict(self, hotkey: str) -> bool:
        """检查快捷键是否冲突"""
        return self._input.check_conflict(hotkey)
