#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 引擎管理器单元测试

测试 EngineManager 的核心功能：
- 引擎注册和发现
- 引擎切换
- 延迟加载
- 延迟销毁
- 失败回退
- 配置管理
- 统一识别接口

Author: Umi-OCR Team
Date: 2026-01-27
"""

import unittest
import time
import threading
from pathlib import Path


import sys

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.ocr.base_engine import BaseOCREngine
from services.ocr.ocr_result import OCRResult
from services.ocr.engine_manager import EngineManager

# =============================================================================
# Mock 引擎（用于测试）
# =============================================================================


class MockOCREngine(BaseOCREngine):
    """Mock OCR 引擎（用于测试）"""

    ENGINE_TYPE = "mock"
    ENGINE_NAME = "Mock OCR Engine"
    ENGINE_VERSION = "1.0.0"

    def __init__(self, config=None):
        super().__init__(config or {})
        self._initialize_called = False
        self._cleanup_called = False
        self._recognize_count = 0

    def _do_initialize(self) -> bool:
        """模拟初始化"""
        self._initialize_called = True
        return True

    def _do_recognize(self, image, **kwargs) -> OCRResult:
        """模拟识别"""
        self._recognize_count += 1
        return OCRResult(
            success=True,
            text_blocks=[],
            full_text="Mock recognition result",
            engine_type=self.ENGINE_TYPE,
            engine_name=self.ENGINE_NAME,
        )

    def _do_cleanup(self) -> None:
        """模拟清理"""
        self._cleanup_called = True

    def is_available(self) -> bool:
        """模拟可用性检查"""
        return True


class FailingOCREngine(BaseOCREngine):
    """始终失败的 Mock 引擎（用于测试回退）"""

    ENGINE_TYPE = "failing"
    ENGINE_NAME = "Failing OCR Engine"
    ENGINE_VERSION = "1.0.0"

    def _do_initialize(self) -> bool:
        """模拟初始化失败"""
        return False

    def _do_recognize(self, image, **kwargs) -> OCRResult:
        """模拟识别"""
        return OCRResult(success=False)

    def _do_cleanup(self) -> None:
        """模拟清理"""
        pass

    def is_available(self) -> bool:
        """模拟不可用"""
        return False


# =============================================================================
# 引擎管理器测试
# =============================================================================


class TestEngineManager(unittest.TestCase):
    """引擎管理器单元测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 重置全局引擎管理器
        import services.ocr.engine_manager as em_module

        em_module._global_engine_manager = None

    def setUp(self):
        """每个测试用例前的初始化"""
        # 创建新的引擎管理器实例
        self.manager = EngineManager.get_instance()

        # 注册测试引擎
        self.manager.register_engine(
            engine_type="mock",
            engine_class=MockOCREngine,
            factory=MockOCREngine,
            is_local=True,
            priority=1,
        )

        self.manager.register_engine(
            engine_type="failing",
            engine_class=FailingOCREngine,
            factory=FailingOCREngine,
            is_local=False,
            priority=10,
        )

    def tearDown(self):
        """每个测试用例后的清理"""
        # 清理引擎管理器
        self.manager._stop_engine("mock")
        self.manager._stop_engine("failing")
        self.manager._current_engine_type = None

    # -------------------------------------------------------------------------
    # 测试引擎注册
    # -------------------------------------------------------------------------

    def test_register_engine(self):
        """测试引擎注册"""
        # 检查引擎是否注册
        info = self.manager.get_engine_info("mock")
        self.assertIsNotNone(info)
        self.assertEqual(info.engine_type, "mock")
        self.assertEqual(info.engine_class, MockOCREngine)
        self.assertTrue(info.is_local)
        self.assertEqual(info.priority, 1)

    def test_unregister_engine(self):
        """测试引擎注销"""
        # 注销引擎
        result = self.manager.unregister_engine("mock")
        self.assertTrue(result)

        # 检查引擎是否已移除
        info = self.manager.get_engine_info("mock")
        self.assertIsNone(info)

    def test_get_available_engines(self):
        """测试获取可用引擎列表"""
        engines = self.manager.get_available_engines()
        self.assertIsInstance(engines, list)
        self.assertGreater(len(engines), 0)
        self.assertIn("mock", engines)
        self.assertIn("failing", engines)

        # 检查排序（本地引擎优先）
        self.assertEqual(engines[0], "mock")  # 本地引擎优先

    # -------------------------------------------------------------------------
    # 测试引擎加载
    # -------------------------------------------------------------------------

    def test_load_engine_instance(self):
        """测试延迟加载引擎实例"""
        # 加载引擎
        engine = self.manager._load_engine_instance("mock")
        self.assertIsNotNone(engine)
        self.assertIsInstance(engine, MockOCREngine)
        self.assertTrue(engine._initialize_called)

        # 检查引擎状态
        state = self.manager.get_engine_state("mock")
        self.assertIsNotNone(state)
        self.assertIsNotNone(state.engine_instance)
        self.assertTrue(state.is_initialized)

    def test_load_failing_engine(self):
        """测试加载失败的引擎"""
        # 尝试加载失败的引擎
        engine = self.manager._load_engine_instance("failing")
        self.assertIsNone(engine)

        # 检查引擎状态
        state = self.manager.get_engine_state("failing")
        self.assertIsNotNone(state)
        self.assertIsNone(state.engine_instance)
        self.assertFalse(state.is_initialized)

    # -------------------------------------------------------------------------
    # 测试引擎切换
    # -------------------------------------------------------------------------

    def test_switch_engine(self):
        """测试引擎切换"""
        # 记录信号
        switched_called = threading.Event()
        switched_args = []

        def on_switched(old_type, new_type):
            switched_args.append((old_type, new_type))
            switched_called.set()

        self.manager.engine_switched.connect(on_switched)

        # 切换到 mock 引擎
        success = self.manager.switch_engine("mock")
        self.assertTrue(success)
        self.assertEqual(self.manager.get_current_engine_type(), "mock")

        # 等待信号
        switched_called.wait(timeout=1.0)
        self.assertEqual(len(switched_args), 1)
        self.assertEqual(switched_args[0], ("", "mock"))

    def test_switch_to_same_engine(self):
        """测试切换到相同引擎"""
        # 先切换到 mock
        self.manager.switch_engine("mock")

        # 再次切换到 mock（应该直接返回）
        success = self.manager.switch_engine("mock")
        self.assertTrue(success)

    def test_switch_to_failing_engine(self):
        """测试切换到失败的引擎"""
        # 先切换到 mock
        self.manager.switch_engine("mock")
        old_type = self.manager.get_current_engine_type()

        # 尝试切换到失败的引擎
        success = self.manager.switch_engine("failing")
        self.assertFalse(success)

        # 应该保持在原引擎
        self.assertEqual(self.manager.get_current_engine_type(), old_type)

    # -------------------------------------------------------------------------
    # 测试延迟销毁
    # -------------------------------------------------------------------------

    def test_delayed_destroy(self):
        """测试延迟销毁"""
        # 加载引擎
        self.manager._load_engine_instance("mock")

        # 调度销毁（1秒后）
        self.manager._schedule_destroy("mock", delay=1.0)

        # 检查引擎仍然存在
        state = self.manager.get_engine_state("mock")
        self.assertIsNotNone(state.engine_instance)

        # 等待1秒
        time.sleep(1.5)

        # 检查引擎已销毁
        state = self.manager.get_engine_state("mock")
        self.assertIsNone(state.engine_instance)
        self.assertFalse(state.is_initialized)

    def test_cancel_destroy(self):
        """测试取消销毁"""
        # 加载引擎
        self.manager._load_engine_instance("mock")

        # 调度销毁（5秒后）
        self.manager._schedule_destroy("mock", delay=5.0)

        # 立即取消销毁
        self.manager._cancel_destroy("mock")

        # 等待超过销毁时间
        time.sleep(5.5)

        # 检查引擎仍然存在
        state = self.manager.get_engine_state("mock")
        self.assertIsNotNone(state.engine_instance)

    # -------------------------------------------------------------------------
    # 测试失败回退
    # -------------------------------------------------------------------------

    def test_fallback_to_default(self):
        """测试失败回退"""
        # 尝试回退到默认引擎
        success = self.manager._fallback_to_default_engine()
        self.assertTrue(success)

        # 检查当前引擎
        current_type = self.manager.get_current_engine_type()
        self.assertIsNotNone(current_type)
        self.assertEqual(current_type, "mock")

    # -------------------------------------------------------------------------
    # 测试统一识别接口
    # -------------------------------------------------------------------------

    def test_recognize(self):
        """测试统一识别接口"""
        # 切换到 mock 引擎
        self.manager.switch_engine("mock")

        # 执行识别（使用PIL Image对象）
        from PIL import Image

        fake_image = Image.new("RGB", (100, 100), color="white")
        result = self.manager.recognize(fake_image)

        # 调试输出
        if not result.success:
            print(f"识别失败: {result.error_code}")
            print(f"错误信息: {result.error_message}")

        self.assertTrue(result.success)
        self.assertEqual(result.engine_type, "mock")

        # 检查引擎实例的识别计数
        engine = self.manager.get_current_engine()
        self.assertIsInstance(engine, MockOCREngine)
        self.assertEqual(engine._recognize_count, 1)

    def test_recognize_without_engine(self):
        """测试没有引擎时的识别"""
        # 清空当前引擎
        self.manager._current_engine_type = None

        # 执行识别（应该自动加载默认引擎）
        from PIL import Image

        fake_image = Image.new("RGB", (100, 100), color="white")
        result = self.manager.recognize(fake_image)

        # 调试输出
        if not result.success:
            print(f"识别失败: {result.error_code}")
            print(f"错误信息: {result.error_message}")

        self.assertTrue(result.success)

    # -------------------------------------------------------------------------
    # 测试配置管理
    # -------------------------------------------------------------------------

    def test_get_engine_config(self):
        """测试获取引擎配置"""
        config = self.manager.get_engine_config("mock")
        self.assertIsInstance(config, dict)

    def test_set_engine_config(self):
        """测试设置引擎配置"""
        new_config = {"lang": "en", "use_gpu": False}
        self.manager.set_engine_config("mock", new_config)

        # 验证配置已更新
        config = self.manager.get_engine_config("mock")
        self.assertEqual(config["lang"], "en")
        self.assertEqual(config["use_gpu"], False)

    # -------------------------------------------------------------------------
    # 测试单例模式
    # -------------------------------------------------------------------------

    def test_singleton(self):
        """测试单例模式"""
        # 获取两个实例
        instance1 = EngineManager.get_instance()
        instance2 = EngineManager.get_instance()

        # 应该是同一个实例
        self.assertIs(instance1, instance2)

    # -------------------------------------------------------------------------
    # 测试信号
    # -------------------------------------------------------------------------

    def test_engine_ready_signal(self):
        """测试引擎就绪信号"""
        ready_called = threading.Event()
        ready_args = []

        def on_ready(engine_type, is_ready):
            ready_args.append((engine_type, is_ready))
            ready_called.set()

        self.manager.engine_ready.connect(on_ready)

        # 加载引擎
        self.manager._load_engine_instance("mock")

        # 等待信号
        ready_called.wait(timeout=1.0)
        self.assertEqual(len(ready_args), 1)
        self.assertEqual(ready_args[0], ("mock", True))


# =============================================================================
# 测试运行器
# =============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
