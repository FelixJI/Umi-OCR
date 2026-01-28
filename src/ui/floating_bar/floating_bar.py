# src/ui/floating_bar/floating_bar.py

import logging
from enum import Enum

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QPoint, QTimer, QEasingCurve
from PySide6.QtGui import QCursor
from .ui_floating_bar import Ui_FloatingBar

logger = logging.getLogger(__name__)


class FloatingBarMode(Enum):
    EDGE_TRIGGER = "edge"  # 边缘触发
    ALWAYS_VISIBLE = "always"  # 常驻显示


class FloatingBar(QWidget):
    """
    悬浮工具栏
    """

    screenshot_clicked = Signal()
    clipboard_ocr_clicked = Signal()
    batch_ocr_clicked = Signal()
    settings_clicked = Signal()

    EDGE_MARGIN = 2  # 边缘检测距离
    ANIMATION_DURATION = 300  # 动画时长(ms)
    HIDE_DELAY = 500  # 隐藏延迟(ms)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._mode = FloatingBarMode.EDGE_TRIGGER
        self._is_visible = False
        self._is_dragging = False
        self._drag_pos = QPoint()

        self._load_ui()
        self._connect_signals()

        # 边缘检测定时器
        self._edge_timer = QTimer(self)
        self._edge_timer.setInterval(100)
        self._edge_timer.timeout.connect(self._check_mouse_at_edge)
        self._edge_timer.start()

        # 自动隐藏定时器
        self._hide_timer = QTimer(self)
        self._hide_timer.setInterval(self.HIDE_DELAY)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._slide_out)

        # 动画
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(self.ANIMATION_DURATION)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        # 初始位置 (屏幕左侧中部)
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(0, geo.height() // 2 - 100)

        # 初始隐藏（如果是边缘触发模式）
        if self._mode == FloatingBarMode.EDGE_TRIGGER:
            self.move(-self.width(), self.y())

    def _load_ui(self):
        try:
            self.ui = Ui_FloatingBar()
            self.ui.setupUi(self)

            # Find widgets
            self.btn_screenshot = self.ui.btn_screenshot
            self.btn_clipboard = self.ui.btn_clipboard
            self.btn_batch = self.ui.btn_batch
            self.btn_settings = self.ui.btn_settings
            self.lbl_grip = self.ui.lbl_grip

        except Exception as e:
            logger.error(f"加载悬浮条 UI 失败: {e}")

    def _connect_signals(self):
        if hasattr(self, "btn_screenshot"):
            self.btn_screenshot.clicked.connect(self.screenshot_clicked.emit)
        if hasattr(self, "btn_clipboard"):
            self.btn_clipboard.clicked.connect(self.clipboard_ocr_clicked.emit)
        if hasattr(self, "btn_batch"):
            self.btn_batch.clicked.connect(self.batch_ocr_clicked.emit)
        if hasattr(self, "btn_settings"):
            self.btn_settings.clicked.connect(self.settings_clicked.emit)

    def set_mode(self, mode: FloatingBarMode):
        self._mode = mode
        if mode == FloatingBarMode.ALWAYS_VISIBLE:
            self._slide_in()
            self._edge_timer.stop()
        else:
            self._slide_out()
            self._edge_timer.start()

    def _check_mouse_at_edge(self):
        if self._mode == FloatingBarMode.ALWAYS_VISIBLE:
            return

        cursor_pos = QCursor.pos()

        # 检查是否在左边缘
        if cursor_pos.x() <= self.EDGE_MARGIN:
            # 检查是否在当前 Y 轴范围内（可选，或者全屏边缘都触发）
            # 这里简化为全屏左边缘触发
            self._slide_in()
        elif not self.geometry().contains(cursor_pos):
            # 鼠标离开且不在悬浮条上，延迟隐藏
            if self._is_visible and not self._hide_timer.isActive():
                self._hide_timer.start()

    def enterEvent(self, event):
        super().enterEvent(event)
        self._hide_timer.stop()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self._mode == FloatingBarMode.EDGE_TRIGGER:
            self._hide_timer.start()

    def _slide_in(self):
        if self._is_visible:
            return

        start_pos = self.pos()
        end_pos = QPoint(0, start_pos.y())

        self._anim.setStartValue(start_pos)
        self._anim.setEndValue(end_pos)
        self._anim.start()

        self._is_visible = True
        self.show()

    def _slide_out(self):
        if not self._is_visible:
            return

        start_pos = self.pos()
        # 留一点边缘可见，或者完全隐藏
        end_pos = QPoint(-self.width() + 5, start_pos.y())

        self._anim.setStartValue(start_pos)
        self._anim.setEndValue(end_pos)
        self._anim.start()

        self._is_visible = False

    # 拖拽移动实现
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 只有按住 grip 区域才能拖拽
            if self.lbl_grip.geometry().contains(event.pos()):
                self._is_dragging = True
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
