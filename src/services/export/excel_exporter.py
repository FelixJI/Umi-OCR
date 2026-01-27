#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR Excel导出器

将OCR结果导出为Excel(CSV)格式。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import csv
import logging
from typing import List, Dict, Any

from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)


class ExcelExporter(BaseExporter):
    """Excel导出器(CSV格式)"""

    def __init__(self):
        """初始化Excel导出器"""
        logger.info("Excel导出器初始化完成")

    def export(
        self,
        data: List[Dict[str, Any]],
        output_path: str,
        delimiter: str = ",",
        include_coordinates: bool = False,
        **kwargs
    ) -> bool:
        """
        导出为CSV(Excel可打开)

        Args:
            data: OCR结果列表
            output_path: 输出文件路径
            delimiter: 分隔符
            include_coordinates: 是否包含坐标
            **kwargs: 额外参数

        Returns:
            bool: 是否成功
        """
        try:
            # 准备CSV字段
            fieldnames = ["text", "confidence"]
            if include_coordinates:
                fieldnames.extend(["x", "y", "width", "height"])

            # 写入CSV文件
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()

                for item in data:
                    # 构建行数据
                    row = {
                        "text": item.get("text", ""),
                        "confidence": item.get("confidence", "")
                    }

                    # 添加坐标信息
                    if include_coordinates:
                        coords = item.get("coordinates", {})
                        row.update({
                            "x": coords.get("x", ""),
                            "y": coords.get("y", ""),
                            "width": coords.get("width", ""),
                            "height": coords.get("height", "")
                        })

                    writer.writerow(row)

            logger.info(f"CSV导出成功: {output_path}")
            return True

        except Exception as e:
            logger.error(f"CSV导出失败: {e}", exc_info=True)
            return False

    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        return ".csv"

    def get_name(self) -> str:
        """获取导出器名称"""
        return "Excel(CSV)"
