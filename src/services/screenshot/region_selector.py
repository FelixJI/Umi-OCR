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
from typing import Optional

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor

from .screen_capture import ScreenCapture
from .window_detector import WindowDetector, WindowInfo
from .magnifier import Magnifier

logger = logging.getLogger(__name__)


class DragMode(Enum):
    """拖动模式"""

    NONE = "none"
    CREATE = "create"  # 创建新选区
    MOVE = "move"  # 移动选区
    RESIZE_N = "resize_n"  # 调整上边
    RESIZE_S = "resize_s"  # 调整下边
    RESIZE_E = "resize_e"  # 调整右边
    RESIZE_W = "resize_w"  # 调整左边
    RESIZE_NE = "resize_ne"  # 调整右上角
    RESIZE_NW = "resize_nw"  # 调整左上角
    RESIZE_SE = "resize_se"  # 调整右下角
    RESIZE_SW = "resize_sw"  # 调整左下角


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
    region_selected = Signal(QRect)  # 选区完成
    selection_cancelled = Signal()  # 取消选择
    save_requested = Signal(QRect)  # 请求保存
    copy_requested = Signal(QRect)  # 请求复制
    mode_changed = Signal(str)      # 模式改变 (text/table)

    # 比例预设
    ASPECT_RATIOS = {
        "free": None,  # 自由比例
        "1:1": 1.0,  # 正方形
        "4:3": 4 / 3,
        "16:9": 16 / 9,
        "3:2": 3 / 2,
    }

    # 手柄尺寸
    HANDLE_SIZE = 14

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        screen_capture: Optional[ScreenCapture] = None,
    ):
        """
        初始化区域选择器

        Args:
            parent: 父窗口
            screen_capture: 屏幕捕获实例
        """
        super().__init__(parent)

        # 创建跨屏无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 初始化服务
        self._screen_capture = screen_capture if screen_capture else ScreenCapture()
        self._window_detector = WindowDetector()
        self._magnifier = Magnifier(self)

        # 选区状态
        self._selection_rect: Optional[QRect] = None
        self._hovered_window: Optional[WindowInfo] = None
        self._current_aspect_ratio: Optional[float] = None
        self._is_shift_pressed = False
        self._ocr_mode = "text"  # OCR模式: text, table

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

        # 重置状态
        self._selection_rect = None
        self._is_dragging = False
        self._hovered_window = None
        self._current_aspect_ratio = None
        self._ocr_mode = "text"
        self._is_shift_pressed = False

        # 重置光标
        self.setCursor(Qt.CrossCursor)

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

        # 获取键盘焦点，确保键盘事件正常处理
        self.grabKeyboard()

        # 激活窗口，确保能接收键盘事件
        self.activateWindow()

        logger.info("区域选择窗口已显示")

    def hideEvent(self, event) -> None:
        """窗口隐藏事件"""
        self._magnifier.hide_magnifier()
        super().hideEvent(event)

    def stop(self) -> None:
        """
        停止选区

        隐藏窗口和放大镜，释放资源。
        """
        logger.info("停止区域选择")

        # 先隐藏放大镜，避免残留
        self._magnifier.hide_magnifier()

        # 释放键盘焦点
        self.releaseKeyboard()

        # 重置拖动状态
        self._is_dragging = False
        self._drag_mode = DragMode.NONE

        # 重置选区状态，避免下次启动时旧选区闪现
        self._selection_rect = None

        # 隐藏窗口
        self.hide()

    def _local_to_global_rect(self, local_rect: QRect) -> QRect:
        """
        将本地坐标转换为全局屏幕坐标

        Args:
            local_rect: 本地坐标矩形

        Returns:
            QRect: 全局屏幕坐标矩形
        """
        if not hasattr(self, "_virtual_geometry"):
            return local_rect

        # 窗口的左上角在全局屏幕中的位置
        offset = self._virtual_geometry.topLeft()

        # 转换坐标
        global_rect = QRect(
            local_rect.left() + offset.x(),
            local_rect.top() + offset.y(),
            local_rect.width(),
            local_rect.height(),
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
        if not hasattr(self, "_virtual_geometry"):
            return global_pos

        offset = self._virtual_geometry.topLeft()
        return QPoint(global_pos.x() - offset.x(), global_pos.y() - offset.y())

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

        # 1. 绘制半透明遮罩层（降低透明度使遮罩更浅）
        mask_color = QColor(0, 0, 0, 60)
        painter.fillRect(self.rect(), mask_color)

        # 2. 绘制选区(无遮罩,显示原图)
        if self._selection_rect and not self._selection_rect.isEmpty():
            # 计算像素比率 (图片物理宽度 / 窗口逻辑宽度)
            pixel_ratio = 1.0
            if self._background_image and not self._background_image.isNull() and self.width() > 0:
                pixel_ratio = self._background_image.width() / self.width()

            # 计算源矩形 (物理坐标)
            source_rect = QRect(
                int(self._selection_rect.x() * pixel_ratio),
                int(self._selection_rect.y() * pixel_ratio),
                int(self._selection_rect.width() * pixel_ratio),
                int(self._selection_rect.height() * pixel_ratio)
            )

            # 绘制选区原图
            painter.drawPixmap(self._selection_rect, self._background_image, source_rect)

            # 绘制选区边框
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self._selection_rect)

            # 绘制调整手柄
            self._draw_resize_handles(painter)

            # 绘制坐标信息
            self._draw_coordinate_info(painter)

            # 绘制比例选择工具栏
            self._draw_ratio_toolbar(painter)

            # 绘制模式切换按钮
            self._draw_mode_buttons(painter)

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
            "tl": rect.topLeft(),
            "tr": rect.topRight(),
            "bl": rect.bottomLeft(),
            "br": rect.bottomRight(),
            "t": QPoint(rect.center().x(), rect.top()),
            "b": QPoint(rect.center().x(), rect.bottom()),
            "l": QPoint(rect.left(), rect.center().y()),
            "r": QPoint(rect.right(), rect.center().y()),
        }

        # 绘制手柄
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(QPen(QColor(0, 0, 0), 1))

        for pos in handles.values():
            painter.drawRect(
                pos.x() - h, pos.y() - h, self.HANDLE_SIZE, self.HANDLE_SIZE
            )

    def _draw_coordinate_info(self, painter: QPainter) -> None:
        """
        绘制坐标信息（显示在选区左上角）

        Args:
            painter: 绘制器
        """
        if not self._selection_rect:
            return

        rect = self._selection_rect

        # 准备信息文本：坐标和大小
        lines = [f"{rect.width()} x {rect.height()}", f"({rect.left()}, {rect.top()})"]

        # 绘制背景框
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        font_metrics = painter.fontMetrics()
        line_height = font_metrics.height()
        max_width = max(font_metrics.horizontalAdvance(line) for line in lines)

        # 计算文本位置（显示在选区左上角外侧）
        padding = 6
        bg_width = max_width + padding * 2
        bg_height = len(lines) * line_height + padding

        # 默认显示在左上角上方
        text_x = rect.left()
        text_y = rect.top() - bg_height - 4

        # 如果上方空间不足，显示在选区内部左上角
        if text_y < 0:
            text_y = rect.top() + padding
            text_x = rect.left() + padding
        else:
            text_x = rect.left() + padding

        # 绘制半透明背景
        bg_rect = QRect(
            text_x - padding,
            text_y - padding + 4 if text_y > rect.top() else text_y - padding,
            bg_width,
            bg_height,
        )
        painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bg_rect, 4, 4)

        # 绘制文本
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        for i, line in enumerate(lines):
            y_offset = (
                text_y
                + i * line_height
                + (
                    font_metrics.ascent()
                    if text_y > rect.top()
                    else font_metrics.ascent()
                )
            )
            painter.drawText(text_x, y_offset, line)

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

    def _draw_ratio_toolbar(self, painter: QPainter) -> None:
        """
        绘制比例选择工具栏（悬浮在选区下方）
        包含：比例选择、保存、复制
        """
        if not self._selection_rect:
            return

        rect = self._selection_rect

        # 按钮配置
        ratios = ["自由", "1:1", "4:3", "16:9", "3:2"]
        ratio_values = [None, 1.0, 4 / 3, 16 / 9, 3 / 2]
        actions = ["💾保存", "📋复制"]
        action_keys = ["save", "copy"]

        button_width = 50
        button_height = 28
        button_spacing = 4
        group_spacing = 12  # 组间距
        toolbar_padding = 8

        # 计算工具栏尺寸
        ratio_group_width = len(ratios) * button_width + (len(ratios) - 1) * button_spacing
        action_group_width = len(actions) * button_width + (len(actions) - 1) * button_spacing
        toolbar_width = ratio_group_width + group_spacing + action_group_width + toolbar_padding * 2
        toolbar_height = button_height + toolbar_padding * 2

        # 计算工具栏位置（选区下方居中）
        toolbar_x = rect.center().x() - toolbar_width // 2
        toolbar_y = rect.bottom() + 12

        # 如果下方空间不足，显示在选区上方
        if toolbar_y + toolbar_height > self.height():
            toolbar_y = rect.top() - toolbar_height - 12

        # 确保不超出屏幕边界
        toolbar_x = max(10, min(toolbar_x, self.width() - toolbar_width - 10))
        toolbar_y = max(10, toolbar_y)

        self._toolbar_rect = QRect(toolbar_x, toolbar_y, toolbar_width, toolbar_height)

        # 绘制工具栏背景
        painter.setBrush(QBrush(QColor(40, 40, 40, 220)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self._toolbar_rect, 8, 8)

        # 字体设置
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        font_metrics = painter.fontMetrics()

        self._toolbar_items = []  # (rect, type, value)

        current_x = toolbar_x + toolbar_padding
        btn_y = toolbar_y + toolbar_padding

        # 1. 绘制比例按钮
        for i, (ratio_name, ratio_value) in enumerate(zip(ratios, ratio_values)):
            btn_rect = QRect(current_x, btn_y, button_width, button_height)
            self._toolbar_items.append((btn_rect, 'ratio', ratio_value))

            # 判断是否当前选中
            is_selected = self._current_aspect_ratio == ratio_value or (
                self._current_aspect_ratio is None and ratio_value is None
            )

            self._draw_toolbar_button(painter, btn_rect, ratio_name, is_selected)
            current_x += button_width + button_spacing

        # 分隔线
        sep_x = current_x + group_spacing // 2 - button_spacing // 2
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawLine(sep_x, btn_y + 4, sep_x, btn_y + button_height - 4)
        
        current_x += group_spacing

        # 2. 绘制操作按钮
        for name, key in zip(actions, action_keys):
            btn_rect = QRect(current_x, btn_y, button_width, button_height)
            self._toolbar_items.append((btn_rect, 'action', key))
            
            self._draw_toolbar_button(painter, btn_rect, name, False)
            current_x += button_width + button_spacing

    def _draw_toolbar_button(self, painter: QPainter, rect: QRect, text: str, is_selected: bool):
        """绘制工具栏按钮"""
        # 背景
        if is_selected:
            painter.setBrush(QBrush(QColor(0, 120, 215)))
        elif rect.contains(self._mouse_pos):
            painter.setBrush(QBrush(QColor(80, 80, 80)))
        else:
            painter.setBrush(Qt.NoBrush) # 透明背景

        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 6, 6)

        # 文字
        if is_selected:
            painter.setPen(QPen(QColor(255, 255, 255), 1))
        elif rect.contains(self._mouse_pos):
             painter.setPen(QPen(QColor(255, 255, 255), 1))
        else:
            painter.setPen(QPen(QColor(200, 200, 200), 1))

        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(text)
        text_x = rect.x() + (rect.width() - text_width) // 2
        text_y = rect.y() + (rect.height() + font_metrics.ascent() - font_metrics.descent()) // 2
        painter.drawText(text_x, text_y, text)

    def _draw_mode_buttons(self, painter: QPainter) -> None:
        """绘制模式切换按钮（选区右侧）"""
        if not self._selection_rect:
            return
            
        rect = self._selection_rect
        
        buttons = [("文本", "text"), ("表格", "table")]
        button_width = 40
        button_height = 30
        spacing = 8
        
        # Calculate position
        x = rect.right() + 12
        total_height = len(buttons) * button_height + (len(buttons) - 1) * spacing
        start_y = rect.top()
        
        # If right side no space, show on left
        if x + button_width > self.width():
            x = rect.left() - button_width - 12
        
        # Ensure y is within screen
        start_y = max(10, min(start_y, self.height() - total_height - 10))
        
        self._mode_button_rects = [] # (rect, mode_key)
        
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        
        current_y = start_y
        for name, key in buttons:
            btn_rect = QRect(x, current_y, button_width, button_height)
            self._mode_button_rects.append((btn_rect, key))
            
            is_selected = self._ocr_mode == key
            
            # Draw background
            if is_selected:
                painter.setBrush(QBrush(QColor(0, 120, 215)))
            elif btn_rect.contains(self._mouse_pos):
                painter.setBrush(QBrush(QColor(80, 80, 80)))
            else:
                painter.setBrush(QBrush(QColor(40, 40, 40, 220)))
                
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(btn_rect, 6, 6)
            
            # Draw Text
            if is_selected or btn_rect.contains(self._mouse_pos):
                painter.setPen(QPen(QColor(255, 255, 255), 1))
            else:
                painter.setPen(QPen(QColor(200, 200, 200), 1))
                
            painter.drawText(btn_rect, Qt.AlignCenter, name)
            
            current_y += button_height + spacing

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
            "1-5: 比例 | Shift: 锁定 | 拖动边缘: 调整",
        ]

        # 设置字体
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        font_metrics = painter.fontMetrics()
        line_height = font_metrics.height()

        # 绘制半透明背景
        bg_width = (
            max(
                font_metrics.horizontalAdvance(mouse_text),
                max(font_metrics.horizontalAdvance(h) for h in hints),
            )
            + 20
        )
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

        开始创建或调整选区，或点击比例按钮。

        Args:
            event: 鼠标事件
        """
        pos = event.pos()

        # 检查是否点击在比例工具栏上 (包括操作按钮)
        if hasattr(self, "_toolbar_items") and self._selection_rect:
            for btn_rect, type_, value in self._toolbar_items:
                if btn_rect.contains(pos):
                    if type_ == 'ratio':
                        self._current_aspect_ratio = value
                        if value is not None:
                            self._apply_aspect_ratio_with_ratio(value)
                        logger.debug(f"选择比例: {value}")
                        self.update()
                    elif type_ == 'action':
                        if value == 'save':
                            global_rect = self._local_to_global_rect(self._selection_rect)
                            self.save_requested.emit(global_rect)
                        elif value == 'copy':
                            global_rect = self._local_to_global_rect(self._selection_rect)
                            self.copy_requested.emit(global_rect)
                    return

        # 检查是否点击在模式按钮上
        if hasattr(self, "_mode_button_rects") and self._selection_rect:
            for btn_rect, key in self._mode_button_rects:
                if btn_rect.contains(pos):
                    self._ocr_mode = key
                    self.mode_changed.emit(key)
                    self.update()
                    logger.debug(f"切换模式: {key}")
                    return

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
            pixel_ratio = 1.0
            if self.width() > 0:
                pixel_ratio = self._background_image.width() / self.width()

            # 计算放大镜应该跟踪的位置
            # 在拖动调整选区时，放大镜跟踪选框的角/边点，而不是鼠标位置
            magnifier_pos = pos
            if self._is_dragging and self._selection_rect and self._drag_mode != DragMode.CREATE and self._drag_mode != DragMode.MOVE:
                # 调整大小时，放大镜跟踪选框对应的角/边点
                magnifier_pos = self._get_magnifier_focus_point()

            # 收集需要避开的区域（工具栏和模式按钮）
            avoid_rects = []
            if hasattr(self, "_toolbar_rect") and self._toolbar_rect:
                avoid_rects.append(self._toolbar_rect)
            if hasattr(self, "_mode_button_rects"):
                for btn_rect, _ in self._mode_button_rects:
                    avoid_rects.append(btn_rect)

            self._magnifier.update_position(
                magnifier_pos,
                self._background_image,
                pixel_ratio=pixel_ratio,
                avoid_rects=avoid_rects
            )

        # 更新光标形状（包括拖动时）
        cursor = self._get_cursor_for_position(pos)
        self.setCursor(cursor)
        
        # 强制刷新以更新按钮悬停状态
        self.update()

        # 处理拖动
        if self._is_dragging:
            delta = pos - self._drag_start_pos

            if self._drag_mode == DragMode.CREATE:
                # 创建选区
                self._selection_rect = QRect(self._drag_start_pos, pos).normalized()

                # 按比例约束（包括 Shift 临时锁定的正方形）
                if self._current_aspect_ratio or self._is_shift_pressed:
                    ratio = (
                        self._current_aspect_ratio
                        if self._current_aspect_ratio
                        else 1.0
                    )
                    self._apply_aspect_ratio_with_ratio(ratio)

            elif self._drag_mode == DragMode.MOVE:
                # 移动选区
                self._selection_rect.moveTo(self._drag_start_rect.topLeft() + delta)

            else:
                # 调整大小
                self._resize_selection(delta)

            self.update()
            return

        # 检测窗口悬停
        if not self._selection_rect or not self._selection_rect.contains(pos):
            self._hovered_window = self._window_detector.get_window_at(
                self.mapToGlobal(pos)
            )
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
                logger.info(
                    f"选区确认 (本地: {self._selection_rect}, 全局: {global_rect})"
                )
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
            # 检查是否在预设比例中，如果不是则清除
            if self._current_aspect_ratio == 1.0:
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
            DragMode.RESIZE_E: QPoint(rect.right(), rect.center().y()),
        }

        for mode, handle_pos in handles.items():
            if (pos - handle_pos).manhattanLength() < h:
                return mode

        return DragMode.NONE

    def _get_magnifier_focus_point(self) -> QPoint:
        """
        获取放大镜应该跟踪的焦点位置

        在调整选区大小时，放大镜应该跟踪选框的角/边点，
        而不是鼠标位置，这样用户可以更精确地看到选框边缘的像素。

        Returns:
            QPoint: 焦点位置（本地坐标）
        """
        if not self._selection_rect:
            return self._mouse_pos

        rect = self._selection_rect
        mode = self._drag_mode

        # 根据拖动模式返回对应的焦点位置
        if mode == DragMode.RESIZE_NW:
            return rect.topLeft()
        elif mode == DragMode.RESIZE_NE:
            return rect.topRight()
        elif mode == DragMode.RESIZE_SW:
            return rect.bottomLeft()
        elif mode == DragMode.RESIZE_SE:
            return rect.bottomRight()
        elif mode == DragMode.RESIZE_N:
            return QPoint(rect.center().x(), rect.top())
        elif mode == DragMode.RESIZE_S:
            return QPoint(rect.center().x(), rect.bottom())
        elif mode == DragMode.RESIZE_W:
            return QPoint(rect.left(), rect.center().y())
        elif mode == DragMode.RESIZE_E:
            return QPoint(rect.right(), rect.center().y())
        else:
            return self._mouse_pos

    def _get_cursor_for_position(self, pos: QPoint) -> Qt.CursorShape:
        """
        根据鼠标位置获取应该显示的光标形状

        Args:
            pos: 鼠标位置

        Returns:
            Qt.CursorShape: 光标形状
        """
        # 1. 检查是否在工具栏按钮上（优先级最高）
        if hasattr(self, "_toolbar_items"):
            for btn_rect, _, _ in self._toolbar_items:
                if btn_rect.contains(pos):
                    return Qt.PointingHandCursor

        # 2. 检查是否在模式按钮上
        if hasattr(self, "_mode_button_rects"):
            for btn_rect, _ in self._mode_button_rects:
                if btn_rect.contains(pos):
                    return Qt.PointingHandCursor

        # 3. 检查是否在选区的调整手柄上
        if self._selection_rect:
            handle_mode = self._get_resize_handle(pos)
            if handle_mode != DragMode.NONE:
                if handle_mode in (DragMode.RESIZE_N, DragMode.RESIZE_S):
                    return Qt.SizeVerCursor
                elif handle_mode in (DragMode.RESIZE_E, DragMode.RESIZE_W):
                    return Qt.SizeHorCursor
                elif handle_mode in (DragMode.RESIZE_NE, DragMode.RESIZE_SW):
                    return Qt.SizeBDiagCursor
                elif handle_mode in (DragMode.RESIZE_NW, DragMode.RESIZE_SE):
                    return Qt.SizeFDiagCursor

            # 4. 检查是否在选区内部（拖动模式）
            if self._selection_rect.contains(pos):
                return Qt.SizeAllCursor

        # 5. 默认十字光标
        return Qt.CrossCursor

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

        # 当前鼠标位置
        current_pos = self._drag_start_pos + delta
        
        # 基础矩形（从拖动开始时的状态计算）
        rect = QRect(self._drag_start_rect)
        
        # 检查是否有比例约束
        ratio = self._current_aspect_ratio
        if not ratio and self._is_shift_pressed:
            ratio = 1.0
            
        if ratio:
            # 比例约束调整
            self._resize_with_ratio(rect, current_pos, self._drag_mode, ratio)
        else:
            # 自由调整
            mode = self._drag_mode
            if mode == DragMode.RESIZE_N:
                rect.setTop(current_pos.y())
            elif mode == DragMode.RESIZE_S:
                rect.setBottom(current_pos.y())
            elif mode == DragMode.RESIZE_E:
                rect.setRight(current_pos.x())
            elif mode == DragMode.RESIZE_W:
                rect.setLeft(current_pos.x())
            elif mode == DragMode.RESIZE_NE:
                rect.setTopRight(current_pos)
            elif mode == DragMode.RESIZE_NW:
                rect.setTopLeft(current_pos)
            elif mode == DragMode.RESIZE_SE:
                rect.setBottomRight(current_pos)
            elif mode == DragMode.RESIZE_SW:
                rect.setBottomLeft(current_pos)

        self._selection_rect = rect.normalized()

    def _resize_with_ratio(self, rect: QRect, pos: QPoint, mode: DragMode, ratio: float) -> None:
        """
        带比例约束的调整
        
        Args:
            rect: 要修改的矩形(in/out)
            pos: 当前鼠标位置
            mode: 拖动模式
            ratio: 宽高比 (width/height)
        """
        # 1. 角调整：固定对角点
        if mode in (DragMode.RESIZE_NW, DragMode.RESIZE_NE, DragMode.RESIZE_SW, DragMode.RESIZE_SE):
            fixed_point = QPoint()
            if mode == DragMode.RESIZE_NW:
                fixed_point = self._drag_start_rect.bottomRight()
            elif mode == DragMode.RESIZE_NE:
                fixed_point = self._drag_start_rect.bottomLeft()
            elif mode == DragMode.RESIZE_SW:
                fixed_point = self._drag_start_rect.topRight()
            elif mode == DragMode.RESIZE_SE:
                fixed_point = self._drag_start_rect.topLeft()
                
            # 计算新的宽和高（基于固定点）
            # 使用 abs 确保方向正确，最后再根据方向调整坐标
            width = abs(pos.x() - fixed_point.x())
            height = abs(pos.y() - fixed_point.y())
            
            # 按照比例约束
            # 策略：取较大的变化方向作为主导，或者取当前鼠标位置对应的最大矩形
            # 这里简单处理：如果 width/height > ratio，说明宽度偏大，以高度为准计算宽度，反之亦然
            # 或者更直观的：以鼠标拖动距离较长的轴为主
            
            if height == 0: height = 1
            current_ratio = width / height
            
            if current_ratio > ratio:
                # 宽度过大（相对于高度），以高度为基准，或者限制宽度？
                # 通常是取由于鼠标位置导致的较大的一边？
                # 让我们尝试：保持鼠标所在的那个轴的值，调整另一个轴
                # 比如鼠标在很远X，很近Y，我们应该让Y变大来匹配X？还是让X变小匹配Y？
                # 标准做法是投影到对角线上。
                # 简单做法：取 max(width, height * ratio) 的维度? 不行，单位不一样。
                # 采用：谁更大（归一化后）听谁的。
                if width / ratio > height:
                    # 宽度由于比例要求更大，说明鼠标在X轴拉得更远 -> 以X为准
                    height = int(width / ratio)
                else:
                    width = int(height * ratio)
            else:
                if height * ratio > width:
                    width = int(height * ratio)
                else:
                    height = int(width / ratio)
            
            # 根据固定点和当前鼠标相对位置确定新矩形方向
            new_x = fixed_point.x()
            new_y = fixed_point.y()
            
            # 判断方向
            if pos.x() < fixed_point.x():
                new_x -= width
            
            if pos.y() < fixed_point.y():
                new_y -= height
                
            # 对于 NE/SW/NW/SE，方向是固定的，可以直接设置
            if mode == DragMode.RESIZE_SE:
                rect.setTopLeft(fixed_point)
                rect.setWidth(width)
                rect.setHeight(height)
            elif mode == DragMode.RESIZE_NW:
                rect.setBottomRight(fixed_point)
                rect.setLeft(fixed_point.x() - width)
                rect.setTop(fixed_point.y() - height)
            elif mode == DragMode.RESIZE_NE:
                rect.setBottomLeft(fixed_point)
                rect.setWidth(width)
                rect.setTop(fixed_point.y() - height)
            elif mode == DragMode.RESIZE_SW:
                rect.setTopRight(fixed_point)
                rect.setLeft(fixed_point.x() - width)
                rect.setHeight(height)
                
        # 2. 边调整：固定中心轴
        elif mode in (DragMode.RESIZE_N, DragMode.RESIZE_S, DragMode.RESIZE_E, DragMode.RESIZE_W):
            center = self._drag_start_rect.center()
            
            if mode == DragMode.RESIZE_E: # 调整右边，左边不动，高度居中调整
                new_width = abs(pos.x() - self._drag_start_rect.left())
                new_height = int(new_width / ratio)
                rect.setLeft(self._drag_start_rect.left())
                rect.setWidth(new_width)
                rect.setTop(center.y() - new_height // 2)
                rect.setHeight(new_height)
                
            elif mode == DragMode.RESIZE_W: # 调整左边，右边不动
                new_width = abs(self._drag_start_rect.right() - pos.x())
                new_height = int(new_width / ratio)
                rect.setRight(self._drag_start_rect.right())
                rect.setLeft(self._drag_start_rect.right() - new_width)
                rect.setTop(center.y() - new_height // 2)
                rect.setHeight(new_height)
                
            elif mode == DragMode.RESIZE_S: # 调整下边，上边不动，宽度居中调整
                new_height = abs(pos.y() - self._drag_start_rect.top())
                new_width = int(new_height * ratio)
                rect.setTop(self._drag_start_rect.top())
                rect.setHeight(new_height)
                rect.setLeft(center.x() - new_width // 2)
                rect.setWidth(new_width)
                
            elif mode == DragMode.RESIZE_N: # 调整上边，下边不动
                new_height = abs(self._drag_start_rect.bottom() - pos.y())
                new_width = int(new_height * ratio)
                rect.setBottom(self._drag_start_rect.bottom())
                rect.setTop(self._drag_start_rect.bottom() - new_height)
                rect.setLeft(center.x() - new_width // 2)
                rect.setWidth(new_width)

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
