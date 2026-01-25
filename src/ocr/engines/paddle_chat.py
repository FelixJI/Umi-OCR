# ===============================================
# =============== PP-ChatOCRv4 引擎 ===============
# ===============================================

"""
PP-ChatOCRv4 智能信息抽取引擎实现
- 集成ERNIE 4.5大语言模型
- 智能问答和信息抽取
- 从文档中精准提取关键信息
- 需要百度千帆API Key
"""

import os
import logging
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Dict, Any, Union, List, Optional

from .base import LLMOCREngine

logger = logging.getLogger(__name__)


class PaddleChatEngine(LLMOCREngine):
    """
    PP-ChatOCRv4 智能信息抽取引擎
    
    基于ERNIE 4.5的文档智能分析引擎，支持问答和关键信息抽取。
    特点：
    - 集成ERNIE 4.5大语言模型
    - 智能问答和信息抽取
    - 精度较上一代提升15%
    - 支持自定义抽取模板
    """
    
    ENGINE_TYPE = "pp_chat"
    ENGINE_NAME = "PP-ChatOCRv4 智能抽取"
    SUPPORTED_FEATURES = [
        "intelligent_extraction",
        "qa",
        "key_value_extraction",
        "document_understanding",
        "template_extraction",
    ]
    REQUIRES_API_KEY = True
    
    # 支持的LLM模型
    SUPPORTED_LLMS = [
        "ernie-4.5",
        "ernie-4.0",
        "ernie-3.5",
    ]
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._chat_pipeline = None
        
        # 获取API配置
        self.api_key = config.get("api_key", "")
        self.secret_key = config.get("secret_key", "")
        self.llm_name = config.get("llm_name", "ernie-4.5")
    
    def initialize(self) -> bool:
        """初始化PP-ChatOCRv4引擎"""
        # 检查API Key
        if not self.validate_api_key():
            logger.warning("PP-ChatOCRv4: API Key未配置或无效")
            # 不阻止初始化，但会在实际调用时返回错误
        
        try:
            # 尝试导入PP-ChatOCRv4
            try:
                from paddleocr import PPChatOCRv4Doc
                
                # 构建LLM参数
                llm_params = {
                    "api_key": self.api_key,
                }
                if self.secret_key:
                    llm_params["secret_key"] = self.secret_key
                
                self._chat_pipeline = PPChatOCRv4Doc(
                    llm_name=self.llm_name,
                    llm_params=llm_params,
                )
                self._use_chat = True
                logger.info(f"PP-ChatOCRv4 初始化成功 (LLM: {self.llm_name})")
                
            except ImportError:
                # 回退模式：仅使用OCR，不使用LLM
                from paddleocr import PaddleOCR
                self._chat_pipeline = PaddleOCR(lang="ch", use_textline_orientation=True)
                self._use_chat = False
                logger.warning("PP-ChatOCRv4不可用，使用PaddleOCR替代（无LLM功能）")
            
            self._initialized = True
            self._engine = self._chat_pipeline
            
            return True
            
        except Exception as e:
            logger.error(f"PP-ChatOCRv4 初始化失败: {e}", exc_info=True)
            return False
    
    def validate_api_key(self) -> bool:
        """验证API Key是否有效"""
        if not self.api_key:
            return False
        # 基本格式检查
        if len(self.api_key) < 10:
            return False
        return True
    
    def _do_recognize(self, image: Union[str, bytes, Image.Image], **kwargs) -> Dict[str, Any]:
        """执行智能识别"""
        prompt = kwargs.get("prompt", "")
        
        # 准备图像
        img_input = self._prepare_image(image)
        
        if self._use_chat:
            if not self.validate_api_key():
                return {
                    "code": 907,
                    "data": "[Error] API Key未配置。请在设置中配置百度千帆API Key。"
                }
            
            # 使用ChatOCR
            result = self._chat_pipeline.predict(img_input, prompt=prompt)
            return self._parse_chat_result(result)
        else:
            # 回退到标准OCR
            result = self._chat_pipeline.ocr(img_input)
            return self._parse_ocr_result(result)
    
    def extract_info(
        self,
        image: Union[str, bytes, Image.Image],
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行智能信息抽取
        
        Args:
            image: 图像数据
            prompt: 抽取指令/问题
            **kwargs: 额外参数
            
        Returns:
            抽取结果
        """
        return self.recognize(image, prompt=prompt, **kwargs)
    
    def ask_question(
        self,
        image: Union[str, bytes, Image.Image],
        question: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        对文档提问
        
        Args:
            image: 图像数据
            question: 问题
            **kwargs: 额外参数
            
        Returns:
            回答结果
        """
        return self.extract_info(image, prompt=question, **kwargs)
    
    def extract_key_values(
        self,
        image: Union[str, bytes, Image.Image],
        keys: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """
        提取指定的键值对信息
        
        Args:
            image: 图像数据
            keys: 要提取的字段名列表
            **kwargs: 额外参数
            
        Returns:
            键值对结果
        """
        # 构建抽取提示
        prompt = f"请从图片中提取以下信息：{', '.join(keys)}。以JSON格式返回结果。"
        return self.extract_info(image, prompt=prompt, **kwargs)
    
    def _prepare_image(self, image: Union[str, bytes, Image.Image]) -> Union[str, np.ndarray]:
        """准备图像输入"""
        if isinstance(image, str):
            return image
        
        if isinstance(image, bytes):
            pil_img = Image.open(BytesIO(image))
        elif isinstance(image, Image.Image):
            pil_img = image
        else:
            raise ValueError(f"不支持的图像类型: {type(image)}")
        
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        
        return np.array(pil_img)
    
    def _parse_chat_result(self, result: Any) -> Dict[str, Any]:
        """解析ChatOCR结果"""
        if not result:
            return {"code": 101, "data": ""}
        
        try:
            # ChatOCR返回格式可能因版本而异
            if isinstance(result, str):
                return {"code": 100, "data": result, "type": "chat"}
            
            if isinstance(result, dict):
                # 提取回答内容
                answer = result.get("answer", result.get("result", result.get("output", "")))
                
                # 提取置信度
                confidence = result.get("confidence", result.get("score", 1.0))
                
                # 提取OCR结果（如果有）
                ocr_result = result.get("ocr_result", [])
                
                return {
                    "code": 100,
                    "data": answer,
                    "confidence": confidence,
                    "ocr_result": ocr_result,
                    "type": "chat",
                    "raw": result,
                }
            
            if isinstance(result, list):
                # 多个结果
                return {
                    "code": 100,
                    "data": result,
                    "type": "chat",
                }
            
            return {"code": 100, "data": str(result), "type": "chat"}
            
        except Exception as e:
            logger.error(f"解析ChatOCR结果失败: {e}", exc_info=True)
            return {"code": 906, "data": f"[Error] 结果解析失败: {e}"}
    
    def _parse_ocr_result(self, result: List) -> Dict[str, Any]:
        """解析标准OCR结果（回退模式）"""
        if not result or not result[0]:
            return {"code": 101, "data": ""}
        
        # 提取所有文本
        texts = []
        for block in result[0]:
            if len(block) >= 2:
                text_info = block[1]
                text = text_info[0] if text_info else ""
                if text:
                    texts.append(text)
        
        return {
            "code": 100,
            "data": "\n".join(texts),
            "type": "ocr_fallback",
            "message": "使用OCR回退模式，未启用智能抽取功能",
        }
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """获取配置项定义"""
        return {
            "api_key": {
                "label": "百度千帆 API Key",
                "type": "password",
                "default": "",
                "tip": "从百度千帆平台获取",
                "required": True,
            },
            "secret_key": {
                "label": "百度千帆 Secret Key",
                "type": "password",
                "default": "",
                "tip": "可选，部分API需要",
            },
            "llm_name": {
                "label": "LLM模型/LLM Model",
                "type": "combobox",
                "default": "ernie-4.5",
                "options": [
                    {"value": "ernie-4.5", "label": "ERNIE 4.5 (推荐)"},
                    {"value": "ernie-4.0", "label": "ERNIE 4.0"},
                    {"value": "ernie-3.5", "label": "ERNIE 3.5"},
                ],
            },
            "default_prompt": {
                "label": "默认提示词/Default Prompt",
                "type": "text",
                "default": "",
                "tip": "不填写时需要在每次调用时指定",
            },
        }
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "api_key": "",
            "secret_key": "",
            "llm_name": "ernie-4.5",
            "default_prompt": "",
        }
    
    @staticmethod
    def get_extraction_templates() -> Dict[str, str]:
        """获取常用抽取模板"""
        return {
            "invoice": "请从发票图片中提取：发票号码、开票日期、购买方名称、销售方名称、金额、税额、价税合计。以JSON格式返回。",
            "id_card": "请从身份证图片中提取：姓名、性别、民族、出生日期、住址、身份证号码。以JSON格式返回。",
            "business_card": "请从名片图片中提取：姓名、职位、公司名称、电话、邮箱、地址。以JSON格式返回。",
            "contract": "请从合同图片中提取：合同编号、甲方、乙方、合同金额、签订日期、合同期限。以JSON格式返回。",
            "receipt": "请从收据图片中提取：收据编号、日期、收款人、付款人、金额、事由。以JSON格式返回。",
        }
