# ===============================================
# =============== 腾讯云OCR引擎 ===============
# ===============================================

"""
腾讯云OCR API引擎
支持功能：
- 通用文字识别
- 高精度文字识别
- 表格识别
- 增值税发票识别
- 票据识别
- 身份证识别
- 名片识别
"""

import json
import time
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Dict, Any, Union
from urllib.request import Request, urlopen

from .cloud_api_base import CloudAPIEngine

logger = logging.getLogger(__name__)


class TencentOCREngine(CloudAPIEngine):
    """
    腾讯云OCR引擎
    
    API文档: https://cloud.tencent.com/document/product/866
    """
    
    ENGINE_TYPE = "tencent_ocr"
    ENGINE_NAME = "腾讯云OCR"
    SUPPORTED_FEATURES = [
        "general_ocr",
        "accurate_ocr",
        "table_recognition",
        "invoice_recognition",
        "vat_invoice",
        "idcard",
        "business_card",
    ]
    
    # API服务信息
    SERVICE = "ocr"
    HOST = "ocr.tencentcloudapi.com"
    ENDPOINT = f"https://{HOST}"
    REGION = "ap-guangzhou"
    VERSION = "2018-11-19"
    
    # Action映射
    ACTION_MAP = {
        "general": "GeneralBasicOCR",
        "accurate": "GeneralAccurateOCR",
        "general_efficient": "GeneralEfficientOCR",
        "general_fast": "GeneralFastOCR",
        "table": "TableOCR",
        "table_detect": "RecognizeTableOCR",
        "vat_invoice": "VatInvoiceOCR",
        "invoice": "MixedInvoiceOCR",
        "idcard": "IDCardOCR",
        "business_card": "BusinessCardOCR",
        "handwriting": "GeneralHandwritingOCR",
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.secret_id = config.get("api_key", "")  # SecretId
        self.secret_key = config.get("secret_key", "")  # SecretKey
        self.region = config.get("region", self.REGION)
    
    def _get_api_url(self, api_type: str) -> str:
        """获取API URL（腾讯云使用统一endpoint）"""
        return self.ENDPOINT
    
    def _sign(self, secret_key: str, date: str, service: str, string_to_sign: str) -> str:
        """计算腾讯云签名"""
        def _hmac_sha256(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
        
        secret_date = _hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)
        secret_service = _hmac_sha256(secret_date, service)
        secret_signing = _hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        return signature
    
    def _build_request_body(self, image_base64: str, api_type: str) -> str:
        """构建请求体"""
        body = {
            "ImageBase64": image_base64,
        }
        
        # 表格识别的额外参数
        if api_type in ["table", "table_detect"]:
            body["TableLanguage"] = "zh"  # 中文表格
        
        # 身份证识别的额外参数
        if api_type == "idcard":
            body["CardSide"] = self.config.get("idcard_side", "FRONT")
        
        return json.dumps(body)
    
    def _get_headers(self, api_type: str) -> Dict[str, str]:
        """获取腾讯云API请求头（含签名）"""
        action = self.ACTION_MAP.get(api_type, "GeneralBasicOCR")
        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        
        # 构建规范请求
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        ct = "application/json; charset=utf-8"
        
        # 请求体（用于签名）
        payload = self._build_request_body("", api_type)  # 临时空body用于计算
        
        canonical_headers = f"content-type:{ct}\nhost:{self.HOST}\nx-tc-action:{action.lower()}\n"
        signed_headers = "content-type;host;x-tc-action"
        hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        
        canonical_request = f"{http_request_method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{hashed_payload}"
        
        # 构建待签名字符串
        algorithm = "TC3-HMAC-SHA256"
        credential_scope = f"{date}/{self.SERVICE}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
        
        # 计算签名
        signature = self._sign(self.secret_key, date, self.SERVICE, string_to_sign)
        
        # 构建Authorization
        authorization = f"{algorithm} Credential={self.secret_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        return {
            "Content-Type": ct,
            "Host": self.HOST,
            "X-TC-Action": action,
            "X-TC-Version": self.VERSION,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": self.region,
            "Authorization": authorization,
        }
    
    def _call_api(self, image_base64: str, api_type: str) -> Dict:
        """调用腾讯云API"""
        url = self._get_api_url(api_type)
        
        # 重新构建带图像的请求体
        body_dict = {
            "ImageBase64": image_base64,
        }
        if api_type in ["table", "table_detect"]:
            body_dict["TableLanguage"] = "zh"
        if api_type == "idcard":
            body_dict["CardSide"] = self.config.get("idcard_side", "FRONT")
        
        body = json.dumps(body_dict)
        
        # 重新计算签名
        action = self.ACTION_MAP.get(api_type, "GeneralBasicOCR")
        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        
        ct = "application/json; charset=utf-8"
        canonical_headers = f"content-type:{ct}\nhost:{self.HOST}\nx-tc-action:{action.lower()}\n"
        signed_headers = "content-type;host;x-tc-action"
        hashed_payload = hashlib.sha256(body.encode("utf-8")).hexdigest()
        
        canonical_request = f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{hashed_payload}"
        
        algorithm = "TC3-HMAC-SHA256"
        credential_scope = f"{date}/{self.SERVICE}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
        
        signature = self._sign(self.secret_key, date, self.SERVICE, string_to_sign)
        authorization = f"{algorithm} Credential={self.secret_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        headers = {
            "Content-Type": ct,
            "Host": self.HOST,
            "X-TC-Action": action,
            "X-TC-Version": self.VERSION,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": self.region,
            "Authorization": authorization,
        }
        
        request = Request(url, data=body.encode("utf-8"), headers=headers, method="POST")
        
        with urlopen(request, timeout=30) as response:
            result = response.read().decode("utf-8")
            return json.loads(result)
    
    def _parse_response(self, response: Dict, api_type: str) -> Dict[str, Any]:
        """解析腾讯云API响应"""
        # 检查错误
        if "Response" not in response:
            return {"code": 909, "data": f"[Error] 响应格式错误: {response}"}
        
        resp = response["Response"]
        
        if "Error" in resp:
            error = resp["Error"]
            return {
                "code": 909,
                "data": f"[Error] 腾讯云API错误 {error.get('Code', '')}: {error.get('Message', '')}"
            }
        
        # 根据API类型解析结果
        if api_type in ["general", "accurate", "general_efficient", "general_fast"]:
            return self._parse_general_result(resp)
        elif api_type in ["table", "table_detect"]:
            return self._parse_table_result(resp)
        elif api_type == "vat_invoice":
            return self._parse_vat_invoice_result(resp)
        elif api_type == "invoice":
            return self._parse_invoice_result(resp)
        elif api_type == "idcard":
            return self._parse_idcard_result(resp)
        elif api_type == "business_card":
            return self._parse_business_card_result(resp)
        else:
            return self._parse_general_result(resp)
    
    def _parse_general_result(self, resp: Dict) -> Dict[str, Any]:
        """解析通用OCR结果"""
        text_detections = resp.get("TextDetections", [])
        
        if not text_detections:
            return {"code": 101, "data": ""}
        
        parsed_data = []
        for item in text_detections:
            text = item.get("DetectedText", "")
            confidence = item.get("Confidence", 100) / 100.0
            
            # 获取位置
            polygon = item.get("Polygon", [])
            if len(polygon) >= 4:
                box = [[p.get("X", 0), p.get("Y", 0)] for p in polygon[:4]]
            else:
                box = []
            
            parsed_data.append({
                "text": text,
                "score": confidence,
                "box": box,
                "end": "\n",
                "from": "tencent_ocr",
            })
        
        return {"code": 100, "data": parsed_data}
    
    def _parse_table_result(self, resp: Dict) -> Dict[str, Any]:
        """解析表格识别结果"""
        table_detections = resp.get("TableDetections", [])
        
        if not table_detections:
            # 尝试其他格式
            tables = resp.get("Tables", [])
            if tables:
                return {
                    "code": 100,
                    "data": {"tables": tables},
                    "format": "json",
                    "type": "table",
                }
            return {"code": 101, "data": ""}
        
        tables = []
        for table_det in table_detections:
            cells = table_det.get("Cells", [])
            table_data = {"cells": []}
            
            for cell in cells:
                table_data["cells"].append({
                    "row": cell.get("RowTl", 0),
                    "col": cell.get("ColTl", 0),
                    "text": cell.get("Text", ""),
                    "row_span": cell.get("RowBr", 0) - cell.get("RowTl", 0) + 1,
                    "col_span": cell.get("ColBr", 0) - cell.get("ColTl", 0) + 1,
                })
            
            tables.append(table_data)
        
        return {
            "code": 100,
            "data": {"tables": tables},
            "format": "json",
            "type": "table",
        }
    
    def _parse_vat_invoice_result(self, resp: Dict) -> Dict[str, Any]:
        """解析增值税发票结果"""
        info = resp.get("VatInvoiceInfos", [])
        
        invoice_data = {}
        for item in info:
            name = item.get("Name", "")
            value = item.get("Value", "")
            if name and value:
                invoice_data[name] = value
        
        if not invoice_data:
            return {"code": 101, "data": ""}
        
        return {
            "code": 100,
            "data": invoice_data,
            "format": "json",
            "type": "invoice",
        }
    
    def _parse_invoice_result(self, resp: Dict) -> Dict[str, Any]:
        """解析混合发票结果"""
        invoice_items = resp.get("MixedInvoiceItems", [])
        
        if not invoice_items:
            return {"code": 101, "data": ""}
        
        results = []
        for item in invoice_items:
            invoice_type = item.get("Type", "")
            single_invoice = item.get("SingleInvoiceInfos", {})
            results.append({
                "type": invoice_type,
                "data": single_invoice,
            })
        
        return {
            "code": 100,
            "data": results,
            "format": "json",
            "type": "invoice",
        }
    
    def _parse_idcard_result(self, resp: Dict) -> Dict[str, Any]:
        """解析身份证结果"""
        idcard_data = {
            "姓名": resp.get("Name", ""),
            "性别": resp.get("Sex", ""),
            "民族": resp.get("Nation", ""),
            "出生日期": resp.get("Birth", ""),
            "住址": resp.get("Address", ""),
            "身份证号码": resp.get("IdNum", ""),
            "签发机关": resp.get("Authority", ""),
            "有效期限": resp.get("ValidDate", ""),
        }
        
        # 移除空值
        idcard_data = {k: v for k, v in idcard_data.items() if v}
        
        if not idcard_data:
            return {"code": 101, "data": ""}
        
        return {
            "code": 100,
            "data": idcard_data,
            "format": "json",
            "type": "idcard",
        }
    
    def _parse_business_card_result(self, resp: Dict) -> Dict[str, Any]:
        """解析名片结果"""
        info = resp.get("BusinessCardInfos", [])
        
        card_data = {}
        for item in info:
            name = item.get("Name", "")
            value = item.get("Value", "")
            if name and value:
                card_data[name] = value
        
        if not card_data:
            return {"code": 101, "data": ""}
        
        return {
            "code": 100,
            "data": card_data,
            "format": "json",
            "type": "business_card",
        }
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """获取配置项定义"""
        return {
            "api_key": {
                "label": "SecretId",
                "type": "password",
                "default": "",
                "tip": "腾讯云API密钥的SecretId",
                "required": True,
            },
            "secret_key": {
                "label": "SecretKey",
                "type": "password",
                "default": "",
                "tip": "腾讯云API密钥的SecretKey",
                "required": True,
            },
            "api_type": {
                "label": "识别类型/Recognition Type",
                "type": "combobox",
                "default": "accurate",
                "options": [
                    {"value": "general", "label": "通用印刷体识别"},
                    {"value": "accurate", "label": "通用印刷体识别(高精度版)"},
                    {"value": "general_efficient", "label": "通用印刷体识别(精简版)"},
                    {"value": "table", "label": "表格识别"},
                    {"value": "table_detect", "label": "表格识别V2"},
                    {"value": "vat_invoice", "label": "增值税发票识别"},
                    {"value": "invoice", "label": "混合发票识别"},
                    {"value": "idcard", "label": "身份证识别"},
                    {"value": "business_card", "label": "名片识别"},
                    {"value": "handwriting", "label": "手写体识别"},
                ],
            },
            "region": {
                "label": "地域/Region",
                "type": "combobox",
                "default": "ap-guangzhou",
                "options": [
                    {"value": "ap-guangzhou", "label": "广州"},
                    {"value": "ap-shanghai", "label": "上海"},
                    {"value": "ap-beijing", "label": "北京"},
                    {"value": "ap-chengdu", "label": "成都"},
                    {"value": "ap-hongkong", "label": "香港"},
                ],
            },
            "idcard_side": {
                "label": "身份证面/ID Card Side",
                "type": "combobox",
                "default": "FRONT",
                "options": [
                    {"value": "FRONT", "label": "正面(人像面)"},
                    {"value": "BACK", "label": "背面(国徽面)"},
                ],
                "tip": "仅身份证识别时生效",
            },
        }
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "api_key": "",
            "secret_key": "",
            "api_type": "accurate",
            "region": "ap-guangzhou",
            "idcard_side": "FRONT",
        }
