#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 应用程序类

这是新架构的应用程序类，负责：
1. QApplication 的初始化
2. 全局配置的加载
3. 日志系统的初始化
4. 多语言支持的初始化
5. 应用程序级别的设置

Author: Umi-OCR Team
Date: 2025-01-25
"""

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QLocale, QTranslator


class UmiApplication(QApplication):
    """
    Umi-OCR 应用程序主类

    继承自 QApplication，提供应用程序级别的初始化和管理功能
    """

    def __init__(self, argv):
        """
        初始化应用程序

        Args:
            argv: 命令行参数列表
        """
        super().__init__(argv)

        # 设置应用程序属性
        self._setup_application_attributes()

        # 启用高 DPI 缩放
        self._setup_high_dpi()

        # 初始化路径
        self._init_paths()

        # 初始化日志系统（阶段2）
        self._init_logger()

        # 初始化配置管理器（阶段3）
        self._init_config()

        # 初始化多语言支持（阶段4）
        self._init_i18n()

    def _setup_application_attributes(self):
        """设置应用程序的基本属性"""
        self.setApplicationName("Umi-OCR")
        self.setApplicationVersion("2.0.0")  # 新架构版本
        self.setOrganizationName("Umi-OCR Team")
        self.setOrganizationDomain("umi-ocr.com")

    def _setup_high_dpi(self):
        """
        配置高 DPI 缩放设置

        Qt6 默认支持高 DPI，这里可以额外配置
        """
        # Qt6 默认启用高 DPI 缩放
        # 可以通过环境变量自定义行为
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
        os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

    def _init_paths(self):
        """
        初始化应用程序路径

        定义项目根目录、资源目录、数据目录等关键路径
        """
        # 项目根目录（src 的父目录）
        self.project_root = Path(__file__).parent.parent

        # 源代码目录
        self.source_dir = self.project_root / "src"

        # 资源目录（项目根目录下的 resources/）
        self.resources_dir = self.project_root / "resources"

        # 用户数据目录
        if sys.platform == "win32":
            # Windows: 使用项目目录下的 UmiOCR-data/
            self.data_dir = self.project_root / "UmiOCR-data"
        else:
            # Linux/Mac: 使用用户主目录下的 .umi-ocr/
            self.data_dir = Path.home() / ".umi-ocr"

        # 确保数据目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 日志目录
        self.logs_dir = self.data_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # 缓存目录
        self.cache_dir = self.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 配置文件路径
        self.config_file = self.data_dir / "config.json"

        # 日志文件路径
        self.log_file = self.logs_dir / "umi_ocr.log"

    def _init_logger(self):
        """
        初始化日志系统（阶段2已完成）

        初始化全局日志记录器，用于应用程序的日志输出。
        """
        from src.utils.logger import Logger

        # 设置日志目录
        Logger.LOGS_DIR = str(self.logs_dir)

        # 获取日志记录器实例（单例）
        self.logger = Logger.get_instance()

        # 记录应用程序启动
        self.logger.info("=" * 50)
        self.logger.info("应用程序启动")
        self.logger.info(f"版本: {self.applicationVersion()}")
        self.logger.info(f"数据目录: {self.data_dir}")

        # 安装 Qt 消息处理器，将 Qt 日志重定向到日志系统
        from PySide6.QtCore import qInstallMessageHandler
        qInstallMessageHandler(self.logger.get_qt_message_handler())

    def _init_config(self):
        """
        初始化配置管理器（阶段3已完成）

        加载应用程序配置，提供配置读写和变更通知功能。
        """
        from src.utils.config_manager import ConfigManager

        # 获取配置管理器实例（单例）
        self.config_manager = ConfigManager.get_instance()

        # 设置配置文件路径
        self.config_manager.set_config_path(self.config_file)

        # 加载配置文件（如果不存在会创建默认配置）
        if self.config_manager.load():
            self.logger.info(f"配置文件加载成功: {self.config_file}")
        else:
            self.logger.warning(f"使用默认配置，将创建新文件: {self.config_file}")

        # 根据配置设置日志级别
        log_level = self.config_manager.get("system.log_level", "info")
        self.logger.set_file_log_level(log_level.upper())
        self.logger.info(f"文件日志级别: {log_level}")

        # 连接配置变更信号
        self.config_manager.config_changed.connect(self._on_config_changed)
        self.config_manager.config_saved.connect(self._on_config_saved)
        self.config_manager.config_error.connect(self._on_config_error)

    def _on_config_changed(self, key_path: str, old_value, new_value):
        """
        配置变更回调

        Args:
            key_path: 变化的配置路径
            old_value: 旧值
            new_value: 新值
        """
        self.logger.debug(f"配置变更: {key_path} = {new_value} (原值: {old_value})")

    def _on_config_saved(self, file_path: str):
        """
        配置保存回调

        Args:
            file_path: 保存的文件路径
        """
        self.logger.info(f"配置已保存: {file_path}")

    def _on_config_error(self, error_msg: str):
        """
        配置错误回调

        Args:
            error_msg: 错误信息
        """
        self.logger.error(f"配置错误: {error_msg}")

    def _init_i18n(self):
        """
        初始化多语言支持（阶段4）

        加载语言包，提供多语言切换功能。
        """
        from src.utils.i18n import I18nManager

        # 获取语言管理器实例（单例）
        self.i18n = I18nManager.get_instance()

        # 设置语言包目录
        i18n_dir = self.resources_dir / "i18n"
        self.i18n.set_i18n_dir(i18n_dir)
        self.logger.info(f"语言包目录: {i18n_dir}")

        # 加载所有可用语言
        self.i18n.load_all_languages()
        available_languages = self.i18n.get_available_languages()
        self.logger.info(f"可用语言: {', '.join(available_languages)}")

        # 从配置中读取首选语言，或使用系统默认语言
        preferred_language = self.config_manager.get("ui.language", "zh_CN")

        # 尝试加载首选语言
        if preferred_language in available_languages:
            self.i18n.set_language(preferred_language)
        else:
            # 使用默认语言
            self.i18n.set_language("zh_CN")
            self.logger.warning(f"未找到首选语言 {preferred_language}，使用默认语言")

        # 记录当前语言
        current_lang = self.i18n.get_language()
        lang_name = self.i18n.get_language_name()
        self.logger.info(f"当前语言: {current_lang} ({lang_name})")

        # 连接语言变更信号
        self.i18n.language_changed.connect(self._on_language_changed)
        self.i18n.load_error.connect(self._on_i18n_load_error)

    def _on_language_changed(self, lang_code: str):
        """
        语言变更回调

        Args:
            lang_code: 新语言代码
        """
        lang_name = self.i18n.get_language_name(lang_code)
        self.logger.info(f"语言已切换: {lang_code} ({lang_name})")

        # 更新配置
        self.config_manager.set("ui.language", lang_code)

        # TODO: 在后续阶段中，通知所有 UI 组件更新文本
        # 例如：self.ui.update_translations()

    def _on_i18n_load_error(self, lang_code: str, error_msg: str):
        """
        语言包加载错误回调

        Args:
            lang_code: 语言代码
            error_msg: 错误信息
        """
        self.logger.error(f"加载语言包失败 [{lang_code}]: {error_msg}")

    def get_resource_path(self, relative_path):
        """
        获取资源文件的完整路径

        Args:
            relative_path: 相对于 resources/ 的路径

        Returns:
            Path: 资源文件的完整路径
        """
        return self.resources_dir / relative_path

    def get_data_path(self, relative_path=""):
        """
        获取数据目录的完整路径

        Args:
            relative_path: 相对于数据目录的路径

        Returns:
            Path: 数据目录的完整路径
        """
        if relative_path:
            return self.data_dir / relative_path
        return self.data_dir


# 创建全局应用程序实例的访问点
_app_instance = None


def get_app_instance():
    """
    获取全局应用程序实例

    Returns:
        UmiApplication: 全局唯一的应用程序实例
    """
    global _app_instance
    return _app_instance


def set_app_instance(app):
    """
    设置全局应用程序实例

    Args:
        app: UmiApplication 实例
    """
    global _app_instance
    _app_instance = app
