#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR OCR 结果数据类

定义统一的 OCR 识别结果格式，用于所有 OCR 引擎。

主要功能：
- 统一的结果数据结构
- 支持多种序列化格式（JSON、XML、文本、Excel、CSV）
- 记录引擎信息、识别耗时等元数据
- 支持批量识别的结果合并和分页

Author: Umi-OCR Team
Date: 2026-01-26
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class TextBlockType(Enum):
    """文本块类型"""

    PARAGRAPH = "paragraph"  # 段落
    TABLE = "table"  # 表格
    FORMULA = "formula"  # 公式
    HEADER = "header"  # 标题
    FOOTER = "footer"  # 页脚
    UNKNOWN = "unknown"  # 未知类型


@dataclass
class BoundingBox:
    """
    边界框（Bounding Box）

    定义文本区域的位置和大小，支持多种坐标系。
    """

    # 四个顶点坐标：[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    # 坐标顺序：左上、右上、右下、左下
    points: List[List[int]]

    # 可选：矩形边界框（用于快速检测）
    x: int = 0  # 左上角 X 坐标
    y: int = 0  # 左上角 Y 坐标
    width: int = 0  # 宽度
    height: int = 0  # 高度

    def __post_init__(self):
        """初始化后处理，自动计算矩形边界框"""
        if len(self.points) == 4 and (self.width == 0 or self.height == 0):
            # 从四个顶点计算矩形边界框
            x_coords = [p[0] for p in self.points]
            y_coords = [p[1] for p in self.points]
            self.x = min(x_coords)
            self.y = min(y_coords)
            self.width = max(x_coords) - self.x
            self.height = max(y_coords) - self.y

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            Dict[str, Any]: 边界框字典
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoundingBox":
        """
        从字典创建边界框

        Args:
            data: 边界框字典

        Returns:
            BoundingBox: 边界框对象
        """
        return cls(
            points=data.get("points", []),
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 0),
            height=data.get("height", 0),
        )


@dataclass
class TextBlock:
    """
    文本块

    表示 OCR 识别出的单个文本单元，包含文本内容、位置、置信度等信息。
    """

    # 基本字段
    text: str  # 识别的文本内容
    confidence: float = 0.0  # 置信度（0.0 - 1.0）
    bbox: Optional[BoundingBox] = None  # 边界框

    # 扩展字段
    block_type: TextBlockType = TextBlockType.UNKNOWN  # 文本块类型
    language: Optional[str] = None  # 检测到的语言
    font_size: Optional[float] = None  # 字体大小
    font_style: Optional[str] = None  # 字体样式

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            Dict[str, Any]: 文本块字典
        """
        result = asdict(self)
        if self.bbox:
            result["bbox"] = self.bbox.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextBlock":
        """
        从字典创建文本块

        Args:
            data: 文本块字典

        Returns:
            TextBlock: 文本块对象
        """
        bbox_data = data.pop("bbox", None)
        bbox = BoundingBox.from_dict(bbox_data) if bbox_data else None

        return cls(bbox=bbox, **data)


@dataclass
class OCRResult:
    """
    OCR 识别结果

    统一的 OCR 识别结果格式，包含单次识别的所有信息。
    支持序列化和多种导出格式。
    """

    # -------------------------------------------------------------------------
    # 基本字段
    # -------------------------------------------------------------------------

    text_blocks: List[TextBlock] = field(default_factory=list)  # 文本块列表
    full_text: str = ""  # 完整文本（合并所有文本块）

    # -------------------------------------------------------------------------
    # 元数据字段
    # -------------------------------------------------------------------------

    image_path: Optional[str] = None  # 图片路径（如果有）
    image_width: int = 0  # 图片宽度（像素）
    image_height: int = 0  # 图片高度（像素）

    recognize_time: Optional[datetime] = None  # 识别时间
    duration: float = 0.0  # 识别耗时（秒）

    # -------------------------------------------------------------------------
    # 引擎信息
    # -------------------------------------------------------------------------

    engine_type: str = ""  # 引擎类型（如 "paddle", "baidu"）
    engine_name: str = ""  # 引擎名称
    engine_version: str = ""  # 引擎版本

    # -------------------------------------------------------------------------
    # 状态信息
    # -------------------------------------------------------------------------

    success: bool = True  # 是否成功
    error_code: Optional[str] = None  # 错误码（如果失败）
    error_message: Optional[str] = None  # 错误信息（如果失败）

    # -------------------------------------------------------------------------
    # 批量识别支持
    # -------------------------------------------------------------------------

    batch_index: int = 0  # 批量中的索引（0表示单张）
    batch_total: int = 1  # 批量总数
    page_number: Optional[int] = None  # 页码（用于PDF等文档）

    # -------------------------------------------------------------------------
    # 扩展字段（用于存储自定义数据）
    # -------------------------------------------------------------------------

    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        # 如果未指定识别时间，使用当前时间
        if self.recognize_time is None:
            self.recognize_time = datetime.now()

    # -------------------------------------------------------------------------
    # 文本操作
    # -------------------------------------------------------------------------

    def get_text(self, separator: str = "\n") -> str:
        """
        获取合并后的文本

        Args:
            separator: 文本块之间的分隔符

        Returns:
            str: 合并后的文本
        """
        if self.full_text:
            return self.full_text

        # 从文本块合并文本
        texts = [block.text for block in self.text_blocks if block.text]
        return separator.join(texts)

    def get_text_blocks_by_confidence(
        self, min_confidence: float = 0.5
    ) -> List[TextBlock]:
        """
        获取指定置信度以上的文本块

        Args:
            min_confidence: 最小置信度

        Returns:
            List[TextBlock]: 筛选后的文本块列表
        """
        return [
            block for block in self.text_blocks if block.confidence >= min_confidence
        ]

    def get_text_blocks_by_type(self, block_type: TextBlockType) -> List[TextBlock]:
        """
        按类型获取文本块

        Args:
            block_type: 文本块类型

        Returns:
            List[TextBlock]: 指定类型的文本块列表
        """
        return [block for block in self.text_blocks if block.block_type == block_type]

    # -------------------------------------------------------------------------
    # 序列化方法
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（用于 JSON 序列化）

        Returns:
            Dict[str, Any]: 结果字典
        """
        result = asdict(self)

        # 转换 datetime 对象
        if self.recognize_time:
            result["recognize_time"] = self.recognize_time.isoformat()

        # 转换 TextBlock 列表
        result["text_blocks"] = [block.to_dict() for block in self.text_blocks]

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OCRResult":
        """
        从字典创建结果对象（用于反序列化）

        Args:
            data: 结果字典

        Returns:
            OCRResult: 结果对象
        """
        # 解析 datetime
        if "recognize_time" in data and data["recognize_time"]:
            if isinstance(data["recognize_time"], str):
                data["recognize_time"] = datetime.fromisoformat(data["recognize_time"])

        # 解析 TextBlock 列表
        if "text_blocks" in data:
            data["text_blocks"] = [
                TextBlock.from_dict(block) for block in data["text_blocks"]
            ]

        return cls(**data)

    def to_json(self, indent: int = 2) -> str:
        """
        转换为 JSON 字符串

        Args:
            indent: 缩进空格数

        Returns:
            str: JSON 字符串
        """
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "OCRResult":
        """
        从 JSON 字符串创建结果对象

        Args:
            json_str: JSON 字符串

        Returns:
            OCRResult: 结果对象
        """
        import json

        data = json.loads(json_str)
        return cls.from_dict(data)

    # -------------------------------------------------------------------------
    # 批量操作
    # -------------------------------------------------------------------------

    @staticmethod
    def merge_results(results: List["OCRResult"]) -> "OCRResult":
        """
        合并多个结果（用于批量识别）

        Args:
            results: 结果列表

        Returns:
            OCRResult: 合并后的结果
        """
        if not results:
            return OCRResult()

        # 使用第一个结果作为基础
        merged = results[0]

        # 合并文本块
        for result in results[1:]:
            merged.text_blocks.extend(result.text_blocks)

        # 更新总文本
        merged.full_text = ""

        # 更新批量信息
        merged.batch_index = 0
        merged.batch_total = len(results)
        merged.duration = sum(r.duration for r in results)

        return merged

    @staticmethod
    def paginate_results(
        results: List["OCRResult"], page_size: int
    ) -> List[List["OCRResult"]]:
        """
        对结果列表进行分页

        Args:
            results: 结果列表
            page_size: 每页大小

        Returns:
            List[List[OCRResult]]: 分页后的结果列表
        """
        pages = []
        for i in range(0, len(results), page_size):
            page = results[i : i + page_size]
            # 为每页结果设置页码
            for j, result in enumerate(page):
                result.page_number = i // page_size + 1
            pages.append(page)
        return pages

    # -------------------------------------------------------------------------
    # 导出格式
    # -------------------------------------------------------------------------

    def to_plain_text(self) -> str:
        """
        导出为纯文本格式

        Returns:
            str: 纯文本
        """
        return self.get_text(separator="\n")

    def to_csv(self) -> str:
        """
        导出为 CSV 格式

        Returns:
            str: CSV 格式字符串
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow(["文本", "置信度", "X", "Y", "宽度", "高度", "类型"])

        # 写入数据
        for block in self.text_blocks:
            x = block.bbox.x if block.bbox else 0
            y = block.bbox.y if block.bbox else 0
            width = block.bbox.width if block.bbox else 0
            height = block.bbox.height if block.bbox else 0

            writer.writerow(
                [
                    block.text,
                    f"{block.confidence:.4f}",
                    x,
                    y,
                    width,
                    height,
                    block.block_type.value,
                ]
            )

        return output.getvalue()

    def to_xml(self) -> str:
        """
        导出为 XML 格式

        Returns:
            str: XML 格式字符串
        """
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append("<OCRResult>")

        # 元数据
        lines.append("  <metadata>")
        lines.append(f"    <engine_type>{self.engine_type}</engine_type>")
        lines.append(f"    <engine_name>{self.engine_name}</engine_name>")
        lines.append(f"    <success>{str(self.success).lower()}</success>")
        if self.duration > 0:
            lines.append(f"    <duration>{self.duration:.3f}</duration>")
        lines.append("  </metadata>")

        # 文本块
        lines.append("  <text_blocks>")
        for i, block in enumerate(self.text_blocks, 1):
            lines.append(f'    <block id="{i}">')
            lines.append(f"      <text>{block.text}</text>")
            lines.append(f"      <confidence>{block.confidence:.4f}</confidence>")
            lines.append(f"      <type>{block.block_type.value}</type>")

            if block.bbox:
                lines.append("      <bbox>")
                lines.append(f"        <x>{block.bbox.x}</x>")
                lines.append(f"        <y>{block.bbox.y}</y>")
                lines.append(f"        <width>{block.bbox.width}</width>")
                lines.append(f"        <height>{block.bbox.height}</height>")
                lines.append("      </bbox>")

            lines.append("    </block>")
        lines.append("  </text_blocks>")

        lines.append("</OCRResult>")
        return "\n".join(lines)


# =============================================================================
# 批量结果类
# =============================================================================


@dataclass
class BatchOCRResult:
    """
    批量 OCR 结果

    用于管理批量图片识别的多个结果。
    """

    results: List[OCRResult] = field(default_factory=list)
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration: float = 0.0

    def add_result(self, result: OCRResult) -> None:
        """
        添加单个结果

        Args:
            result: OCR 结果
        """
        self.results.append(result)
        self.total_count += 1

        if result.success:
            self.success_count += 1
        else:
            self.failure_count += 1

        self.total_duration += result.duration

    def get_success_rate(self) -> float:
        """
        获取成功率

        Returns:
            float: 成功率（0.0 - 1.0）
        """
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count

    def get_average_duration(self) -> float:
        """
        获取平均识别耗时

        Returns:
            float: 平均耗时（秒）
        """
        if self.total_count == 0:
            return 0.0
        return self.total_duration / self.total_count

    def merge_all(self) -> OCRResult:
        """
        合并所有结果为一个

        Returns:
            OCRResult: 合并后的结果
        """
        return OCRResult.merge_results(self.results)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            Dict[str, Any]: 批量结果字典
        """
        return {
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.get_success_rate(),
            "total_duration": self.total_duration,
            "average_duration": self.get_average_duration(),
            "results": [result.to_dict() for result in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        """
        转换为 JSON 字符串

        Args:
            indent: 缩进空格数

        Returns:
            str: JSON 字符串
        """
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
