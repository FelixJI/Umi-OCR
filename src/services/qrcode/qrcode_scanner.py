#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 二维码扫描服务

实现二维码/条形码扫描功能。

主要功能：
- 支持多种码型
- 一图多码识别

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import List, Optional
from dataclasses import dataclass
from PIL import Image
try:
    from pyzbar.pyzbar import decode, ZBarSymbol
except ImportError:
    decode = None
    ZBarSymbol = None
    
logger = logging.getLogger(__name__)


@dataclass
class QRCodeResult:
    """二维码识别结果"""
    type: str                  # 码型
    data: str                  # 数据
    rect: Optional[tuple] = None   # 位置矩形 (x, y, w, h)


class QRCodeScanner:
    """
    二维码扫描器

    提供二维码/条形码识别功能。
    """

    # 支持的码型
    SUPPORTED_TYPES = [
        "QR_CODE",
        "CODE_128",
        "CODE_39",
        "EAN_13",
        "EAN_8",
        "UPC_A",
        "UPC_E",
        "DATA_MATRIX",
        "PDF_417",
    ]

    def __init__(self):
        """初始化二维码扫描器"""
        if decode is None:
            logger.warning("未安装 pyzbar 库，二维码扫描功能不可用")
        else:
            logger.info("二维码扫描器初始化完成")

    def scan_from_image(self, image_path: str) -> List[QRCodeResult]:
        """
        从图像扫描二维码

        Args:
            image_path: 图像文件路径

        Returns:
            List[QRCodeResult]: 识别结果列表
        """
        logger.info(f"扫描二维码: {image_path}")

        if decode is None:
            logger.error("pyzbar 库未安装")
            return []

        try:
            image = Image.open(image_path)
            decoded_objects = decode(image)
            
            results = []
            for obj in decoded_objects:
                # pyzbar returns bytes, need decode
                data = obj.data.decode('utf-8')
                code_type = obj.type
                rect = (obj.rect.left, obj.rect.top, obj.rect.width, obj.rect.height)
                
                results.append(QRCodeResult(
                    type=code_type,
                    data=data,
                    rect=rect
                ))
            
            logger.info(f"扫描完成, 发现 {len(results)} 个码")
            return results

        except Exception as e:
            logger.error(f"二维码扫描失败: {e}", exc_info=True)
            return []

    def scan_from_pixmap(self, pixmap) -> List[QRCodeResult]:
        """
        从QPixmap扫描二维码

        Args:
            pixmap: Qt图像对象

        Returns:
            List[QRCodeResult]: 识别结果列表
        """
        if decode is None:
            return []
            
        try:
            # Convert QPixmap to PIL Image
            # This requires converting QPixmap -> QImage -> bytes -> PIL Image
            # Or save to temp file
            # Ideally we should use memory buffer
            
            # Simple implementation: save to temp file (robust but slow)
            # Better: QImage to bytes
            
            qimage = pixmap.toImage()
            # ... conversion logic ...
            # For simplicity in this refactor step, assuming we handle file paths mostly.
            # If strictly needed, we can implement QImage -> PIL conversion.
            # But scan_from_image is the main entry point for now.
            
            # TODO: Implement in-memory conversion for performance
            logger.warning("scan_from_pixmap not fully implemented for in-memory conversion")
            return []
            
        except Exception as e:
            logger.error(f"二维码扫描失败: {e}", exc_info=True)
            return []
