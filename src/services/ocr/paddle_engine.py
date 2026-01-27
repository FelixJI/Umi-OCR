#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 引擎实现 - 向后兼容导入层

本文件为向后兼容，实际实现已拆分到 services/ocr/paddle/ 包中：
- paddle_config.py: 配置数据类 (~100行)
- paddle_preprocessor.py: 图像预处理 (~170行)
- paddle_postprocessor.py: 结果后处理 (~230行)
- paddle_engine_core.py: 核心引擎 (~490行)

原有导入方式仍然有效:
    from services.ocr.paddle_engine import PaddleOCREngine, PaddleConfig

Author: Umi-OCR Team
Date: 2026-01-27
"""

# 从拆分的子模块导入所有公开接口
from .paddle.paddle_config import PaddleConfig
from .paddle.paddle_preprocessor import ImagePreprocessor
from .paddle.paddle_postprocessor import TextBlockInference, TextPostprocessor
from .paddle.paddle_engine_core import (
    PaddleOCREngine,
    PaddleBatchOCREngine,
    LANGUAGE_MAP,
)

__all__ = [
    # 配置
    'PaddleConfig',
    # 预处理
    'ImagePreprocessor',
    # 后处理
    'TextBlockInference',
    'TextPostprocessor',
    # 引擎
    'PaddleOCREngine',
    'PaddleBatchOCREngine',
    # 语言映射
    'LANGUAGE_MAP',
]
