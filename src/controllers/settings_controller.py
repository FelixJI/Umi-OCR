#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 设置控制器

负责处理设置界面的逻辑，连接 UI 和 ConfigManager。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import Dict, Any

from PySide6.QtCore import QObject, Signal

from src.utils.config_manager import get_config_manager
from src.utils.credential_manager import CredentialManager
from src.services.ocr.engine_manager import EngineManager

# 创建凭证管理器实例
global_credential_manager = CredentialManager()

logger = logging.getLogger(__name__)


class SettingsController(QObject):
    """
    设置控制器
    """

    config_changed = Signal(str, object)  # 配置变更信号 (key, new_value)

    def __init__(self):
        super().__init__()
        self._config_manager = get_config_manager()
        self._engine_manager = EngineManager

        # Connect to config manager signal if available
        # self._config_manager.config_changed.connect(self._on_config_changed)

        logger.info("设置控制器初始化完成")

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置"""
        return self._config_manager.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """设置配置"""
        self._config_manager.set(key, value)
        self.config_changed.emit(key, value)

    def get_all_engines(self) -> Dict[str, Any]:
        """获取所有引擎"""
        return self._engine_manager.get_all_engines()

    def save_cloud_credentials(self, provider: str, **kwargs) -> bool:
        """保存云服务凭证"""
        try:
            # Filter out empty values? Or just save what is provided.
            credentials = kwargs

            global_credential_manager.save(provider, credentials)
            logger.info(f"保存云服务凭证成功: {provider}")
            return True
        except Exception as e:
            logger.error(f"保存云服务凭证失败: {provider}, {e}")
            return False

    def load_cloud_credentials(self, provider: str) -> Dict[str, str]:
        """加载云服务凭证"""
        return global_credential_manager.load(provider) or {}

    def validate_cloud_config(self, provider: str) -> bool:
        """
        验证云服务配置是否有效
        """
        creds = self.load_cloud_credentials(provider)
        if not creds:
            return False

        try:
            # 动态导入引擎类
            engine_class = None
            if provider == "baidu":
                from src.services.ocr.cloud.baidu_ocr import BaiduOCREngine
                engine_class = BaiduOCREngine
            elif provider == "tencent":
                from src.services.ocr.cloud.tencent_ocr import TencentOCREngine
                engine_class = TencentOCREngine
            elif provider == "aliyun":
                from src.services.ocr.cloud.aliyun_ocr import AliyunOCREngine
                engine_class = AliyunOCREngine

            if engine_class:
                # 创建临时引擎实例 (传入空配置，因为主要依赖凭证管理器)
                engine = engine_class(config={})
                # 检查凭证格式是否正确
                if engine.is_available():
                    return True
                else:
                    logger.warning(f"云服务凭证格式验证失败: {provider}")
                    return False
            
            logger.warning(f"未知的云服务提供商: {provider}")
            return False
            
        except Exception as e:
            logger.error(f"验证云配置出错: {e}")
            return False
