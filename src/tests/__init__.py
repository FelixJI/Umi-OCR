#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 测试包

包含所有单元测试模块：
- test_logger: 日志系统测试
- test_config: 配置管理系统测试
- test_i18n: 多语言支持测试
- test_ocr_engines: OCR 引擎抽象层测试

运行测试:
    python -m pytest src/tests/ -v
    或
    python -m unittest src.tests.test_logger -v

Author: Umi-OCR Team
Date: 2025-01-26
"""

import sys
from pathlib import Path
from . import test_logger
from . import test_config
from . import test_i18n
from . import test_ocr_engines

# 确保项目根目录在路径中
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

__all__ = [
    "test_logger",
    "test_config",
    "test_i18n",
    "test_ocr_engines",
]
