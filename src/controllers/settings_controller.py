#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 设置控制器

负责处理设置界面的逻辑，连接 UI 和 ConfigManager。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import Dict, Any, List

from PySide6.QtCore import QObject, Signal

from utils.config_manager import ConfigManager
from utils.credential_manager import CredentialManager
from services.ocr.engine_manager import EngineManager

logger = logging.getLogger(__name__)


class SettingsController(QObject):
    """
    设置控制器
    """
    
    config_changed = Signal(str, object)  # 配置变更信号 (key, new_value)
    
    def __init__(self):
        super().__init__()
        self._config_manager = ConfigManager.instance()
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
            
            CredentialManager.save(provider, credentials)
            logger.info(f"保存云服务凭证成功: {provider}")
            return True
        except Exception as e:
            logger.error(f"保存云服务凭证失败: {provider}, {e}")
            return False
            
    def load_cloud_credentials(self, provider: str) -> Dict[str, str]:
        """加载云服务凭证"""
        return CredentialManager.load(provider) or {}
        
    def validate_cloud_config(self, provider: str) -> bool:
        """
        验证云服务配置是否有效
        
        TODO: 发送一个测试请求来验证
        """
        creds = self.load_cloud_credentials(provider)
        if not creds:
            return False
        return True # Placeholder
