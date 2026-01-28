#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 百度云 OCR 引擎

集成百度云 OCR API，支持 OAuth 2.0 认证和自动 Token 刷新。

主要功能:
- OAuth 2.0 Token 获取和自动刷新
- 完整的 OCR 识别类型支持
- 请求重试和错误处理
- 与 BaseCloudEngine 完全集成

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import Dict, Any, List, Optional
import requests
import time

from .base_cloud import BaseCloudEngine, CloudOCRType, CloudOCRResult
from ...utils.credential_manager import CredentialManager

# =============================================================================
# 百度 OCR 引擎配置
# =============================================================================


class BaiduOCREngine(BaseCloudEngine):
    """
    百度云 OCR 引擎

    认证方式: OAuth 2.0
    特点: Token 有效期 30 天，需自动刷新

    支持的识别类型:
    - 通用文字识别 (general)
    - 高精度版 (accurate)
    - 身份证 (idcard)
    - 银行卡 (bank_card)
    - 营业执照 (license)
    - 发票 (invoice)
    - 火车票 (train_ticket)
    - 表格 (table)
    - 公式 (formula)
    - 手写体 (handwriting)
    """

    # -------------------------------------------------------------------------
    # 引擎配置
    # -------------------------------------------------------------------------

    ENGINE_TYPE = "baidu_cloud"
    ENGINE_NAME = "百度云 OCR"
    ENGINE_VERSION = "1.0.0"

    # API 配置
    API_BASE = "https://aip.baidubce.com"
    TOKEN_URL = f"{API_BASE}/oauth/2.0/token"

    # 各识别类型对应的 API 端点
    API_ENDPOINTS = {
        CloudOCRType.GENERAL: f"{API_BASE}/rest/2.0/ocr/v1/general_basic",
        CloudOCRType.GENERAL_ACCURATE: f"{API_BASE}/rest/2.0/ocr/v1/accurate_basic",
        CloudOCRType.IDCARD: f"{API_BASE}/rest/2.0/ocr/v1/idcard",
        CloudOCRType.BANK_CARD: f"{API_BASE}/rest/2.0/ocr/v1/bankcard",
        CloudOCRType.BUSINESS_LICENSE: f"{API_BASE}/rest/2.0/ocr/v1/business_license",
        CloudOCRType.INVOICE: f"{API_BASE}/rest/2.0/ocr/v1/vat_invoice",
        CloudOCRType.TRAIN_TICKET: f"{API_BASE}/rest/2.0/ocr/v1/train_ticket",
        CloudOCRType.TABLE: f"{API_BASE}/rest/2.0/ocr/v1/table",
        CloudOCRType.FORMULA: f"{API_BASE}/rest/2.0/ocr/v1/formula",
        CloudOCRType.HANDWRITING: f"{API_BASE}/rest/2.0/ocr/v1/handwriting",
    }

    # Token 有效期（秒）- 设置为29天避免边界问题
    TOKEN_TTL = 29 * 24 * 3600

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, config: Dict[str, Any], qps_limit: int = 10):
        """
        初始化百度云 OCR 引擎

        Args:
            config: 引擎配置
            qps_limit: 每秒最大请求数
        """
        super().__init__(config, qps_limit)

        # Token 相关
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

        # HTTP 会话
        self._http_session: Optional[requests.Session] = None

    # -------------------------------------------------------------------------
    # BaseCloudEngine 抽象方法实现
    # -------------------------------------------------------------------------

    def _get_required_credential_keys(self) -> List[str]:
        """
        获取必需的凭证键

        Returns:
            List[str]: ['api_key', 'secret_key']
        """
        return ["api_key", "secret_key"]

    def _init_session(self) -> None:
        """初始化 HTTP 会话"""
        self._http_session = requests.Session()
        self._http_session.headers.update(
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": f"Umi-OCR/{self.ENGINE_VERSION}",
            }
        )

    def _test_connection(self) -> bool:
        """
        测试连接

        通过获取 Token 测试凭证有效性

        Returns:
            bool: 连接测试是否成功
        """
        try:
            token = self._get_access_token()
            return token is not None
        except Exception as e:
            logging.error(f"百度云连接测试失败: {e}")
            return False

    def _get_credentials(self) -> Dict[str, str]:
        """
        从凭证管理器获取 API 密钥

        Returns:
            Dict[str, str]: {'api_key': '...', 'secret_key': '...'}
        """
        # 从 CredentialManager 加载凭证
        cred_manager = CredentialManager()
        credentials = cred_manager.load("baidu")

        if not credentials:
            raise ValueError(
                "百度云 OCR 凭证未配置，请在设置中添加 API Key 和 Secret Key"
            )

        # 验证凭证格式
        if "api_key" not in credentials or "secret_key" not in credentials:
            raise ValueError("百度云 OCR 凭证格式错误，需要 api_key 和 secret_key")

        return {
            "api_key": credentials["api_key"],
            "secret_key": credentials["secret_key"],
        }

    def _build_request(self, image_data: str, ocr_type: CloudOCRType) -> Dict[str, Any]:
        """
        构建百度 OCR 请求

        Args:
            image_data: Base64 编码的图片字符串
            ocr_type: OCR 识别类型

        Returns:
            Dict: 请求配置
                - url: API URL（含 Token）
                - method: HTTP 方法
                - headers: 请求头
                - data: 请求体
        """
        # 获取 Access Token
        self._get_access_token()

        # 获取 API 端点
        url = self.API_ENDPOINTS.get(ocr_type)
        if not url:
            raise ValueError(f"不支持的 OCR 类型: {ocr_type}")

        # 构建请求体
        data = {"image": image_data}

        # 可选参数（可根据配置添加）
        if self.config.get("detect_direction", False):
            data["detect_direction"] = "true"
        if self.config.get("detect_language", False):
            data["detect_language"] = "true"

        # 构建请求头（已包含 Content-Type）
        headers = self._http_session.headers.copy()

        return {"url": url, "method": "POST", "headers": headers, "data": data}

    def _parse_response(
        self, response: Dict, ocr_type: CloudOCRType
    ) -> List[CloudOCRResult]:
        """
        解析百度响应为统一格式

        Args:
            response: 百度云原始响应
            ocr_type: OCR 识别类型

        Returns:
            List[CloudOCRResult]: 统一格式的识别结果列表
        """
        # 百度响应格式:
        # {
        #   "words_result": [
        #     {
        #       "words": "识别的文本",
        #       "location": {"top": 10, "left": 20, "width": 100, "height": 50}
        #     }
        #   ],
        #   "words_result_num": 10
        # }

        error_code = response.get("error_code")

        if error_code:
            # 百度错误码处理
            error_map = {
                1: "用户或密码错误",
                2: "认证失败",
                3: "Token 不存在",
                4: "Token 无效",
                5: "Token 过期",
                17: "每日请求量超限额",
                18: "QPS 超限额",
                19: "请求总量超限额",
                100: "无效参数",
                110: "Access Token 不存在",
                111: "Access Token 过期",
                216015: "图片格式错误",
                216100: "非法参数",
                216101: "图片超限",
                216102: "OCR 失败",
                216200: "系统错误",
                216201: "系统错误",
                216202: "系统错误",
                216203: "系统错误",
                216500: "未知错误",
            }

            error_msg_cn = error_map.get(error_code, f"错误码 {error_code}")
            raise Exception(f"百度云 OCR 错误: {error_msg_cn} ({error_code})")

        # 解析识别结果
        words_result = response.get("words_result", [])

        if not words_result:
            # 无识别结果，返回空结果
            return [
                CloudOCRResult(text="", confidence=0.0, location=None, extra=response)
            ]

        # 转换为统一格式
        results = []
        for item in words_result:
            text = item.get("words", "")
            location = item.get("location", {})

            # 提取坐标和置信度
            # 百度的置信度在 extra 中（某些接口）
            confidence = 0.0

            # 构建位置信息 [x, y, width, height]
            coords = None
            if location:
                x = location.get("left", 0)
                y = location.get("top", 0)
                width = location.get("width", 0)
                height = location.get("height", 0)
                coords = [x, y, width, height]

            results.append(
                CloudOCRResult(
                    text=text,
                    confidence=confidence,
                    location=coords,
                    extra={"provider": "baidu", "raw_location": location},
                )
            )

        return results

    def _is_auth_error(self, error_code: str) -> bool:
        """
        判断是否为认证错误

        Args:
            error_code: 错误码

        Returns:
            bool: 是否为认证错误
        """
        # 百度认证错误码：1-5
        auth_errors = ["1", "2", "3", "4", "5", "110", "111"]
        return error_code in auth_errors

    def _is_quota_error(self, error_code: str) -> bool:
        """
        判断是否为配额超限错误

        Args:
            error_code: 错误码

        Returns:
            bool: 是否为配额超限
        """
        # 百度配额错误码：17-19
        quota_errors = ["17", "18", "19"]
        return error_code in quota_errors

    # -------------------------------------------------------------------------
    # OAuth 2.0 Token 管理
    # -------------------------------------------------------------------------

    def _get_access_token(self) -> str:
        """
        获取百度云 API 访问令牌

        自动处理 Token 获取和刷新。

        Returns:
            str: 有效的 access_token

        Raises:
            Exception: Token 获取失败
        """
        # 检查缓存 Token 是否有效
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        # 获取新 Token
        credentials = self._get_credentials()
        api_key = credentials["api_key"]
        secret_key = credentials["secret_key"]

        logging.info("百度云 Token 即将过期或不存在，正在刷新...")

        params = {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": secret_key,
        }

        try:
            response = requests.post(self.TOKEN_URL, data=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if "access_token" not in data:
                raise Exception(f"Token 响应格式错误: {data}")

            self._access_token = data["access_token"]

            # 设置过期时间（29天后）
            self._token_expires_at = time.time() + self.TOKEN_TTL

            # 获取 Token 有效期（如果有）
            expires_in = data.get("expires_in", self.TOKEN_TTL)
            logging.info(f"百度云 Token 刷新成功，有效期: {expires_in} 秒")

            return self._access_token

        except requests.exceptions.RequestException as e:
            logging.error(f"百度云 Token 获取失败: {e}")
            raise Exception(f"无法获取百度云 Token: {str(e)}")

    def _clear_token_cache(self) -> None:
        """清除 Token 缓存"""
        self._access_token = None
        self._token_expires_at = 0.0

    # -------------------------------------------------------------------------
    # 清理
    # -------------------------------------------------------------------------

    def _do_cleanup(self) -> None:
        """清理百度云 OCR 引擎资源"""
        if self._http_session:
            self._http_session.close()
            self._http_session = None

        self._clear_token_cache()


# =============================================================================
# 日志记录器
# =============================================================================

logger = logging.getLogger(__name__)
