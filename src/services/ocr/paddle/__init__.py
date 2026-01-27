#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR PaddleOCR 引擎包

提供 PaddleOCR 本地引擎的完整实现。

模块结构:
- paddle_config.py: 配置数据类 (~100行)
- paddle_preprocessor.py: 图像预处理 (~170行)
- paddle_postprocessor.py: 结果后处理 (~230行)
- paddle_engine_core.py: 核心引擎 (~490行)

向后兼容:
    原有导入方式仍然有效:
    from services.ocr.paddle_engine import PaddleOCREngine

Author: Umi-OCR Team
Date: 2026-01-27
"""

# 从拆分的子模块导入
from .paddle_config import PaddleConfig
from .paddle_preprocessor import ImagePreprocessor
from .paddle_postprocessor import TextPostprocessor, TextBlockInference
from .paddle_engine_core import PaddleOCREngine, PaddleBatchOCREngine, LANGUAGE_MAP

__all__ = [
    # 配置
    'PaddleConfig',
    # 预处理
    'ImagePreprocessor',
    # 后处理
    'TextPostprocessor',
    'TextBlockInference',
    # 引擎
    'PaddleOCREngine',
    'PaddleBatchOCREngine',
    # 映射
    'LANGUAGE_MAP',
]
