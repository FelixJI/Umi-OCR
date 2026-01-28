#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型仓库

统一的模型仓库，引用 model_download_config 的完整模型定义。

Author: Umi-OCR Team
Date: 2026-01-27
"""

from typing import Dict, List, Optional, Tuple

# 导入官方模型配置
from ..model_download_config import (
    ALL_MODELS,
    TEXT_DETECTION_MODELS,
    TEXT_RECOGNITION_MODELS,
    MODEL_PRESETS,
    get_model_by_id,
    get_preset_by_id,
)


class ModelRepository:
    """
    模型仓库

    统一的模型仓库，引用 model_download_config 的完整模型定义。
    """

    # 官方模型配置（引用 model_download_config）
    ALL_MODELS = ALL_MODELS

    @classmethod
    def get_model_info(cls, model_name: str) -> Optional[Dict]:
        """
        获取模型信息

        Args:
            model_name: 模型名称

        Returns:
            Optional[Dict]: 模型信息字典（兼容旧格式）
        """
        model = get_model_by_id(model_name)
        if model:
            return {
                "name": model.name,
                "type": model.category.value,
                "version": cls._extract_version(model.name),
                "language": model.language,
                "required": True,
                "url": model.download_url,
                "md5": None,
                "display_name": model.display_name,
                "description": model.description,
                "size_mb": model.size_mb,
            }
        return None

    @classmethod
    def _extract_version(cls, model_name: str) -> str:
        """从模型名称提取版本号"""
        if "PP-OCRv5" in model_name:
            return "v5"
        elif "PP-OCRv4" in model_name:
            return "v4"
        elif "PP-OCRv3" in model_name:
            return "v3"
        elif "SVTRv2" in model_name:
            return "v2"
        elif "FormulaNet" in model_name:
            return "plus" if "plus" in model_name else "v1"
        elif "PP-DocBee" in model_name:
            return "vlm"
        else:
            return "unknown"

    @classmethod
    def get_models_by_language(cls, language: str) -> List[str]:
        """按语言获取模型列表"""
        language_models = []

        for model_id, model in ALL_MODELS.items():
            if model.language == language or model.language == "multilingual":
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
        """获取核心OCR必需模型列表"""
        required_models = []

        for model_id, model in TEXT_DETECTION_MODELS.items():
            if model.language == language or model.language == "multilingual":
                required_models.append(model.name)
                break

        for model_id, model in TEXT_RECOGNITION_MODELS.items():
            if model.language == language or model.language == "multilingual":
                required_models.append(model.name)
                break

        return required_models

    @classmethod
    def get_models_by_version(cls, version: str) -> List[str]:
        """按版本获取模型列表"""
        version_models = []

        for model_id, model in ALL_MODELS.items():
            model_version = cls._extract_version(model.name)
            if model_version == version:
                version_models.append(model.name)

        return version_models

    @classmethod
    def get_latest_models(cls) -> List[str]:
        """获取最新版本的模型列表（v5）"""
        return cls.get_models_by_version("v5")

    @classmethod
    def validate_language_code(cls, language: str) -> Tuple[bool, Optional[str]]:
        """验证语言代码是否有效"""
        # 统一模型
        VALID_UNIFIED_MODELS = ["ch", "en", "japan", "korean"]

        # 语言组
        VALID_LANGUAGE_GROUPS = ["cyrillic", "latin", "arabic", "devanagari"]

        # 单一语言模型
        VALID_SINGLE_LANGUAGES = [
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
            "be",
            "bg",
            "mk",
            "ru",
            "uk",
            "sr",
            "id",
            "ku",
            "la",
            "ta",
            "te",
            "ar",
            "fa",
            "ug",
            "ur",
            "hi",
            "mr",
            "ne",
            "bh",
            "mai",
            "ang",
            "bho",
            "mah",
            "sw",
            "uz",
            "th",
            "el",
        ]

        # 已弃用的语言
        DEPRECATED_LANGUAGES = ["flemish", "german", "english", "chinese", "japanese"]

        all_valid = list(
            set(VALID_UNIFIED_MODELS + VALID_LANGUAGE_GROUPS + VALID_SINGLE_LANGUAGES)
        )

        if language not in all_valid:
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
        """获取语言详细信息"""
        language_map = {
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
            "cyrillic": {
                "name": "Cyrillic Languages",
                "family": "Slavic",
                "supported": [
                    "俄语",
                    "乌克兰语",
                    "白俄罗斯语",
                    "保加利亚语",
                    "等 20+ 种语言",
                ],
                "model_type": "optimized_group",
            },
            "latin": {
                "name": "Latin Languages",
                "family": "Indo-European",
                "supported": ["法文", "德文", "西班牙文", "等 37+ 种欧洲语言"],
                "model_type": "optimized_group",
            },
            "arabic": {
                "name": "Arabic Languages",
                "family": "Semitic",
                "supported": ["阿拉伯语", "波斯语", "乌尔都语", "等 20+ 种语言"],
                "model_type": "optimized_group",
            },
            "devanagari": {
                "name": "Devanagari Languages",
                "family": "Indo-Aryan",
                "supported": ["印地语", "马拉地语", "尼泊尔语", "等 10+ 种印度语言"],
                "model_type": "optimized_group",
            },
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
        """获取预设组合信息"""
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
        """获取所有预设组合的ID列表"""
        return [preset.id for preset in MODEL_PRESETS.values()]
