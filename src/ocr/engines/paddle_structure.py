# ===============================================
# =============== PP-StructureV3 引擎 ===============
# ===============================================

"""
PP-StructureV3 文档结构化引擎实现
- 支持表格识别和结构化输出
- 支持版式分析
- 支持多种输出格式（Markdown/JSON/HTML/Excel）
- 保持文档原始结构
"""

import os
import logging
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Dict, Any, Union, List, Optional

from .base import StructuredOCREngine

logger = logging.getLogger(__name__)


class PaddleStructureEngine(StructuredOCREngine):
    """
    PP-StructureV3 文档结构化引擎
    
    将复杂PDF和文档图像转换为保留原始结构的Markdown和JSON文件。
    特点：
    - 表格识别与结构化
    - 版式分析
    - 公式识别
    - 图表理解
    """
    
    ENGINE_TYPE = "pp_structure"
    ENGINE_NAME = "PP-StructureV3 文档结构化"
    SUPPORTED_FEATURES = [
        "table_recognition",
        "layout_analysis",
        "formula_recognition",
        "markdown_output",
        "json_output",
        "html_output",
        "excel_output",
    ]
    SUPPORTED_OUTPUT_FORMATS = ["markdown", "json", "html", "excel"]
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._table_converter = None
    
    def initialize(self) -> bool:
        """初始化PP-StructureV3引擎"""
        try:
            # 尝试导入PP-StructureV3
            try:
                from paddleocr import PPStructureV3
                self._engine = PPStructureV3()
                self._use_v3 = True
            except ImportError:
                # 回退到旧版PPStructure
                from paddleocr import PPStructure
                self._engine = PPStructure(
                    table=True,
                    layout=True,
                    show_log=False,
                )
                self._use_v3 = False
                logger.warning("PPStructureV3不可用，使用PPStructure替代")
            
            self._initialized = True
            logger.info(f"PP-Structure 初始化成功 (V3: {self._use_v3})")
            
            return True
            
        except ImportError as e:
            logger.error(f"导入PP-Structure失败: {e}")
            return False
        except Exception as e:
            logger.error(f"PP-Structure 初始化失败: {e}", exc_info=True)
            return False
    
    def _do_recognize(self, image: Union[str, bytes, Image.Image], **kwargs) -> Dict[str, Any]:
        """执行文档结构化识别"""
        output_format = kwargs.get("output_format", "markdown")
        
        # 准备图像
        img_input = self._prepare_image(image)
        
        # 执行识别
        if self._use_v3:
            result = self._engine.predict(img_input)
        else:
            result = self._engine(img_input)
        
        # 转换输出格式
        return self._convert_result(result, output_format)
    
    def recognize_structured(
        self,
        image: Union[str, bytes, Image.Image],
        output_format: str = "markdown",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行结构化识别
        
        Args:
            image: 图像数据
            output_format: 输出格式 (markdown/json/html/excel)
            **kwargs: 额外参数
            
        Returns:
            结构化识别结果
        """
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
    
    def _convert_result(self, result: Any, output_format: str) -> Dict[str, Any]:
        """转换识别结果为指定格式"""
        try:
            if self._use_v3:
                return self._convert_v3_result(result, output_format)
            else:
                return self._convert_legacy_result(result, output_format)
        except Exception as e:
            logger.error(f"结果转换失败: {e}", exc_info=True)
            return {"code": 904, "data": f"[Error] 结果转换失败: {e}"}
    
    def _convert_v3_result(self, result: Any, output_format: str) -> Dict[str, Any]:
        """转换PPStructureV3结果"""
        if not result:
            return {"code": 101, "data": ""}
        
        # PPStructureV3直接输出结构化数据
        if output_format == "markdown":
            markdown_content = self._to_markdown(result)
            return {
                "code": 100,
                "data": markdown_content,
                "format": "markdown",
                "raw": result,
            }
        elif output_format == "json":
            return {
                "code": 100,
                "data": result,
                "format": "json",
            }
        elif output_format == "html":
            html_content = self._to_html(result)
            return {
                "code": 100,
                "data": html_content,
                "format": "html",
                "raw": result,
            }
        elif output_format == "excel":
            # Excel需要特殊处理，返回表格数据
            tables = self._extract_tables(result)
            return {
                "code": 100,
                "data": tables,
                "format": "excel",
                "raw": result,
            }
        else:
            return {"code": 905, "data": f"[Error] 不支持的输出格式: {output_format}"}
    
    def _convert_legacy_result(self, result: List, output_format: str) -> Dict[str, Any]:
        """转换旧版PPStructure结果"""
        if not result:
            return {"code": 101, "data": ""}
        
        # 解析旧版结果格式
        structured_data = {
            "tables": [],
            "texts": [],
            "figures": [],
        }
        
        for item in result:
            item_type = item.get("type", "text")
            
            if item_type == "table":
                table_data = {
                    "bbox": item.get("bbox", []),
                    "html": item.get("res", {}).get("html", ""),
                    "cells": item.get("res", {}).get("cells", []),
                }
                structured_data["tables"].append(table_data)
            elif item_type == "text":
                text_data = {
                    "bbox": item.get("bbox", []),
                    "text": item.get("res", ""),
                }
                structured_data["texts"].append(text_data)
            elif item_type == "figure":
                figure_data = {
                    "bbox": item.get("bbox", []),
                }
                structured_data["figures"].append(figure_data)
        
        # 转换为指定格式
        if output_format == "markdown":
            return {
                "code": 100,
                "data": self._legacy_to_markdown(structured_data),
                "format": "markdown",
            }
        elif output_format == "json":
            return {
                "code": 100,
                "data": structured_data,
                "format": "json",
            }
        elif output_format == "html":
            return {
                "code": 100,
                "data": self._legacy_to_html(structured_data),
                "format": "html",
            }
        elif output_format == "excel":
            return {
                "code": 100,
                "data": structured_data["tables"],
                "format": "excel",
            }
        else:
            return {"code": 905, "data": f"[Error] 不支持的输出格式: {output_format}"}
    
    def _to_markdown(self, result: Any) -> str:
        """将结果转换为Markdown格式"""
        # 如果结果已经是markdown字符串
        if isinstance(result, str):
            return result
        
        # 如果是字典或列表，需要解析
        md_lines = []
        
        if isinstance(result, dict):
            # 处理文本
            if "text" in result:
                md_lines.append(result["text"])
            
            # 处理表格
            if "tables" in result:
                for table in result["tables"]:
                    md_lines.append(self._table_to_markdown(table))
        
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, str):
                    md_lines.append(item)
                elif isinstance(item, dict):
                    if item.get("type") == "table":
                        md_lines.append(self._table_to_markdown(item))
                    else:
                        md_lines.append(item.get("text", ""))
        
        return "\n\n".join(md_lines)
    
    def _table_to_markdown(self, table_data: Dict) -> str:
        """将表格数据转换为Markdown表格"""
        # 如果有HTML格式，尝试转换
        if "html" in table_data:
            return self._html_table_to_markdown(table_data["html"])
        
        # 如果有cells数据，构建表格
        if "cells" in table_data:
            return self._cells_to_markdown(table_data["cells"])
        
        return ""
    
    def _html_table_to_markdown(self, html: str) -> str:
        """将HTML表格转换为Markdown"""
        try:
            from html.parser import HTMLParser
            
            class TableParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.rows = []
                    self.current_row = []
                    self.current_cell = ""
                    self.in_cell = False
                
                def handle_starttag(self, tag, attrs):
                    if tag in ("td", "th"):
                        self.in_cell = True
                        self.current_cell = ""
                    elif tag == "tr":
                        self.current_row = []
                
                def handle_endtag(self, tag):
                    if tag in ("td", "th"):
                        self.in_cell = False
                        self.current_row.append(self.current_cell.strip())
                    elif tag == "tr":
                        if self.current_row:
                            self.rows.append(self.current_row)
                
                def handle_data(self, data):
                    if self.in_cell:
                        self.current_cell += data
            
            parser = TableParser()
            parser.feed(html)
            
            if not parser.rows:
                return ""
            
            # 构建Markdown表格
            md_lines = []
            
            # 表头
            header = parser.rows[0]
            md_lines.append("| " + " | ".join(header) + " |")
            md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
            
            # 表体
            for row in parser.rows[1:]:
                # 确保列数一致
                while len(row) < len(header):
                    row.append("")
                md_lines.append("| " + " | ".join(row[:len(header)]) + " |")
            
            return "\n".join(md_lines)
            
        except Exception as e:
            logger.warning(f"HTML表格转Markdown失败: {e}")
            return html
    
    def _cells_to_markdown(self, cells: List) -> str:
        """将cells数据转换为Markdown表格"""
        if not cells:
            return ""
        
        # 解析cells获取表格结构
        # cells格式: [{"row": 0, "col": 0, "text": "..."}, ...]
        max_row = max(c.get("row", 0) for c in cells) + 1
        max_col = max(c.get("col", 0) for c in cells) + 1
        
        # 创建表格矩阵
        table = [["" for _ in range(max_col)] for _ in range(max_row)]
        
        for cell in cells:
            row = cell.get("row", 0)
            col = cell.get("col", 0)
            text = cell.get("text", "")
            if 0 <= row < max_row and 0 <= col < max_col:
                table[row][col] = text
        
        # 构建Markdown
        md_lines = []
        for i, row in enumerate(table):
            md_lines.append("| " + " | ".join(row) + " |")
            if i == 0:
                md_lines.append("| " + " | ".join(["---"] * len(row)) + " |")
        
        return "\n".join(md_lines)
    
    def _to_html(self, result: Any) -> str:
        """将结果转换为HTML格式"""
        if isinstance(result, str):
            return f"<div>{result}</div>"
        
        html_parts = ["<div class='document'>"]
        
        if isinstance(result, dict):
            if "html" in result:
                html_parts.append(result["html"])
            if "tables" in result:
                for table in result["tables"]:
                    if "html" in table:
                        html_parts.append(table["html"])
        
        html_parts.append("</div>")
        return "\n".join(html_parts)
    
    def _legacy_to_markdown(self, structured_data: Dict) -> str:
        """将旧版结构化数据转换为Markdown"""
        md_parts = []
        
        # 添加文本
        for text_item in structured_data.get("texts", []):
            md_parts.append(text_item.get("text", ""))
        
        # 添加表格
        for table in structured_data.get("tables", []):
            if "html" in table:
                md_parts.append(self._html_table_to_markdown(table["html"]))
        
        return "\n\n".join(md_parts)
    
    def _legacy_to_html(self, structured_data: Dict) -> str:
        """将旧版结构化数据转换为HTML"""
        html_parts = ["<div class='document'>"]
        
        for text_item in structured_data.get("texts", []):
            text = text_item.get("text", "")
            html_parts.append(f"<p>{text}</p>")
        
        for table in structured_data.get("tables", []):
            if "html" in table:
                html_parts.append(table["html"])
        
        html_parts.append("</div>")
        return "\n".join(html_parts)
    
    def _extract_tables(self, result: Any) -> List[Dict]:
        """从结果中提取表格数据"""
        tables = []
        
        if isinstance(result, dict) and "tables" in result:
            tables = result["tables"]
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and item.get("type") == "table":
                    tables.append(item)
        
        return tables
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """获取配置项定义"""
        return {
            "output_format": {
                "label": "输出格式/Output Format",
                "type": "combobox",
                "default": "markdown",
                "options": [
                    {"value": "markdown", "label": "Markdown"},
                    {"value": "json", "label": "JSON"},
                    {"value": "html", "label": "HTML"},
                    {"value": "excel", "label": "Excel"},
                ],
            },
            "table_recognition": {
                "label": "表格识别/Table Recognition",
                "type": "bool",
                "default": True,
            },
            "layout_analysis": {
                "label": "版式分析/Layout Analysis",
                "type": "bool",
                "default": True,
            },
        }
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "output_format": "markdown",
            "table_recognition": True,
            "layout_analysis": True,
        }
