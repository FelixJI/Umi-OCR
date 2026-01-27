#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction

logger = logging.getLogger(__name__)

class TrayManager(QObject):
    """
    系统托盘管理器
    
    右键菜单:
    - 显示主窗口
    - 截图 OCR
    - 剪贴板 OCR
    - 暂停/恢复任务
    - 退出
    """
    
    show_window_requested = Signal()
    screenshot_requested = Signal()
    clipboard_ocr_requested = Signal()
    pause_all_requested = Signal()
    quit_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tray = QSystemTrayIcon(parent)
        self._menu = QMenu()
        self._init_tray()
        
    def _init_tray(self):
        # 设置图标
        # 尝试查找图标文件
        possible_paths = [
            Path("images/icons/umiocr.svg"),
            Path("src/resources/icons/umiocr.svg"),
            Path("resources/icons/umiocr.svg"),
        ]
        
        icon_path = None
        for p in possible_paths:
            if p.exists():
                icon_path = p
                break
                
        if icon_path:
            self._tray.setIcon(QIcon(str(icon_path)))
        else:
            logger.warning("未找到托盘图标文件")

        # 设置菜单
        self._setup_menu()
        self._tray.setContextMenu(self._menu)
        
        # 连接信号
        self._tray.activated.connect(self._on_activated)
        
        # 显示托盘
        self._tray.show()
        logger.info("系统托盘已初始化")
        
    def _setup_menu(self):
        self._menu.clear()
        
        # 显示主窗口
        act_show = QAction("显示主窗口", self)
        act_show.triggered.connect(self.show_window_requested.emit)
        self._menu.addAction(act_show)
        
        self._menu.addSeparator()
        
        # 截图 OCR
        act_ss = QAction("📷 截图 OCR", self)
        act_ss.triggered.connect(self.screenshot_requested.emit)
        self._menu.addAction(act_ss)
        
        # 剪贴板 OCR
        act_clip = QAction("📋 剪贴板 OCR", self)
        act_clip.triggered.connect(self.clipboard_ocr_requested.emit)
        self._menu.addAction(act_clip)
        
        self._menu.addSeparator()
        
        # 暂停/恢复
        self.act_pause = QAction("⏸ 暂停所有任务", self)
        self.act_pause.triggered.connect(self.pause_all_requested.emit)
        self._menu.addAction(self.act_pause)
        
        self._menu.addSeparator()
        
        # 退出
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(act_quit)
        
    def _on_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.Trigger:
            # 单击，可以做些什么，或者不做
            pass
        elif reason == QSystemTrayIcon.DoubleClick:
            # 双击显示主窗口
            self.show_window_requested.emit()
            
    def show_notification(self, title: str, message: str, duration_ms: int = 3000):
        """显示气泡通知"""
        self._tray.showMessage(title, message, QSystemTrayIcon.Information, duration_ms)
        
    def update_pause_state(self, is_paused: bool):
        """更新暂停菜单项状态"""
        if is_paused:
            self.act_pause.setText("▶ 恢复所有任务")
        else:
            self.act_pause.setText("⏸ 暂停所有任务")
