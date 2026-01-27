#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR JSON导出器

将OCR结果导出为JSON格式。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import json
import logging
from typing import List, Dict, Any

from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)


class JSONExporter(BaseExporter):
    """JSON导出器"""

    def __init__(self):
        """初始化JSON导出器"""
        logger.info("JSON导出器初始化完成")

    def export(
        self,
        data: List[Dict[str, Any]],
        output_path: str,
        indent: int = 2,
        ensure_ascii: bool = False,
        **kwargs
    ) -> bool:
        """
        导出为 JSON

        Args:
            data: OCR 结果列表
            output_path: 输出文件路径
            indent: 缩进空格数
            ensure_ascii: 是否确保 ASCII
            **kwargs: 额外参数

        Returns:
            bool: 是否成功
        """
        try:
            # 序列化 JSON
            json_content = json.dumps(
                data,
                indent=indent,
                ensure_ascii=ensure_ascii,
                default=str
            )

            # 写入文件
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_content)

            logger.info(f"JSON 导出成功: {output_path}")
            return True

        except Exception as e:
            logger.error(f"JSON导出失败: {e}", exc_info=True)
            return False

    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        return ".json"

    def get_name(self) -> str:
        """获取导出器名称"""
        return "JSON"
