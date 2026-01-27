#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 模型管理器 - 向后兼容导入层

本文件为向后兼容，实际实现已拆分到 services/ocr/models/ 包中：
- model_types.py: 枚举和数据类 (~130行)
- model_repository.py: 模型仓库 (~220行)
- model_manager_core.py: 管理器主类 (~300行)

原有导入方式仍然有效:
    from services.ocr.model_manager import PaddleModelManager, get_model_manager

Author: Umi-OCR Team
Date: 2026-01-27
"""

# 从拆分的子模块导入所有公开接口
from .models.model_types import ModelType, ModelStatus, ModelInfo
from .models.model_repository import ModelRepository
from .models.model_manager_core import PaddleModelManager, get_model_manager

__all__ = [
    # 类型定义
    'ModelType',
    'ModelStatus',
    'ModelInfo',
    # 仓库
    'ModelRepository',
    # 管理器
    'PaddleModelManager',
    'get_model_manager',
]
