#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 窗口检测器

实现Windows窗口枚举和检测功能,用于截图时的窗口识别。

主要功能：
- 枚举所有可见窗口
- 获取指定位置的窗口
- 获取窗口信息

Author: Umi-OCR Team
Date: 2026-01-27
"""

import ctypes
import logging
from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import QRect, QPoint

logger = logging.getLogger(__name__)


# =============================================================================
# Windows API 定义
# =============================================================================

# 加载 user32.dll
user32 = ctypes.windll.user32

# 常量定义
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000

# 回调函数类型
WNDENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.c_bool,
    ctypes.c_int,
    ctypes.c_long
)


@dataclass
class WindowInfo:
    """窗口信息"""
    hwnd: int                      # 窗口句柄
    title: str                     # 窗口标题
    rect: QRect                    # 窗口矩形
    class_name: str                # 窗口类名


# =============================================================================
# 窗口结构体
# =============================================================================

class RECT(ctypes.Structure):
    """Windows RECT 结构体"""
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

    def to_qrect(self) -> QRect:
        """转换为 QRect"""
        return QRect(
            self.left, self.top,
            self.right - self.left,
            self.bottom - self.top
        )


class WINDOWINFO(ctypes.Structure):
    """Windows WINDOWINFO 结构体"""
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcWindow", RECT),
        ("rcClient", RECT),
        ("dwStyle", ctypes.c_ulong),
        ("dwExStyle", ctypes.c_ulong),
        ("dwWindowStatus", ctypes.c_ulong),
        ("cxWindowBorders", ctypes.c_uint),
        ("cyWindowBorders", ctypes.c_uint),
        ("atomWindowType", ctypes.c_ushort),
        ("wCreatorVersion", ctypes.c_ushort)
    ]


# =============================================================================
# Windows API 函数声明
# =============================================================================

def _get_window_rect(hwnd: int) -> Optional[RECT]:
    """
    获取窗口矩形

    Args:
        hwnd: 窗口句柄

    Returns:
        Optional[RECT]: 窗口矩形,失败返回None
    """
    rect = RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return rect
    return None


def _get_window_text(hwnd: int) -> str:
    """
    获取窗口标题

    Args:
        hwnd: 窗口句柄

    Returns:
        str: 窗口标题
    """
    # 第一次调用获取标题长度
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""

    # 分配缓冲区
    buffer = ctypes.create_unicode_buffer(length + 1)

    # 获取窗口标题
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _get_window_class_name(hwnd: int) -> str:
    """
    获取窗口类名

    Args:
        hwnd: 窗口句柄

    Returns:
        str: 窗口类名
    """
    buffer_size = 256
    buffer = ctypes.create_unicode_buffer(buffer_size)
    user32.GetClassNameW(hwnd, buffer, buffer_size)
    return buffer.value


def _is_window_visible(hwnd: int) -> bool:
    """
    判断窗口是否可见

    Args:
        hwnd: 窗口句柄

    Returns:
        bool: 是否可见
    """
    return bool(user32.IsWindowVisible(hwnd))


# =============================================================================
# 窗口检测器
# =============================================================================

class WindowDetector:
    """
    窗口检测器

    提供Windows窗口枚举和检测功能。
    """

    def __init__(self):
        """初始化窗口检测器"""
        self._all_windows: List[WindowInfo] = []
        logger.info("窗口检测器初始化完成")

    def get_window_at(self, pos: QPoint) -> Optional[WindowInfo]:
        """
        获取指定位置的窗口

        Args:
            pos: 屏幕坐标点

        Returns:
            Optional[WindowInfo]: 窗口信息,未找到返回None
        """
        # 使用 WindowFromPoint 获取窗口句柄
        hwnd = user32.WindowFromPoint(pos.x(), pos.y())

        if hwnd == 0:
            return None

        # 获取窗口信息
        rect = _get_window_rect(hwnd)
        if not rect:
            return None

        return WindowInfo(
            hwnd=hwnd,
            title=_get_window_text(hwnd),
            rect=rect.to_qrect(),
            class_name=_get_window_class_name(hwnd)
        )

    def get_all_windows(self) -> List[WindowInfo]:
        """
        枚举所有可见窗口

        Returns:
            List[WindowInfo]: 窗口信息列表
        """
        self._all_windows = []

        # 枚举回调函数
        def enum_callback(hwnd, lparam):
            """窗口枚举回调"""
            # 跳过不可见窗口
            if not _is_window_visible(hwnd):
                return True

            # 获取窗口矩形
            rect = _get_window_rect(hwnd)
            if not rect or rect.left == 0 and rect.top == 0:
                return True

            # 跳过过小窗口(可能是控件)
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            if width < 100 or height < 50:
                return True

            # 获取窗口信息
            title = _get_window_text(hwnd)
            class_name = _get_window_class_name(hwnd)

            # 跳过无标题窗口(可能是系统窗口)
            if not title:
                return True

            # 添加到列表
            self._all_windows.append(WindowInfo(
                hwnd=hwnd,
                title=title,
                rect=rect.to_qrect(),
                class_name=class_name
            ))

            return True

        # 创建回调函数对象
        callback = WNDENUMPROC(enum_callback)

        # 枚举所有顶层窗口
        user32.EnumWindows(callback, 0)

        logger.debug(f"枚举到 {len(self._all_windows)} 个可见窗口")
        return self._all_windows

    def find_windows_by_title(self, title: str, exact: bool = False) -> List[WindowInfo]:
        """
        按标题查找窗口

        Args:
            title: 窗口标题
            exact: 是否精确匹配

        Returns:
            List[WindowInfo]: 匹配的窗口列表
        """
        if not self._all_windows:
            self.get_all_windows()

        if exact:
            return [w for w in self._all_windows if w.title == title]
        else:
            return [w for w in self._all_windows if title.lower() in w.title.lower()]

    def get_desktop_window(self) -> WindowInfo:
        """
        获取桌面窗口

        Returns:
            WindowInfo: 桌面窗口信息
        """
        hwnd = user32.GetDesktopWindow()
        rect = _get_window_rect(hwnd)

        return WindowInfo(
            hwnd=hwnd,
            title="Desktop",
            rect=rect.to_qrect() if rect else QRect(),
            class_name="Desktop"
        )
