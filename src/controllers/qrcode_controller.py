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
import json
import time
from typing import List, Optional, Dict
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from services.qrcode.qrcode_scanner import QRCodeScanner
from services.qrcode.qrcode_generator import QRCodeGenerator
from utils.logger import get_logger

logger = get_logger()


class QrcodeController(QObject):
    """
    二维码控制器

    功能:
    - 扫描二维码/条形码
    - 生成二维码/条形码
    - 管理二维码历史记录
    """

    # 信号定义
    scan_started = Signal()  # 开始扫描
    scan_completed = Signal(list)  # 扫描完成(QRCodeResult列表)
    scan_failed = Signal(str)  # 扫描失败
    generate_started = Signal()  # 开始生成
    generate_completed = Signal(str)  # 生成成功(文件路径)
    generate_failed = Signal(str)  # 生成失败
    history_changed = Signal()  # 历史记录变更

    def __init__(self, parent: Optional[QObject] = None):
        """
        初始化二维码控制器

        Args:
            parent: 父对象
        """
        super().__init__(parent)

        self._scanner = QRCodeScanner()
        self._generator = QRCodeGenerator()
        self._history_file = Path("UmiOCR-data/qrcode_history.json")
        self._history_list: List[Dict] = []
        
        self.load_history()

        logger.info("二维码控制器初始化完成")

    # -------------------------------------------------------------------------
    # 历史记录管理
    # -------------------------------------------------------------------------

    def load_history(self):
        """加载历史记录"""
        try:
            if self._history_file.exists():
                with open(self._history_file, "r", encoding="utf-8") as f:
                    self._history_list = json.load(f)
            else:
                self._history_list = []
        except Exception as e:
            logger.error(f"加载二维码历史记录失败: {e}")
            self._history_list = []

    def save_history(self):
        """保存历史记录"""
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._history_file, "w", encoding="utf-8") as f:
                json.dump(self._history_list, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"保存二维码历史记录失败: {e}")

    def add_history(self, record_type: str, data: str):
        """
        添加历史记录

        Args:
            record_type: 类型 ('scan' 或 'generate')
            data: 内容
        """
        # 查重：如果最近一条相同，则更新时间
        if self._history_list and self._history_list[0].get("data") == data and self._history_list[0].get("type") == record_type:
            self._history_list[0]["timestamp"] = int(time.time())
        else:
            record = {
                "type": record_type,
                "data": data,
                "timestamp": int(time.time())
            }
            self._history_list.insert(0, record)
            
            # 限制数量，例如保留最近100条
            if len(self._history_list) > 100:
                self._history_list.pop()

        self.save_history()
        self.history_changed.emit()

    def get_history(self) -> List[Dict]:
        """获取历史记录列表"""
        return self._history_list

    def delete_history(self, index: int):
        """删除指定历史记录"""
        if 0 <= index < len(self._history_list):
            self._history_list.pop(index)
            self.save_history()
            self.history_changed.emit()

    def clear_history(self):
        """清空历史记录"""
        self._history_list = []
        self.save_history()
        self.history_changed.emit()

    # -------------------------------------------------------------------------
    # 扫描与生成
    # -------------------------------------------------------------------------

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
                # 添加到历史记录 (取第一个结果)
                if len(results) > 0:
                    self.add_history("scan", results[0].data)
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

    def scan_pixmap(self, pixmap) -> None:
        """
        扫描二维码（UI调用的方法，直接扫描 QPixmap）

        Args:
            pixmap: QPixmap 对象
        """
        logger.info("开始扫描 QPixmap")
        self.scan_started.emit()
        
        try:
            results = self._scanner.scan_from_pixmap(pixmap)
            
            if results:
                logger.info(f"扫描完成: {len(results)} 个码")
                self.scan_completed.emit(results)
                if len(results) > 0:
                    self.add_history("scan", results[0].data)
            else:
                logger.warning("未检测到二维码")
                self.scan_completed.emit([])
                
        except Exception as e:
            logger.error(f"扫描失败: {e}", exc_info=True)
            self.scan_failed.emit(str(e))


    def generate_qr_code(
        self,
        data: str,
        output_path: str = "",
        code_type: str = "QR_CODE",
        correction: str = "M",
        size: int = 300,
        fill_color: str = "black",
        back_color: str = "white",
    ) -> None:
        """
        生成QR码（UI调用的方法）

        Args:
            data: 数据
            output_path: 输出文件路径
            code_type: 码型
            correction: 纠错等级
            size: 尺寸
            fill_color: 前景色
            back_color: 背景色
        """
        # 如果没有提供输出路径，生成默认路径
        if not output_path:
            output_path = f"qrcode_{int(time.time())}.png"

        logger.info(f"开始生成QR码: {data[:50]}...")
        self.generate_started.emit()

        try:
            # 生成QR码
            success = self._generator.generate_qr_code(
                data, output_path, correction, size, fill_color, back_color
            )

            if success:
                logger.info(f"QR码生成完成: {output_path}")
                self.generate_completed.emit(output_path)
                # 添加到历史记录
                self.add_history("generate", data)
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
            options: 生成选项(code_type, correction, size, fill_color, back_color)

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
                fill_color=options.get("fill_color", "black"),
                back_color=options.get("back_color", "white"),
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
