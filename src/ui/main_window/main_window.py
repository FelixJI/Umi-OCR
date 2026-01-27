 #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 主窗口

主窗口类，负责：
- 加载和管理主窗口 UI
- 侧边栏导航和视图切换
- 菜单栏和工具栏管理
- 状态栏更新
- 集成日志、配置、多语言等系统功能

Author: Umi-OCR Team
Date: 2025-01-26
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QListWidget, QStackedWidget,
    QLabel, QMessageBox, QStatusBar, QToolBar, QVBoxLayout
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtUiTools import QUiLoader

from src.utils.logger import get_logger
from src.utils.config_manager import get_config_manager
from src.utils.i18n import get_i18n_manager
from src.ui.settings.settings import SettingsWindow
from src.ui.screenshot_ocr.screenshot_ocr import ScreenshotOCRView
from src.ui.batch_ocr.batch_ocr import BatchOCRView
from src.ui.batch_doc.batch_doc import BatchDocView
from src.ui.qrcode.qrcode import QRCodeView
from src.ui.task_manager.task_manager import TaskManagerView


class MainWindow(QMainWindow):
    """
    Umi-OCR 主窗口

    负责管理整个应用程序的主界面，包括侧边栏导航、内容区域显示等。
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

        # 应用多语言
        self._apply_translations()

        self.logger.info("主窗口初始化完成")

    def _load_ui(self):
        """加载 UI 文件"""
        try:
            # 获取 .ui 文件路径
            ui_file = Path(__file__).parent / "main_window.ui"

            if not ui_file.exists():
                raise FileNotFoundError(f"UI 文件不存在: {ui_file}")

            # 使用 QUiLoader 加载 UI
            ui_loader = QUiLoader()
            self.ui = ui_loader.load(str(ui_file))

            if not self.ui:
                raise RuntimeError("UI 加载失败")

            # 调试：检查加载的UI对象类型和子对象
            self.logger.debug(f"Loaded UI type: {type(self.ui).__name__}")
            self.logger.debug(f"Loaded UI objectName: {self.ui.objectName()}")

            # 查找所有子对象
            def find_all_children(widget, depth=0):
                indent = "  " * depth
                result = []
                result.append(f"{indent}{widget.objectName()} ({type(widget).__name__})")
                for child in widget.findChildren(QWidget):
                    if child.parent() == widget:
                        result.extend(find_all_children(child, depth + 1))
                return result

            children = find_all_children(self.ui)
            self.logger.debug(f"UI children:\n" + "\n".join(children[:20]))  # 只显示前20个

            # 将 UI 的内容设置为中心部件
            central_widget = self.ui.findChild(QWidget, "centralWidget")
            if central_widget:
                self.setCentralWidget(central_widget)

            # 导入 UI 元素到实例属性
            self._import_ui_elements()

            self.logger.debug(f"UI 文件加载成功: {ui_file}")

        except Exception as e:
            self.logger.error(f"加载 UI 文件失败: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "错误",
                f"无法加载界面文件：\n{e}"
            )
            sys.exit(1)

    def _import_ui_elements(self):
        """从 UI 对象导入常用元素到实例属性"""
        # 侧边栏 - 从UI对象中查找，注意类型是QListWidget不是QWidget
        self.sidebarListWidget = self.ui.findChild(QListWidget, "sidebarListWidget")

        # 内容区域 - 从self（MainWindow）中查找，因为我们已经设置了centralWidget
        self.contentStackedWidget = self.findChild(QStackedWidget, "contentStackedWidget")

        # 调试：检查contentStackedWidget
        if self.contentStackedWidget:
            self.logger.debug(f"contentStackedWidget found, count: {self.contentStackedWidget.count()}")
            for i in range(self.contentStackedWidget.count()):
                widget = self.contentStackedWidget.widget(i)
                self.logger.debug(f"  Page {i}: {widget.objectName()} (type: {type(widget).__name__})")
        else:
            self.logger.error("contentStackedWidget not found!")

        # 状态栏（使用不同的名称避免与 statusBar() 方法冲突）
        self.statusBarWidget = self.ui.findChild(QStatusBar, "statusBar")

        # 各个页面 - 从contentStackedWidget中查找
        if self.contentStackedWidget:
            self.pageScreenshotOcr = self.contentStackedWidget.findChild(QWidget, "pageScreenshotOcr")
            self.pageBatchOcr = self.contentStackedWidget.findChild(QWidget, "pageBatchOcr")
            self.pageBatchDoc = self.contentStackedWidget.findChild(QWidget, "pageBatchDoc")
            self.pageQrcode = self.contentStackedWidget.findChild(QWidget, "pageQrcode")
            self.pageTaskManager = self.contentStackedWidget.findChild(QWidget, "pageTaskManager")
            self.pageSettings = self.contentStackedWidget.findChild(QWidget, "pageSettings")
        else:
            # 如果找不到contentStackedWidget，设置为None
            self.pageScreenshotOcr = None
            self.pageBatchOcr = None
            self.pageBatchDoc = None
            self.pageQrcode = None
            self.pageTaskManager = None
            self.pageSettings = None

        # 动作（菜单项）
        self.actionOpenFile = self.ui.findChild(QAction, "actionOpenFile")
        self.actionExit = self.ui.findChild(QAction, "actionExit")
        self.actionSettings = self.ui.findChild(QAction, "actionSettings")
        self.actionToggleSidebar = self.ui.findChild(QAction, "actionToggleSidebar")
        self.actionToggleToolbar = self.ui.findChild(QAction, "actionToggleToolbar")
        self.actionFullscreen = self.ui.findChild(QAction, "actionFullscreen")
        self.actionScreenshot = self.ui.findChild(QAction, "actionScreenshot")
        self.actionTaskManager = self.ui.findChild(QAction, "actionTaskManager")
        self.actionAbout = self.ui.findChild(QAction, "actionAbout")

    def _init_ui_components(self):
        """初始化 UI 组件"""
        # 设置侧边栏样式
        if self.sidebarListWidget:
            self.sidebarListWidget.setCurrentRow(0)  # 默认选中第一项

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
                self.taskManagerView = TaskManagerView()
                self._set_page_widget(self.pageTaskManager, self.taskManagerView)
                self.logger.debug("任务管理视图初始化成功")
            except Exception as e:
                self.logger.error(f"任务管理视图初始化失败: {e}", exc_info=True)

        # 初始化设置页面
        if self.pageSettings:
            try:
                self.settingsWindow = SettingsWindow()
                self._set_page_widget(self.pageSettings, self.settingsWindow)
                self.logger.debug("设置视图初始化成功")
            except Exception as e:
                self.logger.error(f"设置视图初始化失败: {e}", exc_info=True)

        # 默认显示第一页，确保右侧不为空
        if self.contentStackedWidget and self.contentStackedWidget.count() > 0:
            self.contentStackedWidget.setCurrentIndex(0)

    # -------------------------------------------------------------------------
    # 侧边栏导航
    # -------------------------------------------------------------------------

    def _connect_signals(self):
        """连接信号和槽"""
        # 侧边栏点击事件
        if self.sidebarListWidget:
            # 使用 itemClicked 信号而不是 currentRowChanged
            # 因为 focusPolicy 设置为 NoFocus 可能导致 currentRowChanged 不触发
            self.sidebarListWidget.itemClicked.connect(self._on_sidebar_item_clicked)
            # 同时保留 currentRowChanged 信号以处理编程式切换
            self.sidebarListWidget.currentRowChanged.connect(self._on_sidebar_row_changed)

        # 菜单动作事件
        if self.actionToggleSidebar:
            self.actionToggleSidebar.triggered.connect(self._toggle_sidebar)

        if self.actionToggleToolbar:
            self.actionToggleToolbar.triggered.connect(self._toggle_toolbar)

        if self.actionFullscreen:
            self.actionFullscreen.triggered.connect(self._toggle_fullscreen)

        if self.actionExit:
            self.actionExit.triggered.connect(self.close)

        if self.actionAbout:
            self.actionAbout.triggered.connect(self._show_about_dialog)

        if self.actionSettings:
            self.actionSettings.triggered.connect(lambda: self.switch_to_page(5))  # 设置页面

        if self.actionTaskManager:
            self.actionTaskManager.triggered.connect(lambda: self.switch_to_page(4))  # 任务管理页面

        if self.actionScreenshot:
            self.actionScreenshot.triggered.connect(self._on_action_screenshot)

        # 连接语言变更信号
        self.i18n.language_changed.connect(self._apply_translations)

        # 连接配置变更信号
        self.config_manager.config_changed.connect(self._on_config_changed)

    def _on_action_screenshot(self):
        """菜单/工具栏触发截图页面与动作"""
        self.switch_to_page(0)
        try:
            # 触发视图开始截图（视图内部连接控制器）
            if hasattr(self, "screenshotView"):
                # 使用视图的按钮逻辑以复用现有行为
                self.screenshotView._on_start_capture()
        except Exception as e:
            self.logger.error(f"触发截图失败: {e}", exc_info=True)
    
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
        self.logger.debug(f"已将 {type(widget).__name__} 添加到 {page_container.objectName()}，layout.count(): {layout.count()}")

    def _on_sidebar_item_clicked(self, item):
        """
        侧边栏项点击事件处理

        Args:
            item: 点击的 QListWidgetItem
        """
        # 获取点击项的索引
        row = self.sidebarListWidget.row(item)
        self.logger.debug(f"侧边栏点击，行号: {row}")

        if self.contentStackedWidget and 0 <= row < self.contentStackedWidget.count():
            # 切换页面
            self.contentStackedWidget.setCurrentIndex(row)
            self.logger.debug(f"QStackedWidget 当前索引: {self.contentStackedWidget.currentIndex()}")
            current_widget = self.contentStackedWidget.currentWidget()
            self.logger.debug(f"QStackedWidget 当前 widget: {current_widget.objectName() if current_widget else 'None'}")

            # 发送页面切换信号
            self.page_changed.emit(row)

            # 更新状态栏
            self._update_status_bar_for_page(row)

            self.logger.debug(f"切换到页面: {row}")
        else:
            self.logger.error(f"无效的页面索引: {row}, contentStackedWidget.count(): {self.contentStackedWidget.count() if self.contentStackedWidget else 'None'}")

    def switch_to_page(self, page_index: int):
        """
        切换到指定页面

        Args:
            page_index: 页面索引（0-5）
        """
        if self.sidebarListWidget and 0 <= page_index < self.sidebarListWidget.count():
            self.sidebarListWidget.setCurrentRow(page_index)
            # 触发点击事件以确保页面切换
            item = self.sidebarListWidget.item(page_index)
            if item:
                self._on_sidebar_item_clicked(item)
        elif self.contentStackedWidget and 0 <= page_index < self.contentStackedWidget.count():
            self.contentStackedWidget.setCurrentIndex(page_index)

    # -------------------------------------------------------------------------
    # 内容区域管理
    # -------------------------------------------------------------------------

    def get_current_page(self) -> Optional[QWidget]:
        """
        获取当前页面

        Returns:
            Optional[QWidget]: 当前页面的 widget
        """
        if self.contentStackedWidget:
            return self.contentStackedWidget.currentWidget()
        return None

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
        self.statusReadyLabel = QLabel(self.i18n.translate("main_window.statusbar.ready"))
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
        page_names = [
            "截图OCR",
            "批量图片",
            "批量文档",
            "二维码",
            "任务管理",
            "设置"
        ]

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
    # 菜单和工具栏
    # -------------------------------------------------------------------------

    def _toggle_sidebar(self, checked: bool):
        """
        切换侧边栏显示/隐藏

        Args:
            checked: 是否显示
        """
        if self.sidebarListWidget:
            self.sidebarListWidget.setVisible(checked)

            # 更新配置
            self.config_manager.set("ui.main_window.sidebar_visible", checked)

    def _toggle_toolbar(self, checked: bool):
        """
        切换工具栏显示/隐藏

        Args:
            checked: 是否显示
        """
        # 通过对象名称查找工具栏
        main_toolbar = self.ui.findChild(QToolBar, "mainToolBar")
        if main_toolbar:
            main_toolbar.setVisible(checked)

    def _toggle_fullscreen(self, checked: bool):
        """
        切换全屏模式

        Args:
            checked: 是否全屏
        """
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def _show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 Umi-OCR",
            (
                f"<h3>Umi-OCR {self.i18n.translate('app.version')}</h3>"
                f"<p>{self.i18n.translate('app.description')}</p>"
                "<p>版本: 2.0.0 (重构版)</p>"
                "<p>© 2025 Umi-OCR Team</p>"
            )
        )

    # -------------------------------------------------------------------------
    # 多语言支持
    # -------------------------------------------------------------------------

    def _apply_translations(self):
        """应用多语言翻译"""
        # 更新窗口标题
        self.setWindowTitle(self.i18n.translate("main_window.title"))

        # 更新状态栏
        if hasattr(self, "statusReadyLabel"):
            self.statusReadyLabel.setText(self.i18n.translate("main_window.statusbar.ready"))

        if hasattr(self, "statusLanguageLabel"):
            self.statusLanguageLabel.setText(self.i18n.get_language_name())

        # 更新侧边栏文本
        self._update_sidebar_translations()

        # 更新菜单栏文本
        self._update_menu_translations()

    def _update_sidebar_translations(self):
        """更新侧边栏文本翻译"""
        sidebar_items = [
            "main_window.sidebar.screenshot_ocr",
            "main_window.sidebar.batch_ocr",
            "main_window.sidebar.batch_doc",
            "main_window.sidebar.qrcode",
            "main_window.sidebar.task_manager",
            "main_window.sidebar.settings"
        ]
        if self.sidebarListWidget:
            for i, key_path in enumerate(sidebar_items):
                item = self.sidebarListWidget.item(i)
                if item:
                    item.setText(self.i18n.translate(key_path))

    def _update_menu_translations(self):
        """更新菜单栏文本翻译"""
        if not self.ui:
            return

        # 获取菜单栏
        menu_bar = self.ui.findChild(QWidget, "menuBar")
        if not menu_bar:
            return

        # 菜单标题翻译映射
        menu_translations = {
            "menuFile": "main_window.menu.file",
            "menuEdit": "main_window.menu.edit",
            "menuView": "main_window.menu.view",
            "menuTools": "main_window.menu.tools",
            "menuHelp": "main_window.menu.help"
        }

        # 遍历所有子菜单并更新标题
        for menu_name, key_path in menu_translations.items():
            menu = self.ui.findChild(QWidget, menu_name)
            if menu:
                # 设置菜单标题（支持多语言）
                new_title = self.i18n.translate(key_path)
                # 移除Qt的助记符标记(&)并重新添加
                menu.setTitle(new_title.replace("&", ""))

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
        sidebar_visible = self.config_manager.get("ui.main_window.sidebar_visible", True)

        # 设置窗口大小
        self.resize(width, height)

        # 设置窗口位置
        if x >= 0 and y >= 0:
            self.move(x, y)

        # 设置最大化状态
        if maximized:
            self.showMaximized()

        # 设置侧边栏可见性
        if self.actionToggleSidebar:
            self.actionToggleSidebar.setChecked(sidebar_visible)
            self._toggle_sidebar(sidebar_visible)

    def _save_window_state(self):
        """保存窗口状态"""
        # 保存窗口大小和位置
        geometry = self.geometry()
        self.config_manager.set("ui.main_window.width", geometry.width())
        self.config_manager.set("ui.main_window.height", geometry.height())
        self.config_manager.set("ui.main_window.x", geometry.x())
        self.config_manager.set("ui.main_window.y", geometry.y())
        self.config_manager.set("ui.main_window.maximized", self.isMaximized())

        # 保存侧边栏可见性
        if self.sidebarListWidget:
            self.config_manager.set("ui.main_window.sidebar_visible", self.sidebarListWidget.isVisible())

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
