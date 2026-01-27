#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 屏幕捕获服务

实现跨屏幕的屏幕捕获功能，支持多显示器。

主要功能：
- 获取所有显示器信息
- 获取跨屏虚拟画布范围
- 截取指定区域
- 截取全屏

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from dataclasses import dataclass
from typing import List

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QScreen, QPixmap
from PySide6.QtCore import QRect, QPoint

logger = logging.getLogger(__name__)


@dataclass
class ScreenInfo:
    """显示器信息"""
    name: str                      # 显示器名称
    geometry: QRect                 # 显示器几何信息
    is_primary: bool               # 是否为主显示器
    scale_factor: float            # 缩放因子 (DPI缩放)


class ScreenCapture:
    """
    屏幕捕获服务

    提供跨屏幕的屏幕捕获功能。
    """

    def __init__(self):
        """初始化屏幕捕获服务"""
        self._app = QApplication.instance()
        if not self._app:
            raise RuntimeError("QApplication未初始化")

        logger.info("屏幕捕获服务初始化完成")

    def get_all_screens(self) -> List[ScreenInfo]:
        """
        获取所有显示器信息

        Returns:
            List[ScreenInfo]: 显示器信息列表
        """
        screens = self._app.screens()
        screen_info_list = []

        for screen in screens:
            screen_info = ScreenInfo(
                name=screen.name(),
                geometry=screen.geometry(),
                is_primary=screen == self._app.primaryScreen(),
                scale_factor=screen.devicePixelRatio()
            )
            screen_info_list.append(screen_info)

        logger.debug(f"检测到 {len(screen_info_list)} 个显示器")
        return screen_info_list

    def get_virtual_screen_geometry(self) -> QRect:
        """
        获取跨屏虚拟画布范围

        Returns:
            QRect: 虚拟屏幕的几何范围
        """
        virtual_geometry = self._app.primaryScreen().virtualGeometry()
        logger.debug(f"虚拟屏幕范围: {virtual_geometry}")
        return virtual_geometry

    def capture_region(self, rect: QRect) -> QPixmap:
        """
        截取指定区域

        Args:
            rect: 要截取的矩形区域

        Returns:
            QPixmap: 截取的图像
        """
        # 验证矩形
        if rect.isEmpty():
            logger.warning("截取区域为空")
            return QPixmap()

        # 获取虚拟屏幕范围
        virtual_geometry = self.get_virtual_screen_geometry()

        # 检查区域是否在虚拟屏幕范围内
        if not virtual_geometry.contains(rect):
            logger.warning(f"截取区域 {rect} 不在虚拟屏幕范围内 {virtual_geometry}")
            # 调整区域到虚拟屏幕范围内
            rect = virtual_geometry.intersected(rect)
            if rect.isEmpty():
                return QPixmap()

        # 获取包含该区域的屏幕
        screens = self._app.screens()
        target_screen = None

        for screen in screens:
            if screen.geometry().contains(rect):
                target_screen = screen
                break

        if target_screen:
            # 在单个屏幕内截取
            logger.debug(f"在显示器 {target_screen.name()} 上截取区域 {rect}")
            pixmap = target_screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
        else:
            # 跨多个屏幕，使用主屏幕的抓取方法
            logger.debug(f"跨屏截取区域 {rect}")
            screen = self._app.primaryScreen()
            pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())

        if pixmap.isNull():
            logger.error("截取失败,返回空图像")
        else:
            logger.debug(f"截取成功: {pixmap.width()}x{pixmap.height()}")

        return pixmap

    def capture_full_screen(self) -> QPixmap:
        """
        截取全屏(包含所有显示器)

        Returns:
            QPixmap: 全屏截图
        """
        virtual_geometry = self.get_virtual_screen_geometry()
        logger.info(f"截取全屏: {virtual_geometry.width()}x{virtual_geometry.height()}")

        pixmap = self.capture_region(virtual_geometry)
        return pixmap

    def capture_screen_at_point(self, point: QPoint) -> QPixmap:
        """
        截取指定点所在的屏幕

        Args:
            point: 屏幕坐标点

        Returns:
            QPixmap: 该屏幕的截图
        """
        screens = self._app.screens()
        for screen in screens:
            if screen.geometry().contains(point):
                pixmap = screen.grabWindow(0)
                logger.debug(f"截取屏幕 {screen.name()}")
                return pixmap

        logger.warning(f"未找到包含点 {point} 的屏幕")
        return QPixmap()
