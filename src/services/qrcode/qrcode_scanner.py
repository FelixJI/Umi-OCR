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

from PySide6.QtGui import QImage
    
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
            # Convert QPixmap to PIL Image in memory using QBuffer
            from PySide6.QtCore import QBuffer, QIODevice
            import io

            # Convert QPixmap to QImage
            qimage = pixmap.toImage()

            # Save to bytes buffer (PNG format for reliability)
            buffer = QBuffer()
            buffer.open(QIODevice.ReadWrite)
            qimage.save(buffer, "PNG")
            buffer_data = buffer.data()

            # Create PIL Image from bytes
            pil_image = Image.open(io.BytesIO(bytes(buffer_data)))

            # Decode barcodes
            decoded_objects = decode(pil_image)

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

            logger.info(f"从QPixmap扫描完成, 发现 {len(results)} 个码")
            return results

        except Exception as e:
            logger.error(f"二维码扫描失败: {e}", exc_info=True)
            return []

        try:
            # Convert QPixmap to PIL Image in memory
            from PySide6.QtGui import QImage
            import io

            # Convert QPixmap to QImage
            qimage = pixmap.toImage()

            # Get image dimensions
            width = qimage.width()
            height = qimage.height()

            # Determine the format
            # QImage.Format_RGBA8888 is commonly used
            format_id = qimage.format()

            # Convert to bytes
            # We'll use Format_RGBA8888 to ensure proper byte alignment
            if format_id != QImage.Format_RGBA8888:
                qimage = qimage.convertToFormat(QImage.Format_RGBA8888)

            # Get raw bytes
            ptr = qimage.bits()
            ptr.setsize(qimage.sizeInBytes())
            data = ptr.asstring()

            # Create PIL Image from bytes
            pil_image = Image.frombytes("RGBA", (width, height), data)

            # Convert RGBA to RGB if needed (pyzbar works better with RGB)
            if pil_image.mode == "RGBA":
                # Convert to RGB - create white background for transparency
                background = Image.new("RGB", (width, height), (255, 255, 255))
                background.paste(pil_image, mask=pil_image.split()[3])  # Use alpha channel as mask
                pil_image = background

            # Decode barcodes
            decoded_objects = decode(pil_image)

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

            logger.info(f"从QPixmap扫描完成, 发现 {len(results)} 个码")
            return results

        except Exception as e:
            logger.error(f"二维码扫描失败: {e}", exc_info=True)
            return []
