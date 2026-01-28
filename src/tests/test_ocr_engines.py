#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 引擎抽象层单元测试

测试 OCR 引擎抽象基类和结果数据类的功能：
- 错误码枚举
- 配置 Schema
- 性能监控指标
- OCRResult 数据类
- TextBlock 数据类
- BoundingBox 数据类
- 批量识别支持

Author: Umi-OCR Team
Date: 2026-01-26
"""

import sys
import os
import unittest
import tempfile
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtCore import QCoreApplication


class TestOCRErrorCode(unittest.TestCase):
    """测试 OCR 错误码枚举"""

    def test_error_code_categories(self):
        """测试错误码分类"""
        from src.services.ocr.base_engine import OCRErrorCode

        # 成功状态
        self.assertEqual(OCRErrorCode.SUCCESS.value, "success")
        self.assertEqual(OCRErrorCode.NO_CONTENT.value, "no_content")

        # 初始化错误
        self.assertEqual(OCRErrorCode.ENGINE_INIT_FAILED.value, "engine_init_failed")
        self.assertEqual(OCRErrorCode.CONFIG_INVALID.value, "config_invalid")
        self.assertEqual(OCRErrorCode.MODEL_LOAD_FAILED.value, "model_load_failed")

        # 网络错误
        self.assertEqual(OCRErrorCode.NETWORK_TIMEOUT.value, "network_timeout")
        self.assertEqual(OCRErrorCode.NETWORK_ERROR.value, "network_error")
        self.assertEqual(OCRErrorCode.AUTH_FAILED.value, "auth_failed")

        # 识别错误
        self.assertEqual(
            OCRErrorCode.IMAGE_FORMAT_UNSUPPORTED.value, "image_format_unsupported"
        )
        self.assertEqual(OCRErrorCode.IMAGE_TOO_LARGE.value, "image_too_large")
        self.assertEqual(OCRErrorCode.RECOGNITION_FAILED.value, "recognition_failed")

        # 资源错误
        self.assertEqual(OCRErrorCode.OUT_OF_MEMORY.value, "out_of_memory")
        self.assertEqual(OCRErrorCode.RESOURCE_BUSY.value, "resource_busy")

        # 其他错误
        self.assertEqual(OCRErrorCode.UNKNOWN_ERROR.value, "unknown_error")
        self.assertEqual(OCRErrorCode.NOT_INITIALIZED.value, "not_initialized")
        self.assertEqual(OCRErrorCode.OPERATION_CANCELLED.value, "operation_cancelled")

    def test_error_code_count(self):
        """测试错误码数量"""
        from src.services.ocr.base_engine import OCRErrorCode

        # 确保有足够的错误码覆盖各种情况
        error_codes = list(OCRErrorCode)
        self.assertGreaterEqual(len(error_codes), 20, "应该有至少20个错误码")


class TestConfigSchema(unittest.TestCase):
    """测试配置 Schema"""

    def test_create_field_string(self):
        """测试创建字符串字段"""
        from src.services.ocr.base_engine import ConfigSchema

        field = ConfigSchema.create_field(
            field_type="string",
            title="测试字段",
            description="这是一个测试字段",
            default="默认值",
            required=True,
        )

        self.assertEqual(field["type"], "string")
        self.assertEqual(field["title"], "测试字段")
        self.assertEqual(field["description"], "这是一个测试字段")
        self.assertEqual(field["default"], "默认值")
        self.assertEqual(field["required"], True)

    def test_create_field_number(self):
        """测试创建数字字段"""
        from src.services.ocr.base_engine import ConfigSchema

        field = ConfigSchema.create_field(
            field_type="number",
            title="数字字段",
            min_value=0,
            max_value=100,
            default=50,
        )

        self.assertEqual(field["type"], "number")
        self.assertEqual(field["minimum"], 0)
        self.assertEqual(field["maximum"], 100)
        self.assertEqual(field["default"], 50)

    def test_create_field_enum(self):
        """测试创建枚举字段"""
        from src.services.ocr.base_engine import ConfigSchema

        field = ConfigSchema.create_field(
            field_type="string",
            title="选择字段",
            options=["option1", "option2", "option3"],
            default="option1",
        )

        self.assertEqual(field["type"], "string")
        self.assertEqual(field["enum"], ["option1", "option2", "option3"])
        self.assertEqual(field["default"], "option1")

    def test_create_field_with_i18n(self):
        """测试创建带国际化的字段"""
        from src.services.ocr.base_engine import ConfigSchema

        field = ConfigSchema.create_field(
            field_type="string", title="国际化字段", i18n_key="config.field.name"
        )

        self.assertEqual(field["i18n_key"], "config.field.name")

    def test_create_section(self):
        """测试创建配置节"""
        from src.services.ocr.base_engine import ConfigSchema

        section = ConfigSchema.create_section(
            title="测试节",
            description="这是一个测试配置节",
            fields={
                "field1": ConfigSchema.create_field("string", "字段1"),
                "field2": ConfigSchema.create_field("number", "字段2"),
            },
            i18n_key="config.section.test",
        )

        self.assertEqual(section["title"], "测试节")
        self.assertEqual(section["type"], "object")
        self.assertIn("field1", section["properties"])
        self.assertIn("field2", section["properties"])
        self.assertEqual(section["i18n_key"], "config.section.test")


class TestEnginePerformanceMetrics(unittest.TestCase):
    """测试引擎性能指标"""

    def test_update_success(self):
        """测试更新成功指标"""
        from src.services.ocr.base_engine import EnginePerformanceMetrics

        metrics = EnginePerformanceMetrics()
        self.assertEqual(metrics.total_calls, 0)
        self.assertEqual(metrics.success_calls, 0)

        # 更新成功
        metrics.update_success(0.5)

        self.assertEqual(metrics.total_calls, 1)
        self.assertEqual(metrics.success_calls, 1)
        self.assertEqual(metrics.total_duration, 0.5)
        self.assertEqual(metrics.min_duration, 0.5)
        self.assertEqual(metrics.max_duration, 0.5)
        self.assertEqual(metrics.avg_duration, 0.5)

    def test_update_failure(self):
        """测试更新失败指标"""
        from src.services.ocr.base_engine import EnginePerformanceMetrics

        metrics = EnginePerformanceMetrics()
        metrics.update_failure(0.3)

        self.assertEqual(metrics.total_calls, 1)
        self.assertEqual(metrics.failure_calls, 1)
        self.assertEqual(metrics.total_duration, 0.3)

    def test_get_success_rate(self):
        """测试获取成功率"""
        from src.services.ocr.base_engine import EnginePerformanceMetrics

        metrics = EnginePerformanceMetrics()

        # 初始状态
        self.assertEqual(metrics.get_success_rate(), 0.0)

        # 添加成功
        metrics.update_success(0.5)
        self.assertEqual(metrics.get_success_rate(), 1.0)

        # 添加失败
        metrics.update_failure(0.3)
        self.assertAlmostEqual(metrics.get_success_rate(), 0.5)

    def test_to_dict(self):
        """测试转换为字典"""
        from src.services.ocr.base_engine import EnginePerformanceMetrics

        metrics = EnginePerformanceMetrics()
        metrics.update_success(1.0)
        metrics.update_success(2.0)

        result = metrics.to_dict()

        self.assertEqual(result["total_calls"], 2)
        self.assertEqual(result["success_calls"], 2)
        self.assertEqual(result["failure_calls"], 0)
        self.assertEqual(result["success_rate"], 1.0)
        self.assertEqual(result["min_duration"], 1.0)
        self.assertEqual(result["max_duration"], 2.0)
        self.assertEqual(result["avg_duration"], 1.5)


class TestBoundingBox(unittest.TestCase):
    """测试边界框数据类"""

    def test_create_from_points(self):
        """测试从点创建边界框"""
        from src.services.ocr.ocr_result import BoundingBox

        bbox = BoundingBox(points=[[10, 10], [100, 10], [100, 50], [10, 50]])

        self.assertEqual(bbox.x, 10)
        self.assertEqual(bbox.y, 10)
        self.assertEqual(bbox.width, 90)
        self.assertEqual(bbox.height, 40)

    def test_create_with_values(self):
        """测试带值的边界框"""
        from src.services.ocr.ocr_result import BoundingBox

        bbox = BoundingBox(
            points=[[0, 0], [100, 0], [100, 100], [0, 100]],
            x=5,
            y=5,
            width=90,
            height=90,
        )

        self.assertEqual(bbox.x, 5)
        self.assertEqual(bbox.y, 5)

    def test_to_dict(self):
        """测试转换为字典"""
        from src.services.ocr.ocr_result import BoundingBox

        bbox = BoundingBox(points=[[0, 0], [100, 0], [100, 100], [0, 100]])
        result = bbox.to_dict()

        self.assertIn("points", result)
        self.assertIn("x", result)
        self.assertIn("y", result)
        self.assertIn("width", result)
        self.assertIn("height", result)

    def test_from_dict(self):
        """测试从字典创建"""
        from src.services.ocr.ocr_result import BoundingBox

        data = {
            "points": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "x": 10,
            "y": 20,
            "width": 80,
            "height": 80,
        }

        bbox = BoundingBox.from_dict(data)

        self.assertEqual(bbox.x, 10)
        self.assertEqual(bbox.y, 20)


class TestTextBlock(unittest.TestCase):
    """测试文本块数据类"""

    def test_create_basic(self):
        """测试创建基本文本块"""
        from src.services.ocr.ocr_result import TextBlock, TextBlockType

        block = TextBlock(text="测试文本", confidence=0.95)

        self.assertEqual(block.text, "测试文本")
        self.assertEqual(block.confidence, 0.95)
        self.assertEqual(block.block_type, TextBlockType.UNKNOWN)

    def test_create_with_bbox(self):
        """测试带边界框的文本块"""
        from src.services.ocr.ocr_result import TextBlock, BoundingBox, TextBlockType

        bbox = BoundingBox(points=[[0, 0], [100, 0], [100, 50], [0, 50]])
        block = TextBlock(
            text="测试文本",
            confidence=0.95,
            bbox=bbox,
            block_type=TextBlockType.PARAGRAPH,
        )

        self.assertIsNotNone(block.bbox)
        self.assertEqual(block.block_type, TextBlockType.PARAGRAPH)

    def test_to_dict(self):
        """测试转换为字典"""
        from src.services.ocr.ocr_result import TextBlock, BoundingBox

        bbox = BoundingBox(points=[[0, 0], [100, 0], [100, 50], [0, 50]])
        block = TextBlock(text="测试", confidence=0.9, bbox=bbox)

        result = block.to_dict()

        self.assertEqual(result["text"], "测试")
        self.assertEqual(result["confidence"], 0.9)
        self.assertIn("bbox", result)

    def test_from_dict(self):
        """测试从字典创建"""
        from src.services.ocr.ocr_result import TextBlock

        data = {
            "text": "测试文本",
            "confidence": 0.95,
            "bbox": {
                "points": [[0, 0], [100, 0], [100, 50], [0, 50]],
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 50,
            },
            "block_type": "paragraph",
        }

        block = TextBlock.from_dict(data)

        self.assertEqual(block.text, "测试文本")
        self.assertEqual(block.confidence, 0.95)
        self.assertIsNotNone(block.bbox)


class TestOCRResult(unittest.TestCase):
    """测试 OCR 结果数据类"""

    def test_create_empty(self):
        """测试创建空结果"""
        from src.services.ocr.ocr_result import OCRResult

        result = OCRResult()

        self.assertTrue(result.success)
        self.assertEqual(result.text_blocks, [])
        self.assertEqual(result.full_text, "")
        self.assertIsNone(result.error_code)

    def test_create_with_text(self):
        """测试创建带文本的结果"""
        from src.services.ocr.ocr_result import OCRResult, TextBlock

        blocks = [
            TextBlock(text="第一行", confidence=0.95),
            TextBlock(text="第二行", confidence=0.90),
        ]
        result = OCRResult(
            text_blocks=blocks, full_text="第一行\n第二行", engine_type="paddle"
        )

        self.assertEqual(len(result.text_blocks), 2)
        self.assertEqual(result.get_text(), "第一行\n第二行")
        self.assertEqual(result.engine_type, "paddle")

    def test_get_text_empty(self):
        """测试获取空文本"""
        from src.services.ocr.ocr_result import OCRResult

        result = OCRResult()
        self.assertEqual(result.get_text(), "")

    def test_get_text_from_blocks(self):
        """测试从文本块获取文本"""
        from src.services.ocr.ocr_result import OCRResult, TextBlock

        result = OCRResult()
        result.text_blocks = [TextBlock(text="Hello"), TextBlock(text="World")]

        text = result.get_text(separator=" ")
        self.assertEqual(text, "Hello World")

    def test_get_text_blocks_by_confidence(self):
        """测试按置信度筛选"""
        from src.services.ocr.ocr_result import OCRResult, TextBlock

        result = OCRResult()
        result.text_blocks = [
            TextBlock(text="高置信度", confidence=0.95),
            TextBlock(text="低置信度", confidence=0.60),
            TextBlock(text="中置信度", confidence=0.80),
        ]

        filtered = result.get_text_blocks_by_confidence(0.75)

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].text, "高置信度")
        self.assertEqual(filtered[1].text, "中置信度")

    def test_to_dict(self):
        """测试转换为字典"""
        from src.services.ocr.ocr_result import OCRResult, TextBlock

        result = OCRResult(
            text_blocks=[TextBlock(text="测试", confidence=0.9)],
            full_text="测试",
            engine_type="test",
        )

        data = result.to_dict()

        self.assertIn("text_blocks", data)
        self.assertIn("full_text", data)
        self.assertIn("engine_type", data)
        self.assertEqual(data["full_text"], "测试")

    def test_from_dict(self):
        """测试从字典创建"""
        from src.services.ocr.ocr_result import OCRResult

        data = {
            "text_blocks": [
                {"text": "测试", "confidence": 0.9, "block_type": "unknown"}
            ],
            "full_text": "测试",
            "engine_type": "test",
            "success": True,
            "batch_index": 0,
            "batch_total": 1,
        }

        result = OCRResult.from_dict(data)

        self.assertEqual(len(result.text_blocks), 1)
        self.assertEqual(result.text_blocks[0].text, "测试")
        self.assertEqual(result.engine_type, "test")

    def test_to_json(self):
        """测试转换为 JSON"""
        from src.services.ocr.ocr_result import OCRResult

        result = OCRResult(full_text="测试文本")
        json_str = result.to_json()

        self.assertIn("测试文本", json_str)
        self.assertIn("full_text", json_str)

    def test_merge_results(self):
        """测试合并结果"""
        from src.services.ocr.ocr_result import OCRResult, TextBlock

        results = [
            OCRResult(text_blocks=[TextBlock(text="第一")], duration=0.5),
            OCRResult(text_blocks=[TextBlock(text="第二")], duration=0.3),
            OCRResult(text_blocks=[TextBlock(text="第三")], duration=0.4),
        ]

        merged = OCRResult.merge_results(results)

        self.assertEqual(len(merged.text_blocks), 3)
        self.assertEqual(merged.batch_total, 3)
        self.assertAlmostEqual(merged.duration, 1.2)

    def test_merge_empty_results(self):
        """测试合并空结果"""
        from src.services.ocr.ocr_result import OCRResult

        merged = OCRResult.merge_results([])

        self.assertIsNotNone(merged)
        self.assertEqual(len(merged.text_blocks), 0)


class TestBatchOCRResult(unittest.TestCase):
    """测试批量 OCR 结果"""

    def test_add_result(self):
        """测试添加结果"""
        from src.services.ocr.ocr_result import BatchOCRResult, OCRResult

        batch = BatchOCRResult()

        # 添加成功结果
        result1 = OCRResult(success=True, duration=0.5)
        batch.add_result(result1)

        self.assertEqual(batch.total_count, 1)
        self.assertEqual(batch.success_count, 1)
        self.assertEqual(batch.failure_count, 0)

        # 添加失败结果
        result2 = OCRResult(success=False, error_code="error")
        batch.add_result(result2)

        self.assertEqual(batch.total_count, 2)
        self.assertEqual(batch.success_count, 1)
        self.assertEqual(batch.failure_count, 1)

    def test_get_success_rate(self):
        """测试获取成功率"""
        from src.services.ocr.ocr_result import BatchOCRResult, OCRResult

        batch = BatchOCRResult()

        # 添加4个成功，1个失败
        for _ in range(4):
            batch.add_result(OCRResult(success=True))
        batch.add_result(OCRResult(success=False))

        self.assertAlmostEqual(batch.get_success_rate(), 0.8)

    def test_merge_all(self):
        """测试合并所有结果"""
        from src.services.ocr.ocr_result import BatchOCRResult, OCRResult, TextBlock

        batch = BatchOCRResult()
        batch.add_result(OCRResult(text_blocks=[TextBlock(text="1")]))
        batch.add_result(OCRResult(text_blocks=[TextBlock(text="2")]))

        merged = batch.merge_all()

        self.assertEqual(len(merged.text_blocks), 2)

    def test_to_dict(self):
        """测试转换为字典"""
        from src.services.ocr.ocr_result import BatchOCRResult, OCRResult

        batch = BatchOCRResult()
        batch.add_result(OCRResult(success=True, duration=0.5))

        data = batch.to_dict()

        self.assertIn("total_count", data)
        self.assertIn("success_count", data)
        self.assertIn("results", data)


class TestBaseOCREngine(unittest.TestCase):
    """测试 OCR 引擎抽象基类"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def test_engine_properties(self):
        """测试引擎属性"""
        from src.services.ocr.base_engine import BaseOCREngine

        class TestEngine(BaseOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                from src.services.ocr.ocr_result import OCRResult

                return OCRResult()

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = TestEngine({})

        self.assertEqual(engine.engine_type, "base")
        self.assertEqual(engine.engine_name, "Base OCR Engine")
        self.assertFalse(engine.is_initialized)
        self.assertFalse(engine.SUPPORTS_GPU)
        self.assertTrue(engine.SUPPORTS_BATCH)

    def test_initialize(self):
        """测试引擎初始化"""
        from src.services.ocr.base_engine import BaseOCREngine
        from src.services.ocr.ocr_result import OCRResult

        class TestEngine(BaseOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                return OCRResult()

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = TestEngine({})

        # 未初始化
        self.assertFalse(engine.is_initialized)

        # 初始化
        result = engine.initialize()
        self.assertTrue(result)
        self.assertTrue(engine.is_initialized)

        # 重复初始化
        result = engine.initialize()
        self.assertTrue(result)

    def test_stop(self):
        """测试引擎停止"""
        from src.services.ocr.base_engine import BaseOCREngine
        from src.services.ocr.ocr_result import OCRResult

        class TestEngine(BaseOCREngine):
            initialized = False

            def _do_initialize(self):
                TestEngine.initialized = True
                return True

            def _do_recognize(self, image, **kwargs):
                return OCRResult()

            def _do_cleanup(self):
                TestEngine.initialized = False

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = TestEngine({})
        engine.initialize()

        self.assertTrue(engine.is_initialized)

        engine.stop()

        self.assertFalse(engine.is_initialized)

    def test_recognize_uninitialized(self):
        """测试未初始化时的识别"""
        from src.services.ocr.base_engine import BaseOCREngine
        from src.services.ocr.ocr_result import OCRResult

        class TestEngine(BaseOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                return OCRResult()

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = TestEngine({})

        # 未初始化时识别应该返回错误
        result = engine.recognize("test.png")

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "not_initialized")

    def test_recognize_with_image_path(self):
        """测试使用图片路径识别"""
        from src.services.ocr.base_engine import BaseOCREngine
        from src.services.ocr.ocr_result import OCRResult, TextBlock
        from PIL import Image

        class TestEngine(BaseOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                return OCRResult(
                    success=True,
                    text_blocks=[TextBlock(text="测试结果", confidence=0.95)],
                )

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = TestEngine({})
        engine.initialize()

        # 创建临时图片文件
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False, mode="wb") as f:
            temp_path = f.name
            img = Image.new("RGB", (100, 100), color="white")
            img.save(f, format="PNG")

        try:
            result = engine.recognize(temp_path)
            self.assertTrue(result.success, f"识别失败: {result.error_code}")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_recognize_with_bytes(self):
        """测试使用字节数据识别"""
        from src.services.ocr.base_engine import BaseOCREngine
        from src.services.ocr.ocr_result import OCRResult, TextBlock
        from PIL import Image
        import io

        class TestEngine(BaseOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                return OCRResult(
                    success=True,
                    text_blocks=[TextBlock(text="测试结果", confidence=0.95)],
                )

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = TestEngine({})
        engine.initialize()

        # 创建图片字节
        img = Image.new("RGB", (100, 100), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        result = engine.recognize(img_bytes)

        self.assertTrue(result.success, f"识别失败: {result.error_code}")

    def test_recognize_with_pil_image(self):
        """测试使用 PIL Image 识别"""
        from src.services.ocr.base_engine import BaseOCREngine
        from src.services.ocr.ocr_result import OCRResult, TextBlock
        from PIL import Image

        class TestEngine(BaseOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                # 验证接收到的是 PIL Image
                if not isinstance(image, Image.Image):
                    raise TypeError(f"期望 PIL Image，实际收到 {type(image)}")
                return OCRResult(
                    success=True,
                    text_blocks=[TextBlock(text="识别结果", confidence=0.95)],
                )

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = TestEngine({})
        engine.initialize()

        # 直接传递 PIL Image
        img = Image.new("RGB", (100, 100), color="white")
        result = engine.recognize(img)

        self.assertTrue(result.success, f"识别失败: {result.error_code}")
        self.assertEqual(len(result.text_blocks), 1)

    def test_cancel(self):
        """测试取消操作"""
        from src.services.ocr.base_engine import BaseOCREngine
        from src.services.ocr.ocr_result import OCRResult

        class TestEngine(BaseOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                return OCRResult()

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = TestEngine({})
        engine.initialize()

        # 设置取消标志
        engine.cancel()

        self.assertTrue(engine.is_cancelled())

        # 清除取消标志
        engine._cancel_event.clear()
        self.assertFalse(engine.is_cancelled())

    def test_get_metrics(self):
        """测试获取性能指标"""
        from src.services.ocr.base_engine import BaseOCREngine
        from src.services.ocr.ocr_result import OCRResult, TextBlock
        from PIL import Image
        import io

        class TestEngine(BaseOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                # 不要在 _do_recognize 中添加断言
                return OCRResult(
                    success=True,
                    text_blocks=[TextBlock(text="测试结果", confidence=0.95)],
                )

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = TestEngine({})
        engine.initialize()

        # 使用 BytesIO 传递图片数据
        img = Image.new("RGB", (100, 100), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        result = engine.recognize(buffer)
        self.assertTrue(result.success, f"识别失败: {result.error_code}")

        # 获取指标 - 直接访问内部属性
        metrics = engine._metrics

        self.assertEqual(metrics.total_calls, 1)
        self.assertEqual(metrics.success_calls, 1)

    def test_validate_config(self):
        """测试配置验证"""
        from src.services.ocr.base_engine import BaseOCREngine
        from src.services.ocr.ocr_result import OCRResult

        class TestEngine(BaseOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                return OCRResult()

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {"required": ["lang"]}

        engine = TestEngine({"lang": "ch"})

        # 验证通过
        errors = engine.validate_config()
        self.assertEqual(len(errors), 0)

        # 缺少必需字段
        engine = TestEngine({})
        errors = engine.validate_config()
        self.assertGreater(len(errors), 0)

    def test_get_set_config_value(self):
        """测试获取/设置配置值"""
        from src.services.ocr.base_engine import BaseOCREngine
        from src.services.ocr.ocr_result import OCRResult

        class TestEngine(BaseOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                return OCRResult()

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = TestEngine({"key1": "value1"})

        # 获取配置
        self.assertEqual(engine.get_config_value("key1"), "value1")
        self.assertEqual(engine.get_config_value("key2", "default"), "default")

        # 设置配置
        engine.set_config_value("key2", "value2")
        self.assertEqual(engine.get_config_value("key2"), "value2")

    def test_emit_progress(self):
        """测试进度通知"""
        from src.services.ocr.base_engine import BaseOCREngine
        from src.services.ocr.ocr_result import OCRResult

        class TestEngine(BaseOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                return OCRResult()

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = TestEngine({})
        engine.initialize()

        # 记录进度通知
        progress_calls = []
        engine.progress_updated.connect(
            lambda t, c, total, pct: progress_calls.append((t, c, total, pct))
        )

        engine.emit_progress("task1", 5, 10)

        self.assertEqual(len(progress_calls), 1)
        self.assertEqual(progress_calls[0][1], 5)
        self.assertEqual(progress_calls[0][2], 10)
        self.assertEqual(progress_calls[0][3], 50.0)


class TestBatchOCREngine(unittest.TestCase):
    """测试批量 OCR 引擎"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def test_recognize_batch(self):
        """测试批量识别"""
        from src.services.ocr.base_engine import BatchOCREngine
        from src.services.ocr.ocr_result import OCRResult, TextBlock
        from PIL import Image
        import io

        class BatchTestEngine(BatchOCREngine):
            def _do_initialize(self):
                return True

            def _do_recognize(self, image, **kwargs):
                return OCRResult(success=True, text_blocks=[TextBlock(text="result")])

            def _do_cleanup(self):
                pass

            @classmethod
            def get_config_schema(cls):
                return {}

        engine = BatchTestEngine({})
        engine.initialize()

        # 使用BytesIO对象列表测试批量识别
        img = Image.new("RGB", (100, 100), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        images = [buffer, buffer, buffer]  # 使用相同的BytesIO对象
        results = engine.recognize_batch(images, task_id="batch_task")

        self.assertEqual(len(results), 3)
        for i, result in enumerate(results):
            self.assertTrue(result.success, f"第{i+1}个识别失败: {result.error_code}")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
