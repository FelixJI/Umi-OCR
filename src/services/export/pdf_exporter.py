#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR PDF导出器

将OCR结果导出为PDF格式。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import List, Dict, Any
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)


class PDFExporter(BaseExporter):
    """PDF导出器"""

    def __init__(self):
        """初始化PDF导出器"""
        logger.info("PDF导出器初始化完成")
        # 注册支持中文的字体（如果可能）
        # 目前标准字体可能不很好地支持中文。
        # 理想情况下，我们应该捆绑一个字体或使用系统字体。
        # 这是字体注册的占位符。
        try:
             # 尝试加载常用的 Windows 字体
             pdfmetrics.registerFont(TTFont('SimSun', 'simsun.ttc'))
             self.font_name = 'SimSun'
        except:
             self.font_name = 'Helvetica' # 回退字体

    def export(
        self,
        data: List[Dict[str, Any]],
        output_path: str,
        font_name: str = None,
        font_size: int = 12,
        margin: int = 50,
        **kwargs
    ) -> bool:
        """
        导出为 PDF

        Args:
            data: OCR 结果列表
            output_path: 输出文件路径
            font_name: 字体名称
            font_size: 字体大小
            margin: 页边距
            **kwargs: 额外参数

        Returns:
            bool: 是否成功
        """
        try:
            c = canvas.Canvas(output_path, pagesize=A4)
            width, height = A4
            
            used_font = font_name or self.font_name
            try:
                c.setFont(used_font, font_size)
            except:
                c.setFont("Helvetica", font_size)

            y = height - margin
            line_height = font_size * 1.5

            for item in data:
                text = item.get("text", "")
                # 如果有图片，则绘制图片（简化版）
                # image_path = item.get("image_path")
                # if image_path and Path(image_path).exists():
                #     c.drawImage(image_path, margin, y - 200, width=400, preserveAspectRatio=True)
                #     y -= 220
                
                # 绘制文本
                lines = text.split('\n')
                for line in lines:
                    if y < margin:
                        c.showPage()
                        y = height - margin
                        try:
                            c.setFont(used_font, font_size)
                        except:
                            c.setFont("Helvetica", font_size)
                    
                    c.drawString(margin, y, line)
                    y -= line_height
                
                # 项目之间添加间距
                y -= line_height
            
            c.save()
            logger.info(f"PDF导出成功: {output_path}")

            return True

        except Exception as e:
            logger.error(f"PDF导出失败: {e}", exc_info=True)
            return False

    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        return ".pdf"

    def get_name(self) -> str:
        """获取导出器名称"""
        return "PDF"
