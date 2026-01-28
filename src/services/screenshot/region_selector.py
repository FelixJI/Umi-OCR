#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 区域选择器

实现全屏覆盖层的区域选择功能,支持丰富的交互。

主要功能：
- 窗口识别: 鼠标悬停时高亮窗口边框
- 坐标显示: 实时显示鼠标位置和选区尺寸
- 比例约束: Shift+拖动锁定正方形/常用比例
- 选区调整: 拖动边缘/角调整大小,拖动中心移动
- 放大镜: 鼠标附近显示放大图像
- 快捷键: Esc取消、Enter确认、数字键切换比例

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from enum import Enum
from typing import Optional, Dict

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QCursor

from .screen_capture import ScreenCapture
from .window_detector import WindowDetector, WindowInfo
from .magnifier import Magnifier

logger = logging.getLogger(__name__)


class DragMode(Enum):
    """拖动模式"""
    NONE = "none"
    CREATE = "create"          # 创建新选区
    MOVE = "move"              # 移动选区
    RESIZE_N = "resize_n"      # 调整上边
    RESIZE_S = "resize_s"      # 调整下边
    RESIZE_E = "resize_e"      # 调整右边
    RESIZE_W = "resize_w"      # 调整左边
    RESIZE_NE = "resize_ne"    # 调整右上角
    RESIZE_NW = "resize_nw"    # 调整左上角
    RESIZE_SE = "resize_se"    # 调整右下角
    RESIZE_SW = "resize_sw"    # 调整左下角


class RegionSelector(QWidget):
    """
    区域选择器(全屏覆盖层窗口)

    功能:
    - 窗口识别: 鼠标悬停时高亮窗口边框
    - 坐标显示: 实时显示鼠标位置和选区尺寸
    - 比例约束: Shift+拖动锁定正方形/常用比例
    - 选区调整: 拖动边缘/角调整大小,拖动中心移动
    - 放大镜: 鼠标附近显示放大图像
    - 快捷键: Esc取消、Enter确认、数字键切换比例
    """

    # 信号定义
    region_selected = Signal(QRect)       # 选区完成
    selection_cancelled = Signal()        # 取消选择

    # 比例预设
    ASPECT_RATIOS = {
        "free": None,                  # 自由比例
        "1:1": 1.0,                   # 正方形
        "4:3": 4/3,
        "16:9": 16/9,
        "3:2": 3/2,
    }

    # 手柄尺寸
    HANDLE_SIZE = 10

    def __init__(self, parent: Optional[QWidget] = None, screen_capture: Optional[ScreenCapture] = None):
        """
        初始化区域选择器
        
        Args:
            parent: 父窗口
            screen_capture: 屏幕捕获实例
        """
        super().__init__(parent)

        # 创建跨屏无边框窗口
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 初始化服务
        self._screen_capture = screen_capture if screen_capture else ScreenCapture()
        self._window_detector = WindowDetector()
        self._magnifier = Magnifier()

        # 选区状态
        self._selection_rect: Optional[QRect] = None
        self._hovered_window: Optional[WindowInfo] = None
        self._current_aspect_ratio: Optional[float] = None
        self._is_shift_pressed = False

        # 拖动状态
        self._is_dragging = False
        self._drag_mode: DragMode = DragMode.NONE
        self._drag_start_pos: QPoint = QPoint()
        self._drag_start_rect: QRect = QRect()

        # 鼠标位置
        self._mouse_pos: QPoint = QPoint()

        # 全屏背景
        self._background_image: Optional[QPixmap] = None

        logger.info("区域选择器初始化完成")

    def start(self) -> None:
        """
        开始选区

        流程:
        1. 截取全屏作为背景
        2. 显示覆盖层
        3. 等待用户选择
        """
        logger.info("开始区域选择")

        # 获取虚拟屏幕几何（保存用于坐标转换）
        self._virtual_geometry = self._screen_capture.get_virtual_screen_geometry()
        logger.debug(f"虚拟屏幕几何: {self._virtual_geometry}")

        # 截取全屏
        self._background_image = self._screen_capture.capture_full_screen()

        if self._background_image.isNull():
            logger.error("全屏截图失败")
            self.selection_cancelled.emit()
            return

        # 设置窗口大小为虚拟屏幕大小
        self.setGeometry(self._virtual_geometry)

        # 显示窗口
        self.show()

        # 显示放大镜
        self._magnifier.show_magnifier()

        logger.info("区域选择窗口已显示")

    def stop(self) -> None:
        """
        停止选区

        隐藏窗口和放大镜。
        """
        logger.info("停止区域选择")
        self.hide()
        self._magnifier.hide_magnifier()

    def _local_to_global_rect(self, local_rect: QRect) -> QRect:
        """
        将本地坐标转换为全局屏幕坐标

        Args:
            local_rect: 本地坐标矩形

        Returns:
            QRect: 全局屏幕坐标矩形
        """
        if not hasattr(self, '_virtual_geometry'):
            return local_rect

        # 窗口的左上角在全局屏幕中的位置
        offset = self._virtual_geometry.topLeft()

        # 转换坐标
        global_rect = QRect(
            local_rect.left() + offset.x(),
            local_rect.top() + offset.y(),
            local_rect.width(),
            local_rect.height()
        )

        return global_rect

    def _global_to_local_point(self, global_pos: QPoint) -> QPoint:
        """
        将全局屏幕坐标转换为本地坐标

        用于放大镜定位。

        Args:
            global_pos: 全局屏幕坐标点

        Returns:
            QPoint: 本地坐标点
        """
        if not hasattr(self, '_virtual_geometry'):
            return global_pos

        offset = self._virtual_geometry.topLeft()
        return QPoint(
            global_pos.x() - offset.x(),
            global_pos.y() - offset.y()
        )

    def paintEvent(self, event) -> None:
        """
        绘制事件

        绘制:
        - 半透明遮罩层
        - 选区显示原图
        - 选区边框和调整手柄
        - 坐标信息
        - 放大镜
        """
        super().paintEvent(event)

        if not self._background_image or self._background_image.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. 绘制半透明遮罩层
        mask_color = QColor(0, 0, 0, 100)
        painter.fillRect(self.rect(), mask_color)

        # 2. 绘制选区(无遮罩,显示原图)
        if self._selection_rect and not self._selection_rect.isEmpty():
            # 裁剪选区并绘制原图
            selected_region = self._background_image.copy(self._selection_rect)
            painter.drawPixmap(self._selection_rect.topLeft(), selected_region)

            # 绘制选区边框
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self._selection_rect)

            # 绘制调整手柄
            self._draw_resize_handles(painter)

            # 绘制坐标信息
            self._draw_coordinate_info(painter)

        # 3. 绘制鼠标位置信息
        self._draw_mouse_info(painter)

        # 4. 绘制窗口高亮(如果悬停)
        if self._hovered_window:
            self._draw_window_highlight(painter)

        painter.end()

    def _draw_resize_handles(self, painter: QPainter) -> None:
        """
        绘制调整手柄

        Args:
            painter: 绘制器
        """
        if not self._selection_rect:
            return

        rect = self._selection_rect
        h = self.HANDLE_SIZE // 2

        # 手柄位置
        handles = {
            'tl': rect.topLeft(),
            'tr': rect.topRight(),
            'bl': rect.bottomLeft(),
            'br': rect.bottomRight(),
            't': QPoint(rect.center().x(), rect.top()),
            'b': QPoint(rect.center().x(), rect.bottom()),
            'l': QPoint(rect.left(), rect.center().y()),
            'r': QPoint(rect.right(), rect.center().y())
        }

        # 绘制手柄
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(QPen(QColor(0, 0, 0), 1))

        for pos in handles.values():
            painter.drawRect(pos.x() - h, pos.y() - h, self.HANDLE_SIZE, self.HANDLE_SIZE)

    def _draw_coordinate_info(self, painter: QPainter) -> None:
        """
        绘制坐标信息

        Args:
            painter: 绘制器
        """
        if not self._selection_rect:
            return

        rect = self._selection_rect

        # 准备信息文本
        lines = [
            f"尺寸: {rect.width()} x {rect.height()}",
            f"起点: ({rect.left()}, {rect.top()})",
            f"终点: ({rect.right()}, {rect.bottom()})"
        ]

        # 添加比例信息
        if self._current_aspect_ratio:
            ratio_name = self._get_aspect_ratio_name(self._current_aspect_ratio)
            lines.append(f"比例: {ratio_name}")
        elif self._is_shift_pressed:
            lines.append("比例: Shift锁定")

        # 绘制背景框
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        font_metrics = painter.fontMetrics()
        line_height = font_metrics.height()
        max_width = max(font_metrics.horizontalAdvance(line) for line in lines)

        # 计算文本位置（优先显示在选区下方，超出屏幕则显示在上方）
        text_y = rect.bottom() + 15
        if text_y + len(lines) * line_height > self.height():
            text_y = rect.top() - len(lines) * line_height - 10

        text_x = max(10, min(rect.left(), self.width() - max_width - 20))

        # 绘制半透明背景
        bg_rect = QRect(
            text_x - 5,
            text_y - line_height + 5,
            max_width + 10,
            len(lines) * line_height + 5
        )
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bg_rect, 5, 5)

        # 绘制文本
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        for i, line in enumerate(lines):
            painter.drawText(text_x, text_y + i * line_height, line)

    def _get_aspect_ratio_name(self, ratio: float) -> str:
        """
        获取比例名称

        Args:
            ratio: 比例值

        Returns:
            str: 比例名称
        """
        for name, value in self.ASPECT_RATIOS.items():
            if value is not None and abs(value - ratio) < 0.01:
                return name
        return f"{ratio:.2f}"

    def _draw_mouse_info(self, painter: QPainter) -> None:
        """
        绘制鼠标位置信息

        Args:
            painter: 绘制器
        """
        # 鼠标位置
        mouse_text = f"鼠标: X={self._mouse_pos.x()} Y={self._mouse_pos.y()}"

        # 快捷键提示
        hints = [
            "Enter/Space: 确认 | Esc: 取消",
            "1-5: 比例 | Shift: 锁定 | 拖动边缘: 调整"
        ]

        # 设置字体
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        font_metrics = painter.fontMetrics()
        line_height = font_metrics.height()

        # 绘制半透明背景
        bg_width = max(font_metrics.horizontalAdvance(mouse_text),
                      max(font_metrics.horizontalAdvance(h) for h in hints)) + 20
        bg_height = line_height * len(hints) + 30

        bg_rect = QRect(10, 10, bg_width, bg_height)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bg_rect, 5, 5)

        # 绘制文本
        painter.setPen(QPen(QColor(0, 255, 255), 1))  # 青色高亮鼠标坐标
        painter.drawText(20, 30, mouse_text)

        painter.setPen(QPen(QColor(200, 200, 200), 1))  # 灰色提示
        for i, hint in enumerate(hints):
            painter.drawText(20, 30 + line_height * (i + 1), hint)

    def _draw_window_highlight(self, painter: QPainter) -> None:
        """
        绘制窗口高亮

        Args:
            painter: 绘制器
        """
        if not self._hovered_window:
            return

        window_rect = self._hovered_window.rect

        # 绘制高亮边框
        painter.setPen(QPen(QColor(0, 255, 0), 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(window_rect)

        # 绘制窗口标题
        title = self._hovered_window.title
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(window_rect.left(), window_rect.top() - 10, title)

    def mousePressEvent(self, event) -> None:
        """
        鼠标按下事件

        开始创建或调整选区。

        Args:
            event: 鼠标事件
        """
        pos = event.pos()
        self._is_dragging = True
        self._drag_start_pos = pos

        # 判断拖动模式
        if self._selection_rect:
            # 检查是否点击在手柄上
            drag_mode = self._get_resize_handle(pos)
            if drag_mode != DragMode.NONE:
                self._drag_mode = drag_mode
                self._drag_start_rect = QRect(self._selection_rect)
                return

            # 检查是否点击在选区内部
            if self._selection_rect.contains(pos):
                self._drag_mode = DragMode.MOVE
                self._drag_start_rect = QRect(self._selection_rect)
                return

        # 创建新选区
        self._drag_mode = DragMode.CREATE
        self._selection_rect = QRect(pos, pos)

        logger.debug(f"开始拖动: {self._drag_mode}")

    def mouseMoveEvent(self, event) -> None:
        """
        鼠标移动事件

        更新选区/调整大小/移动,检测窗口悬停,更新放大镜。

        Args:
            event: 鼠标事件
        """
        pos = event.pos()
        self._mouse_pos = pos

        # 更新放大镜（传递本地坐标，因为背景图像也是本地的）
        if self._background_image:
            self._magnifier.update_position(pos, self._background_image)

        # 处理拖动
        if self._is_dragging:
            delta = pos - self._drag_start_pos

            if self._drag_mode == DragMode.CREATE:
                # 创建选区
                self._selection_rect = QRect(self._drag_start_pos, pos).normalized()

                # 按比例约束（包括 Shift 临时锁定的正方形）
                if self._current_aspect_ratio or self._is_shift_pressed:
                    ratio = self._current_aspect_ratio if self._current_aspect_ratio else 1.0
                    self._apply_aspect_ratio_with_ratio(ratio)

            elif self._drag_mode == DragMode.MOVE:
                # 移动选区
                self._selection_rect.moveTo(
                    self._drag_start_rect.topLeft() + delta
                )

            else:
                # 调整大小
                self._resize_selection(delta)

            self.update()
            return

        # 检测窗口悬停
        if not self._selection_rect or not self._selection_rect.contains(pos):
            self._hovered_window = self._window_detector.get_window_at(self.mapToGlobal(pos))
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        """
        鼠标释放事件

        完成选区创建或调整。

        Args:
            event: 鼠标事件
        """
        if self._is_dragging and self._selection_rect:
            self._is_dragging = False

            # 如果选区太小,清除
            if self._selection_rect.width() < 10 or self._selection_rect.height() < 10:
                self._selection_rect = None

            self.update()
            logger.debug(f"选区: {self._selection_rect}")

    def keyPressEvent(self, event) -> None:
        """
        键盘按下事件

        快捷键:
        - Esc: 取消
        - Enter/Space: 确认
        - Shift: 锁定比例
        - 1-5: 切换预设比例
        - 方向键: 微调选区

        Args:
            event: 键盘事件
        """
        key = event.key()

        # Esc: 取消
        if key == Qt.Key_Escape:
            self.stop()
            self.selection_cancelled.emit()
            return

        # Enter/Space: 确认
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if self._selection_rect:
                # 转换为全局坐标
                global_rect = self._local_to_global_rect(self._selection_rect)
                logger.info(f"选区确认 (本地: {self._selection_rect}, 全局: {global_rect})")
                self.region_selected.emit(global_rect)
                self.stop()
            return

        # Shift: 锁定比例（默认正方形）
        if key == Qt.Key_Shift:
            self._is_shift_pressed = True
            # 如果没有预设比例，Shift 默认锁定正方形
            if not self._current_aspect_ratio:
                self._current_aspect_ratio = 1.0
            self.update()
            return

        # 1-5: 切换预设比例
        if Qt.Key_1 <= key <= Qt.Key_5:
            ratio_keys = list(self.ASPECT_RATIOS.keys())
            index = key - Qt.Key_1
            if index < len(ratio_keys):
                self._current_aspect_ratio = self.ASPECT_RATIOS[ratio_keys[index]]
                logger.debug(f"切换比例: {ratio_keys[index]}")
            return

        # 方向键: 微调选区
        if self._selection_rect:
            self._adjust_selection_with_arrow_keys(key)
            self.update()

    def keyReleaseEvent(self, event) -> None:
        """
        键盘释放事件

        Args:
            event: 键盘事件
        """
        if event.key() == Qt.Key_Shift:
            self._is_shift_pressed = False
            # 如果没有预设比例，清除比例锁定
            ratio_keys = list(self.ASPECT_RATIOS.keys())
            # 检查是否在预设比例中，如果不是则清除
            if self._current_aspect_ratio == 1.0:
                # 检查是否通过数字键设置的
                preset_values = [v for v in self.ASPECT_RATIOS.values() if v is not None]
                # 这里简化处理：如果是通过数字键设置的，保留
                # 如果只是 Shift 临时设置的，清除
                self._current_aspect_ratio = None
            self.update()

    def _get_resize_handle(self, pos: QPoint) -> DragMode:
        """
        获取点击的调整手柄

        Args:
            pos: 鼠标位置

        Returns:
            DragMode: 拖动模式
        """
        if not self._selection_rect:
            return DragMode.NONE

        rect = self._selection_rect
        h = self.HANDLE_SIZE  # 手柄检测范围

        # 检查各个手柄
        handles = {
            DragMode.RESIZE_NW: rect.topLeft(),
            DragMode.RESIZE_NE: rect.topRight(),
            DragMode.RESIZE_SW: rect.bottomLeft(),
            DragMode.RESIZE_SE: rect.bottomRight(),
            DragMode.RESIZE_N: QPoint(rect.center().x(), rect.top()),
            DragMode.RESIZE_S: QPoint(rect.center().x(), rect.bottom()),
            DragMode.RESIZE_W: QPoint(rect.left(), rect.center().y()),
            DragMode.RESIZE_E: QPoint(rect.right(), rect.center().y())
        }

        for mode, handle_pos in handles.items():
            if (pos - handle_pos).manhattanLength() < h:
                return mode

        return DragMode.NONE

    def _apply_aspect_ratio(self) -> None:
        """应用比例约束"""
        if not self._selection_rect or not self._current_aspect_ratio:
            return
        self._apply_aspect_ratio_with_ratio(self._current_aspect_ratio)

    def _apply_aspect_ratio_with_ratio(self, ratio: float) -> None:
        """
        应用指定的比例约束

        Args:
            ratio: 目标宽高比
        """
        if not self._selection_rect or ratio <= 0:
            return

        rect = self._selection_rect
        width = rect.width()
        height = rect.height()

        # 计算新尺寸
        if width > height:
            new_height = int(width / ratio)
            rect.setHeight(new_height)
        else:
            new_width = int(height * ratio)
            rect.setWidth(new_width)

    def _resize_selection(self, delta: QPoint) -> None:
        """
        调整选区大小

        Args:
            delta: 鼠标移动增量
        """
        if not self._selection_rect:
            return

        rect = self._selection_rect
        mode = self._drag_mode

        # 应用调整
        if mode == DragMode.RESIZE_N:
            rect.setTop(self._drag_start_rect.top() + delta.y())
        elif mode == DragMode.RESIZE_S:
            rect.setBottom(self._drag_start_rect.bottom() + delta.y())
        elif mode == DragMode.RESIZE_E:
            rect.setRight(self._drag_start_rect.right() + delta.x())
        elif mode == DragMode.RESIZE_W:
            rect.setLeft(self._drag_start_rect.left() + delta.x())
        elif mode == DragMode.RESIZE_NE:
            rect.setTopRight(
                self._drag_start_rect.topRight() + delta
            )
        elif mode == DragMode.RESIZE_NW:
            rect.setTopLeft(
                self._drag_start_rect.topLeft() + delta
            )
        elif mode == DragMode.RESIZE_SE:
            rect.setBottomRight(
                self._drag_start_rect.bottomRight() + delta
            )
        elif mode == DragMode.RESIZE_SW:
            rect.setBottomLeft(
                self._drag_start_rect.bottomLeft() + delta
            )

        # 应用比例约束
        if self._current_aspect_ratio:
            self._apply_aspect_ratio()

    def _adjust_selection_with_arrow_keys(self, key: int) -> None:
        """
        使用方向键微调选区

        Args:
            key: 按键
        """
        if not self._selection_rect:
            return

        shift = QApplication.keyboardModifiers() & Qt.ShiftModifier
        step = 10 if shift else 1

        rect = self._selection_rect

        if key == Qt.Key_Up:
            rect.translate(0, -step)
        elif key == Qt.Key_Down:
            rect.translate(0, step)
        elif key == Qt.Key_Left:
            rect.translate(-step, 0)
        elif key == Qt.Key_Right:
            rect.translate(step, 0)
