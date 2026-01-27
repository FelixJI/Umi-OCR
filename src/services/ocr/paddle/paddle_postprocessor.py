#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 结果后处理器

提供文本后处理功能和文本块类型推断。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import re
from typing import List, Optional

from ..ocr_result import TextBlock, TextBlockType, BoundingBox


# =============================================================================
# 文本块类型推断器
# =============================================================================

class TextBlockInference:
    """
    文本块类型推断器

    基于文本内容和位置特征，自动推断文本块的类型。
    """

    # 关键词模式（用于推断类型）
    PATTERNS = {
        TextBlockType.HEADER: [
            r"第[一二三四五六七八九十百]+章",
            r"^\d+\.",
            r"^[一二三四五六七八九十]+、",
            r"^[A-Z][a-z]*\s*[a-z]*:",
        ],
        TextBlockType.FOOTER: [
            r"第\d+页",
            r"Page\s*\d+",
        ],
        TextBlockType.FORMULA: [
            r"[A-Za-z]+\s*[=≠<>≤≥]+\s*[\d.]+",
            r"[\d.]+\s*[+\-×÷]\s*[\d.]+",
        ]
    }

    @classmethod
    def infer_type(cls, text: str, bbox: Optional[BoundingBox] = None) -> TextBlockType:
        """
        推断文本块类型

        Args:
            text: 文本内容
            bbox: 边界框（用于位置推断）

        Returns:
            TextBlockType: 推断的类型
        """
        # 检查表格特征（多行对齐）
        if cls._is_table_like(text):
            return TextBlockType.TABLE

        # 检查公式特征
        if cls._matches_pattern(text, cls.PATTERNS[TextBlockType.FORMULA]):
            return TextBlockType.FORMULA

        # 检查标题特征
        if cls._matches_pattern(text, cls.PATTERNS[TextBlockType.HEADER]):
            return TextBlockType.HEADER

        # 检查页脚特征
        if cls._matches_pattern(text, cls.PATTERNS[TextBlockType.FOOTER]):
            return TextBlockType.FOOTER

        # 默认为段落
        return TextBlockType.PARAGRAPH

    @classmethod
    def _matches_pattern(cls, text: str, patterns: List[str]) -> bool:
        """
        检查文本是否匹配模式

        Args:
            text: 文本内容
            patterns: 正则表达式模式列表

        Returns:
            bool: 是否匹配
        """
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False

    @classmethod
    def _is_table_like(cls, text: str) -> bool:
        """
        检查文本是否像表格

        Args:
            text: 文本内容

        Returns:
            bool: 是否像表格
        """
        # 检查是否有HTML表格标签
        if '<table>' in text.lower() or '</table>' in text.lower():
            return True
        
        # 检查是否有大量制表符或管道符
        tab_count = text.count('\t')
        pipe_count = text.count('|')
        if tab_count >= 2 or pipe_count >= 2:
            return True

        # 检查是否有大量数字对齐
        lines = text.split('\n')
        if len(lines) > 1:
            # 检查每行的数字数量
            num_counts = [len([c for c in line if c.isdigit()]) for line in lines if line.strip()]
            if num_counts:
                avg_num_count = sum(num_counts) / len(num_counts)
                # 如果平均每行有多个数字，可能是表格
                if avg_num_count >= 2:
                    return True
        
        # 检查是否包含表格关键词
        table_keywords = ['姓名', '年龄', '性别', '部门', '工资', '日期', '金额', '数量', '产品', '价格',
                         'name', 'age', 'sex', 'department', 'salary', 'date', 'amount', 'quantity', 'price', 'product']
        if any(keyword in text for keyword in table_keywords):
            return True
        
        return False


# =============================================================================
# 文本后处理器
# =============================================================================

class TextPostprocessor:
    """
    文本后处理器

    提供文本后处理功能，包括合并相邻行、去除重复等。
    """

    @staticmethod
    def merge_adjacent_lines(
        text_blocks: List[TextBlock],
        vertical_threshold: int = 10,
        horizontal_threshold: int = 20
    ) -> List[TextBlock]:
        """
        合并相邻的文本行

        Args:
            text_blocks: 文本块列表
            vertical_threshold: 垂直间距阈值
            horizontal_threshold: 水平间距阈值

        Returns:
            List[TextBlock]: 合并后的文本块列表
        """
        if len(text_blocks) <= 1:
            return text_blocks

        # 按Y坐标排序
        sorted_blocks = sorted(text_blocks, key=lambda b: b.bbox.y if b.bbox else 0)

        merged = []
        current_block = sorted_blocks[0]

        for block in sorted_blocks[1:]:
            if not current_block.bbox or not block.bbox:
                merged.append(current_block)
                current_block = block
                continue

            # 检查是否在同一行（Y坐标接近）
            y_diff = abs(block.bbox.y - current_block.bbox.y)
            x_overlap = max(0, min(current_block.bbox.x + current_block.bbox.width, block.bbox.x + block.bbox.width) -
                          max(current_block.bbox.x, block.bbox.x))

            if y_diff < vertical_threshold and x_overlap > 0:
                # 合并到同一行
                current_block.text += " " + block.text
                # 更新边界框
                new_x = min(current_block.bbox.x, block.bbox.x)
                new_width = max(current_block.bbox.x + current_block.bbox.width, block.bbox.x + block.bbox.width) - new_x
                current_block.bbox.x = new_x
                current_block.bbox.width = new_width
            else:
                # 添加到结果，开始新的行
                merged.append(current_block)
                current_block = block

        merged.append(current_block)
        return merged

    @staticmethod
    def remove_duplicates(text_blocks: List[TextBlock]) -> List[TextBlock]:
        """
        去除重复的文本块

        Args:
            text_blocks: 文本块列表

        Returns:
            List[TextBlock]: 去重后的文本块列表
        """
        seen = set()
        unique_blocks = []

        for block in text_blocks:
            text = block.text.strip()
            if text and text not in seen:
                seen.add(text)
                unique_blocks.append(block)

        return unique_blocks

    @staticmethod
    def sort_by_position(
        text_blocks: List[TextBlock],
        reading_order: str = "left_to_right"
    ) -> List[TextBlock]:
        """
        按位置排序文本块

        Args:
            text_blocks: 文本块列表
            reading_order: 阅读顺序 ("left_to_right", "top_to_bottom")

        Returns:
            List[TextBlock]: 排序后的文本块列表
        """
        if reading_order == "left_to_right":
            # 先按 Y 排序，再按 X 排序
            return sorted(
                text_blocks,
                key=lambda b: (b.bbox.y if b.bbox else 0, b.bbox.x if b.bbox else 0)
            )
        else:
            # 先按 X 排序，再按 Y 排序
            return sorted(
                text_blocks,
                key=lambda b: (b.bbox.x if b.bbox else 0, b.bbox.y if b.bbox else 0)
            )

    @staticmethod
    def filter_by_confidence(
        text_blocks: List[TextBlock],
        threshold: float = 0.5
    ) -> List[TextBlock]:
        """
        按置信度过滤文本块

        Args:
            text_blocks: 文本块列表
            threshold: 置信度阈值

        Returns:
            List[TextBlock]: 过滤后的文本块列表
        """
        return [block for block in text_blocks if block.confidence >= threshold]

    @staticmethod
    def clean_text(text: str) -> str:
        """
        清理文本（去除多余空白字符）

        Args:
            text: 原始文本

        Returns:
            str: 清理后的文本
        """
        # 替换多个空白为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空白
        text = text.strip()
        return text
