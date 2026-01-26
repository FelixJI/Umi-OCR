#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 主窗口控制器

主窗口控制器负责连接主窗口 UI 和业务逻辑层。
在后续阶段中，这里会集成各种功能模块的控制器。

当前阶段主要职责：
- 初始化主窗口
- 管理页面切换逻辑
- 处理菜单和工具栏命令
- 协调各功能模块之间的交互

Author: Umi-OCR Team
Date: 2025-01-26
"""

from typing import Optional

from PySide6.QtCore import QObject, Signal

from src.ui.main_window.main_window import MainWindow
from src.utils.logger import get_logger
from src.utils.config_manager import get_config_manager
from src.utils.i18n import get_i18n_manager


class MainController(QObject):
    """
    主窗口控制器

    负责管理主窗口的业务逻辑和页面导航。
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    # 应用退出信号
    app_exit_requested = Signal()

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, parent: Optional[QObject] = None):
        """
        初始化主窗口控制器

        Args:
            parent: 父对象
        """
        super().__init__(parent)

        # 获取全局服务
        self.logger = get_logger()
        self.config_manager = get_config_manager()
        self.i18n = get_i18n_manager()

        # 记录初始化
        self.logger.info("初始化主窗口控制器")

        # 主窗口实例
        self.main_window: Optional[MainWindow] = None

        # 页面控制器字典（后续阶段填充）
        self.page_controllers = {}

        # 初始化主窗口
        self._init_main_window()

        self.logger.info("主窗口控制器初始化完成")

    def _init_main_window(self):
        """初始化主窗口"""
        # 创建主窗口
        self.main_window = MainWindow()

        # 连接主窗口信号
        self._connect_window_signals()

        self.logger.debug("主窗口创建完成")

    def _connect_window_signals(self):
        """连接主窗口信号"""
        if not self.main_window:
            return

        # 连接窗口关闭信号
        self.main_window.window_closing.connect(self._on_window_closing)

        # 连接页面切换信号
        self.main_window.page_changed.connect(self._on_page_changed)

    # -------------------------------------------------------------------------
    # 窗口管理
    # -------------------------------------------------------------------------

    def show_window(self):
        """显示主窗口"""
        if self.main_window:
            self.main_window.show()
            self.logger.debug("主窗口已显示")

    def hide_window(self):
        """隐藏主窗口"""
        if self.main_window:
            self.main_window.hide()
            self.logger.debug("主窗口已隐藏")

    def close_window(self):
        """关闭主窗口"""
        if self.main_window:
            self.main_window.close()
            self.logger.debug("主窗口已关闭")

    def get_window(self) -> Optional[MainWindow]:
        """
        获取主窗口实例

        Returns:
            Optional[MainWindow]: 主窗口实例
        """
        return self.main_window

    # -------------------------------------------------------------------------
    # 页面管理
    # -------------------------------------------------------------------------

    def _on_page_changed(self, page_index: int):
        """
        页面切换事件处理

        Args:
            page_index: 页面索引（0-5）

        页面索引映射：
            0: 截图 OCR
            1: 批量图片
            2: 批量文档
            3: 二维码
            4: 任务管理
            5: 设置
        """
        page_names = [
            "screenshot_ocr",
            "batch_ocr",
            "batch_doc",
            "qrcode",
            "task_manager",
            "settings"
        ]

        if 0 <= page_index < len(page_names):
            page_name = page_names[page_index]
            self.logger.debug(f"切换到页面: {page_name}")

            # TODO: 在后续阶段中，激活对应的页面控制器
            # 例如：self._activate_page_controller(page_name)

    def _activate_page_controller(self, page_name: str):
        """
        激活指定页面的控制器

        Args:
            page_name: 页面名称

        TODO: 在后续阶段实现
        """
        # 这个方法会在后续阶段中实现
        # 用于激活或初始化对应功能模块的控制器
        pass

    # -------------------------------------------------------------------------
    # 菜单命令处理
    # -------------------------------------------------------------------------

    # 截图 OCR
    def handle_screenshot_ocr(self):
        """处理截图 OCR 命令"""
        self.logger.debug("执行截图 OCR 命令")
        # 切换到截图 OCR 页面
        if self.main_window:
            self.main_window.switch_to_page(0)

    # 批量 OCR
    def handle_batch_ocr(self):
        """处理批量 OCR 命令"""
        self.logger.debug("执行批量 OCR 命令")
        # 切换到批量 OCR 页面
        if self.main_window:
            self.main_window.switch_to_page(1)

    # 任务管理器
    def handle_task_manager(self):
        """处理任务管理器命令"""
        self.logger.debug("执行任务管理器命令")
        # 切换到任务管理器页面
        if self.main_window:
            self.main_window.switch_to_page(4)

    # 设置
    def handle_settings(self):
        """处理设置命令"""
        self.logger.debug("执行设置命令")
        # 切换到设置页面
        if self.main_window:
            self.main_window.switch_to_page(5)

    # 打开文件
    def handle_open_file(self):
        """处理打开文件命令"""
        self.logger.debug("执行打开文件命令")
        # TODO: 在后续阶段实现文件对话框
        from PySide6.QtWidgets import QFileDialog

        if self.main_window:
            file_path, _ = QFileDialog.getOpenFileName(
                self.main_window,
                "选择图片文件",
                "",
                "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff)"
            )
            if file_path:
                self.logger.info(f"选择的文件: {file_path}")
                # TODO: 根据文件类型打开对应的功能模块

    # 导出结果
    def handle_export(self):
        """处理导出命令"""
        self.logger.debug("执行导出命令")
        # TODO: 在后续阶段实现导出功能

    # 退出应用
    def handle_exit(self):
        """处理退出命令"""
        self.logger.debug("执行退出命令")
        # 发送退出信号
        self.app_exit_requested.emit()

    # 切换侧边栏
    def toggle_sidebar(self, visible: bool):
        """
        切换侧边栏显示/隐藏

        Args:
            visible: 是否显示
        """
        self.logger.debug(f"切换侧边栏: {'显示' if visible else '隐藏'}")
        if self.main_window:
            action = self.main_window.actionToggleSidebar
            if action:
                action.setChecked(visible)

    # 切换全屏
    def toggle_fullscreen(self, fullscreen: bool):
        """
        切换全屏模式

        Args:
            fullscreen: 是否全屏
        """
        self.logger.debug(f"切换全屏模式: {'全屏' if fullscreen else '窗口'}")
        if self.main_window:
            action = self.main_window.actionFullscreen
            if action:
                action.setChecked(fullscreen)

    # -------------------------------------------------------------------------
    # 事件处理
    # -------------------------------------------------------------------------

    def _on_window_closing(self):
        """窗口关闭事件处理"""
        self.logger.info("主窗口关闭请求")

        # 保存配置
        self.config_manager.save()

        # 发送退出信号
        self.app_exit_requested.emit()

    # -------------------------------------------------------------------------
    # 公共方法
    # -------------------------------------------------------------------------

    def show_status_message(self, message: str, timeout: int = 3000):
        """
        在状态栏显示消息

        Args:
            message: 消息文本
            timeout: 显示时长（毫秒）
        """
        if self.main_window:
            self.main_window.show_status_message(message, timeout)

    def get_logger(self):
        """
        获取日志记录器

        Returns:
            Logger: 日志记录器
        """
        return self.logger

    def get_config_manager(self):
        """
        获取配置管理器

        Returns:
            ConfigManager: 配置管理器
        """
        return self.config_manager

    def get_i18n_manager(self):
        """
        获取多语言管理器

        Returns:
            I18nManager: 多语言管理器
        """
        return self.i18n

    def get_main_window(self) -> Optional[MainWindow]:
        """
        获取主窗口实例

        Returns:
            Optional[MainWindow]: 主窗口实例
        """
        return self.main_window
