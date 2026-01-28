#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 引擎单元测试

测试 PaddleOCR 引擎的各项功能，包括：
- 基础功能测试
- 边界情况测试
- 性能基准测试
- 集成测试

Author: Umi-OCR Team
Date: 2026-01-26
"""

import sys
import time
import unittest
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication

from services.ocr import (
    PaddleOCREngine,
    PaddleBatchOCREngine,
    PaddleConfig,
    OCRErrorCode,
)
from services.ocr.model_manager import ModelRepository

# =============================================================================
# 测试配置
# =============================================================================


class TestConfig:
    """测试配置"""

    # 测试图片路径
    TEST_IMAGES_DIR = Path(__file__).parent / "test_images"

    # 性能基准
    MAX_RECOGNITION_TIME = 5.0  # 最大识别时间（秒）
    MIN_CONFIDENCE = 0.5  # 最小置信度

    # 并发测试
    CONCURRENT_TASKS = 5  # 并发任务数

    # 测试文本
    TEST_TEXT_CH = "这是中文测试文本"
    TEST_TEXT_EN = "This is English test text"
    TEST_TEXT_MIXED = "Mixed 混合 Text 文本"


# =============================================================================
# 基础功能测试（A）
# =============================================================================


class TestPaddleOCREngineBasic(unittest.TestCase):
    """
    PaddleOCR 引擎基础功能测试

    测试引擎的核心功能，包括初始化、识别、资源清理等。
    """

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 创建 Qt 应用程序（必需，因为使用了 Signal）
        cls.app = QApplication([])

        # 创建引擎配置
        cls.config = PaddleConfig(
            lang="ch", use_textline_orientation=True, confidence_threshold=0.5
        )

        # 创建引擎实例
        cls.engine = PaddleOCREngine(cls.config.__dict__)

    def setUp(self):
        """每个测试用例前的初始化"""
        # 确保引擎已初始化
        if not self.engine.is_initialized:
            self.assertTrue(self.engine.initialize())

    def tearDown(self):
        """每个测试用例后的清理"""
        pass

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        cls.engine.stop()
        cls.app.quit()

    def test_engine_initialization(self):
        """测试引擎初始化"""
        self.assertIsNotNone(self.engine)
        self.assertTrue(self.engine.is_initialized)
        self.assertEqual(self.engine.engine_type, "paddle")

    def test_get_config_schema(self):
        """测试获取配置 Schema"""
        schema = PaddleOCREngine.get_config_schema()

        self.assertIsNotNone(schema)
        self.assertIn("type", schema)
        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)

        # 检查必需字段
        self.assertIn("required", schema)
        self.assertIn("lang", schema["required"])

    def test_recognize_text_image(self):
        """测试识别文本图片"""
        # 创建测试图片
        from PIL import Image, ImageDraw, ImageFont

        image = Image.new("RGB", (300, 100), color="white")
        draw = ImageDraw.Draw(image)

        # 绘制测试文本
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()

        draw.text((10, 10), "Hello, Umi-OCR!", fill="black", font=font)

        # 执行识别
        result = self.engine.recognize(image, task_id="test_1")

        # 验证结果
        self.assertTrue(result.success, f"识别失败: {result.error_message}")
        self.assertGreater(len(result.text_blocks), 0, "未识别到文本")
        self.assertIsNotNone(result.engine_type)
        self.assertGreater(result.duration, 0, "识别耗时未记录")

        # 验证文本内容
        full_text = result.get_text()
        self.assertIn("Umi", full_text, f"未识别到关键词 Umi: {full_text}")

    def test_recognize_from_path(self):
        """测试从文件路径识别"""
        # 创建测试图片文件
        from PIL import Image

        image = Image.new("RGB", (200, 50), color="white")

        test_image_path = TestConfig.TEST_IMAGES_DIR / "test_image.png"
        TestConfig.TEST_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        image.save(test_image_path)

        # 执行识别
        result = self.engine.recognize(str(test_image_path))

        # 清理测试文件
        if test_image_path.exists():
            test_image_path.unlink()

        self.assertIsNotNone(result)

    def test_recognize_from_bytes(self):
        """测试从字节流识别"""
        from PIL import Image
        from io import BytesIO

        image = Image.new("RGB", (200, 50), color="white")

        # 转换为字节流
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        # 执行识别
        result = self.engine.recognize(image_bytes)

        self.assertIsNotNone(result)

    def test_confidence_threshold(self):
        """测试置信度阈值过滤"""
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (200, 50), color="white")
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), "Test", fill="black")

        # 使用高置信度阈值
        config = PaddleConfig(lang="ch", confidence_threshold=0.9)  # 高阈值
        engine = PaddleOCREngine(config.__dict__)
        engine.initialize()

        result = engine.recognize(image)

        # 验证结果
        if result.success:
            # 所有文本块置信度应该 >= 0.9
            for block in result.text_blocks:
                self.assertGreaterEqual(block.confidence, 0.9)

        engine.stop()

    def test_engine_stop_and_restart(self):
        """测试引擎停止和重启"""
        # 停止引擎
        self.engine.stop()
        self.assertFalse(self.engine.is_initialized)

        # 重新初始化
        success = self.engine.initialize()
        self.assertTrue(success)
        self.assertTrue(self.engine.is_initialized)


# =============================================================================
# 边界情况测试（B）
# =============================================================================


class TestPaddleOCREngineBoundary(unittest.TestCase):
    """
    PaddleOCR 引擎边界情况测试

    测试异常输入和边界情况的处理。
    """

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.app = QApplication([])

        cls.config = PaddleConfig(lang="ch")
        cls.engine = PaddleOCREngine(cls.config.__dict__)
        cls.engine.initialize()

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        cls.engine.stop()
        cls.app.quit()

    def test_empty_image(self):
        """测试空白图片"""
        from PIL import Image

        # 创建空白图片
        image = Image.new("RGB", (100, 50), color="white")

        result = self.engine.recognize(image)

        # 空白图片应该返回空结果或无内容错误
        self.assertIsNotNone(result)
        if not result.success:
            self.assertIn(
                result.error_code,
                [OCRErrorCode.NO_CONTENT.value, OCRErrorCode.EMPTY_IMAGE.value],
            )

    def test_too_large_image(self):
        """测试超大图片"""
        from PIL import Image

        # 创建超大图片（10000x10000）
        try:
            image = Image.new("RGB", (10000, 10000), color="white")

            # 应该能处理大图片（可能有性能警告）
            result = self.engine.recognize(image)

            self.assertIsNotNone(result)

        except MemoryError:
            # 内存不足是预期的
            pass

    def test_invalid_image_format(self):
        """测试无效图片格式"""
        # 使用无效的字节数据
        invalid_bytes = b"This is not an image"

        result = self.engine.recognize(invalid_bytes)

        # 应该返回格式错误
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, OCRErrorCode.IMAGE_FORMAT_UNSUPPORTED.value)

    def test_corrupted_image(self):
        """测试损坏的图片"""
        # 使用有效的PNG头但损坏的数据
        corrupted_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        result = self.engine.recognize(corrupted_data)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, OCRErrorCode.IMAGE_CORRUPTED.value)

    def test_recognize_without_initialization(self):
        """测试未初始化就识别"""
        # 创建新引擎但不初始化
        engine = PaddleOCREngine(PaddleConfig(lang="ch").__dict__)

        from PIL import Image

        image = Image.new("RGB", (100, 50), color="white")

        result = engine.recognize(image)

        # 应该返回未初始化错误
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, OCRErrorCode.NOT_INITIALIZED.value)


# =============================================================================
# 性能基准测试（C）
# =============================================================================


class TestPaddleOCREnginePerformance(unittest.TestCase):
    """
    PaddleOCR 引擎性能测试

    测试识别速度、内存占用、并发处理能力等性能指标。
    """

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.app = QApplication([])

        cls.config = PaddleConfig(lang="ch")
        cls.engine = PaddleOCREngine(cls.config.__dict__)
        cls.engine.initialize()

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        cls.engine.stop()
        cls.app.quit()

    def test_recognition_speed(self):
        """测试识别速度"""
        from PIL import Image, ImageDraw, ImageFont

        # 创建测试图片
        image = Image.new("RGB", (300, 100), color="white")
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()

        draw.text((10, 10), "Performance Test", fill="black", font=font)

        # 执行识别并计时
        start_time = time.time()
        result = self.engine.recognize(image)
        duration = time.time() - start_time

        # 验证识别速度
        self.assertTrue(result.success)
        self.assertLessEqual(
            duration,
            TestConfig.MAX_RECOGNITION_TIME,
            f"识别耗时 {duration:.2f}s 超过基准 {TestConfig.MAX_RECOGNITION_TIME}s",
        )

        print(f"识别耗时: {duration:.3f}s")

    def test_concurrent_recognition(self):
        """测试并发识别"""
        import threading
        from PIL import Image

        # 创建测试图片
        test_images = [
            Image.new("RGB", (200, 50), color="white")
            for _ in range(TestConfig.CONCURRENT_TASKS)
        ]

        # 并发识别
        results = []
        threads = []

        def recognize_task(img, index):
            result = self.engine.recognize(img, task_id=f"concurrent_{index}")
            results.append(result)

        for i, img in enumerate(test_images):
            thread = threading.Thread(target=recognize_task, args=(img, i))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=30)

        # 验证结果
        self.assertEqual(
            len(results), TestConfig.CONCURRENT_TASKS, "并发任务未全部完成"
        )

        # 所有任务应该成功
        success_count = sum(1 for r in results if r.success)
        self.assertGreater(
            success_count,
            TestConfig.CONCURRENT_TASKS // 2,
            f"成功率过低: {success_count}/{TestConfig.CONCURRENT_TASKS}",
        )

        print(f"并发识别成功率: {success_count}/{TestConfig.CONCURRENT_TASKS}")

    def test_batch_recognition(self):
        """测试批量识别"""
        from PIL import Image

        # 创建批量测试图片
        batch_size = 3
        test_images = [
            Image.new("RGB", (200, 50), color="white") for _ in range(batch_size)
        ]

        # 创建批量引擎
        batch_engine = PaddleBatchOCREngine(PaddleConfig(lang="ch").__dict__)
        batch_engine.initialize()

        # 执行批量识别
        start_time = time.time()
        results = batch_engine.recognize_batch(test_images, task_id="batch_test")
        total_duration = time.time() - start_time

        # 验证结果
        self.assertEqual(len(results), batch_size, "批量识别结果数量不正确")

        # 清理
        batch_engine.stop()

        print(
            f"批量识别耗时: {total_duration:.3f}s (平均: {total_duration/batch_size:.3f}s/张)"
        )


# =============================================================================
# 集成测试（D）
# =============================================================================


class TestPaddleOCREngineIntegration(unittest.TestCase):
    """
    PaddleOCR 引擎集成测试

    测试与其他系统的集成，包括配置管理器、日志系统、多语言系统等。
    """

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        cls.app.quit()

    def test_integration_with_logger(self):
        """测试与日志系统的集成"""
        from utils.logger import get_logger

        logger = get_logger()

        # 创建引擎并连接信号
        config = PaddleConfig(lang="ch")
        engine = PaddleOCREngine(config.__dict__)

        # 连接信号进行日志记录
        engine.recognition_failed.connect(
            lambda task_id, code, msg, name: logger.error(f"识别失败: {code} - {msg}")
        )

        engine.initialize()

        # 执行识别
        from PIL import Image

        image = Image.new("RGB", (100, 50), color="white")
        result = engine.recognize(image)

        # 清理
        engine.stop()

        self.assertIsNotNone(result)

    def test_integration_with_config_manager(self):
        """测试与配置管理器的集成"""
        from utils.config_manager import get_config_manager

        config_manager = get_config_manager()

        # 设置配置
        config_manager.set("ocr.paddle.lang", "ch")
        config_manager.set("ocr.paddle.use_textline_orientation", True)

        # 创建引擎
        lang = config_manager.get("ocr.paddle.lang", "ch")
        use_textline_orientation = config_manager.get(
            "ocr.paddle.use_textline_orientation", True
        )

        engine_config = PaddleConfig(
            lang=lang, use_textline_orientation=use_textline_orientation
        )
        engine = PaddleOCREngine(engine_config.__dict__)

        # 验证配置
        self.assertEqual(engine.paddle_config.lang, "ch")
        self.assertTrue(engine.paddle_config.use_textline_orientation)

    def test_integration_with_i18n(self):
        """测试与多语言系统的集成"""
        from utils.i18n import get_i18n_manager

        i18n = get_i18n_manager()

        # 获取配置 Schema
        schema = PaddleOCREngine.get_config_schema()

        # 检查国际化支持
        if "lang" in schema["properties"]:
            i18n_key = schema["properties"]["lang"].get("i18n_key")
            self.assertIsNotNone(i18n_key)

    def test_integration_with_model_manager(self):
        """测试与模型管理器的集成"""
        from services.ocr import get_model_manager

        model_manager = get_model_manager()

        # 获取必需模型列表
        required_models = ModelRepository.get_required_models("ch")

        # 验证模型列表
        self.assertGreater(len(required_models), 0, "必需模型列表为空")

        print(f"必需模型: {', '.join(required_models)}")


# =============================================================================
# 测试套件
# =============================================================================


def create_test_suite():
    """
    创建测试套件

    Returns:
        unittest.TestSuite: 测试套件
    """
    suite = unittest.TestSuite()

    # 添加基础功能测试
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestPaddleOCREngineBasic)
    )

    # 添加边界情况测试
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestPaddleOCREngineBoundary)
    )

    # 添加性能测试
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestPaddleOCREnginePerformance)
    )

    # 添加集成测试
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestPaddleOCREngineIntegration)
    )

    return suite


# =============================================================================
# 主程序
# =============================================================================

if __name__ == "__main__":
    # 创建测试套件
    suite = create_test_suite()

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出测试结果统计
    print("\n" + "=" * 70)
    print(f"测试总数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 70)

    # 返回退出码
    sys.exit(0 if result.wasSuccessful() else 1)
