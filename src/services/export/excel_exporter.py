#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR Excel导出器

将OCR结果导出为Excel格式。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import List, Dict, Any
from pathlib import Path
import openpyxl

from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)


class ExcelExporter(BaseExporter):
    """Excel导出器"""

    def __init__(self):
        """初始化Excel导出器"""
        logger.info("Excel导出器初始化完成")

    def export(
        self,
        data: List[Dict[str, Any]],
        output_path: str,
        **kwargs
    ) -> bool:
        """
        导出为Excel

        Args:
            data: OCR结果列表
            output_path: 输出文件路径
            **kwargs: 额外参数

        Returns:
            bool: 是否成功
        """
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "OCR 识别结果"
            
            # 表头
            ws.append(["文件", "页码", "识别内容", "置信度"])
            
            for item in data:
                text = item.get("text", "")
                title = item.get("title", "")
                page = item.get("page", "")
                confidence = item.get("confidence", 0.0)
                
                # 如果需要，可以将文本拆分为多行，或者放在一个单元格中
                ws.append([title, page, text, confidence])
            
            wb.save(output_path)
            logger.info(f"Excel导出成功: {output_path}")

            return True

        except Exception as e:
            logger.error(f"Excel导出失败: {e}", exc_info=True)
            return False

    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        return ".xlsx"

    def get_name(self) -> str:
        """获取导出器名称"""
        return "Excel"
