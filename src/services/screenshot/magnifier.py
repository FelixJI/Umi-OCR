#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 放大镜控件

实现截图时的放大镜功能,帮助用户精确选择区域。

主要功能：
- 实时显示鼠标附近的放大图像
- 显示像素网格
- 显示坐标和颜色信息(RGB/HEX)
- 跟随鼠标移动

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import Optional

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QCursor, QBrush, QFont, QImage

logger = logging.getLogger(__name__)


class Magnifier(QWidget):
    """
    放大镜控件

    在鼠标位置附近显示放大的图像、网格、坐标和颜色信息。
    """

    # 放大镜配置
    ZOOM_FACTOR = 5  # 放大倍数 (奇数更容易居中)
    IMAGE_SIZE = 135  # 图像区域尺寸(像素) - 使用奇数倍数以确保中心像素居中 (135/5=27)
    INFO_HEIGHT = 110  # 信息区域高度
    BORDER_WIDTH = 1  # 边框宽度
    GRID_COLOR = QColor(255, 255, 255, 80)  # 网格颜色

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化放大镜

        Args:
            parent: 父控件
        """
        super().__init__(parent)

        # 设置窗口属性
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 设置固定大小
        self.setFixedSize(self.IMAGE_SIZE, self.IMAGE_SIZE + self.INFO_HEIGHT)

        # 状态数据
        self._source_image: Optional[QPixmap] = None
        self._local_pos: QPoint = QPoint(0, 0)
        self._global_offset: QPoint = QPoint(0, 0)
        self._current_color: QColor = QColor(0, 0, 0)
        self._pixel_ratio: float = 1.0
        self._center_pixel_pos: QPoint = QPoint(0, 0)
        self._avoid_rects: list = []  # 需要避开的区域列表

        logger.debug("放大镜控件初始化完成")

    def set_avoid_rects(self, rects: list) -> None:
        """
        设置需要避开的区域列表（如工具栏、模式按钮等）

        Args:
            rects: 需要避开的矩形列表
        """
        self._avoid_rects = rects if rects else []

    def update_position(
        self,
        local_pos: QPoint,
        source_image: QPixmap,
        global_offset: QPoint = None,
        pixel_ratio: float = 1.0,
        avoid_rects: list = None,
    ) -> None:
        """
        更新放大镜位置和图像

        Args:
            local_pos: 相对于源图像的本地坐标位置(逻辑坐标)
            source_image: 源图像(物理像素)
            global_offset: 本地坐标到全局坐标的偏移量
            pixel_ratio: 像素比率 (物理像素 / 逻辑像素)
            avoid_rects: 需要避开的区域列表（全局坐标）
        """
        if source_image.isNull():
            return

        self._local_pos = local_pos
        self._source_image = source_image
        self._global_offset = global_offset if global_offset else QPoint(0, 0)
        self._pixel_ratio = pixel_ratio
        self._avoid_rects = avoid_rects if avoid_rects else []

        # 计算在源图像中的物理坐标 center_x, center_y
        center_x = int(local_pos.x() * pixel_ratio)
        center_y = int(local_pos.y() * pixel_ratio)
        self._center_pixel_pos = QPoint(center_x, center_y)

        # 获取当前像素颜色
        # 优化：只复制1x1像素来获取颜色，避免转换大图
        if (
            0 <= center_x < source_image.width()
            and 0 <= center_y < source_image.height()
        ):
            pixel = source_image.copy(center_x, center_y, 1, 1)
            if not pixel.isNull():
                self._current_color = pixel.toImage().pixelColor(0, 0)

        # 计算放大镜显示位置(使用全局鼠标位置)
        cursor_pos = QCursor.pos()
        magnifier_pos = self._calculate_magnifier_position(cursor_pos)
        self.move(magnifier_pos)

        # 重绘
        self.update()

    def _calculate_magnifier_position(self, mouse_pos: QPoint) -> QPoint:
        """
        计算放大镜显示位置

        Args:
            mouse_pos: 鼠标位置

        Returns:
            QPoint: 放大镜位置
        """
        # 默认在鼠标右下方
        offset = 20
        pos = QPoint(mouse_pos.x() + offset, mouse_pos.y() + offset)

        # 检查是否超出屏幕
        screens = self.screen()
        screen_geometry = None
        if screens:
            screen_geometry = screens.geometry()

            # 只有当放大镜完全超出右边界时才改变位置
            # 策略：如果右边放不下，就放左边
            if pos.x() + self.width() > screen_geometry.right():
                pos.setX(mouse_pos.x() - self.width() - offset)

            # 如果下边放不下，就放上边
            if pos.y() + self.height() > screen_geometry.bottom():
                pos.setY(mouse_pos.y() - self.height() - offset)

            # 最后的边界检查，确保不超出屏幕左/上边界
            pos.setX(max(screen_geometry.left(), pos.x()))
            pos.setY(max(screen_geometry.top(), pos.y()))

        # 检查是否与需要避开的区域重叠（如工具栏、模式按钮等）
        pos = self._avoid_overlap(pos, mouse_pos, screen_geometry)

        return pos

    def _avoid_overlap(self, pos: QPoint, mouse_pos: QPoint, screen_geometry) -> QPoint:
        """
        避开与指定区域的重叠

        Args:
            pos: 当前计算的位置
            mouse_pos: 鼠标位置
            screen_geometry: 屏幕几何信息

        Returns:
            QPoint: 调整后的位置
        """
        magnifier_rect = QRect(pos.x(), pos.y(), self.width(), self.height())
        margin = 5  # 与避开区域的间距

        for avoid_rect in self._avoid_rects:
            # 检查是否重叠（增加一些边距）
            check_rect = avoid_rect.adjusted(-margin, -margin, margin, margin)

            if magnifier_rect.intersects(check_rect):
                # 有重叠，尝试调整位置
                # 策略：依次尝试上、下、左、右四个方向
                new_positions = [
                    # 上方
                    QPoint(pos.x(), avoid_rect.top() - self.height() - margin),
                    # 下方
                    QPoint(pos.x(), avoid_rect.bottom() + margin),
                    # 左侧
                    QPoint(avoid_rect.left() - self.width() - margin, pos.y()),
                    # 右侧
                    QPoint(avoid_rect.right() + margin, pos.y()),
                ]

                # 找到第一个不超出屏幕且不与鼠标重叠的位置
                for new_pos in new_positions:
                    if screen_geometry:
                        # 检查屏幕边界
                        if (new_pos.x() < screen_geometry.left() or
                            new_pos.y() < screen_geometry.top() or
                            new_pos.x() + self.width() > screen_geometry.right() or
                            new_pos.y() + self.height() > screen_geometry.bottom()):
                            continue

                    # 检查是否与鼠标位置重叠（避免遮挡鼠标）
                    mouse_rect = QRect(mouse_pos.x() - 10, mouse_pos.y() - 10, 20, 20)
                    new_magnifier_rect = QRect(new_pos.x(), new_pos.y(), self.width(), self.height())
                    if not new_magnifier_rect.intersects(mouse_rect):
                        # 找到合适位置，返回
                        return new_pos

                # 如果所有位置都不合适，保持原位置
                break

        return pos

    def paintEvent(self, event) -> None:
        """
        绘制事件
        """
        super().paintEvent(event)

        if not self._source_image or self._source_image.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)  # 关闭抗锯齿以显示清晰像素

        # 1. 绘制背景
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

        # 2. 绘制放大的图像
        self._draw_magnified_image(painter)

        # 3. 绘制信息栏
        self._draw_info_panel(painter)

        # 4. 绘制边框
        self._draw_border(painter)

        painter.end()

    def _draw_border(self, painter: QPainter) -> None:
        """
        绘制边框（包括反色外圈）
        使用与背景相反的颜色使放大镜更容易识别
        """
        # 外圈反色边框宽度
        border_width = 3

        # 第一层：白色边框（内圈）
        painter.setPen(QPen(QColor(255, 255, 255), border_width))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(
            border_width // 2,
            border_width // 2,
            self.width() - border_width - 1,
            self.height() - border_width - 1
        )

        # 第二层：黑色边框（外圈，形成反色对比效果）
        painter.setPen(QPen(QColor(0, 0, 0), border_width))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        # 图像区和信息区的分割线
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawLine(0, self.IMAGE_SIZE, self.width(), self.IMAGE_SIZE)

    def _draw_magnified_image(self, painter: QPainter) -> None:
        """绘制放大的图像和网格"""
        # 计算源图像区域
        # 我们希望显示 IMAGE_SIZE / ZOOM_FACTOR 个像素
        visible_pixels = self.IMAGE_SIZE // self.ZOOM_FACTOR
        half_pixels = visible_pixels // 2
        
        # 使用计算出的物理像素中心
        center_x = self._center_pixel_pos.x()
        center_y = self._center_pixel_pos.y()
        
        source_rect = QRect(
            center_x - half_pixels,
            center_y - half_pixels,
            visible_pixels,
            visible_pixels,
        )

        # 绘制图像
        # copy会自动处理边界，超出部分为透明/空
        # 但我们需要处理边缘情况，避免图像拉伸错误
        # 简单的做法是先填黑底，再画图
        
        # 目标区域
        target_rect = QRect(0, 0, self.IMAGE_SIZE, self.IMAGE_SIZE)
        
        # 从源图像复制
        # 注意：QPixmap.copy 如果超出范围，返回的图像会变小
        cropped = self._source_image.copy(source_rect)
        
        if not cropped.isNull():
            # 计算缩放后的尺寸
            scaled_w = cropped.width() * self.ZOOM_FACTOR
            scaled_h = cropped.height() * self.ZOOM_FACTOR
            
            # 计算在目标区域中的偏移
            # 如果 source_rect 在图像左/上边缘之外，copy 出来的图会从 (0,0) 开始，导致绘制时需要向右/下偏移
            # 计算 cropped 对应 source_rect 的哪一部分
            
            # 实际截取区域的左上角
            actual_x = max(0, source_rect.x())
            actual_y = max(0, source_rect.y())
            
            # 偏移量 (放大后)
            offset_x = (actual_x - source_rect.x()) * self.ZOOM_FACTOR
            offset_y = (actual_y - source_rect.y()) * self.ZOOM_FACTOR
            
            draw_rect = QRect(offset_x, offset_y, scaled_w, scaled_h)
            
            # 绘制放大后的图像
            painter.drawPixmap(draw_rect, cropped)

        # 绘制十字准星 (中心像素)
        center_pos = self.IMAGE_SIZE // 2
        pixel_size = self.ZOOM_FACTOR
        center_rect = QRect(
            center_pos - pixel_size // 2,
            center_pos - pixel_size // 2,
            pixel_size,
            pixel_size
        )
        
        # 绘制中心像素高亮边框
        painter.setPen(QPen(QColor(255, 0, 0, 180), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(center_rect)
        
        # 绘制网格
        self._draw_grid(painter)

    def _draw_grid(self, painter: QPainter) -> None:
        """绘制网格和中心标识"""
        visible_pixels = self.IMAGE_SIZE // self.ZOOM_FACTOR
        half_pixels = visible_pixels // 2

        # 绘制网格
        painter.setPen(QPen(self.GRID_COLOR, 1))
        for i in range(visible_pixels + 1):
            pos = i * self.ZOOM_FACTOR
            # 竖线
            painter.drawLine(pos, 0, pos, self.IMAGE_SIZE)
            # 横线
            painter.drawLine(0, pos, self.IMAGE_SIZE, pos)

        # 绘制中心十字/高亮框
        # 高亮中心像素
        center_x = half_pixels * self.ZOOM_FACTOR
        center_y = half_pixels * self.ZOOM_FACTOR
        
        # 绿色边框高亮中心像素
        painter.setPen(QPen(QColor(0, 255, 0), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(center_x, center_y, self.ZOOM_FACTOR, self.ZOOM_FACTOR)
        
        # 十字准星 (延伸到整个图像区域)
        painter.setPen(QPen(QColor(0, 255, 0, 120), 1))
        center_center_x = center_x + self.ZOOM_FACTOR // 2
        center_center_y = center_y + self.ZOOM_FACTOR // 2
        
        # 留出中心像素不画十字，避免遮挡
        painter.drawLine(center_center_x, 0, center_center_x, center_y)
        painter.drawLine(center_center_x, center_y + self.ZOOM_FACTOR, center_center_x, self.IMAGE_SIZE)
        painter.drawLine(0, center_center_y, center_x, center_center_y)
        painter.drawLine(center_x + self.ZOOM_FACTOR, center_center_y, self.IMAGE_SIZE, center_center_y)

    def _draw_info_panel(self, painter: QPainter) -> None:
        """绘制信息面板"""
        # 字体设置
        font = painter.font()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(8)
        painter.setFont(font)
        
        # 文本颜色
        painter.setPen(QColor(255, 255, 255))
        
        # 布局参数
        margin_x = 8
        start_y = self.IMAGE_SIZE + 16
        line_height = 18
        
        # 1. 坐标信息
        coord_text = f"POS: ({self._local_pos.x()}, {self._local_pos.y()})"
        painter.drawText(margin_x, start_y, coord_text)
        
        # 2. RGB信息
        rgb = self._current_color
        rgb_text = f"RGB: ({rgb.red()}, {rgb.green()}, {rgb.blue()})"
        painter.drawText(margin_x, start_y + line_height, rgb_text)
        
        # 3. HEX信息
        hex_text = f"HEX: {rgb.name().upper()}"
        painter.drawText(margin_x, start_y + line_height * 2, hex_text)
        
        # 4. 颜色预览块
        preview_size = 30
        preview_x = margin_x
        preview_y = start_y + line_height * 3 + 4
        
        # 颜色块背景（棋盘格，用于显示透明度，虽然这里主要是屏幕截图可能不透明，但保持严谨）
        # 简单起见，画个白框黑底
        painter.fillRect(preview_x, preview_y, preview_size, preview_size, Qt.black)
        painter.fillRect(preview_x, preview_y, preview_size, preview_size, rgb)
        
        # 颜色块边框
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(preview_x, preview_y, preview_size, preview_size)

    def show_magnifier(self) -> None:
        """显示放大镜"""
        self.show()
        logger.debug("显示放大镜")

    def hide_magnifier(self) -> None:
        """隐藏放大镜并清理状态"""
        self.hide()
        # 清理状态，避免下次显示时出现残留
        self._source_image = None
        self._local_pos = QPoint(0, 0)
        self._center_pixel_pos = QPoint(0, 0)
        logger.debug("隐藏放大镜")
