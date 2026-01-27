#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 文本导出器

将OCR结果导出为纯文本格式。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import List, Dict, Any

from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)


class TextExporter(BaseExporter):
    """文本导出器"""

    def __init__(self):
        """初始化文本导出器"""
        logger.info("文本导出器初始化完成")

    def export(
        self,
        data: List[Dict[str, Any]],
        output_path: str,
        separator: str = "\n\n",
        include_coordinates: bool = False,
        **kwargs
    ) -> bool:
        """
        导出为文本

        Args:
            data: OCR结果列表
            output_path: 输出文件路径
            separator: 分隔符
            include_coordinates: 是否包含坐标
            **kwargs: 额外参数

        Returns:
            bool: 是否成功
        """
        try:
            # 构建文本内容
            text_parts = []

            for item in data:
                # 提取文本
                text = item.get("text", "")
                if not text:
                    continue

                # 添加坐标信息(如果需要)
                if include_coordinates:
                    coords = item.get("coordinates", {})
                    if coords:
                        text_parts.append(f"[{coords}]")

                # 添加文本
                text_parts.append(text)

            # 写入文件
            content = separator.join(text_parts)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"文本导出成功: {output_path}")
            return True

        except Exception as e:
            logger.error(f"文本导出失败: {e}", exc_info=True)
            return False

    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        return ".txt"

    def get_name(self) -> str:
        """获取导出器名称"""
        return "文本(TXT)"
