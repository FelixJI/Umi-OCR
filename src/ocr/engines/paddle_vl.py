# ===============================================
# =============== PaddleOCR-VL 引擎 ===============
# ===============================================

"""
PaddleOCR-VL 视觉语言模型引擎实现
- 0.9B超紧凑视觉语言模型
- 支持109种语言
- 复杂元素识别（文本、表格、公式、图表）
- 资源消耗极低
"""

import os
import logging
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Dict, Any, Union, List

from .base import StructuredOCREngine

logger = logging.getLogger(__name__)


class PaddleVLEngine(StructuredOCREngine):
    """
    PaddleOCR-VL 视觉语言模型引擎
    
    基于0.9B参数的超紧凑视觉语言模型，专为文档理解设计。
    特点：
    - 支持109种语言的文档解析
    - 在复杂元素（文本、表格、公式、图表）识别方面表现优异
    - 资源消耗极低，适合边缘部署
    """
    
    ENGINE_TYPE = "paddle_vl"
    ENGINE_NAME = "PaddleOCR-VL 多语言视觉"
    SUPPORTED_FEATURES = [
        "text_recognition",
        "109_languages",
        "table_recognition",
        "formula_recognition",
        "chart_understanding",
        "document_parsing",
        "low_resource",
    ]
    SUPPORTED_OUTPUT_FORMATS = ["text", "markdown", "json"]
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._vl_pipeline = None
    
    def initialize(self) -> bool:
        """初始化PaddleOCR-VL引擎"""
        try:
            # 尝试导入PaddleOCR-VL
            try:
                from paddleocr import PaddleOCRVL
                self._vl_pipeline = PaddleOCRVL()
                self._use_vl = True
                logger.info("PaddleOCR-VL 初始化成功")
            except ImportError:
                # 回退到标准PaddleOCR多语言模式
                from paddleocr import PaddleOCR
                
                lang = self.config.get("lang", "ch")
                self._vl_pipeline = PaddleOCR(
                    lang=lang,
                    use_textline_orientation=True,
                )
                self._use_vl = False
                logger.warning("PaddleOCR-VL不可用，使用PaddleOCR多语言模式替代")
            
            self._initialized = True
            self._engine = self._vl_pipeline
            
            return True
            
        except ImportError as e:
            logger.error(f"导入PaddleOCR失败: {e}")
            return False
        except Exception as e:
            logger.error(f"PaddleOCR-VL 初始化失败: {e}", exc_info=True)
            return False
    
    def _do_recognize(self, image: Union[str, bytes, Image.Image], **kwargs) -> Dict[str, Any]:
        """执行视觉语言模型识别"""
        output_format = kwargs.get("output_format", "text")
        
        # 准备图像
        img_input = self._prepare_image(image)
        
        if self._use_vl:
            # 使用VL模型
            result = self._vl_pipeline.predict(img_input)
            return self._parse_vl_result(result, output_format)
        else:
            # 回退到标准OCR
            result = self._vl_pipeline.ocr(img_input)
            return self._parse_ocr_result(result)
    
    def recognize_structured(
        self,
        image: Union[str, bytes, Image.Image],
        output_format: str = "markdown",
        **kwargs
    ) -> Dict[str, Any]:
        """执行结构化识别"""
        return self.recognize(image, output_format=output_format, **kwargs)
    
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
    
    def _parse_vl_result(self, result: Any, output_format: str) -> Dict[str, Any]:
        """解析VL模型结果"""
        if not result:
            return {"code": 101, "data": ""}
        
        try:
            if output_format == "text":
                # 提取纯文本
                text = self._extract_text_from_vl(result)
                return {"code": 100, "data": text, "format": "text"}
            
            elif output_format == "markdown":
                # 转换为Markdown
                markdown = self._vl_to_markdown(result)
                return {"code": 100, "data": markdown, "format": "markdown"}
            
            elif output_format == "json":
                # 返回原始结构
                return {"code": 100, "data": result, "format": "json"}
            
            else:
                return {"code": 905, "data": f"[Error] 不支持的输出格式: {output_format}"}
                
        except Exception as e:
            logger.error(f"解析VL结果失败: {e}", exc_info=True)
            return {"code": 906, "data": f"[Error] 结果解析失败: {e}"}
    
    def _extract_text_from_vl(self, result: Any) -> str:
        """从VL结果中提取纯文本"""
        if isinstance(result, str):
            return result
        
        if isinstance(result, dict):
            # 尝试多种可能的字段名
            for key in ["text", "content", "output", "result"]:
                if key in result:
                    return str(result[key])
            
            # 递归提取
            texts = []
            for value in result.values():
                if isinstance(value, str):
                    texts.append(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            texts.append(item)
                        elif isinstance(item, dict) and "text" in item:
                            texts.append(item["text"])
            return "\n".join(texts)
        
        if isinstance(result, list):
            texts = []
            for item in result:
                if isinstance(item, str):
                    texts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text", "")
                    if text:
                        texts.append(text)
            return "\n".join(texts)
        
        return str(result)
    
    def _vl_to_markdown(self, result: Any) -> str:
        """将VL结果转换为Markdown"""
        if isinstance(result, str):
            return result
        
        md_parts = []
        
        if isinstance(result, dict):
            # 处理文本内容
            if "text" in result:
                md_parts.append(result["text"])
            
            # 处理表格
            if "tables" in result:
                for table in result["tables"]:
                    md_parts.append(self._table_to_markdown(table))
            
            # 处理公式
            if "formulas" in result:
                for formula in result["formulas"]:
                    md_parts.append(f"$${formula}$$")
        
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, str):
                    md_parts.append(item)
                elif isinstance(item, dict):
                    item_type = item.get("type", "text")
                    if item_type == "table":
                        md_parts.append(self._table_to_markdown(item))
                    elif item_type == "formula":
                        md_parts.append(f"$${item.get('content', '')}$$")
                    else:
                        md_parts.append(item.get("text", ""))
        
        return "\n\n".join(md_parts)
    
    def _table_to_markdown(self, table: Dict) -> str:
        """将表格转换为Markdown"""
        if "markdown" in table:
            return table["markdown"]
        
        if "html" in table:
            # 简单的HTML到Markdown转换
            return f"[表格]\n{table['html']}"
        
        if "cells" in table:
            # 从cells构建Markdown表格
            cells = table["cells"]
            if not cells:
                return ""
            
            max_row = max(c.get("row", 0) for c in cells) + 1
            max_col = max(c.get("col", 0) for c in cells) + 1
            
            grid = [["" for _ in range(max_col)] for _ in range(max_row)]
            for cell in cells:
                r, c = cell.get("row", 0), cell.get("col", 0)
                if 0 <= r < max_row and 0 <= c < max_col:
                    grid[r][c] = cell.get("text", "")
            
            lines = []
            for i, row in enumerate(grid):
                lines.append("| " + " | ".join(row) + " |")
                if i == 0:
                    lines.append("| " + " | ".join(["---"] * len(row)) + " |")
            
            return "\n".join(lines)
        
        return ""
    
    def _parse_ocr_result(self, result: List) -> Dict[str, Any]:
        """解析标准OCR结果（回退模式）"""
        if not result or not result[0]:
            return {"code": 101, "data": ""}
        
        parsed_data = []
        
        for block in result[0]:
            if len(block) >= 2:
                bbox = block[0]
                text_info = block[1]
                
                text = text_info[0] if text_info else ""
                confidence = text_info[1] if len(text_info) > 1 else 0
                
                if len(bbox) == 4:
                    box = [
                        [int(bbox[0][0]), int(bbox[0][1])],
                        [int(bbox[1][0]), int(bbox[1][1])],
                        [int(bbox[2][0]), int(bbox[2][1])],
                        [int(bbox[3][0]), int(bbox[3][1])],
                    ]
                else:
                    box = []
                
                parsed_data.append({
                    "text": text,
                    "score": float(confidence),
                    "box": box,
                    "end": "\n",
                    "from": "ocr",
                })
        
        if parsed_data:
            return {"code": 100, "data": parsed_data}
        else:
            return {"code": 101, "data": ""}
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """获取配置项定义"""
        return {
            "output_format": {
                "label": "输出格式/Output Format",
                "type": "combobox",
                "default": "text",
                "options": [
                    {"value": "text", "label": "纯文本/Plain Text"},
                    {"value": "markdown", "label": "Markdown"},
                    {"value": "json", "label": "JSON"},
                ],
            },
            "lang": {
                "label": "备用语言/Fallback Language",
                "type": "combobox",
                "default": "ch",
                "options": [
                    {"value": "ch", "label": "简体中文"},
                    {"value": "en", "label": "English"},
                    {"value": "japan", "label": "日本語"},
                    {"value": "korean", "label": "한국어"},
                ],
                "tip": "当VL模型不可用时使用的语言",
            },
        }
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "output_format": "text",
            "lang": "ch",
        }
