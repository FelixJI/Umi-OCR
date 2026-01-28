#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 主窗口

主窗口类，负责：
- 加载和管理主窗口 UI
- 标签页导航和视图切换
- 状态栏更新
- 集成日志、配置、多语言等系统功能

Author: Umi-OCR Team
Date: 2025-01-26
"""

import sys
from typing import Optional

from PySide6.QtWidgets import QMainWindow, QWidget, QLabel, QMessageBox, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from src.utils.logger import get_logger
from src.utils.config_manager import get_config_manager
from src.utils.i18n import get_i18n_manager
from src.ui.main_window.ui_main_window import Ui_MainWindow
from src.ui.settings.settings import SettingsWindow
from src.ui.screenshot_ocr.screenshot_ocr import ScreenshotOCRView
from src.ui.batch_ocr.batch_ocr import BatchOCRView
from src.ui.batch_doc.batch_doc import BatchDocView
from src.ui.qrcode.qrcode import QRCodeView
from src.ui.task_manager.task_manager import TaskManagerView


class MainWindow(QMainWindow):
    """
    Umi-OCR 主窗口

    负责管理整个应用程序的主界面，包括标签页导航、内容区域显示等。
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    # 页面切换信号
    # 参数: 页面索引
    page_changed = Signal(int)

    # 窗口关闭信号
    window_closing = Signal()

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化主窗口

        Args:
            parent: 父窗口
        """
        super().__init__(parent)

        # 获取全局服务
        self.logger = get_logger()
        self.config_manager = get_config_manager()
        self.i18n = get_i18n_manager()

        # 记录初始化
        self.logger.info("初始化主窗口")

        # 加载 UI
        self._load_ui()

        # 初始化 UI 组件
        self._init_ui_components()

        # 连接信号和槽
        self._connect_signals()

        # 加载窗口状态
        self._load_window_state()

        # 应用样式优化
        self._apply_ui_styles()

        # 应用多语言
        self._apply_translations()

        self.logger.info("主窗口初始化完成")

    def _apply_ui_styles(self):
        """应用 UI 样式优化"""
        # 1. 标签页样式
        if hasattr(self.ui, "tabWidget"):
            self.ui.tabWidget.setStyleSheet("""
                QTabWidget::pane {
                    border: none;
                    background-color: #ffffff;
                }
                QTabBar::tab {
                    background-color: #f3f3f3;
                    border: none;
                    border-bottom: 2px solid transparent;
                    padding: 10px 20px;
                    margin-right: 2px;
                    font-size: 14px;
                    color: #555;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                    border-bottom: 2px solid #0066cc;
                    color: #0066cc;
                    font-weight: bold;
                }
                QTabBar::tab:hover:!selected {
                    background-color: #e8e8e8;
                    color: #333;
                }
            """)

        # 2. 设置页面侧边栏样式
        if hasattr(self.ui, "listWidget_sidebar"):
            self.ui.listWidget_sidebar.setStyleSheet("""
                QListWidget {
                    background-color: #f8f8f8;
                    border-right: 1px solid #e0e0e0;
                    outline: none;
                    font-size: 13px;
                }
                QListWidget::item {
                    height: 40px;
                    padding-left: 15px;
                    margin: 2px 8px;
                    border-radius: 4px;
                    color: #555;
                }
                QListWidget::item:selected {
                    background-color: #e3f2fd;
                    color: #0066cc;
                }
                QListWidget::item:hover:!selected {
                    background-color: #f0f0f0;
                }
            """)

        # 3. 优化滚动条策略
        if hasattr(self.ui, "scrollArea"):
            self.ui.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.ui.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.ui.scrollArea.setStyleSheet(
                "QScrollArea { border: none; background-color: transparent; }"
            )

        # 4. 全局样式微调
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QStatusBar {
                background-color: #f8f8f8;
                border-top: 1px solid #e0e0e0;
                color: #666;
            }
        """)

    def _load_ui(self):
        """加载 UI"""
        try:
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)

            # 导入 UI 元素到实例属性
            self._import_ui_elements()

            self.logger.debug("UI 加载成功")

        except Exception as e:
            self.logger.error(f"加载 UI 失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"无法加载界面：\n{e}")
            sys.exit(1)

    def _import_ui_elements(self):
        """从 UI 对象导入常用元素到实例属性"""
        # 标签页容器
        self.tabWidget = self.ui.tabWidget

        # 状态栏
        self.statusBarWidget = self.ui.statusBar

        # 各个页面
        self.pageScreenshotOcr = self.ui.pageScreenshotOcr
        self.pageBatchOcr = self.ui.pageBatchOcr
        self.pageBatchDoc = self.ui.pageBatchDoc
        self.pageQrcode = self.ui.pageQrcode
        self.pageTaskManager = self.ui.pageTaskManager
        self.pageSettings = self.ui.pageSettings

    def _init_ui_components(self):
        """初始化 UI 组件"""
        # 设置状态栏
        if self.statusBarWidget:
            self._init_status_bar()

        # 设置窗口标题
        self.setWindowTitle(self.i18n.translate("main_window.title"))

        # 调试：检查页面容器是否被找到
        self.logger.debug(f"pageScreenshotOcr: {self.pageScreenshotOcr is not None}")
        self.logger.debug(f"pageBatchOcr: {self.pageBatchOcr is not None}")
        self.logger.debug(f"pageBatchDoc: {self.pageBatchDoc is not None}")
        self.logger.debug(f"pageQrcode: {self.pageQrcode is not None}")
        self.logger.debug(f"pageTaskManager: {self.pageTaskManager is not None}")
        self.logger.debug(f"pageSettings: {self.pageSettings is not None}")

        # 初始化各功能页面视图
        if self.pageScreenshotOcr:
            try:
                self.screenshotView = ScreenshotOCRView()
                self._set_page_widget(self.pageScreenshotOcr, self.screenshotView)
                self.logger.debug("截图OCR视图初始化成功")
            except Exception as e:
                self.logger.error(f"截图OCR视图初始化失败: {e}", exc_info=True)

        if self.pageBatchOcr:
            try:
                self.batchOcrView = BatchOCRView()
                self._set_page_widget(self.pageBatchOcr, self.batchOcrView)
                self.logger.debug("批量OCR视图初始化成功")
            except Exception as e:
                self.logger.error(f"批量OCR视图初始化失败: {e}", exc_info=True)

        if self.pageBatchDoc:
            try:
                self.batchDocView = BatchDocView()
                self._set_page_widget(self.pageBatchDoc, self.batchDocView)
                self.logger.debug("批量文档视图初始化成功")
            except Exception as e:
                self.logger.error(f"批量文档视图初始化失败: {e}", exc_info=True)

        if self.pageQrcode:
            try:
                self.qrcodeView = QRCodeView()
                self._set_page_widget(self.pageQrcode, self.qrcodeView)
                self.logger.debug("二维码视图初始化成功")
            except Exception as e:
                self.logger.error(f"二维码视图初始化失败: {e}", exc_info=True)

        if self.pageTaskManager:
            try:
                self.taskManagerView = TaskManagerView(self.ui)
                self.logger.debug("任务管理视图初始化成功")
            except Exception as e:
                self.logger.error(f"任务管理视图初始化失败: {e}", exc_info=True)

        # 初始化设置页面
        if self.pageSettings:
            try:
                self.settingsWindow = SettingsWindow(self.ui)
                self.logger.debug("设置视图初始化成功")
            except Exception as e:
                self.logger.error(f"设置视图初始化失败: {e}", exc_info=True)

        # 默认显示第一页
        if self.tabWidget and self.tabWidget.count() > 0:
            self.tabWidget.setCurrentIndex(0)

    # -------------------------------------------------------------------------
    # 标签页导航
    # -------------------------------------------------------------------------

    def _connect_signals(self):
        """连接信号和槽"""
        # 标签页切换事件
        if self.tabWidget:
            self.tabWidget.currentChanged.connect(self._on_tab_changed)

        # 连接语言变更信号
        self.i18n.language_changed.connect(self._apply_translations)

        # 连接配置变更信号
        self.config_manager.config_changed.connect(self._on_config_changed)

    def _set_page_widget(self, page_container: QWidget, widget: QWidget):
        """将页面容器中的占位内容替换为实际视图"""
        layout = page_container.layout()
        if layout is None:
            layout = QVBoxLayout(page_container)
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            # 清空现有项
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
        layout.addWidget(widget)
        self.logger.debug(
            f"已将 {type(widget).__name__} 添加到 {page_container.objectName()}，"
            f"layout.count(): {layout.count()}"
        )

    def _on_tab_changed(self, index: int):
        """
        标签页切换事件处理

        Args:
            index: 当前标签页索引
        """
        self.logger.debug(f"切换到标签页: {index}")

        # 发送页面切换信号
        self.page_changed.emit(index)

        # 更新状态栏
        self._update_status_bar_for_page(index)

    def switch_to_page(self, page_index: int):
        """
        切换到指定页面

        Args:
            page_index: 页面索引（0-5）
        """
        if self.tabWidget and 0 <= page_index < self.tabWidget.count():
            self.tabWidget.setCurrentIndex(page_index)

    # -------------------------------------------------------------------------
    # 内容区域管理
    # -------------------------------------------------------------------------

    def get_current_page(self) -> Optional[QWidget]:
        """
        获取当前页面

        Returns:
            Optional[QWidget]: 当前页面的 widget
        """
        if self.tabWidget:
            return self.tabWidget.currentWidget()
        return None

    def get_current_page_index(self) -> int:
        """
        获取当前页面索引

        Returns:
            int: 当前页面索引
        """
        if self.tabWidget:
            return self.tabWidget.currentIndex()
        return -1

    def get_page_widget(self, page_name: str) -> Optional[QWidget]:
        """
        根据页面名称获取页面 widget

        Args:
            page_name: 页面名称（如 "screenshot_ocr", "batch_ocr"）

        Returns:
            Optional[QWidget]: 页面 widget
        """
        page_map = {
            "screenshot_ocr": self.pageScreenshotOcr,
            "batch_ocr": self.pageBatchOcr,
            "batch_doc": self.pageBatchDoc,
            "qrcode": self.pageQrcode,
            "task_manager": self.pageTaskManager,
            "settings": self.pageSettings,
        }
        return page_map.get(page_name)

    # -------------------------------------------------------------------------
    # 状态栏
    # -------------------------------------------------------------------------

    def _init_status_bar(self):
        """初始化状态栏"""
        if not self.statusBarWidget:
            return

        # 添加就绪标签
        self.statusReadyLabel = QLabel(
            self.i18n.translate("main_window.statusbar.ready")
        )
        self.statusBarWidget.addWidget(self.statusReadyLabel, 1)

        # 添加语言标签
        current_lang = self.i18n.get_language_name()
        self.statusLanguageLabel = QLabel(current_lang)
        self.statusBarWidget.addPermanentWidget(self.statusLanguageLabel)

    def _update_status_bar_for_page(self, page_index: int):
        """
        根据页面更新状态栏

        Args:
            page_index: 页面索引
        """
        if not self.statusBarWidget or not hasattr(self, "statusReadyLabel"):
            return

        # 页面名称列表
        page_names = ["截图OCR", "批量图片", "批量文档", "二维码", "任务管理", "设置"]

        if 0 <= page_index < len(page_names):
            page_name = page_names[page_index]
            self.statusReadyLabel.setText(f"就绪 - {page_name}")

    def show_status_message(self, message: str, timeout: int = 3000):
        """
        在状态栏显示临时消息

        Args:
            message: 消息文本
            timeout: 显示时长（毫秒）
        """
        if self.statusBarWidget:
            self.statusBarWidget.showMessage(message, timeout)

    # -------------------------------------------------------------------------
    # 多语言支持
    # -------------------------------------------------------------------------

    def _apply_translations(self):
        """应用多语言翻译"""
        # 更新窗口标题
        self.setWindowTitle(self.i18n.translate("main_window.title"))

        # 更新状态栏
        if hasattr(self, "statusReadyLabel"):
            self.statusReadyLabel.setText(
                self.i18n.translate("main_window.statusbar.ready")
            )

        if hasattr(self, "statusLanguageLabel"):
            self.statusLanguageLabel.setText(self.i18n.get_language_name())

        # 更新标签页文本
        self._update_tab_translations()

    def _update_tab_translations(self):
        """更新标签页文本翻译"""
        if not self.tabWidget:
            return

        tab_translations = [
            "main_window.sidebar.screenshot_ocr",
            "main_window.sidebar.batch_ocr",
            "main_window.sidebar.batch_doc",
            "main_window.sidebar.qrcode",
            "main_window.sidebar.task_manager",
            "main_window.sidebar.settings",
        ]

        for i, key_path in enumerate(tab_translations):
            if i < self.tabWidget.count():
                self.tabWidget.setTabText(i, self.i18n.translate(key_path))

    # -------------------------------------------------------------------------
    # 配置管理
    # -------------------------------------------------------------------------

    def _load_window_state(self):
        """加载窗口状态（大小、位置等）"""
        # 从配置读取窗口状态
        width = self.config_manager.get("ui.main_window.width", 1000)
        height = self.config_manager.get("ui.main_window.height", 700)
        x = self.config_manager.get("ui.main_window.x", -1)
        y = self.config_manager.get("ui.main_window.y", -1)
        maximized = self.config_manager.get("ui.main_window.maximized", False)
        current_tab = self.config_manager.get("ui.main_window.current_tab", 0)

        # 设置窗口大小
        self.resize(width, height)

        # 设置窗口位置
        if x >= 0 and y >= 0:
            self.move(x, y)

        # 设置最大化状态
        if maximized:
            self.showMaximized()

        # 恢复上次选中的标签页
        if self.tabWidget and 0 <= current_tab < self.tabWidget.count():
            self.tabWidget.setCurrentIndex(current_tab)

    def _save_window_state(self):
        """保存窗口状态"""
        # 保存窗口大小和位置
        geometry = self.geometry()
        self.config_manager.set("ui.main_window.width", geometry.width())
        self.config_manager.set("ui.main_window.height", geometry.height())
        self.config_manager.set("ui.main_window.x", geometry.x())
        self.config_manager.set("ui.main_window.y", geometry.y())
        self.config_manager.set("ui.main_window.maximized", self.isMaximized())

        # 保存当前标签页索引
        if self.tabWidget:
            self.config_manager.set(
                "ui.main_window.current_tab", self.tabWidget.currentIndex()
            )

        # 保存配置
        self.config_manager.save()

    def _on_config_changed(self, key_path: str, old_value, new_value):
        """
        配置变更事件处理

        Args:
            key_path: 变化的配置路径
            old_value: 旧值
            new_value: 新值
        """
        # 如果是语言配置变更，应用新语言
        if key_path == "ui.language":
            self.i18n.set_language(new_value)
            self._apply_translations()

    # -------------------------------------------------------------------------
    # 窗口事件
    # -------------------------------------------------------------------------

    def closeEvent(self, event):
        """
        窗口关闭事件处理

        Args:
            event: 关闭事件
        """
        self.logger.info("主窗口关闭")

        # 发送关闭信号
        self.window_closing.emit()

        # 保存窗口状态
        self._save_window_state()

        # 接受关闭事件
        event.accept()

    def showEvent(self, event):
        """
        窗口显示事件处理

        Args:
            event: 显示事件
        """
        super().showEvent(event)
        self.logger.debug("主窗口显示")

    def hideEvent(self, event):
        """
        窗口隐藏事件处理

        Args:
            event: 隐藏事件
        """
        super().hideEvent(event)
        self.logger.debug("主窗口隐藏")

    # -------------------------------------------------------------------------
    # 公共方法
    # -------------------------------------------------------------------------

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
