#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR OCR 引擎抽象基类

定义 OCR 引擎的统一接口，支持多种 OCR 引擎实现。

主要功能：
- 统一的 OCR 引擎接口规范
- 细粒度错误码定义
- 配置 Schema 支持（JSON Schema）
- 进度通知和信号机制
- 取消处理接口（队列层取消方案）
- 错误传播机制
- 性能监控接口

Author: Umi-OCR Team
Date: 2026-01-26
"""

from abc import abstractmethod
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import threading
import time
from pathlib import Path
from PIL import Image
import base64
from io import BytesIO

from PySide6.QtCore import QObject, Signal

from .ocr_result import OCRResult

# =============================================================================
# 错误码枚举（细粒度）
# =============================================================================


class OCRErrorCode(Enum):
    """
    OCR 错误码枚举

    定义细粒度的错误分类，用于错误处理和日志记录。
    """

    # -------------------------------------------------------------------------
    # 成功状态
    # -------------------------------------------------------------------------
    SUCCESS = "success"  # 成功
    NO_CONTENT = "no_content"  # 无内容

    # -------------------------------------------------------------------------
    # 初始化错误
    # -------------------------------------------------------------------------
    ENGINE_INIT_FAILED = "engine_init_failed"  # 引擎初始化失败
    CONFIG_INVALID = "config_invalid"  # 配置无效
    MODEL_LOAD_FAILED = "model_load_failed"  # 模型加载失败
    RESOURCE_NOT_FOUND = "resource_not_found"  # 资源未找到

    # -------------------------------------------------------------------------
    # 网络错误（云 OCR）
    # -------------------------------------------------------------------------
    NETWORK_TIMEOUT = "network_timeout"  # 网络超时
    NETWORK_ERROR = "network_error"  # 网络错误
    AUTH_FAILED = "auth_failed"  # 认证失败
    API_QUOTA_EXCEEDED = "api_quota_exceeded"  # API 配额超限
    TOKEN_EXPIRED = "token_expired"  # 令牌过期
    INVALID_API_KEY = "invalid_api_key"  # 无效的 API Key

    # -------------------------------------------------------------------------
    # 识别错误
    # -------------------------------------------------------------------------
    IMAGE_FORMAT_UNSUPPORTED = "image_format_unsupported"  # 不支持的图片格式
    IMAGE_TOO_LARGE = "image_too_large"  # 图片过大
    IMAGE_CORRUPTED = "image_corrupted"  # 图片损坏
    RECOGNITION_FAILED = "recognition_failed"  # 识别失败
    EMPTY_IMAGE = "empty_image"  # 空白图片

    # -------------------------------------------------------------------------
    # 资源错误
    # -------------------------------------------------------------------------
    OUT_OF_MEMORY = "out_of_memory"  # 内存不足
    RESOURCE_BUSY = "resource_busy"  # 资源忙碌
    THREAD_LOCK_TIMEOUT = "thread_lock_timeout"  # 线程锁超时

    # -------------------------------------------------------------------------
    # 其他错误
    # -------------------------------------------------------------------------
    UNKNOWN_ERROR = "unknown_error"  # 未知错误
    NOT_INITIALIZED = "not_initialized"  # 未初始化
    OPERATION_CANCELLED = "operation_cancelled"  # 操作已取消


# =============================================================================
# 配置 Schema 定义
# =============================================================================


class ConfigSchema:
    """
    配置 Schema 定义

    使用 JSON Schema 格式定义 OCR 引擎的配置项，用于 UI 动态生成配置界面。
    """

    @staticmethod
    def create_field(
        field_type: str,
        title: str,
        description: str = "",
        default: Any = None,
        required: bool = True,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        options: Optional[List[Any]] = None,
        i18n_key: Optional[str] = None,
        dependencies: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        创建配置字段定义

        Args:
            field_type: 字段类型（string/number/boolean/integer/array/object）
            title: 字段标题
            description: 字段描述
            default: 默认值
            required: 是否必填
            min_value: 最小值（数字类型）
            max_value: 最大值（数字类型）
            options: 选项列表（枚举类型）
            i18n_key: 国际化键名
            dependencies: 依赖关系（满足条件时才显示此字段）

        Returns:
            Dict[str, Any]: 字段定义
        """
        field_def = {
            "type": field_type,
            "title": title,
            "description": description,
            "default": default,
            "required": required,
        }

        # 添加约束条件
        if min_value is not None:
            field_def["minimum"] = min_value
        if max_value is not None:
            field_def["maximum"] = max_value
        if options is not None:
            field_def["enum"] = options

        # 添加国际化支持
        if i18n_key:
            field_def["i18n_key"] = i18n_key

        # 添加依赖关系
        if dependencies:
            field_def["dependencies"] = dependencies

        return field_def

    @staticmethod
    def create_section(
        title: str,
        description: str = "",
        fields: Optional[Dict[str, Dict[str, Any]]] = None,
        i18n_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建配置节定义

        Args:
            title: 节标题
            description: 节描述
            fields: 字段定义字典
            i18n_key: 国际化键名

        Returns:
            Dict[str, Any]: 节定义
        """
        section_def = {
            "type": "object",
            "title": title,
            "description": description,
            "properties": fields or {},
        }

        # 添加国际化支持
        if i18n_key:
            section_def["i18n_key"] = i18n_key

        return section_def


# =============================================================================
# 性能监控数据类
# =============================================================================


class EnginePerformanceMetrics:
    """
    引擎性能指标

    记录引擎的性能数据，用于监控和告警。
    """

    # 基础指标
    total_calls: int = 0  # 总调用次数
    success_calls: int = 0  # 成功次数
    failure_calls: int = 0  # 失败次数

    # 耗时指标
    total_duration: float = 0.0  # 总耗时（秒）
    min_duration: float = float("inf")  # 最小耗时
    max_duration: float = 0.0  # 最大耗时
    avg_duration: float = 0.0  # 平均耗时

    # 资源指标（可选，由引擎实现提供）
    memory_usage: Optional[float] = None  # 内存占用（MB）
    cpu_usage: Optional[float] = None  # CPU 使用率（%）

    # 时间戳
    last_call_time: Optional[float] = None  # 最后调用时间（Unix timestamp）
    last_success_time: Optional[float] = None  # 最后成功时间
    last_failure_time: Optional[float] = None  # 最后失败时间

    def update_success(self, duration: float) -> None:
        """
        更新成功指标

        Args:
            duration: 本次调用耗时（秒）
        """
        import time

        self.total_calls += 1
        self.success_calls += 1
        self.total_duration += duration
        self.last_call_time = time.time()
        self.last_success_time = time.time()

        # 更新最小/最大耗时
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)

        # 更新平均耗时
        if self.total_calls > 0:
            self.avg_duration = self.total_duration / self.total_calls

    def update_failure(self, duration: float = 0.0) -> None:
        """
        更新失败指标

        Args:
            duration: 本次调用耗时（秒）
        """
        import time

        self.total_calls += 1
        self.failure_calls += 1
        self.total_duration += duration
        self.last_call_time = time.time()
        self.last_failure_time = time.time()

        # 更新平均耗时
        if self.total_calls > 0:
            self.avg_duration = self.total_duration / self.total_calls

    def get_success_rate(self) -> float:
        """
        获取成功率

        Returns:
            float: 成功率（0.0 - 1.0）
        """
        if self.total_calls == 0:
            return 0.0
        return self.success_calls / self.total_calls

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            Dict[str, Any]: 性能指标字典
        """
        return {
            "total_calls": self.total_calls,
            "success_calls": self.success_calls,
            "failure_calls": self.failure_calls,
            "success_rate": self.get_success_rate(),
            "total_duration": self.total_duration,
            "min_duration": (
                self.min_duration if self.min_duration != float("inf") else 0.0
            ),
            "max_duration": self.max_duration,
            "avg_duration": self.avg_duration,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "last_call_time": self.last_call_time,
            "last_success_time": self.last_success_time,
            "last_failure_time": self.last_failure_time,
        }


# 导入 dataclass


# =============================================================================
# OCR 引擎抽象基类
# =============================================================================


class BaseOCREngine(QObject):
    """
    OCR 引擎抽象基类

    所有 OCR 引擎实现必须继承此类并实现抽象方法。
    提供统一的接口规范，支持多种输入格式和输出格式。

    主要功能：
    - 引擎初始化和资源管理
    - 图像识别和结果返回
    - 配置管理和校验
    - 进度通知和错误传播
    - 性能监控和告警
    - 线程安全保证
    """

    # -------------------------------------------------------------------------
    # 信号定义（用于与 UI 和任务系统通信）
    # -------------------------------------------------------------------------

    # 进度通知信号
    # 参数: task_id (str), current (int), total (int), percentage (float)
    progress_updated = Signal(str, int, int, float)

    # 识别开始信号
    # 参数: task_id (str)
    recognition_started = Signal(str)

    # 识别完成信号
    # 参数: task_id (str), result (OCRResult)
    recognition_completed = Signal(str, object)

    # 识别失败信号
    # 参数: task_id (str), error_code (str), error_message (str), engine_name (str)
    recognition_failed = Signal(str, str, str, str)

    # 引擎状态变更信号
    # 参数: initialized (bool)
    engine_status_changed = Signal(bool)

    # 性能告警信号
    # 参数: warning_type (str), message (str), metrics (dict)
    performance_warning = Signal(str, str, object)

    # -------------------------------------------------------------------------
    # 类属性（子类必须重写）
    # -------------------------------------------------------------------------

    ENGINE_TYPE: str = "base"  # 引擎类型标识
    ENGINE_NAME: str = "Base OCR Engine"  # 引擎显示名称
    ENGINE_VERSION: str = "1.0.0"  # 引擎版本

    # 支持的图片格式
    SUPPORTED_IMAGE_FORMATS: List[str] = ["jpg", "jpeg", "png", "bmp", "tiff", "webp"]

    # 是否支持批量识别
    SUPPORTS_BATCH: bool = True

    # 是否支持 GPU
    SUPPORTS_GPU: bool = False

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, config: Dict[str, Any]):
        """
        初始化引擎

        Args:
            config: 引擎配置字典
        """
        super().__init__()

        # 配置
        self.config = config.copy() if config else {}

        # 状态标志
        self._initialized: bool = False
        self._engine_instance: Any = None

        # 线程安全锁（引擎级锁）
        self._lock = threading.RLock()

        # 性能监控
        self._metrics = EnginePerformanceMetrics()

        # 取消标志（队列层取消方案）
        self._cancel_event = threading.Event()

        # 告警阈值配置
        self._warning_thresholds = {
            "max_duration": 5.0,  # 单次识别最大耗时（秒）
            "min_success_rate": 0.9,  # 最低成功率
            "max_failure_rate": 0.1,  # 最高失败率
        }

    # -------------------------------------------------------------------------
    # 抽象方法（子类必须实现）
    # -------------------------------------------------------------------------

    @abstractmethod
    def _do_initialize(self) -> bool:
        """
        执行实际的引擎初始化（子类实现）

        Returns:
            bool: 初始化是否成功
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查引擎是否可用

        用于引擎管理器在初始化前检查引擎是否可以正常使用。
        检查项包括：
        - 依赖库是否已安装
        - 模型文件是否存在
        - 硬件要求是否满足（如GPU）

        Returns:
            bool: 引擎是否可用
        """
        pass

    @abstractmethod
    def _do_recognize(self, image: Image.Image, **kwargs) -> OCRResult:
        """
        执行实际的 OCR 识别（子类实现）

        Args:
            image: PIL Image 对象
            **kwargs: 额外的识别参数

        Returns:
            OCRResult: 识别结果
        """
        pass

    @abstractmethod
    def _do_cleanup(self) -> None:
        """
        执行实际的资源清理（子类实现）

        释放引擎占用的资源，如卸载模型、关闭连接等。
        """
        pass

    # -------------------------------------------------------------------------
    # 配置 Schema
    # -------------------------------------------------------------------------

    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        获取配置项定义（用于 UI 动态生成）

        Returns:
            Dict[str, Any]: JSON Schema 格式的配置定义

        示例:
            {
                "type": "object",
                "properties": {
                    "lang": {
                        "type": "string",
                        "title": "语言",
                        "default": "ch",
                        "enum": ["ch", "en", "fr"]
                    },
                    "use_gpu": {
                        "type": "boolean",
                        "title": "使用 GPU",
                        "default": False
                    }
                }
            }
        """
        pass

    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """
        获取默认配置

        Returns:
            Dict[str, Any]: 默认配置字典
        """
        return {}

    # -------------------------------------------------------------------------
    # 引擎管理
    # -------------------------------------------------------------------------

    def initialize(self) -> bool:
        """
        初始化引擎

        Returns:
            bool: 初始化是否成功
        """
        with self._lock:
            if self._initialized:
                return True

            try:
                # 执行子类的初始化逻辑
                success = self._do_initialize()

                if success:
                    self._initialized = True
                    self.engine_status_changed.emit(True)
                    return True
                else:
                    return False

            except Exception:
                self.engine_status_changed.emit(False)
                return False

    def stop(self) -> None:
        """
        停止引擎，释放资源
        """
        with self._lock:
            if not self._initialized:
                return

            try:
                self._do_cleanup()
            except Exception:
                pass  # 忽略清理错误
            finally:
                self._engine_instance = None
                self._initialized = False
                self.engine_status_changed.emit(False)

    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._initialized

    @property
    def engine_type(self) -> str:
        """引擎类型标识"""
        return self.ENGINE_TYPE

    @property
    def engine_name(self) -> str:
        """引擎显示名称"""
        return self.ENGINE_NAME

    @property
    def engine_version(self) -> str:
        """引擎版本"""
        return self.ENGINE_VERSION

    # -------------------------------------------------------------------------
    # 识别接口
    # -------------------------------------------------------------------------

    def recognize(
        self,
        image: Union[str, bytes, Image.Image],
        task_id: Optional[str] = None,
        **kwargs,
    ) -> OCRResult:
        """
        执行 OCR 识别

        Args:
            image: 图像数据（路径、字节流或 PIL Image 对象）
            task_id: 任务 ID（用于进度通知）
            **kwargs: 额外的识别参数

        Returns:
            OCRResult: 识别结果
        """
        # 生成任务 ID（如果未提供）
        if task_id is None:
            task_id = f"task_{int(time.time() * 1000)}"

        # 检查初始化状态
        if not self._initialized:
            return OCRResult(
                success=False,
                error_code=OCRErrorCode.NOT_INITIALIZED.value,
                error_message="引擎未初始化，请先调用 initialize() 方法",
                engine_type=self.ENGINE_TYPE,
                engine_name=self.ENGINE_NAME,
            )

        # 检查取消标志（队列层取消方案）
        if self._cancel_event.is_set():
            self._cancel_event.clear()  # 清除取消标志
            return OCRResult(
                success=False,
                error_code=OCRErrorCode.OPERATION_CANCELLED.value,
                error_message="操作已取消",
                engine_type=self.ENGINE_TYPE,
                engine_name=self.ENGINE_NAME,
            )

        # 加载图像
        try:
            pil_image = self._load_image(image)
        except Exception as e:
            self.recognition_failed.emit(
                task_id,
                OCRErrorCode.IMAGE_FORMAT_UNSUPPORTED.value,
                f"图像加载失败: {str(e)}",
                self.ENGINE_NAME,
            )
            return OCRResult(
                success=False,
                error_code=OCRErrorCode.IMAGE_FORMAT_UNSUPPORTED.value,
                error_message=f"图像加载失败: {str(e)}",
                engine_type=self.ENGINE_TYPE,
                engine_name=self.ENGINE_NAME,
            )

        # 发送识别开始信号
        self.recognition_started.emit(task_id)

        # 执行识别（带性能监控）
        start_time = time.time()
        try:
            result = self._do_recognize(pil_image, **kwargs)
            duration = time.time() - start_time

            # 更新结果元数据
            result.duration = duration
            result.engine_type = self.ENGINE_TYPE
            result.engine_name = self.ENGINE_NAME
            result.engine_version = self.ENGINE_VERSION

            # 记录成功指标
            self._metrics.update_success(duration)

            # 检查性能告警
            self._check_performance_warnings(duration, success=True)

            # 发送识别完成信号
            self.recognition_completed.emit(task_id, result)

            return result

        except Exception as e:
            duration = time.time() - start_time

            # 记录失败指标
            self._metrics.update_failure(duration)

            # 检查性能告警
            self._check_performance_warnings(duration, success=False)

            # 发送识别失败信号
            error_code = OCRErrorCode.RECOGNITION_FAILED.value
            error_message = str(e)

            self.recognition_failed.emit(
                task_id, error_code, error_message, self.ENGINE_NAME
            )

            return OCRResult(
                success=False,
                error_code=error_code,
                error_message=error_message,
                engine_type=self.ENGINE_TYPE,
                engine_name=self.ENGINE_NAME,
                duration=duration,
            )

    # -------------------------------------------------------------------------
    # 图像加载
    # -------------------------------------------------------------------------

    def _load_image(
        self, image: Union[str, bytes, Image.Image, BytesIO]
    ) -> Image.Image:
        """
        加载图像为 PIL Image 对象

        Args:
            image: 图像数据（路径、字节流、BytesIO 或 PIL Image 对象）

        Returns:
            Image.Image: PIL Image 对象

        Raises:
            ValueError: 不支持的图像类型
            FileNotFoundError: 图像文件不存在
        """
        if isinstance(image, Image.Image):
            # 已经是 PIL Image 对象
            return image

        elif isinstance(image, str):
            # 文件路径
            if not Path(image).exists():
                raise FileNotFoundError(f"图像文件不存在: {image}")

            return Image.open(image)

        elif isinstance(image, bytes):
            # 字节流
            return Image.open(BytesIO(image))

        elif isinstance(image, BytesIO):
            # BytesIO 对象
            return Image.open(image)

        elif isinstance(image, dict) and "base64" in image:
            # Base64 编码
            image_bytes = base64.b64decode(image["base64"])
            return Image.open(BytesIO(image_bytes))

        else:
            raise ValueError(f"不支持的图像类型: {type(image)}")

    # -------------------------------------------------------------------------
    # 取消处理（队列层取消方案）
    # -------------------------------------------------------------------------

    def cancel(self) -> None:
        """
        取消当前操作（队列层取消）

        注意：此方法只能在任务队列层调用，用于取消等待中的任务。
        正在执行的 OCR 任务无法中途中断。
        """
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        """
        检查是否已取消

        Returns:
            bool: 是否已取消
        """
        return self._cancel_event.is_set()

    # -------------------------------------------------------------------------
    # 性能监控
    # -------------------------------------------------------------------------

    def get_metrics(self) -> EnginePerformanceMetrics:
        """
        获取性能指标

        Returns:
            EnginePerformanceMetrics: 性能指标对象
        """
        with self._lock:
            # 深拷贝指标，避免外部修改
            from dataclasses import replace

            return replace(self._metrics)

    def reset_metrics(self) -> None:
        """重置性能指标"""
        with self._lock:
            self._metrics = EnginePerformanceMetrics()

    def _check_performance_warnings(self, duration: float, success: bool) -> None:
        """
        检查性能告警

        Args:
            duration: 本次调用耗时（秒）
            success: 是否成功
        """
        warnings = []

        # 检查耗时告警
        if duration > self._warning_thresholds["max_duration"]:
            warnings.append(f"识别耗时过长: {duration:.2f}秒")

        # 检查成功率告警（只在失败时检查）
        if not success:
            success_rate = self._metrics.get_success_rate()
            if (
                success_rate < self._warning_thresholds["min_success_rate"]
                and self._metrics.total_calls > 10
            ):
                warnings.append(f"成功率过低: {success_rate:.1%}")

        # 发送告警
        for warning in warnings:
            self.performance_warning.emit(
                "performance", warning, self._metrics.to_dict()
            )

    def set_warning_threshold(self, key: str, value: float) -> None:
        """
        设置告警阈值

        Args:
            key: 阈值键名（max_duration, min_success_rate, max_failure_rate）
            value: 阈值
        """
        if key in self._warning_thresholds:
            self._warning_thresholds[key] = value

    # -------------------------------------------------------------------------
    # 进度通知
    # -------------------------------------------------------------------------

    def emit_progress(self, task_id: str, current: int, total: int) -> None:
        """
        发送进度通知

        Args:
            task_id: 任务 ID
            current: 当前进度
            total: 总数
        """
        if total > 0:
            percentage = (current / total) * 100
        else:
            percentage = 0.0

        self.progress_updated.emit(task_id, current, total, percentage)

    # -------------------------------------------------------------------------
    # 错误传播
    # -------------------------------------------------------------------------

    def _propagate_error(
        self,
        error_code: OCRErrorCode,
        error_message: str,
        task_id: Optional[str] = None,
    ) -> None:
        """
        传播错误信息

        Args:
            error_code: 错误码
            error_message: 错误信息
            task_id: 任务 ID（可选）
        """
        if task_id is None:
            task_id = "unknown"

        self.recognition_failed.emit(
            task_id, error_code.value, error_message, self.ENGINE_NAME
        )

    # -------------------------------------------------------------------------
    # 工具方法
    # -------------------------------------------------------------------------

    def validate_config(self) -> List[str]:
        """
        验证配置有效性

        Returns:
            List[str]: 错误信息列表（空表示无错误）
        """
        errors = []

        schema = self.get_config_schema()

        # 简单验证配置是否包含必需的字段
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in self.config:
                errors.append(f"缺少必需的配置项: {field}")

        return errors

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            Any: 配置值
        """
        return self.config.get(key, default)

    def set_config_value(self, key: str, value: Any) -> None:
        """
        设置配置值

        Args:
            key: 配置键
            value: 配置值
        """
        self.config[key] = value


# =============================================================================
# 批量识别支持
# =============================================================================


class BatchOCREngine(BaseOCREngine):
    """
    批量 OCR 引擎基类

    支持批量图片识别的 OCR 引擎。
    """

    def recognize_batch(
        self,
        images: List[Union[str, bytes, Image.Image]],
        task_id: Optional[str] = None,
        **kwargs,
    ) -> List[OCRResult]:
        """
        批量识别

        Args:
            images: 图像列表
            task_id: 任务 ID
            **kwargs: 额外的识别参数

        Returns:
            List[OCRResult]: 识别结果列表
        """
        results = []

        for i, image in enumerate(images):
            # 发送进度通知
            self.emit_progress(task_id or "batch", i + 1, len(images))

            # 执行识别
            result = self.recognize(image, task_id, **kwargs)
            results.append(result)

            # 检查是否取消
            if self.is_cancelled():
                break

        return results

    def recognize_batch_to_file(
        self,
        image_paths: List[str],
        output_path: str,
        task_id: Optional[str] = None,
        output_format: str = "json",
        **kwargs,
    ) -> bool:
        """
        批量识别并保存到文件

        Args:
            image_paths: 图片路径列表
            output_path: 输出文件路径
            task_id: 任务 ID
            output_format: 输出格式（json/csv/txt）
            **kwargs: 额外的识别参数

        Returns:
            bool: 是否成功
        """
        # 执行批量识别
        results = self.recognize_batch(image_paths, task_id, **kwargs)

        # 保存结果
        try:
            if output_format == "json":
                # 合并为批量结果
                from .ocr_result import BatchOCRResult

                batch_result = BatchOCRResult(results=results)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(batch_result.to_json())
            elif output_format == "csv":
                # 保存为 CSV（每张图片一个文件）
                base_path = Path(output_path)
                base_path.mkdir(parents=True, exist_ok=True)
                for i, result in enumerate(results, 1):
                    csv_path = base_path / f"result_{i}.csv"
                    with open(csv_path, "w", encoding="utf-8") as f:
                        f.write(result.to_csv())
            else:
                # 其他格式
                pass

            return True

        except Exception:
            return False
