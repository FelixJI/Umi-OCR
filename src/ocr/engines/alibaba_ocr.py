# ===============================================
# =============== 阿里云OCR引擎 ===============
# ===============================================

"""
阿里云OCR API引擎
支持功能：
- 通用文字识别
- 高精度文字识别
- 表格识别
- 增值税发票识别
- 票据识别
- 身份证识别
- 名片识别
- 印章识别
"""

import json
import time
import uuid
import hashlib
import hmac
import base64
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Union
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote

from .cloud_api_base import CloudAPIEngine

logger = logging.getLogger(__name__)


class AlibabaOCREngine(CloudAPIEngine):
    """
    阿里云OCR引擎
    
    API文档: https://help.aliyun.com/document_detail/442323.html
    使用阿里云视觉智能开放平台的OCR服务
    """
    
    ENGINE_TYPE = "alibaba_ocr"
    ENGINE_NAME = "阿里云OCR"
    SUPPORTED_FEATURES = [
        "general_ocr",
        "accurate_ocr",
        "table_recognition",
        "invoice_recognition",
        "vat_invoice",
        "idcard",
        "business_card",
        "seal_recognition",
    ]
    
    # API服务信息 (使用RPC风格API)
    VERSION = "2021-07-07"
    
    # 不同服务的Endpoint
    ENDPOINTS = {
        "ocr": "ocr-api.cn-hangzhou.aliyuncs.com",
        "invoice": "ocr-api.cn-hangzhou.aliyuncs.com",
    }
    
    # Action映射
    ACTION_MAP = {
        "general": "RecognizeGeneral",
        "accurate": "RecognizeAdvanced",
        "table": "RecognizeTable",
        "table_detect": "RecognizeTableOcr",
        "vat_invoice": "RecognizeInvoice",
        "invoice": "RecognizeMixedInvoices",
        "idcard": "RecognizeIdcard",
        "business_card": "RecognizeBusinessCard",
        "handwriting": "RecognizeHandwriting",
        "seal": "RecognizeSeal",
        "train_ticket": "RecognizeTrainTicket",
        "taxi_invoice": "RecognizeTaxiInvoice",
        "bank_card": "RecognizeBankCard",
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_key_id = config.get("api_key", "")
        self.access_key_secret = config.get("secret_key", "")
        self.region = config.get("region", "cn-hangzhou")
    
    def _get_api_url(self, api_type: str) -> str:
        """获取API URL"""
        endpoint = self.ENDPOINTS.get("ocr", "ocr-api.cn-hangzhou.aliyuncs.com")
        return f"https://{endpoint}"
    
    def _get_timestamp(self) -> str:
        """获取ISO8601格式时间戳"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def _sign_string(self, string_to_sign: str) -> str:
        """使用HMAC-SHA256签名"""
        signature = hmac.new(
            (self.access_key_secret + "&").encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode("utf-8")
    
    def _build_common_params(self, action: str) -> Dict[str, str]:
        """构建公共请求参数"""
        return {
            "Format": "JSON",
            "Version": self.VERSION,
            "AccessKeyId": self.access_key_id,
            "SignatureMethod": "HMAC-SHA256",
            "Timestamp": self._get_timestamp(),
            "SignatureVersion": "1.0",
            "SignatureNonce": str(uuid.uuid4()),
            "Action": action,
        }
    
    def _percent_encode(self, value: str) -> str:
        """URL编码（阿里云特殊编码规则）"""
        return quote(str(value), safe="~").replace("+", "%20").replace("*", "%2A")
    
    def _build_signature(self, method: str, params: Dict[str, str]) -> str:
        """构建签名"""
        # 按参数名排序
        sorted_params = sorted(params.items())
        
        # 构建规范化查询字符串
        canonicalized_query_string = "&".join([
            f"{self._percent_encode(k)}={self._percent_encode(v)}"
            for k, v in sorted_params
        ])
        
        # 构建待签名字符串
        string_to_sign = f"{method}&%2F&{self._percent_encode(canonicalized_query_string)}"
        
        return self._sign_string(string_to_sign)
    
    def _build_request_body(self, image_base64: str, api_type: str) -> str:
        """构建请求体（阿里云使用查询参数）"""
        # 阿里云新版API使用body传图像
        body = {
            "body": image_base64,
        }
        return json.dumps(body)
    
    def _call_api(self, image_base64: str, api_type: str) -> Dict:
        """调用阿里云API"""
        action = self.ACTION_MAP.get(api_type, "RecognizeGeneral")
        
        # 构建请求参数
        params = self._build_common_params(action)
        
        # 添加特定参数
        if api_type in ["table", "table_detect"]:
            params["NeedRotate"] = "true"
            params["LineLess"] = "false"
        
        if api_type == "idcard":
            params["OutputFigure"] = "false"
        
        # 计算签名
        signature = self._build_signature("POST", params)
        params["Signature"] = signature
        
        # 构建URL
        url = self._get_api_url(api_type)
        query_string = urlencode(params)
        full_url = f"{url}/?{query_string}"
        
        # 构建请求体
        body = image_base64.encode("utf-8")
        
        headers = {
            "Content-Type": "application/octet-stream",
            "Accept": "application/json",
        }
        
        request = Request(full_url, data=body, headers=headers, method="POST")
        
        with urlopen(request, timeout=30) as response:
            result = response.read().decode("utf-8")
            return json.loads(result)
    
    def _parse_response(self, response: Dict, api_type: str) -> Dict[str, Any]:
        """解析阿里云API响应"""
        # 检查错误
        if "Code" in response and response["Code"] != "200":
            return {
                "code": 909,
                "data": f"[Error] 阿里云API错误 {response.get('Code', '')}: {response.get('Message', '')}"
            }
        
        # 获取识别数据
        data = response.get("Data", {})
        
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                pass
        
        # 根据API类型解析结果
        if api_type in ["general", "accurate", "handwriting"]:
            return self._parse_general_result(data)
        elif api_type in ["table", "table_detect"]:
            return self._parse_table_result(data)
        elif api_type in ["vat_invoice", "invoice"]:
            return self._parse_invoice_result(data)
        elif api_type == "idcard":
            return self._parse_idcard_result(data)
        elif api_type == "business_card":
            return self._parse_business_card_result(data)
        elif api_type == "seal":
            return self._parse_seal_result(data)
        else:
            return self._parse_general_result(data)
    
    def _parse_general_result(self, data: Dict) -> Dict[str, Any]:
        """解析通用OCR结果"""
        # 新版API返回content字段
        content = data.get("content", "")
        if content:
            # 简单文本结果
            return {
                "code": 100,
                "data": [{"text": content, "score": 1.0, "box": [], "end": "\n", "from": "alibaba_ocr"}]
            }
        
        # 结构化结果
        prism_words = data.get("prism_wordsInfo", [])
        if not prism_words:
            prism_words = data.get("blocks", [])
        
        if not prism_words:
            return {"code": 101, "data": ""}
        
        parsed_data = []
        for item in prism_words:
            if isinstance(item, dict):
                text = item.get("word", item.get("text", ""))
                confidence = item.get("prob", item.get("confidence", 100))
                if confidence > 1:
                    confidence = confidence / 100.0
                
                # 获取位置
                pos = item.get("pos", [])
                box = []
                if pos:
                    box = [[p.get("x", 0), p.get("y", 0)] for p in pos]
                
                parsed_data.append({
                    "text": text,
                    "score": confidence,
                    "box": box,
                    "end": "\n",
                    "from": "alibaba_ocr",
                })
        
        if not parsed_data:
            return {"code": 101, "data": ""}
        
        return {"code": 100, "data": parsed_data}
    
    def _parse_table_result(self, data: Dict) -> Dict[str, Any]:
        """解析表格识别结果"""
        tables = data.get("tables", [])
        
        if not tables:
            # 尝试其他格式
            table_html = data.get("tableHtml", "")
            if table_html:
                return {
                    "code": 100,
                    "data": {"html": table_html, "tables": []},
                    "format": "html",
                    "type": "table",
                }
            return {"code": 101, "data": ""}
        
        parsed_tables = []
        for table in tables:
            cells = table.get("cells", table.get("tableRows", []))
            table_data = {"cells": []}
            
            if isinstance(cells, list):
                for cell in cells:
                    if isinstance(cell, dict):
                        table_data["cells"].append({
                            "row": cell.get("row", cell.get("rowIndex", 0)),
                            "col": cell.get("col", cell.get("colIndex", 0)),
                            "text": cell.get("text", cell.get("word", "")),
                            "row_span": cell.get("rowSpan", 1),
                            "col_span": cell.get("colSpan", 1),
                        })
                    elif isinstance(cell, list):
                        # 行格式
                        for col_idx, col_cell in enumerate(cell):
                            if isinstance(col_cell, dict):
                                table_data["cells"].append({
                                    "row": cells.index(cell),
                                    "col": col_idx,
                                    "text": col_cell.get("text", ""),
                                    "row_span": 1,
                                    "col_span": 1,
                                })
            
            parsed_tables.append(table_data)
        
        return {
            "code": 100,
            "data": {"tables": parsed_tables},
            "format": "json",
            "type": "table",
        }
    
    def _parse_invoice_result(self, data: Dict) -> Dict[str, Any]:
        """解析发票识别结果"""
        # 统一发票结果
        invoice_data = {}
        
        # 增值税发票字段映射
        field_map = {
            "invoiceCode": "发票代码",
            "invoiceNo": "发票号码",
            "invoiceDate": "开票日期",
            "sellerName": "销售方名称",
            "sellerTaxNo": "销售方税号",
            "buyerName": "购买方名称",
            "buyerTaxNo": "购买方税号",
            "totalAmount": "合计金额",
            "totalTax": "合计税额",
            "amountWithTax": "价税合计",
            "checkCode": "校验码",
            "machineCode": "机器编号",
        }
        
        for eng_key, cn_key in field_map.items():
            value = data.get(eng_key, "")
            if value:
                invoice_data[cn_key] = value
        
        # 处理商品明细
        items = data.get("items", data.get("invoiceItems", []))
        if items:
            invoice_data["商品明细"] = items
        
        if not invoice_data:
            # 尝试其他格式
            content = data.get("content", "")
            if content:
                return {
                    "code": 100,
                    "data": {"raw_content": content},
                    "format": "json",
                    "type": "invoice",
                }
            return {"code": 101, "data": ""}
        
        return {
            "code": 100,
            "data": invoice_data,
            "format": "json",
            "type": "invoice",
        }
    
    def _parse_idcard_result(self, data: Dict) -> Dict[str, Any]:
        """解析身份证识别结果"""
        # 字段映射
        idcard_data = {}
        
        face_fields = {
            "name": "姓名",
            "sex": "性别",
            "ethnicity": "民族",
            "birthDate": "出生日期",
            "address": "住址",
            "idNumber": "身份证号码",
        }
        
        back_fields = {
            "issueAuthority": "签发机关",
            "validPeriod": "有效期限",
            "startDate": "有效期起始",
            "endDate": "有效期截止",
        }
        
        for eng_key, cn_key in {**face_fields, **back_fields}.items():
            value = data.get(eng_key, "")
            if value:
                idcard_data[cn_key] = value
        
        if not idcard_data:
            return {"code": 101, "data": ""}
        
        return {
            "code": 100,
            "data": idcard_data,
            "format": "json",
            "type": "idcard",
        }
    
    def _parse_business_card_result(self, data: Dict) -> Dict[str, Any]:
        """解析名片识别结果"""
        card_data = {}
        
        field_map = {
            "name": "姓名",
            "company": "公司",
            "department": "部门",
            "title": "职位",
            "mobile": "手机",
            "telephone": "电话",
            "email": "邮箱",
            "address": "地址",
            "website": "网址",
        }
        
        for eng_key, cn_key in field_map.items():
            value = data.get(eng_key, "")
            if value:
                card_data[cn_key] = value
        
        if not card_data:
            return {"code": 101, "data": ""}
        
        return {
            "code": 100,
            "data": card_data,
            "format": "json",
            "type": "business_card",
        }
    
    def _parse_seal_result(self, data: Dict) -> Dict[str, Any]:
        """解析印章识别结果"""
        seals = data.get("seals", [])
        
        if not seals:
            text = data.get("text", data.get("content", ""))
            if text:
                return {
                    "code": 100,
                    "data": [{"text": text, "type": "seal"}],
                    "format": "json",
                    "type": "seal",
                }
            return {"code": 101, "data": ""}
        
        seal_data = []
        for seal in seals:
            seal_data.append({
                "text": seal.get("text", ""),
                "type": seal.get("type", "unknown"),
                "position": seal.get("position", {}),
            })
        
        return {
            "code": 100,
            "data": seal_data,
            "format": "json",
            "type": "seal",
        }
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """获取配置项定义"""
        return {
            "api_key": {
                "label": "AccessKey ID",
                "type": "password",
                "default": "",
                "tip": "阿里云AccessKey ID",
                "required": True,
            },
            "secret_key": {
                "label": "AccessKey Secret",
                "type": "password",
                "default": "",
                "tip": "阿里云AccessKey Secret",
                "required": True,
            },
            "api_type": {
                "label": "识别类型/Recognition Type",
                "type": "combobox",
                "default": "accurate",
                "options": [
                    {"value": "general", "label": "通用文字识别"},
                    {"value": "accurate", "label": "通用文字识别(高精度)"},
                    {"value": "table", "label": "表格识别"},
                    {"value": "vat_invoice", "label": "增值税发票识别"},
                    {"value": "invoice", "label": "混合发票识别"},
                    {"value": "idcard", "label": "身份证识别"},
                    {"value": "business_card", "label": "名片识别"},
                    {"value": "handwriting", "label": "手写识别"},
                    {"value": "seal", "label": "印章识别"},
                    {"value": "train_ticket", "label": "火车票识别"},
                    {"value": "taxi_invoice", "label": "出租车发票识别"},
                    {"value": "bank_card", "label": "银行卡识别"},
                ],
            },
            "region": {
                "label": "地域/Region",
                "type": "combobox",
                "default": "cn-hangzhou",
                "options": [
                    {"value": "cn-hangzhou", "label": "杭州"},
                    {"value": "cn-shanghai", "label": "上海"},
                    {"value": "cn-beijing", "label": "北京"},
                    {"value": "cn-shenzhen", "label": "深圳"},
                ],
            },
        }
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "api_key": "",
            "secret_key": "",
            "api_type": "accurate",
            "region": "cn-hangzhou",
        }
