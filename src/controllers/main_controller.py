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
from src.platforms.win32.hotkey_manager import HotkeyManager
from src.services.server.http_server import HTTPServer
import asyncio


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

        # 初始化系统托盘 (阶段21)
        self._init_tray()

        # 初始化全局快捷键 (阶段22)
        self._init_hotkeys()

        # 初始化悬浮工具栏 (阶段24)
        self._init_floating_bar()

        # 初始化 HTTP 服务 (阶段26)
        self._init_http_server()

        self.logger.info("主窗口控制器初始化完成")

    def _init_http_server(self):
        """初始化 HTTP 服务"""
        # 检查是否启用
        if not self.config_manager.get("system.http_server_enabled", False):
            return

        self.http_server = HTTPServer()

        # 使用 qasync 将 asyncio 集成到 Qt 事件循环
        # 注意：这需要在 main.py 中正确设置 loop
        try:
            loop = asyncio.get_event_loop()
            asyncio.ensure_future(self.http_server.start(), loop=loop)
        except Exception as e:
            self.logger.error(f"无法启动 HTTP 服务: {e}")

    def _init_floating_bar(self):
        """初始化悬浮工具栏"""
        from src.ui.floating_bar.floating_bar import FloatingBar

        self.floating_bar = FloatingBar()

        # 连接信号
        self.floating_bar.screenshot_clicked.connect(self.handle_screenshot_ocr)
        self.floating_bar.clipboard_ocr_clicked.connect(self.handle_clipboard_ocr)
        self.floating_bar.batch_ocr_clicked.connect(self.handle_batch_ocr)
        self.floating_bar.settings_clicked.connect(self.handle_settings)

        # 初始状态
        # 从配置读取模式（如果 FloatingBar 有 set_mode 方法）
        try:
            mode = self.config_manager.get("ui.floating_bar_mode", "always_visible")
            if hasattr(self.floating_bar, "set_mode"):
                self.floating_bar.set_mode(mode)
        except Exception as e:
            self.logger.warning(f"设置悬浮栏模式失败: {e}")

    def _init_hotkeys(self):
        """初始化全局快捷键"""
        self.hotkey_manager = HotkeyManager(self)
        self.hotkey_manager.hotkey_triggered.connect(self._on_hotkey_triggered)
        self.hotkey_manager.start()

        # 初始注册
        self._update_hotkeys_registration()

        # 监听配置变更
        self.config_manager.config_changed.connect(self._on_config_changed_hotkey)

    def _update_hotkeys_registration(self):
        """更新热键注册"""
        # Screenshot
        key = self.config_manager.get("hotkeys.screenshot", "")
        if key:
            self.hotkey_manager.register_hotkey("screenshot", key)
        else:
            self.hotkey_manager.unregister_hotkey("screenshot")

        # Clipboard
        key = self.config_manager.get("hotkeys.clipboard", "")
        if key:
            self.hotkey_manager.register_hotkey("clipboard", key)
        else:
            self.hotkey_manager.unregister_hotkey("clipboard")

        # Show/Hide
        key = self.config_manager.get("hotkeys.show_hide", "")
        if key:
            self.hotkey_manager.register_hotkey("show_hide", key)
        else:
            self.hotkey_manager.unregister_hotkey("show_hide")

    def _on_config_changed_hotkey(self, key_path, old, new):
        """配置变更处理"""
        if key_path.startswith("hotkeys."):
            self._update_hotkeys_registration()

    def _on_hotkey_triggered(self, action_name):
        """热键触发处理"""
        self.logger.info(f"热键触发: {action_name}")
        if action_name == "screenshot":
            self.handle_screenshot_ocr()
        elif action_name == "clipboard":
            self.handle_clipboard_ocr()
        elif action_name == "show_hide":
            if self.main_window and self.main_window.isVisible():
                self.hide_window()
            else:
                self.show_window()
                if self.main_window:
                    self.main_window.activateWindow()

    def _init_tray(self):
        """初始化系统托盘"""
        from src.utils.tray_manager import TrayManager

        self.tray_manager = TrayManager(self)

        # 连接托盘信号
        self.tray_manager.show_window_requested.connect(self.show_window)
        self.tray_manager.screenshot_requested.connect(self.handle_screenshot_ocr)
        self.tray_manager.clipboard_ocr_requested.connect(self.handle_clipboard_ocr)
        self.tray_manager.pause_all_requested.connect(self.handle_pause_all)
        self.tray_manager.quit_requested.connect(self.handle_exit_from_tray)

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
            "settings",
        ]

        if 0 <= page_index < len(page_names):
            page_name = page_names[page_index]
            self.logger.debug(f"切换到页面: {page_name}")

            # 激活对应的页面控制器
            self._activate_page_controller(page_name)

    def _activate_page_controller(self, page_name: str):
        """
        激活指定页面的控制器

        Args:
            page_name: 页面名称
        """
        self.logger.debug(f"激活页面控制器: {page_name}")

        # 如果控制器不存在，则创建
        if page_name not in self.page_controllers:
            try:
                if page_name == "screenshot_ocr":
                    from src.controllers.screenshot_controller import (
                        ScreenshotController,
                    )

                    self.page_controllers[page_name] = ScreenshotController(
                        self.main_window
                    )
                elif page_name == "batch_ocr":
                    from src.controllers.batch_ocr_controller import BatchOcrController

                    self.page_controllers[page_name] = BatchOcrController(
                        self.main_window
                    )
                elif page_name == "batch_doc":
                    from src.controllers.batch_doc_controller import BatchDocController

                    self.page_controllers[page_name] = BatchDocController(
                        self.main_window
                    )
                elif page_name == "qrcode":
                    from src.controllers.qrcode_controller import QrcodeController

                    self.page_controllers[page_name] = QrcodeController(
                        self.main_window
                    )
                elif page_name == "settings":
                    # Settings 需要 ui 对象，稍后处理
                    self.page_controllers[page_name] = None
                elif page_name == "task_manager":
                    from src.ui.task_manager.task_manager import TaskManagerWindow

                    self.page_controllers[page_name] = TaskManagerWindow()

                self.logger.info(f"页面控制器已创建: {page_name}")
            except Exception as e:
                self.logger.error(f"创建页面控制器失败 {page_name}: {e}")
        else:
            self.logger.debug(f"页面控制器已存在: {page_name}")

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
        from PySide6.QtWidgets import QFileDialog
        import os

        if self.main_window:
            file_path, _ = QFileDialog.getOpenFileName(
                self.main_window,
                "选择文件",
                "",
                "所有支持的文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.pdf *.doc *.docx);;"+
                "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff);;"+
                "文档文件 (*.pdf *.doc *.docx)",
            )
            if file_path and os.path.exists(file_path):
                self.logger.info(f"选择的文件: {file_path}")
                # 根据文件类型打开对应的功能模块
                file_ext = os.path.splitext(file_path)[1].lower()

                # 图片文件 -> 批量 OCR
                if file_ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
                    self.show_status_message("正在打开批量 OCR 页面...")
                    self.handle_batch_ocr()
                    # TODO: 将文件路径传递给批量 OCR 控制器

                # 文档文件 -> 批量文档
                elif file_ext in [".pdf", ".doc", ".docx"]:
                    self.show_status_message("正在打开批量文档页面...")
                    # TODO: 切换到批量文档页面
                    # self.main_window.switch_to_page(2)

                else:
                    self.show_status_message("不支持的文件类型")

    # 导出结果
    def handle_export(self):
        """处理导出命令"""
        self.logger.debug("执行导出命令")
        from PySide6.QtWidgets import QMessageBox

        if self.main_window:
            # TODO: 根据当前活动页面确定要导出的内容
            # 暂时只显示提示信息
            QMessageBox.information(
                self.main_window,
                "导出功能",
                "导出功能尚未完全实现。请使用各个页面提供的导出按钮。",
                QMessageBox.StandardButton.Ok,
            )

    # 剪贴板 OCR
    def handle_clipboard_ocr(self):
        """处理剪贴板 OCR 命令"""
        self.logger.debug("执行剪贴板 OCR 命令")
        from PySide6.QtWidgets import QApplication, QMessageBox

        clipboard = QApplication.clipboard()
        image = clipboard.image()

        if not image.isNull():
            self.show_status_message("正在识别剪贴板图片...")
            # TODO: 将图片传递给截图 OCR 控制器进行识别
            self.handle_screenshot_ocr()
        else:
            text = clipboard.text()
            if text:
                self.show_status_message(f"剪贴板文本: {text[:50]}...")
                self.logger.debug(f"剪贴板内容: {text}")
            else:
                self.show_status_message("剪贴板为空")
                QMessageBox.information(
                    self.main_window,
                    "提示",
                    "剪贴板中没有可识别的图片或文本。",
                    QMessageBox.StandardButton.Ok,
                )

    # 暂停/恢复所有任务
    def handle_pause_all(self):
        """处理暂停/恢复所有任务命令"""
        self.logger.debug("执行暂停/恢复所有任务命令")

        # 检查是否有任务管理器控制器
        if "task_manager" in self.page_controllers:
            task_manager = self.page_controllers["task_manager"]
            if hasattr(task_manager, "toggle_pause_all"):
                task_manager.toggle_pause_all()
                self.show_status_message("已切换所有任务的暂停状态")
            else:
                self.show_status_message("任务管理器不支持暂停功能")
        else:
            self.show_status_message("任务管理器未初始化")
            self.logger.warning("任务管理器未初始化，无法执行暂停/恢复操作")

    def handle_exit_from_tray(self):
        """处理托盘退出命令"""
        self.logger.info("托盘请求退出")
        self.config_manager.save()
        self.app_exit_requested.emit()

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
        # 检查是否关闭到托盘
        close_to_tray = self.config_manager.get("ui.close_to_tray", False)

        if close_to_tray:
            self.logger.info("主窗口关闭请求 -> 最小化到托盘")
            self.hide_window()
            if self.tray_manager:
                self.tray_manager.show_notification("Umi-OCR", "程序已最小化到托盘运行")
        else:
            self.logger.info("主窗口关闭请求 -> 退出程序")
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
