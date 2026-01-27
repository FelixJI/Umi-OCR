#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 阿里云 OCR 引擎

集成阿里云 OCR API，支持 AccessKey 签名机制。

主要功能:
- V3 签名算法实现（ACS3-HMAC-SHA256）
- 完整的 OCR 识别类型支持
- 与 BaseCloudEngine 完全集成

Author: Umi-OCR Team
Date: 2026-01-27
"""

import hashlib
import hmac
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from urllib.parse import quote
import uuid
import json
import requests

from .base_cloud import BaseCloudEngine, CloudOCRType, CloudOCRResult
from ...utils.credential_manager import CredentialManager


# =============================================================================
# 阿里云 V3 签名算法
# =============================================================================

class AliyunV3Signature:
    """
    阿里云 V3 签名算法（ACS3-HMAC-SHA256）

    官方文档: https://help.aliyun.com/zh/sdk/product-overview/v3-request-structure-and-signature
    """

    def __init__(self, access_key_id: str, access_key_secret: str):
        """
        初始化签名器

        Args:
            access_key_id: 访问密钥 ID
            access_key_secret: 访问密钥
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret

    @staticmethod
    def percent_encode(value: str) -> str:
        """
        URL 编码（符合阿里云规范的编码方式）

        规则：
        - A-Z, a-z, 0-9, -, _, ., ~ 不编码
        - 其他字符编码为 %XY 格式
        - 空格编码为 %20（不是+）

        Args:
            value: 要编码的字符串

        Returns:
            str: 编码后的字符串
        """
        if value is None:
            return ""

        result = quote(str(value), safe='-_.~')
        # 替换特殊字符以符合阿里云规范
        result = result.replace('+', '%20').replace('*', '%2A').replace('%7E', '~')
        return result

    @staticmethod
    def sha256_hex(data: str) -> str:
        """计算 SHA256 哈希值（十六进制）"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    @staticmethod
    def hmac_sha256(key: str, data: str) -> str:
        """计算 HMAC-SHA256 签名"""
        return hmac.new(
            key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def build_authorization_header(
        self,
        method: str,
        endpoint: str,
        action: str,
        version: str,
        params: Dict[str, str] = None
    ) -> Dict[str, str]:
        """
        构建Authorization头和请求头（V3签名）

        Args:
            method: HTTP方法
            endpoint: 服务端点（如 'ocr-api.cn-hangzhou.aliyuncs.com'）
            action: API动作（如 'RecognizeAllText'）
            version: API版本（如 '2021-07-07'）
            params: 查询参数（可选）

        Returns:
            Dict: 请求头字典
        """
        # 获取当前时间（UTC时间）
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        date = now.strftime("%Y-%m-%d")

        # 生成随机数
        signature_nonce = str(uuid.uuid4())

        # 请求体的SHA256哈希（空body为该值）
        content_sha256 = self.sha256_hex("")

        # 构建规范头
        canonical_headers = (
            f"host:{endpoint}\n"
            f"x-acs-action:{action}\n"
            f"x-acs-content-sha256:{content_sha256}\n"
            f"x-acs-date:{timestamp}\n"
            f"x-acs-signature-nonce:{signature_nonce}\n"
            f"x-acs-version:{version}"
        )

        # 已签名头列表
        signed_headers = (
            "host;x-acs-action;x-acs-content-sha256;x-acs-date;x-acs-signature-nonce;x-acs-version"
        )

        # 构造规范请求字符串
        canonicalized_resource = "/" + self.percent_encode(action)

        # 处理查询参数
        canonicalized_query_string = ""
        if params:
            # 参数按字典序排序
            sorted_params = sorted(params.items())
            encoded_params = [
                f"{self.percent_encode(k)}={self.percent_encode(v)}"
                for k, v in sorted_params
            ]
            canonicalized_query_string = "&".join(encoded_params)

        # 拼接规范请求字符串
        canonical_request = "\n".join([
            method.upper(),
            canonicalized_resource,
            canonicalized_query_string,
            canonical_headers,
            signed_headers,
            content_sha256
        ])

        # 计算签名
        # 签名字符串: AccessKeySecret + "&"
        string_to_sign = "\n".join([
            "ACS3-HMAC-SHA256",
            timestamp,
            self.sha256_hex(canonical_request)
        ])

        signing_key = self.access_key_secret + "&"
        signature = self.hmac_sha256(signing_key, string_to_sign)

        # 拼接Authorization头
        authorization = (
            f"ACS3-HMAC-SHA256 "
            f"Credential={self.access_key_id}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        # 构建请求头
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": endpoint,
            "x-acs-action": action,
            "x-acs-content-sha256": content_sha256,
            "x-acs-date": timestamp,
            "x-acs-signature-nonce": signature_nonce,
            "x-acs-version": version,
            "Accept": "application/json",
            "User-Agent": "Umi-OCR/1.0.0"
        }

        return headers


# =============================================================================
# 阿里云 OCR 引擎
# =============================================================================

class AliyunOCREngine(BaseCloudEngine):
    """
    阿里云 OCR 引擎

    认证方式: AccessKey 签名（V3算法）
    特点: 每次请求都需要计算签名，无需 Token 刷新
    """

    # -------------------------------------------------------------------------
    # 引擎配置
    # -------------------------------------------------------------------------

    ENGINE_TYPE = "aliyun_cloud"
    ENGINE_NAME = "阿里云 OCR"
    ENGINE_VERSION = "1.0.0"

    # API 配置
    API_HOST = "ocr-api.cn-hangzhou.aliyuncs.com"
    API_VERSION = "2021-07-07"
    REGION = "cn-hangzhou"

    # 各识别类型对应的 Action
    ACTIONS = {
        CloudOCRType.GENERAL: "RecognizeAllText",
        CloudOCRType.GENERAL_ACCURATE: "RecognizeAdvanced",
        CloudOCRType.IDCARD: "RecognizeIdcard",
        CloudOCRType.BANK_CARD: "RecognizeBankCard",
        CloudOCRType.BUSINESS_LICENSE: "RecognizeBusinessLicense",
        CloudOCRType.INVOICE: "RecognizeInvoice",
        CloudOCRType.TRAIN_TICKET: "RecognizeTrainTicket",
        CloudOCRType.TABLE: "RecognizeTable",
        CloudOCRType.FORMULA: "RecognizeFormula",
        CloudOCRType.HANDWRITING: "RecognizeHandwriting",
    }

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, config: Dict[str, Any], qps_limit: int = 10):
        """
        初始化阿里云 OCR 引擎

        Args:
            config: 引擎配置
            qps_limit: 每秒最大请求数（QPS限制）
        """
        super().__init__(config, qps_limit)

        # HTTP 会话
        self._http_session: Optional[requests.Session] = None
        self._signature: Optional[AliyunV3Signature] = None

    # -------------------------------------------------------------------------
    # BaseCloudEngine 抽象方法实现
    # -------------------------------------------------------------------------

    def _get_required_credential_keys(self) -> List[str]:
        """
        获取必需的凭证键

        Returns:
            List[str]: ['access_key_id', 'access_key_secret']
        """
        return ['access_key_id', 'access_key_secret']

    def _init_session(self) -> None:
        """初始化 HTTP 会话"""
        self._http_session = requests.Session()
        self._http_session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': f'Umi-OCR/{self.ENGINE_VERSION}'
        })

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
            self._signature = AliyunV3Signature(
                access_key_id=credentials['access_key_id'],
                access_key_secret=credentials['access_key_secret']
            )

            # 构建一个最小测试请求
            payload = json.dumps({"Url": "https://example.com/test.jpg"})

            # 生成签名
            headers = self._signature.build_authorization_header(
                method='POST',
                endpoint=self.API_HOST,
                action='RecognizeAllText',
                version=self.API_VERSION
            )

            # 发送测试请求（即使失败也能验证签名是否正确）
            url = f"https://{self.API_HOST}/{self.ACTIONS[CloudOCRType.GENERAL]}"
            response = self._http_session.post(url, headers=headers, data=payload, timeout=10)

            # 检查是否为认证错误（阿里云签名错误通常是 403）
            if response.status_code == 403:
                logging.warning("阿里云连接测试失败：签名错误或凭证无效")
                return False
            elif response.status_code >= 500:
                logging.warning(f"阿里云连接测试失败：服务器错误 {response.status_code}")
                return False
            else:
                return True

        except Exception as e:
            logging.error(f"阿里云连接测试异常: {e}")
            return False

    def _get_credentials(self) -> Dict[str, str]:
        """
        从凭证管理器获取 API 密钥

        Returns:
            Dict[str, str]: {'access_key_id': '...', 'access_key_secret': '...'}
        """
        # 从 CredentialManager 加载凭证
        cred_manager = CredentialManager()
        credentials = cred_manager.load('aliyun')

        if not credentials:
            raise ValueError("阿里云 OCR 凭证未配置，请在设置中添加 AccessKeyId 和 AccessKeySecret")

        # 验证凭证格式
        if 'access_key_id' not in credentials or 'access_key_secret' not in credentials:
            raise ValueError("阿里云 OCR 凭证格式错误，需要 access_key_id 和 access_key_secret")

        return {
            'access_key_id': credentials['access_key_id'],
            'access_key_secret': credentials['access_key_secret']
        }

    def _build_request(self, image_data: str, ocr_type: CloudOCRType) -> Dict[str, Any]:
        """
        构建阿里云 OCR 请求

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
        payload = json.dumps({
            "Image": image_data
        })

        # 生成签名和请求头
        headers = self._signature.build_authorization_header(
            method='POST',
            endpoint=self.API_HOST,
            action=action,
            version=self.API_VERSION
        )

        # 构建完整 URL
        url = f"https://{self.API_HOST}/{action}"

        return {
            'url': url,
            'method': 'POST',
            'headers': headers,
            'data': payload
        }

    def _parse_response(self, response: Dict, ocr_type: CloudOCRType) -> List[CloudOCRResult]:
        """
        解析阿里云响应为统一格式

        阿里云响应格式:
        {
            "Data": {
                "Content": "识别的文本",
                "WordsInfos": [...]  # 词级别信息（包含坐标、置信度）
            },
            "RequestId": "..."
        }

        Args:
            response: 阿里云原始响应
            ocr_type: OCR 识别类型

        Returns:
            List[CloudOCRResult]: 统一格式的识别结果列表
        """
        # 检查是否有错误
        if 'Code' in response:
            error_code = response.get('Code', '')
            error_msg = response.get('Message', f"错误码 {error_code}")

            # 阿里云错误码处理
            if error_code == 'InvalidParameter':
                raise Exception(f"参数错误: {error_msg}")
            elif error_code == 'AuthFailure':
                raise Exception(f"认证失败: {error_msg}")
            else:
                raise Exception(f"阿里云 OCR 错误: {error_msg} ({error_code})")

        # 解析识别结果
        data = response.get('Data', {})
        words_infos = data.get('WordsInfos', [])
        content = data.get('Content', '')

        # 阿里云的WordsInfos格式：
        # [{
        #   "Index": 0,
        #   "Content": "文本内容",
        #   "Score": 99.5,  # 置信度
        #   "WordRectangle": {"Left": x, "Top": y, "Width": w, "Height": h}
        # }]

        if not words_infos and not content:
            # 无识别结果，返回空结果
            return [CloudOCRResult(
                text='',
                confidence=0.0,
                location=None,
                extra=response
            )]

        # 如果有Content（通用识别结果），按换行符分割
        if content:
            texts = content.split('\n')
            results = []
            for i, text in enumerate(texts):
                if text.strip():
                    results.append(CloudOCRResult(
                        text=text.strip(),
                        confidence=0.95,  # 默认置信度
                        location=None,
                        extra={'provider': 'aliyun', 'line_index': i}
                    ))

            return results

        # 如果有WordsInfos（词级别详细结果）
        if words_infos:
            results = []
            for word_info in words_infos:
                text = word_info.get('Content', '')
                confidence = word_info.get('Score', 0.0) / 100.0  # 转换为 0-1
                rect = word_info.get('WordRectangle', {})

                location = None
                if rect:
                    # 阿里云坐标：Top=左上, Left=左上
                    left = int(rect.get('Left', 0))
                    top = int(rect.get('Top', 0))
                    width = int(rect.get('Width', 0))
                    height = int(rect.get('Height', 0))
                    location = [left, top, width, height]

                results.append(CloudOCRResult(
                    text=text,
                    confidence=confidence,
                    location=location,
                    extra={
                        'provider': 'aliyun',
                        'index': word_info.get('Index', 0),
                        'raw_rect': rect
                    }
                ))

            return results

        # 默认返回空结果
        return [CloudOCRResult(
            text='',
            confidence=0.0,
            location=None,
            extra=response
        )]

    def _is_auth_error(self, error_code: str) -> bool:
        """
        判断是否为认证错误

        阿里云认证错误通常返回 403 或 AuthFailure

        Args:
            error_code: 错误码

        Returns:
            bool: 是否为认证错误
        """
        auth_errors = [
            'AuthFailure',
            'InvalidAccessKeyId',
            'InvalidAccessKeySecret'
        ]
        return error_code in auth_errors

    def _is_quota_error(self, error_code: str) -> bool:
        """
        判断是否为配额超限错误

        阿里云配额超限错误码

        Args:
            error_code: 错误码

        Returns:
            bool: 是否为配额超限
        """
        quota_errors = [
            'QuotaExceeded',
            'ServiceUnavailable'
        ]
        return error_code in quota_errors

    # -------------------------------------------------------------------------
    # 清理
    # -------------------------------------------------------------------------

    def _do_cleanup(self) -> None:
        """清理阿里云 OCR 引擎资源"""
        if self._http_session:
            self._http_session.close()
            self._http_session = None

        self._signature = None


# =============================================================================
# 日志记录器
# =============================================================================

logger = logging.getLogger(__name__)
