#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 模型管理器（统一版本）

负责 PaddleOCR 模型的自动下载、缓存管理和按需加载。

主要功能：
- 自动下载 PaddleOCR 模型
- 模型缓存管理（清理旧模型、更新检查）
- 按需加载模型（必需模型 + 可选模型）
- 模型版本管理
- 下载进度通知

Author: Umi-OCR Team
Date: 2026-01-26
Update: 2026-01-26 - 统一模型定义，添加语言验证
"""

import os
import json
import shutil
import threading
import hashlib
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from PySide6.QtCore import QObject, Signal

# 导入官方模型配置
from .model_download_config import (
    ALL_MODELS,
    TEXT_DETECTION_MODELS,
    TEXT_RECOGNITION_MODELS,
    ORIENTATION_MODELS,
    DOC_UNWARPING_MODELS,
    LAYOUT_DETECTION_MODELS,
    LAYOUT_BLOCK_MODELS,
    LAYOUT_TABLE_MODELS,
    LAYOUT_EN_MODELS,
    LAYOUT_3CLS_MODELS,
    LAYOUT_17CLS_MODELS,
    TABLE_STRUCTURE_MODELS,
    TABLE_CELLS_MODELS,
    TABLE_CLASSIFICATION_MODELS,
    FORMULA_RECOGNITION_MODELS,
    DOC_VLM_MODELS,
    MODEL_PRESETS,
    get_model_by_id,
    get_preset_by_id,
)


logger = logging.getLogger(__name__)


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
            "download_time": self.download_time.isoformat()
            if self.download_time
            else None,
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


# =============================================================================
# 模型仓库配置（统一版本）
# =============================================================================


class ModelRepository:
    """
    模型仓库

    统一的模型仓库，引用 model_download_config 的完整模型定义。
    """

    # ========== 为什么保留 v4 模型？ ==========
    #
    # PP-OCRv5 是 PaddleOCR 3.x 的最新版本（2025年发布）
    # 相比 v4，v5 的主要改进：
    #   - 精度提升 13%（中英文混合识别）
    #   - 手写文本错误率降低 26%
    #   - 支持更多语言（109 种 vs 80+ 种）
    #   - 更大的字典（识别更多字符）
    #
    # 然而，保留 v4 模型的原因：
    #
    # 1. 向后兼容性
    #    - 现有用户的配置可能使用 v4
    #    - v4 模型已经在生产环境验证过，更稳定
    #    - 某些场景下，v4 的精度可能与 v5 相当或更好
    #
    # 2. 特定语言支持
    #    - 某些语言可能在 v4 上有更好的支持
    #    - 部分语种的模型可能只有 v4 版本
    #
    # 3. 性能考虑
    #    - v4 模型在某些硬件上可能有更优的性能
    #    - 用户可以根据场景选择速度 vs 精度
    #
    # 4. 渐进迁移策略
    #    - 保留 v4 允许用户平滑迁移到 v5
    #    - 可以通过 A/B 测试对比两个版本的效果
    #    - 避免"一刀切"强制升级可能带来的问题
    #
    # 推荐使用：
    #   - 新项目：默认使用 PP-OCRv5
    #   - 生产环境：建议使用 v5（精度提升）
    #   - 需要稳定：可以选择 v4（经验证）
    #   - 特定场景：根据实际测试结果选择
    #
    # 注：PP-OCRv3 已标记为 deprecated，不建议使用
    # ===================================================================

    # 官方模型配置（引用 model_download_config）
    ALL_MODELS = ALL_MODELS  # 所有模型定义

    # ========== 推荐模型选择策略 ==========
    #
    # 策略 1: 默认使用最新版本
    #   - 中文：默认使用 PP-OCRv5_server_rec
    #   - 英文：默认使用 en_PP-OCRv5_mobile_rec (如果可用)
    #   - 多语言：使用统一的多语言模型
    #
    # 策略 2: 向后兼容
    #   - 如果用户配置明确指定 v4，使用 v4
    #   - 如果未指定，使用 v5
    #
    # 策略 3: 功能驱动
    #   - 表格识别：使用 SLANeXt 系列（v5 对应）
    #   - 版面分析：使用 PP-DocLayout_plus-L
    #   - 公式识别：使用 PP-FormulaNet_plus 系列
    #
    # ===================================================================

    # ========== 语言映射说明 ==========
    #
    # PaddleOCR 3.3.0 支持的语言代码（2025官方文档）：
    #
    # 统一模型（PP-OCRv5 统一支持）：
    #   - "ch": 简体中文（自动支持繁体、英文、日文、韩文、拼音）
    #   - "en": 英文
    #   - "japan": 日文
    #   - "korean": 韩文
    #   - "cyrillic": 西里尔字母语族（20+ 种语言）
    #   - "latin": 拉丁语系（37+ 种语言）
    #   - "arabic": 阿拉伯语系
    #   - "devanagari": 印地语系
    #   - "th": 泰语
    #   - "el": 希腊语
    #
    # 语言组模型（单独优化的模型）：
    #   - "korean_PP-OCRv5_mobile_rec": 韩文优化 (+65% 精度)
    #   - "latin_PP-OCRv5_mobile_rec": 拉丁语系 (37 种语言，+46.8% 精度)
    #   - "eslav_PP-OCRv5_mobile_rec": 东斯拉夫语族 (俄、乌、白俄等，+31.4%)
    #   - "th_PP-OCRv5_mobile_rec": 泰语优化 (82.68% 精度)
    #   - "el_PP-OCRv5_mobile_rec": 希腊语优化 (89.28% 精度)
    #   - "arabic_PP-OCRv5_mobile_rec": 阿拉伯语系 (+22.83% 精度)
    #   - "devanagari_PP-OCRv5_mobile_rec": 印地语系 (+68.26% 精度)
    #   - "ta_PP-OCRv5_mobile_rec": 泰米尔语 (94.2% 精度)
    #   - "te_PP-OCRv5_mobile_rec": 泰卢固语 (87.65% 精度)
    #
    # 单一语言模型（v4 时代）：
    #   - "fr": 法文
    #   - "de": 德文
    #   - "es": 西班牙文
    #   - ... （80+ 种单一语言模型）
    #
    # 注：PP-OCRv5 的统一模型是未来趋势，可以处理多语言混合场景。
    #     但对于单一语言的批量处理，专用优化模型可能更高效。
    # ===================================================================

    @classmethod
    def get_model_info(cls, model_name: str) -> Optional[Dict]:
        """
        获取模型信息

        Args:
            model_name: 模型名称

        Returns:
            Optional[Dict]: 模型信息字典（兼容旧格式）
        """
        # 尝试从 model_download_config 获取模型信息
        model = get_model_by_id(model_name)
        if model:
            return {
                "name": model.name,
                "type": model.category.value,
                "version": cls._extract_version(model.name),
                "language": model.language,
                "required": True,  # 默认必需
                "url": model.download_url,
                "md5": None,  # 配置中未提供
                "display_name": model.display_name,
                "description": model.description,
                "size_mb": model.size_mb,
            }
        return None

    @classmethod
    def _extract_version(cls, model_name: str) -> str:
        """
        从模型名称提取版本号

        Args:
            model_name: 模型名称

        Returns:
            str: 版本号（"v4", "v5", "v2.0", "3.0.0" 等）
        """
        if "PP-OCRv5" in model_name or "PP-OCRv5" in model_name:
            return "v5"
        elif "PP-OCRv4" in model_name or "PP-OCRv4" in model_name:
            return "v4"
        elif "PP-OCRv3" in model_name or "PP-OCRv3" in model_name:
            return "v3"
        elif "SVTRv2" in model_name or "SVTRv2" in model_name:
            return "v2"
        elif "FormulaNet" in model_name or "FormulaNet" in model_name:
            return "plus" if "plus" in model_name else "v1"
        elif "PP-DocBee" in model_name or "PP-DocBee" in model_name:
            return "vlm"
        else:
            return "unknown"

    @classmethod
    def get_models_by_language(cls, language: str) -> List[str]:
        """
        按语言获取模型列表

        Args:
            language: 语言代码（如 "ch", "en"）

        Returns:
            List[str]: 模型名称列表
        """
        language_models = []

        for model_id, model in ALL_MODELS.items():
            # 检查模型语言是否匹配
            if model.language == language or model.language == "multilingual":
                # 特殊处理：PP-OCRv5 统一模型支持多语言
                if model.language == "ch" and language in [
                    "ch",
                    "en",
                    "japan",
                    "korean",
                    "cyrillic",
                ]:
                    language_models.append(model.name)
                elif model.language == language:
                    language_models.append(model.name)

        return language_models

    @classmethod
    def get_required_models(cls, language: str = "ch") -> List[str]:
        """
        获取核心OCR必需模型列表

        Args:
            language: 语言代码

        Returns:
            List[str]: 必需模型名称列表
        """
        # 核心OCR通常需要：检测 + 识别
        required_models = []

        # 获取检测模型
        for model_id, model in TEXT_DETECTION_MODELS.items():
            if model.language == language or model.language == "multilingual":
                required_models.append(model.name)
                break  # 只需要一个检测模型

        # 获取识别模型
        for model_id, model in TEXT_RECOGNITION_MODELS.items():
            if model.language == language or model.language == "multilingual":
                required_models.append(model.name)
                break  # 只需要一个识别模型

        return required_models

    @classmethod
    def get_models_by_version(cls, version: str) -> List[str]:
        """
        按版本获取模型列表

        Args:
            version: 版本号（"v3", "v4", "v5"）

        Returns:
            List[str]: 该版本的模型名称列表
        """
        version_models = []

        for model_id, model in ALL_MODELS.items():
            model_version = cls._extract_version(model.name)
            if model_version == version:
                version_models.append(model.name)

        return version_models

    @classmethod
    def get_latest_models(cls) -> List[str]:
        """
        获取最新版本的模型列表（v5）

        Returns:
            List[str]: v5 模型名称列表
        """
        return cls.get_models_by_version("v5")

    @classmethod
    def validate_language_code(cls, language: str) -> Tuple[bool, Optional[str]]:
        """
        验证语言代码是否有效

        Args:
            language: 语言代码

        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误信息)
        """
        # ========== 官方 PaddleOCR 3.3.0 支持的语言 ==========
        #
        # 统一模型（PP-OCRv5 统一支持 5 种文字类型）：
        VALID_UNIFIED_MODELS = [
            "ch",  # 简体中文（自动支持繁体、英文、日文、韩文、拼音）
            "en",  # 英文
            "japan",  # 日文
            "korean",  # 韩文
        ]
        #
        # 语言组（专用优化模型）：
        VALID_LANGUAGE_GROUPS = [
            "cyrillic",  # 西里尔字母语族（20+ 种语言）
            "latin",  # 拉丁语系（37+ 种语言）
            "arabic",  # 阿拉伯语系
            "devanagari",  # 印地语系
        ]
        #
        # 单一语言模型（PP-OCRv5 多语言扩展，109 种语言）：
        VALID_SINGLE_LANGUAGES = [
            # 拉丁语系（欧洲语言）
            "af",
            "az",
            "bs",
            "cs",
            "cy",
            "da",
            "de",
            "es",
            "et",
            "fi",
            "fr",
            "ga",
            "hr",
            "hu",
            "is",
            "it",
            "lt",
            "lv",
            "mi",
            "ms",
            "nl",
            "no",
            "oc",
            "pi",
            "pl",
            "pt",
            "ro",
            "rs_latin",
            "sk",
            "sl",
            "sq",
            "sv",
            "tr",
            "vi",
            # 西里尔字母（斯拉夫语言）
            "be",
            "bg",
            "mk",
            "ru",
            "uk",
            "sr",
            # 亚洲语言
            "id",
            "ku",
            "la",
            "ms",
            "ta",
            "te",
            # 阿拉伯语系
            "ar",
            "fa",
            "ug",
            "ur",
            # 印地语系
            "hi",
            "mr",
            "ne",
            "bh",
            "mai",
            "ang",
            "bho",
            "mah",
            # 其他
            "sw",
            "uz",
            # 泰语、希腊语等
            "th",
            "el",
        ]
        #
        # ========== 已弃用或不推荐的语言 ==========
        #
        # 以下语言代码在旧文档中出现，但建议避免使用：
        #   - "flemish" (已弃用，使用 "nl" 代替)
        #   - "german" (已弃用，使用 "de" 代替)
        #   - "english" (别名，使用 "en" 代替)
        #   - "chinese" (别名，使用 "ch" 代替)
        #   - "japanese" (别名，使用 "japan" 代替)
        #
        DEPRECATED_LANGUAGES = ["flemish", "german", "english", "chinese", "japanese"]

        # 合并所有有效语言代码
        all_valid = (
            VALID_UNIFIED_MODELS + VALID_LANGUAGE_GROUPS + VALID_SINGLE_LANGUAGES
        )

        # 去重
        all_valid = list(set(all_valid))

        if language not in all_valid:
            # 尝试提供有帮助的建议
            suggestion = None
            if language in DEPRECATED_LANGUAGES:
                suggestions = {
                    "flemish": "nl",
                    "german": "de",
                    "english": "en",
                    "chinese": "ch",
                    "japanese": "japan",
                }
                suggestion = suggestions.get(language)
                return False, f"语言代码 '{language}' 已弃用，建议使用 '{suggestion}'"
            else:
                # 检查是否是拼写错误
                similar = []
                if language.startswith("ch"):
                    similar.append("ch")
                elif language.startswith("en"):
                    similar.append("en")
                elif language.startswith("jp"):
                    similar.append("japan")
                elif language.startswith("ko"):
                    similar.append("korean")

                if similar:
                    return (
                        False,
                        f"未知的语言代码 '{language}'，可能想使用：{', '.join(similar)}",
                    )
                else:
                    return False, f"未知的语言代码 '{language}'"

        return True, None

    @classmethod
    def get_language_info(cls, language: str) -> Optional[Dict]:
        """
        获取语言详细信息

        Args:
            language: 语言代码

        Returns:
            Optional[Dict]: 语言信息（包括支持的语言族）
        """
        language_map = {
            # 统一模型（PP-OCRv5 统一支持）
            "ch": {
                "name": "简体中文",
                "family": "Chinese",
                "supported": ["简体中文", "繁体中文", "英文", "日文", "韩文", "拼音"],
                "model_type": "unified",
            },
            "en": {
                "name": "English",
                "family": "Germanic",
                "supported": ["English"],
                "model_type": "unified",
            },
            "japan": {
                "name": "日本語",
                "family": "Japanese",
                "supported": ["Japanese"],
                "model_type": "unified",
            },
            "korean": {
                "name": "한국어",
                "family": "Korean",
                "supported": ["Korean"],
                "model_type": "unified",
            },
            # 语言组
            "cyrillic": {
                "name": "Cyrillic Languages",
                "family": "Slavic",
                "supported": [
                    "俄语",
                    "乌克兰语",
                    "白俄罗斯语",
                    "保加利亚语",
                    "塞尔维亚语",
                    "马其顿语",
                    "哈萨克语",
                    "吉尔吉斯语",
                    "塔吉克语",
                    "蒙古语",
                    "等 20+ 种语言",
                ],
                "model_type": "optimized_group",
            },
            "latin": {
                "name": "Latin Languages",
                "family": "Indo-European",
                "supported": [
                    "法文",
                    "德文",
                    "西班牙文",
                    "意大利文",
                    "葡萄牙文",
                    "荷兰文",
                    "波兰文",
                    "捷克文",
                    "瑞典文",
                    "挪威文",
                    "芬兰文",
                    "等 37+ 种欧洲语言",
                ],
                "model_type": "optimized_group",
            },
            "arabic": {
                "name": "Arabic Languages",
                "family": "Semitic",
                "supported": [
                    "阿拉伯语",
                    "波斯语",
                    "乌尔都语",
                    "普什图语",
                    "维吾尔语",
                    "哈萨克语(阿拉伯)",
                    "等 20+ 种语言",
                ],
                "model_type": "optimized_group",
            },
            "devanagari": {
                "name": "Devanagari Languages",
                "family": "Indo-Aryan",
                "supported": [
                    "印地语",
                    "马拉地语",
                    "尼泊尔语",
                    "孟加拉语",
                    "梵语",
                    "等 10+ 种印度语言",
                ],
                "model_type": "optimized_group",
            },
            # 单一语言（109 种语言扩展）
            "th": {
                "name": "泰语",
                "family": "Kra-Dai",
                "supported": ["泰语"],
                "model_type": "single_optimized",
            },
            "el": {
                "name": "Ελληνικά (Greek)",
                "family": "Hellenic",
                "supported": ["希腊语"],
                "model_type": "single_optimized",
            },
        }

        return language_map.get(language)

    @classmethod
    def get_preset_info(cls, preset_id: str) -> Optional[Dict]:
        """
        获取预设组合信息

        Args:
            preset_id: 预设ID

        Returns:
            Optional[Dict]: 预设信息
        """
        preset = get_preset_by_id(preset_id)
        if preset:
            return {
                "id": preset.id,
                "name": preset.name,
                "description": preset.description,
                "models": preset.models,
                "total_size_mb": preset.total_size_mb,
                "recommended_for": preset.recommended_for,
            }
        return None

    @classmethod
    def get_all_presets(cls) -> List[str]:
        """
        获取所有预设组合的ID列表

        Returns:
            List[str]: 预设ID列表
        """
        preset_ids = []
        for preset in MODEL_PRESETS.values():
            preset_ids.append(preset.id)
        return preset_ids


# =============================================================================
# 模型管理器
# =============================================================================


class PaddleModelManager(QObject):
    """
    PaddleOCR 模型管理器

    负责模型的下载、缓存、加载和管理。
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    # 下载进度信号
    # 参数: model_name (str), downloaded (int), total (int), percentage (float)
    download_progress = Signal(str, int, int, float)

    # 下载完成信号
    # 参数: model_name (str), success (bool), message (str)
    download_completed = Signal(str, bool, str)

    # 模型加载完成信号
    # 参数: model_name (str), success (bool)
    model_loaded = Signal(str, bool)

    # 缓存清理完成信号
    # 参数: cleaned_count (int), freed_space (int)
    cache_cleaned = Signal(int, int)

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        初始化模型管理器

        Args:
            cache_dir: 模型缓存目录（默认为项目根目录下的 models/）
        """
        super().__init__()

        # 缓存目录
        if cache_dir is None:
            from pathlib import Path

            project_root = Path(__file__).parent.parent.parent
            self.cache_dir = project_root / "models"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 模型信息缓存
        self._models: Dict[str, ModelInfo] = {}
        self._load_model_cache()

        # 线程安全锁
        self._lock = threading.RLock()

        # 下载会话管理
        self._active_downloads: Set[str] = set()

    # -------------------------------------------------------------------------
    # 模型缓存管理
    # -------------------------------------------------------------------------

    def _load_model_cache(self) -> None:
        """加载模型信息缓存"""
        cache_file = self.cache_dir / "model_cache.json"

        if not cache_file.exists():
            return

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for name, model_data in data.items():
                self._models[name] = ModelInfo(
                    name=model_data["name"],
                    type=ModelType(model_data["type"]),
                    version=model_data["version"],
                    language=model_data["language"],
                    url=model_data.get("url"),
                    size=model_data.get("size", 0),
                    md5=model_data.get("md5"),
                    local_path=Path(model_data["local_path"])
                    if model_data.get("local_path")
                    else None,
                    status=ModelStatus(
                        model_data.get("status", ModelStatus.NOT_DOWNLOADED)
                    ),
                    last_used=datetime.fromisoformat(model_data["last_used"])
                    if model_data.get("last_used")
                    else None,
                    download_time=datetime.fromisoformat(model_data["download_time"])
                    if model_data.get("download_time")
                    else None,
                    required=model_data.get("required", True),
                    enabled=model_data.get("enabled", True),
                    # 额外字段
                    display_name=model_data.get("display_name"),
                    description=model_data.get("description"),
                    size_mb=model_data.get("size_mb"),
                    download_url=model_data.get("download_url"),
                )

            logger.info(f"加载了 {len(self._models)} 个模型的缓存信息")

        except Exception as e:
            logger.error(f"加载模型缓存失败: {e}", exc_info=True)

    def _save_model_cache(self) -> None:
        """保存模型信息缓存"""
        cache_file = self.cache_dir / "model_cache.json"

        try:
            data = {name: model.to_dict() for name, model in self._models.items()}

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存模型缓存失败: {e}", exc_info=True)

    def _update_model_cache(self, model_name: str, **kwargs) -> None:
        """
        更新单个模型的缓存信息

        Args:
            model_name: 模型名称
            **kwargs: 要更新的字段
        """
        if model_name not in self._models:
            return

        for key, value in kwargs.items():
            if hasattr(self._models[model_name], key):
                setattr(self._models[model_name], key, value)

        self._save_model_cache()

    # -------------------------------------------------------------------------
    # 模型下载
    # -------------------------------------------------------------------------

    def download_model(self, model_name: str, force: bool = False) -> bool:
        """
        下载模型

        Args:
            model_name: 模型名称
            force: 是否强制重新下载

        Returns:
            bool: 是否下载成功
        """
        with self._lock:
            # 检查模型是否存在
            model_info = ModelRepository.get_model_info(model_name)
            if not model_info:
                logger.error(f"未找到模型: {model_name}")
                self.download_completed.emit(
                    model_name, False, f"未找到模型: {model_name}"
                )
                return False

            # 检查是否已下载
            if model_name in self._models:
                cached_model = self._models[model_name]
                if cached_model.status == ModelStatus.DOWNLOADED and not force:
                    logger.info(f"模型 {model_name} 已存在，跳过下载")
                    self.download_completed.emit(model_name, True, "模型已存在")
                    return True

            # 检查是否正在下载
            if model_name in self._active_downloads:
                logger.info(f"模型 {model_name} 正在下载中")
                return False

            # 添加到下载列表
            self._active_downloads.add(model_name)

        # 执行下载（异步）
        import threading

        thread = threading.Thread(
            target=self._download_model_thread, args=(model_name, model_info, force)
        )
        thread.daemon = True
        thread.start()

        return True

    def _download_model_thread(
        self, model_name: str, model_info: Dict, force: bool
    ) -> None:
        """
        下载模型（线程函数）

        Args:
            model_name: 模型名称
            model_info: 模型信息
            force: 是否强制重新下载
        """
        try:
            # 更新状态为下载中
            with self._lock:
                if model_name not in self._models:
                    self._models[model_name] = ModelInfo(
                        name=model_name,
                        type=ModelType(model_info["type"]),
                        version=model_info["version"],
                        language=model_info["language"],
                        url=model_info["url"],
                        required=model_info.get("required", True),
                        status=ModelStatus.DOWNLOADING,
                    )
                else:
                    self._models[model_name].status = ModelStatus.DOWNLOADING

                self._save_model_cache()

            # 下载文件
            url = model_info.get("download_url", model_info["url"])
            target_path = self.cache_dir / f"{model_name}.tar"

            logger.info(f"开始下载模型: {model_name} from {url}")

            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))

            # 写入文件
            with open(target_path, "wb") as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # 发送进度信号
                        if total_size > 0:
                            percentage = (downloaded / total_size) * 100
                            self.download_progress.emit(
                                model_name, downloaded, total_size, percentage
                            )

            # 更新模型信息
            with self._lock:
                self._models[model_name].status = ModelStatus.DOWNLOADED
                self._models[model_name].local_path = target_path
                self._models[model_name].size = downloaded
                self._models[model_name].download_time = datetime.now()
                self._save_model_cache()

            logger.info(f"模型 {model_name} 下载完成")
            self.download_completed.emit(model_name, True, "下载成功")

        except Exception as e:
            logger.error(f"下载模型 {model_name} 失败: {e}", exc_info=True)

            with self._lock:
                if model_name in self._models:
                    self._models[model_name].status = ModelStatus.ERROR
                    self._save_model_cache()

            self.download_completed.emit(model_name, False, str(e))

        finally:
            with self._lock:
                self._active_downloads.discard(model_name)

    def cancel_download(self, model_name: str) -> bool:
        """
        取消下载

        Args:
            model_name: 模型名称

        Returns:
            bool: 是否成功取消
        """
        # TODO: 实现下载取消
        return False

    # -------------------------------------------------------------------------
    # 模型加载
    # -------------------------------------------------------------------------

    def load_model(self, model_name: str) -> Optional[Path]:
        """
        加载模型

        Args:
            model_name: 模型名称

        Returns:
            Optional[Path]: 模型路径（如果加载成功）
        """
        with self._lock:
            # 检查模型是否存在
            if model_name not in self._models:
                logger.error(f"模型未找到: {model_name}")
                self.model_loaded.emit(model_name, False)
                return None

            model = self._models[model_name]

            # 检查模型状态
            if model.status == ModelStatus.LOADED:
                logger.info(f"模型 {model_name} 已加载")
                self.model_loaded.emit(model_name, True)
                return model.local_path

            if model.status == ModelStatus.NOT_DOWNLOADED:
                logger.warning(f"模型 {model_name} 未下载")
                self.model_loaded.emit(model_name, False)
                return None

            # 模型已下载，标记为已加载
            if model.status == ModelStatus.DOWNLOADED:
                model.status = ModelStatus.LOADED
                model.last_used = datetime.now()
                self._save_model_cache()

                logger.info(f"模型 {model_name} 加载成功")
                self.model_loaded.emit(model_name, True)
                return model.local_path

            return None

    def unload_model(self, model_name: str) -> None:
        """
        卸载模型

        Args:
            model_name: 模型名称
        """
        with self._lock:
            if model_name in self._models:
                self._models[model_name].status = ModelStatus.DOWNLOADED
                self._save_model_cache()

    # -------------------------------------------------------------------------
    # 缓存清理
    # -------------------------------------------------------------------------

    def clean_cache(
        self, max_age_days: int = 30, max_size_gb: float = 10.0
    ) -> Tuple[int, int]:
        """
        清理模型缓存

        Args:
            max_age_days: 最大保留天数
            max_size_gb: 最大缓存大小（GB）

        Returns:
            Tuple[int, int]: (清理的模型数, 释放的空间MB）
        """
        import time

        with self._lock:
            cleaned_count = 0
            freed_space = 0

            # 计算总大小
            total_size = sum(model.size for model in self._models.values())
            total_size_gb = total_size / (1024**3)

            # 检查时间
            now = datetime.now()

            for name, model in list(self._models.items()):
                # 跳过必需模型
                if model.required:
                    continue

                # 检查年龄
                if model.last_used:
                    age_days = (now - model.last_used).days
                elif model.download_time:
                    age_days = (now - model.download_time).days
                else:
                    age_days = 0

                # 决定是否清理
                should_clean = False

                # 超过最大天数
                if age_days > max_age_days:
                    should_clean = True
                    logger.info(f"清理过期模型: {name} (未使用 {age_days} 天)")

                # 超过最大大小
                elif total_size_gb > max_size_gb:
                    # 清理最久未使用的模型
                    should_clean = True
                    logger.info(f"清理模型以释放空间: {name}")

                if should_clean:
                    # 删除文件
                    if model.local_path and model.local_path.exists():
                        freed_space += model.size
                        shutil.rmtree(model.local_path.parent, ignore_errors=True)

                    # 从缓存中移除
                    del self._models[name]
                    cleaned_count += 1

                    # 重新计算总大小
                    total_size = sum(model.size for model in self._models.values())
                    total_size_gb = total_size / (1024**3)

            # 保存缓存
            self._save_model_cache()

            # 发送信号
            self.cache_cleaned.emit(cleaned_count, freed_space // (1024 * 1024))

            logger.info(
                f"缓存清理完成: 清理了 {cleaned_count} 个模型，释放了 {freed_space // (1024 * 1024)} MB"
            )

            return cleaned_count, freed_space // (1024 * 1024)

    # -------------------------------------------------------------------------
    # 模型查询
    # -------------------------------------------------------------------------

    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """
        获取模型信息

        Args:
            model_name: 模型名称

        Returns:
            Optional[ModelInfo]: 模型信息
        """
        return self._models.get(model_name)

    def list_models(self, status: Optional[ModelStatus] = None) -> List[ModelInfo]:
        """
        列出模型

        Args:
            status: 状态过滤器（None 表示不过滤）

        Returns:
            List[ModelInfo]: 模型列表
        """
        models = list(self._models.values())

        if status:
            models = [m for m in models if m.status == status]

        return models

    def get_cache_size(self) -> int:
        """
        获取缓存大小（字节）

        Returns:
            int: 缓存大小（字节）
        """
        return sum(model.size for model in self._models.values())


# =============================================================================
# 全局模型管理器实例
# =============================================================================

_global_model_manager: Optional[PaddleModelManager] = None


def get_model_manager(cache_dir: Optional[Path] = None) -> PaddleModelManager:
    """
    获取全局模型管理器

    Args:
        cache_dir: 模型缓存目录

    Returns:
        PaddleModelManager: 模型管理器单例
    """
    global _global_model_manager
    if _global_model_manager is None:
        _global_model_manager = PaddleModelManager(cache_dir)
    return _global_model_manager
