#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 导出器基类

定义导出器的统一接口。

Author: Umi-OCR Team
Date: 2026-01-27
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pathlib import Path


class BaseExporter(ABC):
    """
    导出器抽象基类

    实现者需要:
    1. 实现 export() 方法
    2. 实现 get_file_extension() 方法
    """

    @abstractmethod
    def export(
        self,
        data: List[Dict[str, Any]],
        output_path: str,
        **kwargs
    ) -> bool:
        """
        导出数据

        Args:
            data: 要导出的数据(OCR结果列表)
            output_path: 输出文件路径
            **kwargs: 额外参数

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """
        获取文件扩展名

        Returns:
            str: 扩展名(如 ".txt")
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        获取导出器名称

        Returns:
            str: 名称
        """
        pass
