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
import barcode
from barcode.writer import ImageWriter

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
        "UPC_A",
        "ISBN",
        "JAN",
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
        fill_color: str = "black",
        back_color: str = "white",
    ) -> Optional[bytes]:
        """
        生成二维码/条形码

        Args:
            data: 数据
            code_type: 码型
            output_path: 输出文件路径
            error_correction: 纠错等级 (仅QR)
            size: 尺寸
            fill_color: 前景色
            back_color: 背景色

        Returns:
            Optional[bytes]: 图像数据
        """
        logger.info(f"生成码: {code_type}, 数据: {data[:50]}...")

        # 确保输出目录存在
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            img = None
            if code_type == "QR_CODE":
                img = self._create_qr_image(data, error_correction, fill_color, back_color)
            else:
                img = self._create_barcode_image(data, code_type, fill_color, back_color)

            if img:
                # 调整尺寸 (使用 NEAREST 保持清晰度)
                # 对于条形码，保持宽高比
                if size > 0:
                    if code_type == "QR_CODE":
                        img = img.resize((size, size), Image.Resampling.NEAREST)
                    else:
                        # 条形码按宽度缩放，高度自适应
                        w, h = img.size
                        ratio = size / w
                        new_h = int(h * ratio)
                        img = img.resize((size, new_h), Image.Resampling.NEAREST)

                if output_path:
                    img.save(output_path)
                    logger.info(f"码生成成功: {output_path}")
                    with open(output_path, "rb") as f:
                        return f.read()
                return None # TODO: Return bytes directly if needed
        except Exception as e:
            logger.error(f"生成失败: {e}", exc_info=True)
            return None
            
        return None

    def generate_qr_code(
        self, 
        data: str, 
        output_path: str, 
        error_correction: str = "M", 
        size: int = 300,
        fill_color: str = "black",
        back_color: str = "white",
    ) -> bool:
        """兼容旧接口"""
        return self.generate(data, "QR_CODE", output_path, error_correction, size, fill_color, back_color) is not None

    def _create_qr_image(self, data, error_correction, fill_color, back_color):
        ec_level = self._ERROR_MAPPING.get(
            error_correction, qrcode.constants.ERROR_CORRECT_M
        )
        qr = qrcode.QRCode(
            version=None,
            error_correction=ec_level,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        return qr.make_image(fill_color=fill_color, back_color=back_color).convert('RGB')

    def _create_barcode_image(self, data, code_type, fill_color, back_color):
        # 映射码型名称到 python-barcode 的名称
        # python-barcode 支持: code128, code39, ean, ean13, ean8, gs1, gtin, isbn, isbn10, isbn13, issn, jan, pzn, upc, upca
        
        type_map = {
            "CODE_128": "code128",
            "CODE_39": "code39",
            "EAN_13": "ean13",
            "EAN_8": "ean8",
            "UPC_A": "upca",
            "ISBN": "isbn13",
            "JAN": "jan",
        }
        
        bc_type = type_map.get(code_type)
        if not bc_type:
            raise ValueError(f"不支持的条形码类型: {code_type}")

        # 配置 Writer
        writer = ImageWriter()
        
        # 获取条形码类
        barcode_class = barcode.get_barcode_class(bc_type)
        
        # 创建条形码对象
        # writer_options 可以设置 module_height, module_width, font_size, text_distance, quiet_zone
        # foreground, background
        bc = barcode_class(data, writer=writer)
        
        # 生成图片
        # render 返回 PIL Image
        img = bc.render(writer_options={
            'foreground': fill_color,
            'background': back_color,
            'write_text': True, # 是否显示文本
            'font_size': 10,
            'text_distance': 5.0,
            'quiet_zone': 6.5,
        })
        
        return img

