#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR 引擎抽象层使用示例

展示如何使用第6阶段创建的 OCR 引擎抽象层。

Author: Umi-OCR Team
Date: 2026-01-26
"""

from src.services.ocr import (
    BaseOCREngine,
    OCRResult,
    OCRErrorCode,
    TextBlock,
    TextBlockType,
    BoundingBox,
)
from PySide6.QtCore import QObject

# =============================================================================
# 示例引擎实现
# =============================================================================


class ExampleOCREngine(BaseOCREngine):
    """
    示例 OCR 引擎

    演示如何继承 BaseOCREngine 并实现抽象方法。
    """

    ENGINE_TYPE = "example"
    ENGINE_NAME = "示例引擎"
    ENGINE_VERSION = "1.0.0"

    def _do_initialize(self) -> bool:
        """初始化引擎"""
        self._engine_instance = "initialized"
        return True

    def _do_recognize(self, image, **kwargs) -> OCRResult:
        """执行识别"""

        # 创建示例结果
        width, height = image.size

        result = OCRResult(
            engine_type=self.ENGINE_TYPE,
            engine_name=self.ENGINE_NAME,
            engine_version=self.ENGINE_VERSION,
            image_width=width,
            image_height=height,
            success=True,
        )

        # 添加示例文本块
        result.text_blocks = [
            TextBlock(
                text="这是示例文本",
                confidence=0.95,
                bbox=BoundingBox(points=[[10, 10], [200, 10], [200, 50], [10, 50]]),
                block_type=TextBlockType.PARAGRAPH,
                language="zh",
            ),
            TextBlock(
                text="Example Text",
                confidence=0.98,
                bbox=BoundingBox(points=[[10, 60], [200, 60], [200, 100], [10, 100]]),
                block_type=TextBlockType.PARAGRAPH,
                language="en",
            ),
        ]

        # 生成完整文本
        result.full_text = result.get_text(separator="\n")

        return result

    def _do_cleanup(self) -> None:
        """清理资源"""
        self._engine_instance = None

    @classmethod
    def get_config_schema(cls) -> dict:
        """获取配置 Schema"""
        return {
            "type": "object",
            "properties": {
                "lang": {
                    "type": "string",
                    "title": "语言",
                    "default": "ch",
                    "enum": ["ch", "en", "fr"],
                    "i18n_key": "ocr.lang",
                },
                "use_gpu": {
                    "type": "boolean",
                    "title": "使用 GPU",
                    "default": False,
                    "i18n_key": "ocr.use_gpu",
                },
            },
            "required": ["lang"],
        }


# =============================================================================
# 使用示例
# =============================================================================


def example_basic_usage():
    """基本使用示例"""
    print("\n=== 基本使用示例 ===")

    # 创建引擎
    config = {"lang": "ch", "use_gpu": False}
    engine = ExampleOCREngine(config)

    # 初始化
    if engine.initialize():
        print("引擎初始化成功")

        # 创建测试图像
        from PIL import Image

        test_image = Image.new("RGB", (300, 150), color="white")

        # 执行识别
        result = engine.recognize(test_image, task_id="test_task_1")

        # 检查结果
        if result.success:
            print(f"识别成功: {result.get_text()}")
            print(f"文本块数量: {len(result.text_blocks)}")
            print(f"识别耗时: {result.duration:.3f}秒")
        else:
            print(f"识别失败: {result.error_message}")
    else:
        print("引擎初始化失败")

    # 清理
    engine.stop()


def example_error_handling():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")

    # 创建引擎
    config = {"lang": "ch"}
    ExampleOCREngine(config)

    # 测试不同的错误情况
    print(f"未初始化错误: {OCRErrorCode.NOT_INITIALIZED.value}")
    print(f"配置无效错误: {OCRErrorCode.CONFIG_INVALID.value}")
    print(f"识别失败错误: {OCRErrorCode.RECOGNITION_FAILED.value}")


def example_progress_notification():
    """进度通知示例"""
    print("\n=== 进度通知示例 ===")

    class ProgressHandler(QObject):
        """进度处理器"""

        def on_progress(
            self, task_id: str, current: int, total: int, percentage: float
        ):
            """进度更新回调"""
            print(f"任务 {task_id}: {current}/{total} ({percentage:.1f}%)")

        def on_started(self, task_id: str):
            """开始回调"""
            print(f"任务 {task_id} 开始")

        def on_completed(self, task_id: str, result: OCRResult):
            """完成回调"""
            if result.success:
                print(f"任务 {task_id} 完成，识别 {len(result.text_blocks)} 个文本块")
            else:
                print(f"任务 {task_id} 失败: {result.error_message}")

    # 创建引擎
    config = {"lang": "ch"}
    engine = ExampleOCREngine(config)

    # 初始化
    engine.initialize()

    # 连接信号
    handler = ProgressHandler()
    engine.progress_updated.connect(handler.on_progress)
    engine.recognition_started.connect(handler.on_started)
    engine.recognition_completed.connect(handler.on_completed)

    # 执行识别
    from PIL import Image

    test_image = Image.new("RGB", (300, 150), color="white")
    engine.recognize(test_image, task_id="progress_task")

    # 清理
    engine.stop()


def example_performance_monitoring():
    """性能监控示例"""
    print("\n=== 性能监控示例 ===")

    # 创建引擎
    config = {"lang": "ch"}
    engine = ExampleOCREngine(config)

    # 初始化
    engine.initialize()

    # 执行多次识别
    from PIL import Image

    test_image = Image.new("RGB", (300, 150), color="white")

    for i in range(5):
        engine.recognize(test_image, task_id=f"perf_task_{i}")

    # 获取性能指标
    metrics = engine.get_metrics()

    print(f"总调用次数: {metrics.total_calls}")
    print(f"成功次数: {metrics.success_calls}")
    print(f"失败次数: {metrics.failure_calls}")
    print(f"成功率: {metrics.get_success_rate():.1%}")
    print(f"平均耗时: {metrics.avg_duration:.3f}秒")
    print(f"最小耗时: {metrics.min_duration:.3f}秒")
    print(f"最大耗时: {metrics.max_duration:.3f}秒")

    # 清理
    engine.stop()


def example_config_schema():
    """配置 Schema 示例"""
    print("\n=== 配置 Schema 示例 ===")

    # 获取配置 Schema
    schema = ExampleOCREngine.get_config_schema()

    print("配置 Schema:")
    import json

    print(json.dumps(schema, indent=2, ensure_ascii=False))

    # 验证配置
    engine = ExampleOCREngine({"lang": "ch"})
    errors = engine.validate_config()

    if errors:
        print(f"配置验证失败: {errors}")
    else:
        print("配置验证通过")


def example_result_serialization():
    """结果序列化示例"""
    print("\n=== 结果序列化示例 ===")

    # 创建测试图像
    from PIL import Image

    test_image = Image.new("RGB", (300, 150), color="white")

    # 执行识别
    config = {"lang": "ch"}
    engine = ExampleOCREngine(config)
    engine.initialize()
    result = engine.recognize(test_image)

    # 转换为字典
    result_dict = result.to_dict()
    print(f"结果字典: {list(result_dict.keys())}")

    # 转换为 JSON
    result_json = result.to_json()
    print(f"JSON 长度: {len(result_json)} 字节")

    # 转换为 XML
    result_xml = result.to_xml()
    print(f"XML 长度: {len(result_xml)} 字节")

    # 转换为 CSV
    result_csv = result.to_csv()
    print(f"CSV 长度: {len(result_csv)} 字节")

    # 清理
    engine.stop()


def example_batch_recognition():
    """批量识别示例"""
    print("\n=== 批量识别示例 ===")

    from src.services.ocr import BatchOCREngine

    # 创建批量引擎
    class ExampleBatchEngine(BatchOCREngine):
        ENGINE_TYPE = "example_batch"
        ENGINE_NAME = "示例批量引擎"

        def _do_initialize(self) -> bool:
            self._engine_instance = "initialized"
            return True

        def _do_recognize(self, image, **kwargs) -> OCRResult:
            result = OCRResult(
                engine_type=self.ENGINE_TYPE, engine_name=self.ENGINE_NAME, success=True
            )
            result.text_blocks = [
                TextBlock(
                    text=f"批量识别文本 {kwargs.get('index', 0)}", confidence=0.95
                )
            ]
            return result

        def _do_cleanup(self) -> None:
            self._engine_instance = None

        @classmethod
        def get_config_schema(cls) -> dict:
            return {"type": "object", "properties": {}}

    # 创建引擎
    config = {}
    engine = ExampleBatchEngine(config)
    engine.initialize()

    # 准备测试图像
    from PIL import Image

    test_images = [
        Image.new("RGB", (300, 150), color="white"),
        Image.new("RGB", (300, 150), color="white"),
        Image.new("RGB", (300, 150), color="white"),
    ]

    # 执行批量识别
    results = engine.recognize_batch(test_images, task_id="batch_task")

    print(f"批量识别完成: {len(results)} 张图片")

    # 合并结果
    merged_result = OCRResult.merge_results(results)
    print(f"合并后的文本块数量: {len(merged_result.text_blocks)}")

    # 清理
    engine.stop()


# =============================================================================
# 主程序
# =============================================================================

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    # 创建 Qt 应用程序（必需，因为使用了 Signal）
    app = QApplication([])

    # 运行所有示例
    example_basic_usage()
    example_error_handling()
    example_progress_notification()
    example_performance_monitoring()
    example_config_schema()
    example_result_serialization()
    example_batch_recognition()

    print("\n=== 所有示例运行完成 ===")
