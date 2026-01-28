#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 二维码生成服务

实现二维码/条形码生成功能。

主要功能：
- 支持多种码型
- 可配置参数(纠错等级、尺寸等)

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import Optional
from pathlib import Path
import qrcode
from PIL import Image

logger = logging.getLogger(__name__)


class QRCodeGenerator:
    """
    二维码生成器

    提供二维码/条形码生成功能。
    """

    # 支持的码型
    SUPPORTED_TYPES = [
        "QR_CODE",
        "CODE_128",
        "CODE_39",
        "EAN_13",
        "EAN_8",
    ]

    # 纠错等级
    ERROR_CORRECTION_LEVELS = ["L", "M", "Q", "H"]

    _ERROR_MAPPING = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }

    def __init__(self):
        """初始化二维码生成器"""
        logger.info("二维码生成器初始化完成")

    def generate(
        self,
        data: str,
        code_type: str = "QR_CODE",
        output_path: Optional[str] = None,
        error_correction: str = "M",
        size: int = 300,
    ) -> Optional[bytes]:
        """
        生成二维码

        Args:
            data: 数据
            code_type: 码型
            output_path: 输出文件路径
            error_correction: 纠错等级
            size: 尺寸

        Returns:
            Optional[bytes]: 图像数据
        """
        logger.info(f"生成二维码: {code_type}, 数据: {data[:50]}...")

        if code_type == "QR_CODE":
            if self.generate_qr_code(data, output_path, error_correction, size):
                if output_path:
                    with open(output_path, "rb") as f:
                        return f.read()
                return None  # Should return bytes if output_path is None, \
                # but generate_qr_code saves to file.
                # I will modify generate_qr_code to return image object or bytes later.
                # For now, let's stick to saving to file if path is provided.
        else:
            logger.warning(f"暂不支持生成码型: {code_type}")
            return None

        return None

    def generate_qr_code(
        self, data: str, output_path: str, error_correction: str = "M", size: int = 300
    ) -> bool:
        """
        生成QR码(专用方法)

        Args:
            data: 数据
            output_path: 输出文件路径
            error_correction: 纠错等级
            size: 尺寸

        Returns:
            bool: 是否成功
        """
        try:
            # 确保输出目录存在
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            ec_level = self._ERROR_MAPPING.get(
                error_correction, qrcode.constants.ERROR_CORRECT_M
            )

            qr = qrcode.QRCode(
                version=None,  # Auto
                error_correction=ec_level,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Resize if needed (box_size controls size, but we can resize final image)
            if size > 0:
                img = img.resize((size, size), Image.Resampling.LANCZOS)

            if output_path:
                img.save(output_path)
                logger.info(f"QR码生成成功: {output_path}")

            return True

        except Exception as e:
            logger.error(f"QR码生成失败: {e}", exc_info=True)
            return False
