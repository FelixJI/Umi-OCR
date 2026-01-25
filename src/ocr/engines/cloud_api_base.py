# ===============================================
# =============== 云API引擎基类 ===============
# ===============================================

"""
云厂商OCR API引擎基类
提供统一的云API调用框架，支持：
- 百度智能云OCR
- 腾讯云OCR
- 阿里云OCR
"""

import base64
import json
import logging
import time
import hashlib
import hmac
from abc import abstractmethod
from typing import Dict, Any, Union, List, Optional
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError
from PIL import Image
from io import BytesIO

from .base import BaseOCREngine

logger = logging.getLogger(__name__)


class CloudAPIEngine(BaseOCREngine):
    """
    云API OCR引擎基类
    
    提供通用的云API调用框架，子类实现具体厂商的API对接。
    """
    
    ENGINE_TYPE = "cloud_api"
    ENGINE_NAME = "Cloud API Engine"
    REQUIRES_API_KEY = True
    
    # API类型
    API_TYPES = {
        "general": "通用文字识别",
        "accurate": "高精度识别",
        "table": "表格识别",
        "invoice": "发票识别",
        "vat_invoice": "增值税发票",
        "receipt": "票据识别",
        "idcard": "身份证识别",
        "business_card": "名片识别",
        "handwriting": "手写识别",
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.secret_key = config.get("secret_key", "")
        self.api_type = config.get("api_type", "general")
        self._access_token = None
        self._token_expire_time = 0
    
    def validate_api_key(self) -> bool:
        """验证API Key是否配置"""
        return bool(self.api_key and len(self.api_key) > 5)
    
    @abstractmethod
    def _get_api_url(self, api_type: str) -> str:
        """获取API URL（子类实现）"""
        pass
    
    @abstractmethod
    def _build_request_body(self, image_base64: str, api_type: str) -> Dict:
        """构建请求体（子类实现）"""
        pass
    
    @abstractmethod
    def _parse_response(self, response: Dict, api_type: str) -> Dict[str, Any]:
        """解析响应结果（子类实现）"""
        pass
    
    def _do_recognize(self, image: Union[str, bytes, Image.Image], **kwargs) -> Dict[str, Any]:
        """执行云API识别"""
        api_type = kwargs.get("api_type", self.api_type)
        
        if not self.validate_api_key():
            return {
                "code": 907,
                "data": "[Error] API Key未配置。请在设置中配置API Key。"
            }
        
        try:
            # 准备图像Base64
            image_base64 = self._prepare_image_base64(image)
            
            # 调用API
            response = self._call_api(image_base64, api_type)
            
            # 解析结果
            return self._parse_response(response, api_type)
            
        except Exception as e:
            logger.error(f"云API调用失败: {e}", exc_info=True)
            return {"code": 908, "data": f"[Error] API调用失败: {e}"}
    
    def _prepare_image_base64(self, image: Union[str, bytes, Image.Image]) -> str:
        """准备图像的Base64编码"""
        if isinstance(image, str):
            # 文件路径
            with open(image, "rb") as f:
                image_bytes = f.read()
        elif isinstance(image, bytes):
            image_bytes = image
        elif isinstance(image, Image.Image):
            buffer = BytesIO()
            img_format = image.format or "PNG"
            image.save(buffer, format=img_format)
            image_bytes = buffer.getvalue()
        else:
            raise ValueError(f"不支持的图像类型: {type(image)}")
        
        return base64.b64encode(image_bytes).decode("utf-8")
    
    def _call_api(self, image_base64: str, api_type: str) -> Dict:
        """调用API"""
        url = self._get_api_url(api_type)
        body = self._build_request_body(image_base64, api_type)
        headers = self._get_headers(api_type)
        
        # 发送请求
        if isinstance(body, dict):
            data = urlencode(body).encode("utf-8")
        else:
            data = body.encode("utf-8") if isinstance(body, str) else body
        
        request = Request(url, data=data, headers=headers, method="POST")
        
        try:
            with urlopen(request, timeout=30) as response:
                result = response.read().decode("utf-8")
                return json.loads(result)
        except HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error(f"HTTP错误 {e.code}: {error_body}")
            raise Exception(f"HTTP错误 {e.code}: {error_body}")
        except URLError as e:
            logger.error(f"URL错误: {e.reason}")
            raise Exception(f"网络错误: {e.reason}")
    
    def _get_headers(self, api_type: str) -> Dict[str, str]:
        """获取请求头（可被子类重写）"""
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
    
    def initialize(self) -> bool:
        """初始化引擎"""
        self._initialized = True
        logger.info(f"{self.ENGINE_NAME} 初始化成功")
        return True
    
    @classmethod
    def get_api_types(cls) -> Dict[str, str]:
        """获取支持的API类型"""
        return cls.API_TYPES
