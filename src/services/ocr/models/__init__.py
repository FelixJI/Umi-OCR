#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 模型管理包

提供 OCR 模型的下载、缓存和管理功能。

模块结构:
- model_types.py: 枚举和数据类 (~130行)
- model_repository.py: 模型仓库 (~220行)
- model_manager_core.py: 管理器主类 (~300行)

向后兼容:
    原有导入方式仍然有效:
    from services.ocr.model_manager import PaddleModelManager

Author: Umi-OCR Team
Date: 2026-01-27
"""

# 从拆分的子模块导入
from .model_types import ModelType, ModelStatus, ModelInfo
from .model_repository import ModelRepository
from .model_manager_core import PaddleModelManager, get_model_manager

__all__ = [
    # 类型定义
    "ModelType",
    "ModelStatus",
    "ModelInfo",
    # 仓库
    "ModelRepository",
    # 管理器
    "PaddleModelManager",
    "get_model_manager",
]
