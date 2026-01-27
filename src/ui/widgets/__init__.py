#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR UI 组件包

提供通用 UI 控件和组件。

包含控件:
- EngineSelector: 引擎选择器
- HotkeyInput: 快捷键输入框
- ResultPanel: OCR结果面板
- FileDropZone: 文件拖拽区域
- ProgressCard: 进度卡片
- ImageViewer: 图片查看器
"""

# 新控件（无复杂依赖）
from .hotkey_input import HotkeyInput, HotkeyInputWithClear
from .result_panel import ResultPanel, ResultViewMode
from .file_drop_zone import FileDropZone
from .progress_card import ProgressCard, ProgressStatus
from .image_viewer import ImageViewer

# 原有控件（可能有外部依赖，延迟导入）
# EngineSelector 依赖 EngineManager，在需要时再导入
def get_engine_selector():
    """获取 EngineSelector（延迟导入避免循环依赖）"""
    from .engine_selector import EngineSelector
    return EngineSelector


__all__ = [
    # 引擎选择（延迟导入）
    'get_engine_selector',
    # 快捷键输入
    'HotkeyInput',
    'HotkeyInputWithClear',
    # 结果面板
    'ResultPanel',
    'ResultViewMode',
    # 文件拖拽
    'FileDropZone',
    # 进度卡片
    'ProgressCard',
    'ProgressStatus',
    # 图片查看
    'ImageViewer',
]
