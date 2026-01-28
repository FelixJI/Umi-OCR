#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 二维码控制器

连接二维码界面和服务层。

主要功能：
- 处理二维码扫描请求
- 处理二维码生成请求

Author: Umi-OCR Team
Date: 2026-01-27
"""

import os
from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from services.qrcode.qrcode_scanner import QRCodeScanner
from services.qrcode.qrcode_generator import QRCodeGenerator
from utils.logger import get_logger

logger = get_logger()


class QRCodeController(QObject):
    """
    二维码控制器

    功能:
    - 扫描二维码/条形码
    - 生成二维码/条形码
    """

    # 信号定义
    scan_started = Signal()  # 开始扫描
    scan_completed = Signal(list)  # 扫描完成(QRCodeResult列表)
    scan_failed = Signal(str)  # 扫描失败
    generate_started = Signal()  # 开始生成
    generate_completed = Signal(str)  # 生成成功(文件路径)
    generate_failed = Signal(str)  # 生成失败

    def __init__(self):
        """初始化二维码控制器"""
        super().__init__()

        self._scanner = QRCodeScanner()
        self._generator = QRCodeGenerator()

        logger.info("二维码控制器初始化完成")

    def scan_image(self, image_path: str) -> None:
        """
        扫描图像中的二维码

        Args:
            image_path: 图像文件路径
        """
        logger.info(f"开始扫描: {image_path}")
        self.scan_started.emit()

        try:
            # 扫描二维码
            results = self._scanner.scan_from_image(image_path)

            if results:
                logger.info(f"扫描完成: {len(results)} 个码")
                self.scan_completed.emit(results)
            else:
                logger.warning("未检测到二维码")
                self.scan_completed.emit([])

        except Exception as e:
            logger.error(f"扫描失败: {e}", exc_info=True)
            self.scan_failed.emit(str(e))

    def scan_qr_code(self, image_path: str) -> None:
        """
        扫描二维码（UI调用的方法）

        Args:
            image_path: 图像文件路径
        """
        self.scan_image(image_path)

    def generate_qr_code(
        self,
        data: str,
        output_path: str = "",
        code_type: str = "QR_CODE",
        correction: str = "M",
        size: int = 300,
    ) -> None:
        """
        生成QR码（UI调用的方法）

        Args:
            data: 数据
            output_path: 输出文件路径
            code_type: 码型
            correction: 纠错等级
            size: 尺寸
        """
        # 如果没有提供输出路径，生成默认路径
        if not output_path:
            output_path = f"qrcode_{len(data)}.png"

        logger.info(f"开始生成QR码: {data[:50]}...")
        self.generate_started.emit()

        try:
            # 生成QR码
            success = self._generator.generate_qr_code(
                data, output_path, correction, size
            )

            if success:
                logger.info(f"QR码生成完成: {output_path}")
                self.generate_completed.emit(output_path)
            else:
                logger.error("QR码生成失败")
                self.generate_failed.emit("生成失败")

        except Exception as e:
            logger.error(f"QR码生成异常: {e}", exc_info=True)
            self.generate_failed.emit(str(e))

    def batch_generate_qr_codes(
        self, data_list: List[str], output_dir: str, options: Optional[dict] = None
    ) -> List[str]:
        """
        批量生成二维码

        Args:
            data_list: 数据列表
            output_dir: 输出目录
            options: 生成选项(code_type, correction, size)

        Returns:
            List[str]: 生成的文件路径列表
        """
        if not options:
            options = {}

        logger.info(f"批量生成二维码: {len(data_list)} 个")
        generated_files = []

        for i, data in enumerate(data_list):
            output_path = os.path.join(output_dir, f"qrcode_{i}.png")
            self.generate_qr_code(
                data=data,
                output_path=output_path,
                code_type=options.get("code_type", "QR_CODE"),
                correction=options.get("correction", "M"),
                size=options.get("size", 300),
            )
            generated_files.append(output_path)

        return generated_files

    def get_supported_types(self) -> List[str]:
        """
        获取支持的码型列表

        Returns:
            List[str]: 码型列表
        """
        return QRCodeScanner.SUPPORTED_TYPES
