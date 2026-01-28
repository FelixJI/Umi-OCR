#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型类型定义

包含模型相关的枚举和数据类定义。

Author: Umi-OCR Team
Date: 2026-01-27
"""

from enum import Enum
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass

# =============================================================================
# 模型类型枚举
# =============================================================================


class ModelType(Enum):
    """模型类型"""

    DETECTION = "detection"  # 检测模型
    RECOGNITION = "recognition"  # 识别模型
    CLASSIFICATION = "classification"  # 分类模型（方向）
    TABLE = "table"  # 表格模型
    STRUCTURE = "structure"  # 结构分析模型
    LAYOUT = "layout"  # 版面分析模型


class ModelStatus(Enum):
    """模型状态"""

    NOT_DOWNLOADED = "not_downloaded"  # 未下载
    DOWNLOADING = "downloading"  # 下载中
    DOWNLOADED = "downloaded"  # 已下载
    AVAILABLE = "available"  # 可用（已验证）
    LOADED = "loaded"  # 已加载
    ERROR = "error"  # 错误


# =============================================================================
# 模型信息数据类
# =============================================================================


@dataclass
class ModelInfo:
    """
    模型信息

    包含模型的基本信息和状态。
    与 model_download_config.ModelInfo 兼容。
    """

    # 基本信息
    name: str  # 模型名称
    type: ModelType  # 模型类型
    version: str  # 模型版本
    language: str  # 语言（如 "ch", "en"）

    # 下载信息
    url: Optional[str] = None  # 下载URL（自动填充）
    size: int = 0  # 文件大小（字节）
    md5: Optional[str] = None  # MD5校验值

    # 本地信息
    local_path: Optional[Path] = None  # 本地路径
    status: ModelStatus = ModelStatus.NOT_DOWNLOADED
    last_used: Optional[datetime] = None  # 最后使用时间
    download_time: Optional[datetime] = None  # 下载时间

    # 配置
    required: bool = True  # 是否为必需模型
    enabled: bool = True  # 是否启用

    # ========== 额外字段（用于兼容 model_download_config） ==========
    display_name: Optional[str] = None  # 显示名称（来自配置）
    description: Optional[str] = None  # 模型描述（来自配置）
    size_mb: Optional[float] = None  # 模型大小MB（来自配置）
    download_url: Optional[str] = None  # 完整下载URL（来自配置）

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = {
            "name": self.name,
            "type": self.type.value,
            "version": self.version,
            "language": self.language,
            "url": self.url,
            "size": self.size,
            "md5": self.md5,
            "local_path": str(self.local_path) if self.local_path else None,
            "status": self.status.value,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "download_time": (
                self.download_time.isoformat() if self.download_time else None
            ),
            "required": self.required,
            "enabled": self.enabled,
        }

        # 添加额外字段
        if self.display_name:
            result["display_name"] = self.display_name
        if self.description:
            result["description"] = self.description
        if self.size_mb is not None:
            result["size_mb"] = self.size_mb
        if self.download_url:
            result["download_url"] = self.download_url

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "ModelInfo":
        """从字典创建实例"""
        return cls(
            name=data["name"],
            type=ModelType(data["type"]),
            version=data["version"],
            language=data["language"],
            url=data.get("url"),
            size=data.get("size", 0),
            md5=data.get("md5"),
            local_path=Path(data["local_path"]) if data.get("local_path") else None,
            status=ModelStatus(data.get("status", "not_downloaded")),
            last_used=(
                datetime.fromisoformat(data["last_used"])
                if data.get("last_used")
                else None
            ),
            download_time=(
                datetime.fromisoformat(data["download_time"])
                if data.get("download_time")
                else None
            ),
            required=data.get("required", True),
            enabled=data.get("enabled", True),
            display_name=data.get("display_name"),
            description=data.get("description"),
            size_mb=data.get("size_mb"),
            download_url=data.get("download_url"),
        )
