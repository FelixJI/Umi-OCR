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

        # 初始化日志系统（在后续阶段实现）
        # self._init_logger()

        # 初始化配置管理器（在后续阶段实现）
        # self._init_config()

        # 初始化多语言支持（在后续阶段实现）
        # self._init_i18n()

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
        初始化日志系统

        在阶段2实现此功能
        """
        # TODO: 在阶段2实现
        # from src.utils.logger import Logger
        # self.logger = Logger.get_instance()
        # self.logger.info("应用程序启动")
        pass

    def _init_config(self):
        """
        初始化配置管理器

        在阶段3实现此功能
        """
        # TODO: 在阶段3实现
        # from src.utils.config_manager import ConfigManager
        # self.config_manager = ConfigManager.get_instance()
        # self.config_manager.load()
        pass

    def _init_i18n(self):
        """
        初始化多语言支持

        在阶段4实现此功能
        """
        # TODO: 在阶段4实现
        # from src.utils.i18n import I18nManager
        # self.i18n = I18nManager.get_instance()
        # self.i18n.load_language("zh_CN")
        pass

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
