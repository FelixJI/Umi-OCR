#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 截图OCR服务模块

Author: Umi-OCR Team
Date: 2026-01-27
"""

from .screen_capture import ScreenCapture, ScreenInfo
from .region_selector import RegionSelector, DragMode
from .window_detector import WindowDetector, WindowInfo
from .magnifier import Magnifier

__all__ = [
    "ScreenCapture",
    "ScreenInfo",
    "RegionSelector",
    "DragMode",
    "WindowDetector",
    "WindowInfo",
    "Magnifier",
]
