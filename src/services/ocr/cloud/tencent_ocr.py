#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 腾讯云 OCR 引擎

集成腾讯云 OCR API，支持 TC3-HMAC-SHA256 签名算法。

主要功能:
- TC3-HMAC-SHA256 签名算法实现
- 完整的 OCR 识别类型支持
- 与 BaseCloudEngine 完全集成

Author: Umi-OCR Team
Date: 2026-01-27
"""

import hashlib
import hmac
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import requests

from .base_cloud import BaseCloudEngine, CloudOCRType, CloudOCRResult
from ...utils.credential_manager import CredentialManager

# 默认区域
REGION = "ap-guangzhou"

# =============================================================================
# 腾讯云签名算法
# =============================================================================


class TencentCloudSignature:
    """
    腾讯云 TC3-HMAC-SHA256 签名算法

    官方文档: https://cloud.tencent.com/document/product/866
    """

    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        service: str = "ocr",
        region: str = "ap-guangzhou",
    ):
        """
        初始化签名器

        Args:
            secret_id: 密钥 ID
            secret_key: 密钥
            service: 服务名（默认 'ocr'）
            region: 区域（默认 'ap-guangzhou'）
        """
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.service = service
        self.region = region

    @staticmethod
    def sha256_hex(data: str) -> str:
        """计算字符串的 SHA256 哈希值（十六进制）"""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def hmac_sha256(key: bytes, data: str) -> bytes:
        """计算 HMAC-SHA256 签名"""
        return hmac.new(key, data.encode("utf-8"), hashlib.sha256).digest()

    def _get_signing_key(self, date: str) -> bytes:
        """
        生成签名密钥链

        步骤:
        1. 生成日期密钥
        2. 生成日期-区域密钥
        3. 生成日期-服务密钥
        4. 生成签名密钥

        Args:
            date: 日期（格式: YYYY-MM-DD）

        Returns:
            bytes: 最终签名密钥
        """
        # 步骤1: 生成日期密钥
        secret_date = self.hmac_sha256(f"TC3{self.secret_key}".encode("utf-8"), date)

        # 步骤2: 生成日期-区域密钥
        secret_region = self.hmac_sha256(secret_date, self.region)

        # 步骤3: 生成日期-服务密钥
        secret_service = self.hmac_sha256(secret_region, self.service)

        # 步骤4: 生成签名密钥
        secret_signing = self.hmac_sha256(secret_service, "tc3_request")

        return secret_signing

    def build_authorization_header(
        self, method: str, endpoint: str, action: str, version: str, payload: str
    ) -> Dict[str, str]:
        """
        构建Authorization头和请求头

        Args:
            method: HTTP方法（GET/POST）
            endpoint: 服务端点（如 'ocr.tencentcloudapi.com'）
            action: API动作名（如 'GeneralBasicOCR'）
            version: API版本（如 '2018-11-19'）
            payload: 请求体内容

        Returns:
            Dict: 请求头字典
        """
        # 获取当前时间戳
        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp())
        date = now.strftime("%Y-%m-%d")

        # 步骤1: 构造规范请求
        algorithm = "TC3-HMAC-SHA256"
        canonical_uri = "/"
        canonical_querystring = ""

        # 规范头（必须包含: content-type, host, x-tc-action）
        canonical_headers = (
            f"content-type:application/json; charset=utf-8\n"
            f"host:{endpoint}\n"
            f"x-tc-action:{action.lower()}\n"
        )

        signed_headers = "content-type;host;x-tc-action"

        # 请求体的SHA256哈希
        payload_hash = self.sha256_hex(payload)

        # 拼接规范请求串
        canonical_request = "\n".join(
            [
                method,
                canonical_uri,
                canonical_querystring,
                canonical_headers,
                signed_headers,
                payload_hash,
            ]
        )

        # 步骤2: 创建待签名字符串
        credential_scope = f"{date}/{self.service}/tc3_request"

        hashed_canonical_request = self.sha256_hex(canonical_request)

        string_to_sign = "\n".join(
            [algorithm, str(timestamp), credential_scope, hashed_canonical_request]
        )

        # 步骤3: 计算签名
        signing_key = self._get_signing_key(date)
        signature = self.hmac_sha256(signing_key, string_to_sign).hexdigest()

        # 步骤4: 拼接Authorization头
        authorization = (
            f"{algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        # 构建完整请求头
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": endpoint,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": version,
            "X-TC-Region": self.region,
        }

        return headers


# =============================================================================
# 腾讯云 OCR 引擎
# =============================================================================


class TencentOCREngine(BaseCloudEngine):
    """
    腾讯云 OCR 引擎

    认证方式: TC3-HMAC-SHA256 签名算法
    特点: 每次请求都需要计算签名，无需 Token 刷新
    """

    # -------------------------------------------------------------------------
    # 引擎配置
    # -------------------------------------------------------------------------

    ENGINE_TYPE = "tencent_cloud"
    ENGINE_NAME = "腾讯云 OCR"
    ENGINE_VERSION = "1.0.0"

    # API 配置
    API_HOST = "ocr.tencentcloudapi.com"
    SERVICE = "ocr"
    REGION = "ap-guangzhou"  # 可配置
    API_VERSION = "2018-11-19"

    # 各识别类型对应的 Action
    ACTIONS = {
        CloudOCRType.GENERAL: "GeneralBasicOCR",
        CloudOCRType.GENERAL_ACCURATE: "GeneralAccurateOCR",
        CloudOCRType.IDCARD: "IDCardOCR",
        CloudOCRType.BANK_CARD: "BankCardOCR",
        CloudOCRType.BUSINESS_LICENSE: "BizLicenseOCR",
        CloudOCRType.INVOICE: "VatInvoiceOCR",
        CloudOCRType.TRAIN_TICKET: "TrainTicketOCR",
        CloudOCRType.TABLE: "TableOCR",
        CloudOCRType.FORMULA: "FormulaOCR",
        CloudOCRType.HANDWRITING: "GeneralHandwritingOCR",
    }

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, config: Dict[str, Any], qps_limit: int = 10):
        """
        初始化腾讯云 OCR 引擎

        Args:
            config: 引擎配置
            qps_limit: 每秒最大请求数（QPS限制）
        """
        super().__init__(config, qps_limit)

        # 从配置读取区域
        self._region = config.get("region", REGION)

        # HTTP 会话
        self._http_session: Optional[requests.Session] = None
        self._signature: Optional[TencentCloudSignature] = None

    # -------------------------------------------------------------------------
    # BaseCloudEngine 抽象方法实现
    # -------------------------------------------------------------------------

    def _get_required_credential_keys(self) -> List[str]:
        """
        获取必需的凭证键

        Returns:
            List[str]: ['secret_id', 'secret_key']
        """
        return ["secret_id", "secret_key"]

    def _init_session(self) -> None:
        """初始化 HTTP 会话"""
        self._http_session = requests.Session()
        self._http_session.headers.update(
            {
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "User-Agent": f"Umi-OCR/{self.ENGINE_VERSION}",
            }
        )

    def _test_connection(self) -> bool:
        """
        测试连接

        通过发送一个最小请求测试凭证有效性

        Returns:
            bool: 连接测试是否成功
        """
        try:
            # 获取凭证
            credentials = self._get_credentials()

            # 初始化签名器
            self._signature = TencentCloudSignature(
                secret_id=credentials["secret_id"],
                secret_key=credentials["secret_key"],
                service="ocr",
                region=self._region,
            )

            # 构建一个最小测试请求
            payload = json.dumps({"Url": "https://example.com/test.jpg"})

            # 生成签名
            headers = self._signature.build_authorization_header(
                method="POST",
                endpoint=self.API_HOST,
                action="GeneralBasicOCR",
                version=self.API_VERSION,
                payload=payload,
            )

            # 发送测试请求（即使失败也能验证签名是否正确）
            url = f"https://{self.API_HOST}"
            response = self._http_session.post(
                url, headers=headers, data=payload, timeout=10
            )

            # 检查是否为认证错误（签名错误通常是 401）
            if response.status_code == 401:
                logging.warning("腾讯云连接测试失败：签名错误或凭证无效")
                return False
            elif response.status_code >= 500:
                logging.warning(
                    f"腾讯云连接测试失败：服务器错误 {response.status_code}"
                )
                return False
            else:
                return True

        except Exception as e:
            logging.error(f"腾讯云连接测试异常: {e}")
            return False

    def _get_credentials(self) -> Dict[str, str]:
        """
        从凭证管理器获取 API 密钥

        Returns:
            Dict[str, str]: {'secret_id': '...', 'secret_key': '...'}
        """
        # 从 CredentialManager 加载凭证
        cred_manager = CredentialManager()
        credentials = cred_manager.load("tencent")

        if not credentials:
            raise ValueError(
                "腾讯云 OCR 凭证未配置，请在设置中添加 SecretId 和 SecretKey"
            )

        # 验证凭证格式
        if "secret_id" not in credentials or "secret_key" not in credentials:
            raise ValueError("腾讯云 OCR 凭证格式错误，需要 secret_id 和 secret_key")

        return {
            "secret_id": credentials["secret_id"],
            "secret_key": credentials["secret_key"],
        }

    def _build_request(self, image_data: str, ocr_type: CloudOCRType) -> Dict[str, Any]:
        """
        构建腾讯云 OCR 请求

        Args:
            image_data: Base64 编码的图片字符串
            ocr_type: OCR 识别类型

        Returns:
            Dict: 请求配置
                - url: API URL
                - method: HTTP 方法
                - headers: 请求头
                - data: 请求体
        """
        # 获取 Action
        action = self.ACTIONS.get(ocr_type)
        if not action:
            raise ValueError(f"不支持的 OCR 类型: {ocr_type}")

        # 构建请求体
        payload = json.dumps({"ImageBase64": image_data})

        # 生成签名和请求头
        headers = self._signature.build_authorization_header(
            method="POST",
            endpoint=self.API_HOST,
            action=action,
            version=self.API_VERSION,
            payload=payload,
        )

        # 构建完整 URL
        url = f"https://{self.API_HOST}/{action}"

        return {"url": url, "method": "POST", "headers": headers, "data": payload}

    def _parse_response(
        self, response: Dict, ocr_type: CloudOCRType
    ) -> List[CloudOCRResult]:
        """
        解析腾讯云响应为统一格式

        腾讯云响应格式:
        {
            "Response": {
                "TextDetections": [
                    {
                        "DetectedText": "识别的文本",
                        "Polygon": [...]  # 多边形坐标
                        "Confidence": 90,     # 置信度
                        "ItemPoly": ...      # 项多边形
                    }
                ],
                "RequestId": "..."
            },
            "Error": {
                "Code": "...",
                "Message": "..."
            }
        }

        Args:
            response: 腾讯云原始响应
            ocr_type: OCR 识别类型

        Returns:
            List[CloudOCRResult]: 统一格式的识别结果列表
        """
        # 检查是否有错误
        if "Error" in response:
            error = response["Error"]
            error_code = error.get("Code", "")
            error_msg = error.get("Message", f"错误码 {error_code}")

            # 腾讯云错误码处理
            if error_code == "AuthFailure":
                raise Exception(f"认证失败: {error_msg}")
            elif error_code == "InvalidParameter":
                raise Exception(f"参数错误: {error_msg}")
            else:
                raise Exception(f"腾讯云 OCR 错误: {error_msg} ({error_code})")

        # 解析识别结果
        response_data = response.get("Response", {})
        text_detections = response_data.get("TextDetections", [])

        if not text_detections:
            # 无识别结果，返回空结果
            return [
                CloudOCRResult(text="", confidence=0.0, location=None, extra=response)
            ]

        # 转换为统一格式
        results = []
        for item in text_detections:
            text = item.get("DetectedText", "")
            confidence = item.get("Confidence", 0.0) / 100.0  # 转换为 0-1

            # 提取坐标（腾讯云使用 Polygon）
            polygon = item.get("Polygon", {})
            location = None

            if polygon:
                # Polygon 格式: {'X': x, 'Y': y}
                # 需要提取四个顶点：左上、右上、右下、左下
                coords = []
                points = polygon.get("Points", [])
                if points:
                    # 转换为列表格式 [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    coords = [[p.get("X", 0), p.get("Y", 0)] for p in points[:4]]

                    if len(coords) == 4:
                        # 计算边界框
                        x_coords = [c[0] for c in coords]
                        y_coords = [c[1] for c in coords]
                        x = int(min(x_coords))
                        y = int(min(y_coords))
                        width = int(max(x_coords) - x)
                        height = int(max(y_coords) - y)
                        location = [x, y, width, height]

            results.append(
                CloudOCRResult(
                    text=text,
                    confidence=confidence,
                    location=location,
                    extra={"provider": "tencent", "raw_polygon": polygon},
                )
            )

        return results

    def _is_auth_error(self, error_code: str) -> bool:
        """
        判断是否为认证错误

        腾讯云认证错误通常返回 401 或 AuthFailure

        Args:
            error_code: 错误码

        Returns:
            bool: 是否为认证错误
        """
        return error_code == "AuthFailure"

    def _is_quota_error(self, error_code: str) -> bool:
        """
        判断是否为配额超限错误

        腾讯云配额超限错误码

        Args:
            error_code: 错误码

        Returns:
            bool: 是否为配额超限
        """
        quota_errors = [
            "RequestLimitExceeded",  # 请求频率超限
            "RequestSizeLimitExceeded",  # 请求大小超限
        ]
        return error_code in quota_errors

    # -------------------------------------------------------------------------
    # 清理
    # -------------------------------------------------------------------------

    def _do_cleanup(self) -> None:
        """清理腾讯云 OCR 引擎资源"""
        if self._http_session:
            self._http_session.close()
            self._http_session = None

        self._signature = None


# =============================================================================
# 日志记录器
# =============================================================================

logger = logging.getLogger(__name__)
