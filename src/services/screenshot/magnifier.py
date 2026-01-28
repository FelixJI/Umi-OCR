#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 放大镜控件

实现截图时的放大镜功能,帮助用户精确选择区域。

主要功能：
- 实时显示鼠标附近的放大图像
- 可配置放大倍数和尺寸

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor

logger = logging.getLogger(__name__)


class Magnifier(QWidget):
    """
    放大镜控件

    在鼠标位置附近显示放大的图像。
    """

    # 放大镜配置
    ZOOM_FACTOR = 4              # 放大倍数
    SIZE = 120                  # 放大镜尺寸(像素)
    BORDER_WIDTH = 2             # 边框宽度

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化放大镜

        Args:
            parent: 父控件
        """
        super().__init__(parent)

        # 设置窗口属性
        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 设置固定大小
        self.setFixedSize(self.SIZE, self.SIZE)

        # 图像和位置
        self._source_image: Optional[QPixmap] = None
        self._screen_pos: QPoint = QPoint(0, 0)

        logger.debug("放大镜控件初始化完成")

    def update_position(self, local_pos: QPoint, source_image: QPixmap) -> None:
        """
        更新放大镜位置和图像

        Args:
            local_pos: 相对于源图像的本地坐标位置
            source_image: 源图像
        """
        if source_image.isNull():
            return

        # 保存本地坐标和图像
        self._local_pos = local_pos
        self._source_image = source_image

        # 计算放大镜显示位置(使用全局鼠标位置)
        global_pos = self.mapToGlobal(local_pos) if self.parent() else local_pos
        # 实际使用QCursor获取真实鼠标全局位置
        cursor_pos = QCursor.pos()
        magnifier_pos = self._calculate_magnifier_position(cursor_pos)
        self.move(magnifier_pos)

        # 重绘
        self.update()

    def _calculate_magnifier_position(self, mouse_pos: QPoint) -> QPoint:
        """
        计算放大镜显示位置

        避免遮挡鼠标,选择合适的位置。

        Args:
            mouse_pos: 鼠标位置

        Returns:
            QPoint: 放大镜位置
        """
        # 尝试在鼠标右下方显示
        pos = QPoint(
            mouse_pos.x() + 20,
            mouse_pos.y() + 20
        )

        # 检查是否超出屏幕
        screens = self.screen()
        if screens:
            screen_geometry = screens.geometry()

            # 如果超出右边界,移到左边
            if pos.x() + self.SIZE > screen_geometry.right():
                pos.setX(mouse_pos.x() - self.SIZE - 20)

            # 如果超出下边界,移到上边
            if pos.y() + self.SIZE > screen_geometry.bottom():
                pos.setY(mouse_pos.y() - self.SIZE - 20)

        return pos

    def paintEvent(self, event) -> None:
        """
        绘制事件

        Args:
            event: 绘制事件
        """
        super().paintEvent(event)

        if not self._source_image or self._source_image.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 计算源图像区域（使用本地坐标）
        half_size = self.SIZE // (2 * self.ZOOM_FACTOR)
        source_rect = QRect(
            self._local_pos.x() - half_size,
            self._local_pos.y() - half_size,
            self.SIZE // self.ZOOM_FACTOR,
            self.SIZE // self.ZOOM_FACTOR
        )

        # 确保不超出源图像范围
        image_rect = self._source_image.rect()
        source_rect = source_rect.intersected(image_rect)

        if source_rect.isEmpty():
            painter.end()
            return

        # 裁剪并缩放
        cropped = self._source_image.copy(source_rect)
        if not cropped.isNull():
            scaled = cropped.scaled(
                self.SIZE, self.SIZE,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # 绘制放大的图像
            painter.drawPixmap(0, 0, scaled)

        # 绘制十字准星
        painter.setPen(QPen(QColor(255, 0, 0, 150), 1))
        center = self.SIZE // 2
        painter.drawLine(center, 0, center, self.SIZE)
        painter.drawLine(0, center, self.SIZE, center)

        # 绘制边框
        painter.setPen(QPen(QColor(255, 255, 255), self.BORDER_WIDTH))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(0, 0, self.SIZE - 1, self.SIZE - 1)

        painter.end()

    def show_magnifier(self) -> None:
        """显示放大镜"""
        self.show()
        logger.debug("显示放大镜")

    def hide_magnifier(self) -> None:
        """隐藏放大镜"""
        self.hide()
        logger.debug("隐藏放大镜")
