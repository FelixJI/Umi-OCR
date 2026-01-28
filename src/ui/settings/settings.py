#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 设置界面

Author: Umi-OCR Team
Date: 2026-01-27
"""

from PySide6.QtWidgets import QMessageBox, QCheckBox, QVBoxLayout
from PySide6.QtCore import QObject

from src.controllers.settings_controller import SettingsController
from src.utils.logger import get_logger
from src.utils.startup_manager import StartupManager

logger = get_logger()


class SettingsWindow(QObject):
    """
    设置界面控制器
    """

    def __init__(self, ui, parent=None):
        """
        Args:
            ui: Ui_MainWindow 实例
            parent: 父对象
        """
        super().__init__(parent)
        self.ui = ui
        self.logger = logger
        self.controller = SettingsController()

        self._init_ui()
        self._connect_signals()

        self.logger.info("设置界面初始化完成")

    def _init_ui(self):
        """初始化 UI 组件"""
        # 从 ui 对象获取控件
        self.sidebar = self.ui.listWidget_sidebar
        self.pages = self.ui.stackedWidget_pages

        if self.sidebar:
            self.sidebar.clear()
            self.sidebar.addItem("常规设置")
            self.sidebar.addItem("OCR 引擎")
            self.sidebar.addItem("模型管理")
            self.sidebar.addItem("云服务")
            self.sidebar.setCurrentRow(0)

        # Initialize Cloud Settings Panel
        from .cloud_settings import CloudSettingsPanel

        self.cloud_panel = CloudSettingsPanel(
            self.ui.page_cloud, controller=self.controller
        )

        # Add to page_cloud layout
        page_cloud = self.ui.page_cloud
        if page_cloud:
            layout = page_cloud.layout()
            if layout:
                # Index 0 is label, insert after it
                layout.insertWidget(1, self.cloud_panel)
            else:
                layout = QVBoxLayout(page_cloud)
                layout.addWidget(self.cloud_panel)

        # Initialize OCR Settings Panel
        from .ocr_settings import OcrSettingsPanel

        self.ocr_panel = OcrSettingsPanel(
            self.ui.page_ocr_engine, controller=self.controller
        )

        # Initialize Model Download Settings Panel
        from .model_download_settings import ModelDownloadSettingsPanel

        self.model_panel = ModelDownloadSettingsPanel(
            self.ui.page_model, controller=self.controller
        )

        # Add to page_model layout
        page_model = self.ui.page_model
        if page_model:
            layout = page_model.layout()
            if layout:
                # Index 0 is label, insert after it
                layout.insertWidget(1, self.model_panel)
            else:
                layout = QVBoxLayout(page_model)
                layout.addWidget(self.model_panel)

        # Initialize General Settings (Startup, etc.)
        self._init_general_settings()

    def _init_general_settings(self):
        """初始化常规设置页面"""
        page_general = self.ui.page_general
        if not page_general:
            return

        layout = page_general.layout()
        if not layout:
            layout = QVBoxLayout(page_general)

        # Startup Checkbox
        self.cb_startup = QCheckBox("开机自启")
        self.cb_startup.setChecked(StartupManager.is_enabled())
        self.cb_startup.toggled.connect(self._on_startup_toggled)

        # Add after label (index 1)
        layout.insertWidget(1, self.cb_startup)

        # Close to Tray Checkbox
        self.cb_close_to_tray = QCheckBox("关闭窗口时最小化到托盘")
        self.cb_close_to_tray.setChecked(
            self.controller.get_config("ui.close_to_tray", False)
        )
        self.cb_close_to_tray.toggled.connect(self._on_close_to_tray_toggled)
        layout.insertWidget(2, self.cb_close_to_tray)

    def _on_close_to_tray_toggled(self, checked: bool):
        self.controller.set_config("ui.close_to_tray", checked)

    def _on_startup_toggled(self, checked: bool):
        parent_widget = self.ui.page_general
        if checked:
            if not StartupManager.enable():
                QMessageBox.warning(
                    parent_widget,
                    "警告",
                    "无法设置开机自启，请检查权限或杀毒软件拦截。",
                )
                self.cb_startup.setChecked(False)
        else:
            if not StartupManager.disable():
                QMessageBox.warning(parent_widget, "警告", "无法禁用开机自启。")
                self.cb_startup.setChecked(True)

    def _connect_signals(self):
        """连接信号"""
        if self.sidebar:
            self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)

    def _on_sidebar_changed(self, index: int):
        """侧边栏切换"""
        if self.pages:
            self.pages.setCurrentIndex(index)
