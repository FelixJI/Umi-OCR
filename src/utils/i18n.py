#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 多语言支持系统

提供界面多语言切换功能，支持运行时动态切换语言。
使用单例模式，确保全局只有一个语言管理器实例。

主要功能：
- 从 JSON 文件加载语言包
- 支持运行时语言切换
- 支持嵌套键路径查询（如 "main_window.menu.file"）
- 语言变更信号通知（Qt Signal）
- 线程安全
- 支持占位符替换

使用示例：
    from src.utils.i18n import I18nManager

    # 获取全局语言管理器
    i18n = I18nManager.get_instance()

    # 加载默认语言
    i18n.load_language("zh_CN")

    # 获取翻译文本
    text = i18n.translate("main_window.menu.file")  # 返回 "文件(&F)"

    # 使用占位符
    text = i18n.translate("messages.welcome", {"name": "Umi-OCR"})

    # 切换语言
    i18n.set_language("en_US")

    # 监听语言变更
    i18n.language_changed.connect(lambda lang: print(f"语言已切换到: {lang}"))

Author: Umi-OCR Team
Date: 2025-01-26
"""

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional, List
from PySide6.QtCore import QObject, Signal

# 前向引用，用于类型注解
if False:
    from PySide6.QtCore import QTranslator


class I18nManager(QObject):
    """
    多语言管理器（单例模式）

    提供全局统一的多语言管理功能，支持动态语言切换。
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    # 语言变更信号
    # 参数: 新语言代码（如 "zh_CN", "en_US"）
    language_changed = Signal(str)

    # 语言包加载失败信号
    # 参数: 语言代码, 错误信息
    load_error = Signal(str, str)

    # -------------------------------------------------------------------------
    # 单例模式
    # -------------------------------------------------------------------------

    _instance: Optional["I18nManager"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "I18nManager":
        """
        实现单例模式

        Returns:
            I18nManager: 唯一的语言管理器实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self) -> None:
        """
        初始化语言管理器

        注意：由于单例模式，此方法只会被调用一次。
        """
        # 防止重复初始化
        if hasattr(self, "_initialized") and self._initialized:
            return

        super().__init__()

        self._initialized: bool = True

        # 语言包目录
        self._i18n_dir: Optional[Path] = None

        # 当前语言代码
        self._current_language: str = "zh_CN"

        # 已加载的语言包缓存
        self._translations: Dict[str, Dict[str, Any]] = {}

        # 可用语言列表
        self._available_languages: List[str] = []

        # 默认语言
        self._default_language = "zh_CN"

    # -------------------------------------------------------------------------
    # 语言包路径管理
    # -------------------------------------------------------------------------

    def set_i18n_dir(self, path: Path) -> None:
        """
        设置语言包目录

        Args:
            path: 语言包目录路径
        """
        self._i18n_dir = Path(path)

        # 扫描可用语言
        self._scan_available_languages()

    def get_i18n_dir(self) -> Optional[Path]:
        """
        获取语言包目录

        Returns:
            Optional[Path]: 语言包目录路径
        """
        return self._i18n_dir

    def _scan_available_languages(self) -> None:
        """
        扫描可用的语言包
        """
        self._available_languages.clear()

        if self._i18n_dir is None or not self._i18n_dir.exists():
            return

        # 查找所有 .json 文件
        for file in self._i18n_dir.glob("*.json"):
            # 从文件名提取语言代码（如 zh_CN.json -> zh_CN）
            lang_code = file.stem
            self._available_languages.append(lang_code)

        self._available_languages.sort()

    # -------------------------------------------------------------------------
    # 语言包加载
    # -------------------------------------------------------------------------

    def load_language(self, lang_code: str) -> bool:
        """
        加载指定语言的语言包

        Args:
            lang_code: 语言代码（如 "zh_CN", "en_US"）

        Returns:
            bool: 是否加载成功
        """
        if self._i18n_dir is None:
            error_msg = "未设置语言包目录"
            self.load_error.emit(lang_code, error_msg)
            return False

        lang_file = self._i18n_dir / f"{lang_code}.json"

        if not lang_file.exists():
            error_msg = f"语言包文件不存在: {lang_file}"
            self.load_error.emit(lang_code, error_msg)
            return False

        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                translations = json.load(f)

            # 缓存语言包
            with self._lock:
                self._translations[lang_code] = translations

            return True

        except json.JSONDecodeError as e:
            error_msg = f"语言包 JSON 格式错误: {e}"
            self.load_error.emit(lang_code, error_msg)
            return False

        except Exception as e:
            error_msg = f"加载语言包失败: {e}"
            self.load_error.emit(lang_code, error_msg)
            return False

    def load_all_languages(self) -> None:
        """
        加载所有可用语言的语言包
        """
        if self._i18n_dir is None:
            return

        for lang_code in self._available_languages:
            self.load_language(lang_code)

    # -------------------------------------------------------------------------
    # 语言切换
    # -------------------------------------------------------------------------

    def set_language(self, lang_code: str) -> bool:
        """
        切换当前语言

        Args:
            lang_code: 目标语言代码

        Returns:
            bool: 是否切换成功
        """
        # 检查语言是否已加载
        if lang_code not in self._translations:
            # 尝试加载
            if not self.load_language(lang_code):
                return False

        # 更新当前语言
        old_language = self._current_language
        self._current_language = lang_code

        # 发送语言变更信号
        self.language_changed.emit(lang_code)

        return True

    def get_language(self) -> str:
        """
        获取当前语言代码

        Returns:
            str: 当前语言代码
        """
        return self._current_language

    def get_available_languages(self) -> List[str]:
        """
        获取可用语言列表

        Returns:
            List[str]: 语言代码列表
        """
        return self._available_languages.copy()

    # -------------------------------------------------------------------------
    # 翻译查询
    # -------------------------------------------------------------------------

    def translate(self, key_path: str, **kwargs) -> str:
        """
        获取指定键的翻译文本

        Args:
            key_path: 翻译键路径（点分隔），如 "main_window.menu.file"
            **kwargs: 占位符参数，用于替换文本中的占位符

        Returns:
            str: 翻译后的文本（如果未找到，返回键路径本身）

        Examples:
            >>> i18n.translate("main_window.menu.file")
            "文件(&F)"

            >>> i18n.translate("messages.welcome", name="Umi-OCR")
            "欢迎来到 Umi-OCR"
        """
        with self._lock:
            # 获取当前语言包
            translations = self._translations.get(self._current_language, {})

            # 支持嵌套键路径（如 "main_window.menu.file"）
            keys = key_path.split(".")
            value = translations

            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    # 如果当前语言未找到，尝试使用默认语言
                    if self._current_language != self._default_language:
                        default_translations = self._translations.get(self._default_language, {})
                        value = default_translations
                        for default_key in keys:
                            if isinstance(value, dict) and default_key in value:
                                value = value[default_key]
                            else:
                                # 默认语言也未找到，返回键路径本身
                                return key_path
                        break
                    else:
                        # 返回键路径本身
                        return key_path

            # 处理占位符
            if kwargs and isinstance(value, str):
                try:
                    return value.format(**kwargs)
                except (KeyError, ValueError):
                    # 占位符替换失败，返回原文本
                    return value

            return str(value)

    def t(self, key_path: str, **kwargs) -> str:
        """
        translate 方法的简写

        Args:
            key_path: 翻译键路径
            **kwargs: 占位符参数

        Returns:
            str: 翻译后的文本
        """
        return self.translate(key_path, **kwargs)

    # -------------------------------------------------------------------------
    # 语言信息
    # -------------------------------------------------------------------------

    def get_language_name(self, lang_code: Optional[str] = None) -> str:
        """
        获取语言的显示名称

        Args:
            lang_code: 语言代码（为 None 则使用当前语言）

        Returns:
            str: 语言显示名称（如 "简体中文"）
        """
        lang = lang_code or self._current_language

        with self._lock:
            translations = self._translations.get(lang, {})
            return translations.get("language", lang)

    def get_locale(self, lang_code: Optional[str] = None) -> str:
        """
        获取语言的区域设置

        Args:
            lang_code: 语言代码（为 None 则使用当前语言）

        Returns:
            str: 区域设置（如 "zh_CN"）
        """
        lang = lang_code or self._current_language

        with self._lock:
            translations = self._translations.get(lang, {})
            return translations.get("locale", lang)

    # -------------------------------------------------------------------------
    # Qt 集成
    # -------------------------------------------------------------------------

    def get_qt_translator(self) -> "QTranslator":
        """
        获取 Qt QTranslator 对象（用于 Qt 内置组件的翻译）

        Returns:
            QTranslator: Qt 翻译器对象

        注意：此功能用于翻译 Qt 内置组件（如对话框、按钮等）。
              需要配合 Qt 的 .qm 文件使用。
        """
        from PySide6.QtCore import QTranslator
        from PySide6.QtCore import QLocale

        translator = QTranslator()

        # 尝试加载 Qt 的官方翻译文件
        # 这些文件通常位于 Qt 安装目录的 translations/ 下
        qt_locale = QLocale(self.get_locale())
        translator.load(qt_locale, "qtbase_", "_", ":/i18n")

        return translator

    # -------------------------------------------------------------------------
    # 工具方法
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "I18nManager":
        """
        获取语言管理器单例

        Returns:
            I18nManager: 语言管理器实例
        """
        return cls()

    def is_loaded(self, lang_code: str) -> bool:
        """
        检查指定语言是否已加载

        Args:
            lang_code: 语言代码

        Returns:
            bool: 是否已加载
        """
        return lang_code in self._translations

    def reload_language(self, lang_code: str) -> bool:
        """
        重新加载指定语言的语言包

        Args:
            lang_code: 语言代码

        Returns:
            bool: 是否重载成功
        """
        # 从缓存中移除
        with self._lock:
            if lang_code in self._translations:
                del self._translations[lang_code]

        # 重新加载
        return self.load_language(lang_code)

    def clear_cache(self) -> None:
        """清除所有语言包缓存"""
        with self._lock:
            self._translations.clear()


# =============================================================================
# 全局语言管理器实例
# =============================================================================

_global_i18n_manager: Optional[I18nManager] = None


def get_i18n_manager() -> I18nManager:
    """
    获取全局语言管理器

    Returns:
        I18nManager: 语言管理器单例

    使用示例：
        from src.utils.i18n import get_i18n_manager

        i18n = get_i18n_manager()
        i18n.load_language("zh_CN")
        text = i18n.translate("main_window.menu.file")
    """
    global _global_i18n_manager
    if _global_i18n_manager is None:
        _global_i18n_manager = I18nManager.get_instance()
    return _global_i18n_manager


# 默认导出的翻译函数（快捷方式）
def t(key_path: str, **kwargs) -> str:
    """
    翻译快捷函数

    Args:
        key_path: 翻译键路径
        **kwargs: 占位符参数

    Returns:
        str: 翻译后的文本

    使用示例：
        from src.utils.i18n import t

        print(t("main_window.menu.file"))
        print(t("messages.welcome", name="Umi-OCR"))
    """
    return get_i18n_manager().translate(key_path, **kwargs)
