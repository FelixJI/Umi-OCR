#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR OCR 服务模块

提供 OCR 引擎的抽象接口和基础实现。

主要组件：
- BaseOCREngine: OCR 引擎抽象基类
- OCRResult: 统一的 OCR 结果格式
- OCRErrorCode: 错误码枚举
- ConfigSchema: 配置 Schema 定义
- PaddleOCREngine: PaddleOCR 本地引擎
- ModelManager: 模型管理器

Author: Umi-OCR Team
Date: 2026-01-26
"""

from .base_engine import (
    BaseOCREngine,
    BatchOCREngine,
    OCRErrorCode,
    ConfigSchema,
    EnginePerformanceMetrics
)

from .ocr_result import (
    OCRResult,
    TextBlock,
    TextBlockType,
    BoundingBox,
    BatchOCRResult
)

from .model_manager import (
    PaddleModelManager,
    ModelType,
    ModelStatus,
    ModelInfo,
    ModelRepository,
    get_model_manager
)

from .paddle_engine import (
    PaddleOCREngine,
    PaddleBatchOCREngine,
    PaddleConfig
)

from .engine_manager import (
    EngineManager,
    EngineInfo,
    EngineState,
    get_engine_manager,
    set_config_manager
)

__all__ = [
    # 基础类
    "BaseOCREngine",
    "BatchOCREngine",

    # 错误处理
    "OCRErrorCode",

    # 配置
    "ConfigSchema",

    # 性能监控
    "EnginePerformanceMetrics",

    # 结果数据
    "OCRResult",
    "TextBlock",
    "TextBlockType",
    "BoundingBox",
    "BatchOCRResult",

    # PaddleOCR 引擎
    "PaddleOCREngine",
    "PaddleBatchOCREngine",
    "PaddleConfig",

    # 模型管理
    "PaddleModelManager",
    "ModelType",
    "ModelStatus",
    "ModelInfo",
    "ModelRepository",
    "get_model_manager",

    # 引擎管理
    "EngineManager",
    "EngineInfo",
    "EngineState",
    "get_engine_manager",
    "set_config_manager",
]
