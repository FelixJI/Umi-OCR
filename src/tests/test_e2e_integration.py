#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 端到端集成测试

验证各模块的集成和协作是否正常。

测试场景:
- 通用控件功能测试
- HTTP API 测试
- CLI 测试
- 任务系统流程测试

Author: Umi-OCR Team
Date: 2026-01-27
"""

import os
import sys
import json
import time
import base64
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

import pytest

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# 测试固件
# =============================================================================

@pytest.fixture(scope="module")
def sample_image_path():
    """创建测试用的样本图片"""
    # 创建一个简单的测试图片（白底黑字）
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new('RGB', (200, 50), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Hello OCR Test", fill='black')
        
        # 保存到临时文件
        tmp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix='.png', prefix='test_ocr_'
        )
        img.save(tmp_file.name)
        
        yield tmp_file.name
        
        # 清理
        os.unlink(tmp_file.name)
        
    except ImportError:
        # 如果没有 PIL，使用占位符
        pytest.skip("需要 PIL/Pillow 来创建测试图片")


@pytest.fixture(scope="module")
def sample_image_base64(sample_image_path):
    """将样本图片转为 base64"""
    with open(sample_image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode()


# =============================================================================
# 通用控件测试
# =============================================================================

class TestWidgets:
    """通用控件测试"""
    
    def test_hotkey_input_import(self):
        """测试 HotkeyInput 可导入"""
        from ui.widgets import HotkeyInput, HotkeyInputWithClear
        assert HotkeyInput is not None
        assert HotkeyInputWithClear is not None
    
    def test_result_panel_import(self):
        """测试 ResultPanel 可导入"""
        from ui.widgets import ResultPanel, ResultViewMode
        assert ResultPanel is not None
        assert ResultViewMode is not None
    
    def test_file_drop_zone_import(self):
        """测试 FileDropZone 可导入"""
        from ui.widgets import FileDropZone
        assert FileDropZone is not None
    
    def test_progress_card_import(self):
        """测试 ProgressCard 可导入"""
        from ui.widgets import ProgressCard, ProgressStatus
        assert ProgressCard is not None
        assert ProgressStatus is not None
    
    def test_image_viewer_import(self):
        """测试 ImageViewer 可导入"""
        from ui.widgets import ImageViewer
        assert ImageViewer is not None
    
    def test_widgets_all_exports(self):
        """测试所有控件导出"""
        from ui.widgets import __all__
        
        expected = [
            'EngineSelector',
            'HotkeyInput', 'HotkeyInputWithClear',
            'ResultPanel', 'ResultViewMode',
            'FileDropZone',
            'ProgressCard', 'ProgressStatus',
            'ImageViewer',
        ]
        
        for item in expected:
            assert item in __all__, f"缺少导出: {item}"


# =============================================================================
# 任务系统测试
# =============================================================================

class TestTaskSystem:
    """任务系统测试"""
    
    def test_task_model_import(self):
        """测试任务模型可导入"""
        from services.task.task_model import (
            Task, TaskGroup, TaskType, TaskStatus, CancelMode
        )
        assert Task is not None
        assert TaskGroup is not None
    
    def test_task_manager_singleton(self):
        """测试 TaskManager 单例"""
        from services.task.task_manager import TaskManager
        
        tm1 = TaskManager.instance()
        tm2 = TaskManager.instance()
        
        assert tm1 is tm2, "TaskManager 应该是单例"
    
    def test_task_status_transitions(self):
        """测试任务状态转换"""
        from services.task.task_model import Task, TaskType, TaskStatus
        
        task = Task(id="test-1", task_type=TaskType.OCR, input_data={})
        
        # PENDING -> RUNNING
        assert task.status == TaskStatus.PENDING
        task.transition_to(TaskStatus.RUNNING)
        assert task.status == TaskStatus.RUNNING
        
        # RUNNING -> COMPLETED
        task.transition_to(TaskStatus.COMPLETED)
        assert task.status == TaskStatus.COMPLETED


# =============================================================================
# HTTP API 测试
# =============================================================================

class TestHTTPAPI:
    """HTTP API 测试"""
    
    def test_routes_import(self):
        """测试路由模块可导入"""
        from services.server.routes import setup_routes
        assert setup_routes is not None
    
    def test_http_server_import(self):
        """测试 HTTP 服务器可导入"""
        from services.server.http_server import HTTPServer
        assert HTTPServer is not None


# =============================================================================
# CLI 测试
# =============================================================================

class TestCLI:
    """CLI 测试"""
    
    def test_cli_handler_import(self):
        """测试 CLI 处理器可导入"""
        from cli_handler import CliHandler
        assert CliHandler is not None
    
    def test_cli_help(self):
        """测试 CLI --help"""
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "main.py"), "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        assert result.returncode == 0
        assert "Umi-OCR" in result.stdout or "usage" in result.stdout.lower()


# =============================================================================
# OCR 引擎测试
# =============================================================================

class TestOCREngine:
    """OCR 引擎测试"""
    
    def test_engine_manager_import(self):
        """测试引擎管理器可导入"""
        from services.ocr.engine_manager import EngineManager
        assert EngineManager is not None
    
    def test_base_engine_import(self):
        """测试基础引擎可导入"""
        from services.ocr.base_engine import BaseOCREngine, OCRErrorCode
        assert BaseOCREngine is not None
        assert OCRErrorCode is not None
    
    def test_ocr_result_import(self):
        """测试 OCR 结果可导入"""
        from services.ocr.ocr_result import OCRResult, TextBlock
        assert OCRResult is not None
        assert TextBlock is not None
    
    def test_paddle_module_structure(self):
        """测试 PaddleOCR 模块结构"""
        # 检查新的包结构
        paddle_dir = PROJECT_ROOT / "services" / "ocr" / "paddle"
        assert paddle_dir.exists(), "paddle 目录应该存在"
        assert (paddle_dir / "__init__.py").exists(), "__init__.py 应该存在"
    
    def test_models_module_structure(self):
        """测试模型管理模块结构"""
        models_dir = PROJECT_ROOT / "services" / "ocr" / "models"
        assert models_dir.exists(), "models 目录应该存在"
        assert (models_dir / "__init__.py").exists(), "__init__.py 应该存在"


# =============================================================================
# 云 OCR 测试
# =============================================================================

class TestCloudOCR:
    """云 OCR 测试"""
    
    def test_cloud_engines_import(self):
        """测试云引擎可导入"""
        from services.ocr.cloud import (
            BaseCloudEngine, BaiduOCREngine, 
            TencentOCREngine, AliyunOCREngine
        )
        assert BaseCloudEngine is not None
        assert BaiduOCREngine is not None
        assert TencentOCREngine is not None
        assert AliyunOCREngine is not None
    
    def test_request_queue_import(self):
        """测试请求队列可导入"""
        from services.ocr.cloud.request_queue import RequestQueue
        assert RequestQueue is not None


# =============================================================================
# 配置和工具测试
# =============================================================================

class TestUtilities:
    """工具模块测试"""
    
    def test_config_manager_import(self):
        """测试配置管理器可导入"""
        from utils.config_manager import ConfigManager, get_config_manager
        assert ConfigManager is not None
        assert get_config_manager is not None
    
    def test_logger_import(self):
        """测试日志模块可导入"""
        from utils.logger import get_logger
        logger = get_logger()
        assert logger is not None
    
    def test_i18n_import(self):
        """测试多语言模块可导入"""
        from utils.i18n import get_i18n_manager
        assert get_i18n_manager is not None
    
    def test_credential_manager_import(self):
        """测试凭证管理器可导入"""
        from utils.credential_manager import CredentialManager
        assert CredentialManager is not None


# =============================================================================
# 主入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
