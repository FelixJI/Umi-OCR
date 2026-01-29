#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 云 OCR 引擎基类

定义云 OCR 引擎的统一接口，支持百度、腾讯、阿里云等服务。

主要功能:
- 继承 BaseOCREngine，提供统一的 OCR 引擎接口
- HTTP 请求封装（支持异步）
- 图片 Base64 编码
- 指数退避重试机制
- 降级链管理
- 请求队列（QPS 控制）
- 统一错误码处理

Author: Umi-OCR Team
Date: 2026-01-27
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum
import threading
import asyncio
from io import BytesIO
import logging
from ..base_engine import BaseOCREngine, OCRErrorCode, OCRResult
from ..ocr_result import TextBlock, BoundingBox, TextBlockType
from ...utils.image_preprocessing import ImagePreprocessor, DocumentQualityAnalyzer

logger = logging.getLogger(__name__)

# =============================================================================
# 云 OCR 识别类型枚举
# =============================================================================


class CloudOCRType(Enum):
    """
    云 OCR 识别类型（全量支持）

    支持多种专业识别场景，如通用文字、身份证、银行卡、发票等。
    """

    GENERAL = "general"  # 通用文字识别
    GENERAL_ACCURATE = "accurate"  # 高精度版
    IDCARD = "idcard"  # 身份证
    BANK_CARD = "bank_card"  # 银行卡
    BUSINESS_LICENSE = "license"  # 营业执照
    INVOICE = "invoice"  # 发票
    TRAIN_TICKET = "train_ticket"  # 火车票
    TABLE = "table"  # 表格
    FORMULA = "formula"  # 公式
    HANDWRITING = "handwriting"  # 手写体


@dataclass
class CloudOCRResult:
    """
    云 OCR 统一返回格式（双层结构）

    基础字段：所有云厂商统一
    extra：厂商特有数据

    设计理念：在保证统一接口的同时，保留各云服务商的特有功能。
    """

    text: str  # 识别文本
    confidence: float  # 置信度 (0.0 ~ 1.0)
    location: Optional[List[int]] = None  # 坐标 [x, y, width, height]
    extra: Dict[str, Any] = None  # 厂商特有数据

    # extra 示例:
    # - 百度: {"words_result_num": 10, "direction": 0}
    # - 腾讯: {"ItemPolygon": {...}, "DetectedText": "..."}
    # - 阿里: {"prob": 0.99, "charInfo": [...]}


# =============================================================================
# 云 OCR 引擎基类
# =============================================================================


class BaseCloudEngine(BaseOCREngine, ABC):
    """
    云 OCR 引擎基类

    职责:
    - HTTP 请求封装（异步）
    - 图片 Base64 编码
    - 指数退避重试
    - 降级链管理
    - 请求队列（QPS 控制）

    子类需要实现:
    - _get_credentials(): 获取凭证
    - _build_request(): 构建请求
    - _parse_response(): 解析响应
    """

    # -------------------------------------------------------------------------
    # 重试配置
    # -------------------------------------------------------------------------

    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAYS = [1, 2, 4]  # 指数退避：1s, 2s, 4s
    REQUEST_TIMEOUT = 30  # 请求超时（秒）

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, config: Dict[str, Any], qps_limit: int = 10):
        """
        初始化云引擎

        Args:
            config: 引擎配置
            qps_limit: 每秒最大请求数（QPS限制）
        """
        super().__init__(config)

        # 请求队列（QPS控制）
        from .request_queue import RequestQueue

        self._request_queue = RequestQueue(qps_limit)

        # 降级链（备用引擎列表）
        self._fallback_engines: List["BaseCloudEngine"] = []

        # HTTP 会话（requests/aiohttp）
        self._session = None
        self._session_lock = threading.Lock()

        # 认证信息缓存
        self._credentials_cache: Optional[Dict[str, str]] = None
        self._credentials_cache_time: float = 0.0
        self._credentials_cache_ttl = 3600  # 凭证缓存1小时

    # -------------------------------------------------------------------------
    # 抽象方法（子类必须实现）
    # -------------------------------------------------------------------------

    @abstractmethod
    def _get_credentials(self) -> Dict[str, str]:
        """
        从凭证管理器获取 API 密钥

        Returns:
            Dict[str, str]: 凭证字典
                           百度: {'api_key': '...', 'secret_key': '...'}
                           腾讯: {'secret_id': '...', 'secret_key': '...'}
                           阿里: {'access_key_id': '...', 'access_key_secret': '...'}
        """
        pass

    @abstractmethod
    def _build_request(self, image_data: bytes, ocr_type: CloudOCRType) -> Dict:
        """
        构建 HTTP 请求（各厂商不同）

        Args:
            image_data: 图片字节数据
            ocr_type: OCR识别类型

        Returns:
            Dict: 请求配置，包含:
                - url: API URL
                - method: HTTP 方法
                - headers: 请求头
                - data: 请求体
        """
        pass

    @abstractmethod
    def _parse_response(
        self, response: Dict, ocr_type: CloudOCRType
    ) -> List[CloudOCRResult]:
        """
        解析云厂商响应为统一格式

        Args:
            response: 云厂商原始响应
            ocr_type: OCR识别类型

        Returns:
            List[CloudOCRResult]: 统一格式的识别结果列表
        """
        pass

    # -------------------------------------------------------------------------
    # BaseOCREngine 抽象方法实现
    # -------------------------------------------------------------------------

    def _preprocess_image(self, image) -> Any:
        """
        云OCR本地预处理（使用通用预处理器，不包含PaddleOCR相关处理）

        Args:
            image: PIL Image 对象

        Returns:
            Any: 处理后的图像
        """
        # 检查是否启用本地预处理
        if not self.config.get("enable_local_preprocess", False):
            return image

        # 获取预处理配置
        preprocess_config = self.config.get("preprocessing", {})
        if not preprocess_config.get("enabled", False):
            return image

        try:
            # 创建通用预处理器
            preprocessor = ImagePreprocessor(preprocess_config)

            # 执行预处理
            processed_image = preprocessor.process(image)

            # 记录预处理信息
            logger.debug(f"云OCR本地预处理完成")

            return processed_image

        except Exception as e:
            logger.error(f"云OCR本地预处理失败: {e}", exc_info=True)
            # 预处理失败时返回原图
            return image

    def _do_initialize(self) -> bool:
        """
        执行云引擎初始化

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 1. 检查凭证
            self._validate_credentials()

            # 2. 初始化 HTTP 会话
            self._init_session()

            # 3. 测试连接
            success = self._test_connection()

            if success:
                self._initialized = True
                self.engine_status_changed.emit(True)
                logger.info(f"{self.ENGINE_NAME} 初始化成功")
                return True
            else:
                logger.error(f"{self.ENGINE_NAME} 连接测试失败")
                return False

        except Exception as e:
            logger.error(f"{self.ENGINE_NAME} 初始化失败: {e}", exc_info=True)
            return False

    def _do_cleanup(self) -> None:
        """清理云引擎资源"""
        with self._session_lock:
            if self._session:
                self._session.close()
                self._session = None

        self._initialized = False
        self.engine_status_changed.emit(False)

    def is_available(self) -> bool:
        """
        检查云引擎是否可用

        Returns:
            bool: 引擎是否可用
        """
        # 检查凭证
        try:
            creds = self._get_credentials()
            if not creds:
                return False

            # 检查必要字段
            required_keys = self._get_required_credential_keys()
            for key in required_keys:
                if key not in creds or not creds[key]:
                    return False

            # 检查网络连接（可选，避免启动时阻塞）
            # 这里仅检查凭证有效性，不实际发起网络请求
            return True

        except Exception:
            return False

    def _do_recognize(self, image, **kwargs) -> OCRResult:
        """
        执行云 OCR 识别

        Args:
            image: PIL Image 对象
            **kwargs: 额外的识别参数，支持:
                - ocr_type: CloudOCRType（默认 GENERAL）
                - language: 语言代码
                - detect_direction: 是否检测方向

        Returns:
            OCRResult: 识别结果
        """
        # 解析参数
        ocr_type = kwargs.get("ocr_type", CloudOCRType.GENERAL)

        # 1. 本地预处理（如果启用）
        processed_image = self._preprocess_image(image)

        # 2. 编码图片为 Base64
        try:
            image_bytes = self._image_to_bytes(processed_image)
            image_base64 = self._encode_image(image_bytes)
        except Exception as e:
            return OCRResult(
                success=False,
                error_code=OCRErrorCode.IMAGE_FORMAT_UNSUPPORTED.value,
                error_message=f"图片编码失败: {str(e)}",
                engine_type=self.ENGINE_TYPE,
                engine_name=self.ENGINE_NAME,
            )

        # 通过请求队列发送（QPS控制 + 重试）
        try:
            response = self._send_request_with_retry(image_base64, ocr_type)
        except Exception as e:
            logger.error(f"云引擎请求失败: {e}", exc_info=True)

            # 尝试降级引擎
            if self._fallback_engines:
                return self._try_fallback_engines(image, ocr_type, **kwargs)
            else:
                return OCRResult(
                    success=False,
                    error_code=OCRErrorCode.NETWORK_ERROR.value,
                    error_message=f"云 OCR 失败: {str(e)}",
                    engine_type=self.ENGINE_TYPE,
                    engine_name=self.ENGINE_NAME,
                )

        # 解析响应
        try:
            cloud_results = self._parse_response(response, ocr_type)
            return self._convert_to_ocr_result(cloud_results, response)
        except Exception as e:
            logger.error(f"响应解析失败: {e}", exc_info=True)
            return OCRResult(
                success=False,
                error_code=OCRErrorCode.RECOGNITION_FAILED.value,
                error_message=f"响应解析失败: {str(e)}",
                engine_type=self.ENGINE_TYPE,
                engine_name=self.ENGINE_NAME,
            )

    # -------------------------------------------------------------------------
    # 辅助方法
    # -------------------------------------------------------------------------

    def _validate_credentials(self) -> None:
        """验证凭证配置"""
        creds = self._get_credentials()
        required_keys = self._get_required_credential_keys()

        for key in required_keys:
            if key not in creds or not creds[key]:
                raise ValueError(f"缺少必要凭证: {key}")

    def _get_required_credential_keys(self) -> List[str]:
        """
        获取必需的凭证键（子类可重写）

        Returns:
            List[str]: 必需凭证键列表
        """
        return []

    def _init_session(self) -> None:
        """初始化 HTTP 会话"""
        import requests

        self._session = requests.Session()
        self._session.headers.update({"User-Agent": f"Umi-OCR/{self.ENGINE_VERSION}"})

    def _test_connection(self) -> bool:
        """
        测试连接（子类可重写）

        Returns:
            bool: 连接测试是否成功
        """
        # 默认实现：通过发送一个最小请求测试
        # 子类可以重写为更精确的连接测试
        return True

    def _image_to_bytes(self, image) -> bytes:
        """
        将图片转换为字节数据

        Args:
            image: PIL Image 对象

        Returns:
            bytes: 图片字节数据
        """
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="PNG")
        return img_byte_arr.getvalue()

    def _encode_image(self, image_bytes: bytes) -> str:
        """
        图片转 Base64

        Args:
            image_bytes: 图片字节数据

        Returns:
            str: Base64 编码字符串
        """
        import base64

        return base64.b64encode(image_bytes).decode("utf-8")

    async def _send_request_with_retry(
        self, image_base64: str, ocr_type: CloudOCRType
    ) -> Dict:
        """
        带重试的请求发送（异步）

        失败时按 RETRY_DELAYS 指数退避
        全部失败后尝试降级链

        Args:
            image_base64: Base64 编码的图片
            ocr_type: OCR 识别类型

        Returns:
            Dict: 云厂商响应

        Raises:
            Exception: 所有重试失败后抛出异常
        """
        # 构建请求
        request_config = self._build_request(image_base64, ocr_type)

        last_exception = None

        for attempt, delay in enumerate(self.RETRY_DELAYS, start=1):
            try:
                # 通过请求队列发送（QPS控制）
                async def send():
                    return await self._request_queue.enqueue(
                        lambda: self._execute_request(request_config)
                    )

                response = await send()

                # 检查响应
                if response.get("success"):
                    return response

                # 云厂商返回错误
                error_code = response.get("error_code", "")
                if self._is_auth_error(error_code):
                    # 认证错误，清除凭证缓存
                    self._clear_credentials_cache()
                    raise Exception(f"认证失败: {error_code}")
                elif self._is_quota_error(error_code):
                    # 配额超限，直接返回
                    return response

            except Exception as e:
                last_exception = e
                logger.warning(f"请求失败（第 {attempt} 次尝试）: {e}")

                # 等待指数退避时间
                await asyncio.sleep(delay)

        # 所有重试失败
        raise last_exception or Exception("请求失败，已达最大重试次数")

    def _execute_request(self, request_config: Dict) -> Dict:
        """
        执行实际的 HTTP 请求（同步）

        Args:
            request_config: 请求配置

        Returns:
            Dict: 响应数据
        """
        import requests

        with self._session_lock:
            response = requests.request(
                method=request_config.get("method", "POST"),
                url=request_config["url"],
                headers=request_config.get("headers", {}),
                data=request_config.get("data"),
                timeout=self.REQUEST_TIMEOUT,
            )

        # 解析响应
        result = {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "data": response.json() if response.content else {},
        }

        if not result["success"]:
            result["error_code"] = str(response.status_code)
            result["error_message"] = response.text or f"HTTP {response.status_code}"

        return result

    def _is_auth_error(self, error_code: str) -> bool:
        """
        判断是否为认证错误（子类可重写）

        Args:
            error_code: 错误码

        Returns:
            bool: 是否为认证错误
        """
        return False

    def _is_quota_error(self, error_code: str) -> bool:
        """
        判断是否为配额超限错误（子类可重写）

        Args:
            error_code: 错误码

        Returns:
            bool: 是否为配额超限
        """
        return False

    def _clear_credentials_cache(self) -> None:
        """清除凭证缓存"""
        self._credentials_cache = None
        self._credentials_cache_time = 0.0

    def _convert_to_ocr_result(
        self, cloud_results: List[CloudOCRResult], raw_response: Dict
    ) -> OCRResult:
        """
        转换 CloudOCRResult 为 OCRResult

        Args:
            cloud_results: 云厂商统一格式结果
            raw_response: 原始响应（用于存储到 extra）

        Returns:
            OCRResult: 统一格式的 OCR 结果
        """
        # 构建 TextBlock 列表
        text_blocks = []
        full_text_lines = []

        for i, cloud_result in enumerate(cloud_results, 1):
            # 构建边界框
            bbox = None
            if cloud_result.location:
                # location 格式: [x, y, width, height]
                bbox = BoundingBox(
                    points=[
                        [cloud_result.location[0], cloud_result.location[1]],
                        [
                            cloud_result.location[0] + cloud_result.location[2],
                            cloud_result.location[1],
                        ],
                        [
                            cloud_result.location[0] + cloud_result.location[2],
                            cloud_result.location[1] + cloud_result.location[3],
                        ],
                        [
                            cloud_result.location[0],
                            cloud_result.location[1] + cloud_result.location[3],
                        ],
                    ]
                )

            # 构建 TextBlock
            text_block = TextBlock(
                text=cloud_result.text,
                confidence=cloud_result.confidence,
                bbox=bbox,
                block_type=TextBlockType.PARAGRAPH,
            )
            text_blocks.append(text_block)
            full_text_lines.append(cloud_result.text)

        # 合并完整文本
        full_text = "\n".join(full_text_lines)

        # 构建结果
        return OCRResult(
            text_blocks=text_blocks,
            full_text=full_text,
            success=True,
            engine_type=self.ENGINE_TYPE,
            engine_name=self.ENGINE_NAME,
            engine_version=self.ENGINE_VERSION,
            extra={
                "raw_response": raw_response,
                "cloud_results": [r.__dict__ for r in cloud_results],
            },
        )

    def _try_fallback_engines(
        self, image, ocr_type: CloudOCRType, **kwargs
    ) -> OCRResult:
        """
        尝试降级引擎

        Args:
            image: PIL Image 对象
            ocr_type: OCR 识别类型
            **kwargs: 额外参数

        Returns:
            OCRResult: 降级引擎识别结果
        """
        for fallback_engine in self._fallback_engines:
            logger.info(f"尝试降级引擎: {fallback_engine.ENGINE_NAME}")

            try:
                # 直接调用降级引擎的识别方法
                result = fallback_engine._do_recognize(
                    image, ocr_type=ocr_type, **kwargs
                )

                if result.success:
                    logger.info(f"降级引擎 {fallback_engine.ENGINE_NAME} 识别成功")
                    # 标记为降级结果
                    result.extra["fallback_from"] = self.ENGINE_TYPE
                    result.extra["fallback_to"] = fallback_engine.ENGINE_TYPE
                    return result

            except Exception as e:
                logger.warning(f"降级引擎 {fallback_engine.ENGINE_NAME} 也失败: {e}")
                continue

        # 所有降级引擎都失败
        return OCRResult(
            success=False,
            error_code=OCRErrorCode.RECOGNITION_FAILED.value,
            error_message="所有云引擎（包括降级）均失败",
            engine_type=self.ENGINE_TYPE,
            engine_name=self.ENGINE_NAME,
        )

    def set_fallback_chain(self, engines: List["BaseCloudEngine"]) -> None:
        """
        设置降级链

        Args:
            engines: 降级引擎列表（如：百度 → 腾讯 → 本地）
        """
        self._fallback_engines = engines
        logger.info(
            f"{self.ENGINE_NAME} 降级链已设置: {[e.ENGINE_NAME for e in engines]}"
        )


# =============================================================================
# 日志记录器
# =============================================================================
