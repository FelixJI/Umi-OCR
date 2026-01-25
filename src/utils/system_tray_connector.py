# =========================================
# =============== 系统托盘连接器 ===============
# =========================================

"""
系统托盘连接器 - 使用原生QSystemTrayIcon实现
"""

import os
from pathlib import Path

from PySide6.QtCore import QObject, Slot, Signal, Property
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from umi_log import logger
from src.event_bus.pubsub_service import PubSubService


class SystemTrayConnector(QObject):
    """
    系统托盘连接器 - 封装QSystemTrayIcon供QML使用
    使用原生C++ API，比Qt.labs.platform更稳定
    """

    # 信号
    visibleChanged = Signal()
    iconSourceChanged = Signal()
    tooltipChanged = Signal()
    availableChanged = Signal()
    activated = Signal(int)  # 激活信号：触发原因
    messageClicked = Signal()  # 消息点击信号

    def __init__(self, parent=None):
        super().__init__(parent)

        # 创建系统托盘图标
        self._tray = QSystemTrayIcon(parent)

        # 初始化属性
        self._visible = False
        self._iconSource = ""
        self._tooltip = "Umi-OCR"
        self._available = False

        # 保存qmlapp引用，用于访问pubSub
        self._qmlapp = None

        # 创建右键菜单
        self._menu = QMenu()
        self._tray.setContextMenu(self._menu)

        # 连接原生信号
        self._tray.activated.connect(self._onActivated)
        self._tray.messageClicked.connect(self.messageClicked.emit)

        # 检查系统托盘是否可用
        self._available = self._tray.isSystemTrayAvailable()

        logger.info(f"[SystemTrayConnector] 初始化完成, available: {self._available}")

    def _onActivated(self, reason):
        """
        原生激活信号的处理函数
        reason: QSystemTrayIcon.ActivationReason
        """
        self.activated.emit(reason)
        logger.debug(f"[SystemTrayConnector] 激活, reason: {reason}")

    # ========================= 【属性】 =========================

    def getAvailable(self):
        """系统托盘是否可用"""
        return self._available

    def setAvailable(self, value):
        pass

    available = Property(bool, getAvailable, setAvailable, notify=availableChanged)

    def getVisible(self):
        """托盘图标是否可见"""
        return self._tray.isVisible()

    def setVisible(self, value):
        """设置托盘图标可见性"""
        current_visible = self._tray.isVisible()
        if value != current_visible:
            # 状态不一致时才调用 show/hide
            if value:
                self._tray.show()
                logger.debug(f"[SystemTrayConnector] setVisible: 显示托盘")
            else:
                self._tray.hide()
                logger.debug(f"[SystemTrayConnector] setVisible: 隐藏托盘")
            # 更新内部状态
            self._visible = value
            self.visibleChanged.emit()

    visible = Property(bool, getVisible, setVisible, notify=visibleChanged)

    def getIconSource(self):
        """图标文件路径"""
        return self._iconSource

    def setIconSource(self, path):
        self._iconSource = path
        if path:
            # 转换为绝对路径
            if not os.path.isabs(path):
                # 相对于QML文件所在目录 (resources/MainWindow/)
                qml_file_dir = Path(__file__).parent.parent.parent / "resources" / "MainWindow"
                full_path = (qml_file_dir / path).resolve()
                logger.debug(f"[SystemTrayConnector] 图标路径: {path} -> {full_path}")

                if full_path.exists():
                    icon = QIcon(str(full_path))
                    self._tray.setIcon(icon)
                    logger.info(f"[SystemTrayConnector] 图标已加载: {full_path}")
                else:
                    logger.warning(f"[SystemTrayConnector] 图标文件不存在: {full_path}")
            else:
                icon = QIcon(path)
                self._tray.setIcon(icon)
                logger.info(f"[SystemTrayConnector] 图标已加载: {path}")
        self.iconSourceChanged.emit()

    iconSource = Property(str, getIconSource, setIconSource, notify=iconSourceChanged)

    def getTooltip(self):
        """工具提示"""
        return self._tooltip

    def setTooltip(self, text):
        self._tooltip = text
        self._tray.setToolTip(text)
        self.tooltipChanged.emit()

    tooltip = Property(str, getTooltip, setTooltip, notify=tooltipChanged)

    # ========================= 【方法】 =========================

    @Slot()
    def show(self):
        """显示托盘图标"""
        if self._available:
            # 检查图标是否有效
            if self._tray.icon().isNull():
                logger.warning(f"[SystemTrayConnector] 图标为空，托盘可能无法正常显示")
            else:
                logger.debug(f"[SystemTrayConnector] 图标已设置: {self._iconSource}")

            # 检查当前状态，避免重复调用
            if not self._tray.isVisible():
                self._tray.show()
                self._visible = True
                self.visibleChanged.emit()
                logger.info(f"[SystemTrayConnector] 显示托盘图标")
            else:
                logger.debug(f"[SystemTrayConnector] 托盘图标已显示，跳过")
        else:
            logger.warning(f"[SystemTrayConnector] 系统托盘不可用，无法显示图标")

    @Slot()
    def hide(self):
        """隐藏托盘图标"""
        # 检查当前状态，避免重复调用
        if self._tray.isVisible():
            self._tray.hide()
            self._visible = False
            self.visibleChanged.emit()
            logger.info(f"[SystemTrayConnector] 隐藏托盘图标")
        else:
            logger.debug(f"[SystemTrayConnector] 托盘图标已隐藏，跳过")

    @Slot(str, str, str)
    def showMessage(self, title, message, icon_type="Information"):
        """
        显示托盘消息

        Args:
            title: 消息标题
            message: 消息内容
            icon_type: 图标类型: Information, Warning, Critical, NoIcon
        """
        icon_map = {
            "Information": QSystemTrayIcon.MessageIcon.Information,
            "Warning": QSystemTrayIcon.MessageIcon.Warning,
            "Critical": QSystemTrayIcon.MessageIcon.Critical,
            "NoIcon": QSystemTrayIcon.MessageIcon.NoIcon,
        }

        icon_enum = icon_map.get(icon_type, QSystemTrayIcon.MessageIcon.Information)
        self._tray.showMessage(title, message, icon_enum)
        logger.debug(f"[SystemTrayConnector] 显示消息: {title} - {message}")

    # ========================= 【菜单管理】 =========================

    @Slot("QVariant")
    def setQmlApp(self, qmlapp):
        """设置qmlapp引用"""
        self._qmlapp = qmlapp

    def _getQmlProperty(self, property_name):
        """
        安全地从 QML qmlapp 对象获取属性
        
        QML 对象的属性需要通过 property() 方法访问，而不是直接属性访问
        """
        if not self._qmlapp:
            return None
        try:
            return self._qmlapp.property(property_name)
        except Exception as e:
            logger.error(f"[SystemTrayConnector] 获取属性 {property_name} 失败: {e}")
            return None

    @Slot(str, str, result="QVariant")
    def addMenuItem(self, eventTitle, text=""):
        """
        添加菜单项（使用pubsub机制或直接调用）

        Args:
            eventTitle: 事件标题
            text: 菜单项文本（可选，默认为空）
        """
        action = self._menu.addAction(text if text else eventTitle)

        # 连接到触发函数
        def onTriggered():
            logger.info(f"[SystemTrayConnector] 菜单项被点击: {eventTitle}")
            try:
                # 直接使用 Python 的 PubSubService 发布事件
                PubSubService.publish(eventTitle)
                logger.info(f"[SystemTrayConnector] 已发布事件: {eventTitle}")
            except Exception as e:
                logger.error(f"[SystemTrayConnector] 菜单项点击失败: {e}", exc_info=True)

        action.triggered.connect(onTriggered)
        logger.debug(
            f"[SystemTrayConnector] 添加菜单项: {text or eventTitle} -> {eventTitle}"
        )

    @Slot(str)
    def delMenuItem(self, eventTitle):
        """
        删除菜单项（保留接口兼容性，暂时不实现）

        Args:
            eventTitle: 事件标题
        """
        logger.debug(f"[SystemTrayConnector] 删除菜单项请求（暂未实现）: {eventTitle}")
        # 暂时不实现动态删除功能

    # ========================= 【清理】 =========================

    def cleanup(self):
        """清理资源"""
        self._tray.hide()
        self._menu.clear()
        logger.info(f"[SystemTrayConnector] 资源已清理")
