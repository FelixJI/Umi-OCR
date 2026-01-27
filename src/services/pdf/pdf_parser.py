#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR PDF处理服务

实现PDF文件解析功能,支持批量文档OCR。

主要功能：
- 解析PDF文件
- 提取页面图像
- 提取文本(如有)

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class PDFPage:
    """PDF页面信息"""
    page_number: int            # 页码
    width: int                # 宽度
    height: int               # 高度
    image_path: Optional[str] = None   # 页面图像路径
    text: Optional[str] = None         # 提取的文本


@dataclass
class PDFInfo:
    """PDF文件信息"""
    file_path: str            # 文件路径
    total_pages: int          # 总页数
    title: Optional[str] = None       # 标题
    pages: List[PDFPage] = None        # 页面列表


class PDFParser:
    """
    PDF解析器

    提供PDF文件解析和页面提取功能。
    """

    def __init__(self):
        """初始化PDF解析器"""
        logger.info("PDF解析器初始化完成")

    def parse_pdf(self, file_path: str) -> Optional[PDFInfo]:
        """
        解析PDF文件

        Args:
            file_path: PDF文件路径

        Returns:
            Optional[PDFInfo]: PDF信息,失败返回None
        """
        try:
            # 检查文件是否存在
            path = Path(file_path)
            if not path.exists():
                logger.error(f"PDF文件不存在: {file_path}")
                return None

            doc = fitz.open(file_path)
            total_pages = len(doc)
            title = doc.metadata.get("title", "")
            
            pages = []
            for i in range(total_pages):
                page = doc.load_page(i)
                rect = page.rect
                pages.append(PDFPage(
                    page_number=i + 1,
                    width=int(rect.width),
                    height=int(rect.height)
                ))
            
            doc.close()

            logger.info(f"解析PDF成功: {file_path}, 共 {total_pages} 页")

            # 创建PDF信息
            pdf_info = PDFInfo(
                file_path=file_path,
                total_pages=total_pages,
                title=title,
                pages=pages
            )

            return pdf_info

        except Exception as e:
            logger.error(f"PDF解析失败: {file_path}, {e}", exc_info=True)
            return None

    def extract_page_image(
        self,
        file_path: str,
        page_number: int,
        dpi: int = 200,
        output_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        提取指定页面为图像

        Args:
            file_path: PDF文件路径
            page_number: 页码 (从1开始)
            dpi: DPI
            output_dir: 输出目录

        Returns:
            Optional[str]: 图像文件路径
        """
        try:
            doc = fitz.open(file_path)
            if page_number < 1 or page_number > len(doc):
                logger.error(f"页码超出范围: {page_number}")
                return None
            
            page = doc.load_page(page_number - 1)
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            if output_dir:
                out_path = Path(output_dir)
            else:
                out_path = Path(file_path).parent / "extracted_images"
            
            out_path.mkdir(parents=True, exist_ok=True)
            
            image_filename = f"{Path(file_path).stem}_page_{page_number}.png"
            image_path = out_path / image_filename
            
            pix.save(str(image_path))
            doc.close()
            
            logger.info(f"提取PDF页面成功: {image_path}")

            return str(image_path)

        except Exception as e:
            logger.error(f"页面提取失败: {e}", exc_info=True)
            return None

    def extract_all_images(
        self,
        file_path: str,
        output_dir: str,
        dpi: int = 200
    ) -> List[str]:
        """
        提取所有页面为图像

        Args:
            file_path: PDF文件路径
            output_dir: 输出目录
            dpi: DPI

        Returns:
            List[str]: 图像文件路径列表
        """
        pdf_info = self.parse_pdf(file_path)
        if not pdf_info:
            return []

        images = []
        for page in pdf_info.pages:
            image_path = self.extract_page_image(
                file_path, page.page_number, dpi, output_dir
            )
            if image_path:
                images.append(image_path)

        return images
