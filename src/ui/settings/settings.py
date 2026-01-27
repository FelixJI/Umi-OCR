#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 设置界面

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QWidget, QListWidget, QStackedWidget, QMessageBox, QLineEdit
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt

from src.controllers.settings_controller import SettingsController
from src.utils.logger import get_logger

logger = get_logger()


class SettingsWindow(QWidget):
    """
    设置界面
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.logger = logger
        self.controller = SettingsController()
        
        self._load_ui()
        self._init_ui()
        self._connect_signals()
        
        self.logger.info("设置界面初始化完成")

    def _load_ui(self):
        """加载 UI 文件"""
        try:
            ui_file = Path(__file__).parent / "settings.ui"
            if not ui_file.exists():
                raise FileNotFoundError(f"UI 文件不存在: {ui_file}")

            ui_loader = QUiLoader()
            self.ui = ui_loader.load(str(ui_file), self)
            
            # Make sure the UI widget resizes with this widget
            # Actually, usually we layout the UI widget inside this widget
            # or copy children.
            # Simplified approach: Set layout
            from PySide6.QtWidgets import QVBoxLayout
            layout = QVBoxLayout(self)
            layout.addWidget(self.ui)
            layout.setContentsMargins(0, 0, 0, 0)

            # 导入 UI 元素
            self.sidebar = self.ui.findChild(QListWidget, "listWidget_sidebar")
            self.pages = self.ui.findChild(QStackedWidget, "stackedWidget_pages")
            
        except Exception as e:
            self.logger.error(f"加载设置界面 UI 失败: {e}", exc_info=True)

    def _init_ui(self):
        """初始化 UI 组件"""
        if self.sidebar:
            self.sidebar.clear()
            self.sidebar.addItem("常规设置")
            self.sidebar.addItem("OCR 引擎")
            self.sidebar.addItem("云服务")
            self.sidebar.addItem("快捷键")
            self.sidebar.setCurrentRow(0)

        # Initialize Cloud Settings Panel
        from .cloud_settings import CloudSettingsPanel
        self.cloud_panel = CloudSettingsPanel(self)
        
        # Add to page_cloud layout
        page_cloud = self.ui.findChild(QWidget, "page_cloud")
        if page_cloud:
            layout = page_cloud.layout()
            if layout:
                # Index 0 is label, insert after it
                layout.insertWidget(1, self.cloud_panel)
            else:
                from PySide6.QtWidgets import QVBoxLayout
                layout = QVBoxLayout(page_cloud)
                layout.addWidget(self.cloud_panel)

        # Initialize Hotkey Settings Panel
        from .hotkey_settings import HotkeySettingsPanel
        self.hotkey_panel = HotkeySettingsPanel(self)
        if self.pages:
            self.pages.addWidget(self.hotkey_panel)
            
        # Initialize General Settings (Startup, etc.)
        self._init_general_settings()

    def _init_general_settings(self):
        """初始化常规设置页面"""
        page_general = self.ui.findChild(QWidget, "page_general")
        if not page_general:
            return
            
        layout = page_general.layout()
        if not layout:
            from PySide6.QtWidgets import QVBoxLayout
            layout = QVBoxLayout(page_general)
            
        # Startup Checkbox
        from PySide6.QtWidgets import QCheckBox
        from utils.startup_manager import StartupManager
        
        self.cb_startup = QCheckBox("开机自启")
        self.cb_startup.setChecked(StartupManager.is_enabled())
        self.cb_startup.toggled.connect(self._on_startup_toggled)
        
        # Add after label (index 1)
        layout.insertWidget(1, self.cb_startup)
        
    def _on_startup_toggled(self, checked: bool):
        from utils.startup_manager import StartupManager
        if checked:
            if not StartupManager.enable():
                QMessageBox.warning(self, "警告", "无法设置开机自启，请检查权限或杀毒软件拦截。")
                self.cb_startup.setChecked(False)
        else:
            if not StartupManager.disable():
                QMessageBox.warning(self, "警告", "无法禁用开机自启。")
                self.cb_startup.setChecked(True)

    def _connect_signals(self):
        """连接信号"""
        if self.sidebar:
            self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)

    def _on_sidebar_changed(self, index: int):
        """侧边栏切换"""
        if self.pages:
            self.pages.setCurrentIndex(index)
