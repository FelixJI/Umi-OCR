# ===============================================
# =============== 百度智能云OCR引擎 ===============
# ===============================================

"""
百度智能云OCR API引擎
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
import logging
from typing import Dict, Any, Union, List
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from .cloud_api_base import CloudAPIEngine

logger = logging.getLogger(__name__)


class BaiduOCREngine(CloudAPIEngine):
    """
    百度智能云OCR引擎
    
    API文档: https://cloud.baidu.com/doc/OCR/index.html
    """
    
    ENGINE_TYPE = "baidu_ocr"
    ENGINE_NAME = "百度智能云OCR"
    SUPPORTED_FEATURES = [
        "general_ocr",
        "accurate_ocr",
        "table_recognition",
        "invoice_recognition",
        "vat_invoice",
        "receipt",
        "idcard",
        "business_card",
    ]
    
    # API端点映射
    API_ENDPOINTS = {
        "general": "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic",
        "accurate": "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic",
        "general_location": "https://aip.baidubce.com/rest/2.0/ocr/v1/general",
        "accurate_location": "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate",
        "table": "https://aip.baidubce.com/rest/2.0/ocr/v1/table",
        "table_async": "https://aip.baidubce.com/rest/2.0/ocr/v1/table/async",
        "vat_invoice": "https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice",
        "invoice": "https://aip.baidubce.com/rest/2.0/ocr/v1/invoice",
        "receipt": "https://aip.baidubce.com/rest/2.0/ocr/v1/receipt",
        "idcard": "https://aip.baidubce.com/rest/2.0/ocr/v1/idcard",
        "business_card": "https://aip.baidubce.com/rest/2.0/ocr/v1/business_card",
        "handwriting": "https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting",
    }
    
    # Token URL
    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._access_token = None
        self._token_expire_time = 0
    
    def _get_access_token(self) -> str:
        """获取百度API的access_token"""
        # 检查token是否过期
        if self._access_token and time.time() < self._token_expire_time:
            return self._access_token
        
        # 获取新token
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key,
        }
        
        url = f"{self.TOKEN_URL}?{urlencode(params)}"
        
        try:
            with urlopen(url, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                
                if "access_token" in result:
                    self._access_token = result["access_token"]
                    # token有效期30天，提前1小时刷新
                    self._token_expire_time = time.time() + result.get("expires_in", 2592000) - 3600
                    return self._access_token
                else:
                    raise Exception(f"获取token失败: {result}")
        except Exception as e:
            logger.error(f"获取百度access_token失败: {e}")
            raise
    
    def _get_api_url(self, api_type: str) -> str:
        """获取API URL"""
        base_url = self.API_ENDPOINTS.get(api_type, self.API_ENDPOINTS["general"])
        token = self._get_access_token()
        return f"{base_url}?access_token={token}"
    
    def _build_request_body(self, image_base64: str, api_type: str) -> Dict:
        """构建请求体"""
        body = {
            "image": image_base64,
        }
        
        # 根据API类型添加额外参数
        if api_type in ["general", "accurate", "general_location", "accurate_location"]:
            body["language_type"] = "CHN_ENG"  # 中英混合
            body["detect_direction"] = "true"  # 检测方向
            body["paragraph"] = "true"  # 段落输出
        
        if api_type == "table":
            body["return_type"] = "json"  # 返回JSON格式
        
        if api_type == "idcard":
            body["id_card_side"] = self.config.get("idcard_side", "front")
        
        return body
    
    def _get_headers(self, api_type: str) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
    
    def _parse_response(self, response: Dict, api_type: str) -> Dict[str, Any]:
        """解析百度API响应"""
        # 检查错误
        if "error_code" in response:
            error_msg = response.get("error_msg", "未知错误")
            return {
                "code": 909,
                "data": f"[Error] 百度API错误 {response['error_code']}: {error_msg}"
            }
        
        # 根据API类型解析结果
        if api_type in ["general", "accurate", "general_location", "accurate_location"]:
            return self._parse_general_result(response, api_type)
        elif api_type == "table":
            return self._parse_table_result(response)
        elif api_type in ["vat_invoice", "invoice"]:
            return self._parse_invoice_result(response, api_type)
        elif api_type == "receipt":
            return self._parse_receipt_result(response)
        elif api_type == "idcard":
            return self._parse_idcard_result(response)
        elif api_type == "business_card":
            return self._parse_business_card_result(response)
        else:
            return self._parse_general_result(response, api_type)
    
    def _parse_general_result(self, response: Dict, api_type: str) -> Dict[str, Any]:
        """解析通用OCR结果"""
        words_result = response.get("words_result", [])
        
        if not words_result:
            return {"code": 101, "data": ""}
        
        parsed_data = []
        for item in words_result:
            text = item.get("words", "")
            
            # 获取位置信息（如果有）
            location = item.get("location", {})
            if location:
                left, top = location.get("left", 0), location.get("top", 0)
                width, height = location.get("width", 0), location.get("height", 0)
                box = [
                    [left, top],
                    [left + width, top],
                    [left + width, top + height],
                    [left, top + height],
                ]
            else:
                box = []
            
            parsed_data.append({
                "text": text,
                "score": item.get("probability", {}).get("average", 1.0),
                "box": box,
                "end": "\n",
                "from": "baidu_ocr",
            })
        
        return {"code": 100, "data": parsed_data}
    
    def _parse_table_result(self, response: Dict) -> Dict[str, Any]:
        """解析表格识别结果"""
        tables_result = response.get("tables_result", [])
        
        if not tables_result:
            return {"code": 101, "data": ""}
        
        tables = []
        for table in tables_result:
            table_data = {
                "rows": [],
                "cells": [],
            }
            
            body = table.get("body", [])
            for cell in body:
                row_start = cell.get("row_start", 0)
                col_start = cell.get("col_start", 0)
                words = cell.get("words", "")
                
                table_data["cells"].append({
                    "row": row_start,
                    "col": col_start,
                    "text": words,
                    "row_span": cell.get("row_end", row_start) - row_start + 1,
                    "col_span": cell.get("col_end", col_start) - col_start + 1,
                })
            
            tables.append(table_data)
        
        return {
            "code": 100,
            "data": {"tables": tables},
            "format": "json",
            "type": "table",
        }
    
    def _parse_invoice_result(self, response: Dict, api_type: str) -> Dict[str, Any]:
        """解析发票识别结果"""
        words_result = response.get("words_result", {})
        
        if not words_result:
            return {"code": 101, "data": ""}
        
        # 提取关键字段
        invoice_data = {}
        
        # 增值税发票字段映射
        field_mapping = {
            "InvoiceCode": "发票代码",
            "InvoiceNum": "发票号码",
            "InvoiceDate": "开票日期",
            "InvoiceType": "发票类型",
            "MachineNum": "机器编号",
            "CheckCode": "校验码",
            "PurchaserName": "购买方名称",
            "PurchaserRegisterNum": "购买方纳税人识别号",
            "PurchaserAddress": "购买方地址电话",
            "PurchaserBank": "购买方开户行及账号",
            "SellerName": "销售方名称",
            "SellerRegisterNum": "销售方纳税人识别号",
            "SellerAddress": "销售方地址电话",
            "SellerBank": "销售方开户行及账号",
            "TotalAmount": "合计金额",
            "TotalTax": "合计税额",
            "AmountInFiguers": "价税合计(小写)",
            "AmountInWords": "价税合计(大写)",
            "Remarks": "备注",
        }
        
        for key, label in field_mapping.items():
            if key in words_result:
                value = words_result[key]
                if isinstance(value, dict):
                    value = value.get("word", "")
                invoice_data[label] = value
        
        # 处理商品明细
        commodity_info = []
        if "CommodityName" in words_result:
            names = words_result["CommodityName"]
            if isinstance(names, list):
                for i, name in enumerate(names):
                    item = {"商品名称": name.get("word", "") if isinstance(name, dict) else name}
                    
                    # 尝试获取对应的其他信息
                    for field in ["CommodityNum", "CommodityUnit", "CommodityPrice", "CommodityAmount", "CommodityTaxRate", "CommodityTax"]:
                        if field in words_result:
                            values = words_result[field]
                            if isinstance(values, list) and i < len(values):
                                val = values[i]
                                item[field] = val.get("word", "") if isinstance(val, dict) else val
                    
                    commodity_info.append(item)
        
        if commodity_info:
            invoice_data["商品明细"] = commodity_info
        
        return {
            "code": 100,
            "data": invoice_data,
            "format": "json",
            "type": "invoice",
        }
    
    def _parse_receipt_result(self, response: Dict) -> Dict[str, Any]:
        """解析票据识别结果"""
        words_result = response.get("words_result", {})
        
        if not words_result:
            return {"code": 101, "data": ""}
        
        return {
            "code": 100,
            "data": words_result,
            "format": "json",
            "type": "receipt",
        }
    
    def _parse_idcard_result(self, response: Dict) -> Dict[str, Any]:
        """解析身份证识别结果"""
        words_result = response.get("words_result", {})
        
        if not words_result:
            return {"code": 101, "data": ""}
        
        # 字段映射
        field_mapping = {
            "姓名": "姓名",
            "性别": "性别",
            "民族": "民族",
            "出生": "出生日期",
            "住址": "住址",
            "公民身份号码": "身份证号码",
            "签发机关": "签发机关",
            "签发日期": "签发日期",
            "失效日期": "失效日期",
        }
        
        idcard_data = {}
        for key, label in field_mapping.items():
            if key in words_result:
                value = words_result[key]
                if isinstance(value, dict):
                    value = value.get("words", "")
                idcard_data[label] = value
        
        return {
            "code": 100,
            "data": idcard_data,
            "format": "json",
            "type": "idcard",
        }
    
    def _parse_business_card_result(self, response: Dict) -> Dict[str, Any]:
        """解析名片识别结果"""
        words_result = response.get("words_result", {})
        
        if not words_result:
            return {"code": 101, "data": ""}
        
        return {
            "code": 100,
            "data": words_result,
            "format": "json",
            "type": "business_card",
        }
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """获取配置项定义"""
        return {
            "api_key": {
                "label": "API Key (AK)",
                "type": "password",
                "default": "",
                "tip": "百度智能云应用的API Key",
                "required": True,
            },
            "secret_key": {
                "label": "Secret Key (SK)",
                "type": "password",
                "default": "",
                "tip": "百度智能云应用的Secret Key",
                "required": True,
            },
            "api_type": {
                "label": "识别类型/Recognition Type",
                "type": "combobox",
                "default": "accurate",
                "options": [
                    {"value": "general", "label": "通用文字识别(标准版)"},
                    {"value": "accurate", "label": "通用文字识别(高精度版)"},
                    {"value": "general_location", "label": "通用文字识别(含位置)"},
                    {"value": "accurate_location", "label": "高精度识别(含位置)"},
                    {"value": "table", "label": "表格识别"},
                    {"value": "vat_invoice", "label": "增值税发票识别"},
                    {"value": "invoice", "label": "通用发票识别"},
                    {"value": "receipt", "label": "票据识别"},
                    {"value": "idcard", "label": "身份证识别"},
                    {"value": "business_card", "label": "名片识别"},
                    {"value": "handwriting", "label": "手写文字识别"},
                ],
            },
            "idcard_side": {
                "label": "身份证面/ID Card Side",
                "type": "combobox",
                "default": "front",
                "options": [
                    {"value": "front", "label": "正面(人像面)"},
                    {"value": "back", "label": "背面(国徽面)"},
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
            "idcard_side": "front",
        }
