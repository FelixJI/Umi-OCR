#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 开机自启管理器

通过 Windows 注册表实现开机自启功能。
"""

import sys
import winreg
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class StartupManager:
    """开机自启管理器（注册表 Run 键）"""

    REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "UmiOCR"

    @classmethod
    def is_enabled(cls) -> bool:
        """检查是否已启用开机自启"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, cls.REGISTRY_KEY, 0, winreg.KEY_READ
            )
            value, _ = winreg.QueryValueEx(key, cls.APP_NAME)
            winreg.CloseKey(key)

            # 检查路径是否匹配当前可执行文件
            current_exe = sys.executable
            # 如果是 python 脚本运行，可能需要特殊处理，但在打包后 sys.executable 指向 exe
            # 这里简单比对，实际可能包含引号或参数

            # 标准化路径比较
            reg_path = Path(value.replace('"', "")).resolve()
            curr_path = Path(current_exe).resolve()

            return reg_path == curr_path
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"检查开机自启状态失败: {e}")
            return False

    @classmethod
    def enable(cls) -> bool:
        """启用开机自启"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, cls.REGISTRY_KEY, 0, winreg.KEY_SET_VALUE
            )
            # 添加引号以处理带空格的路径
            exe_path = f'"{sys.executable}"'
            winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            logger.info("已启用开机自启")
            return True
        except Exception as e:
            logger.error(f"启用开机自启失败: {e}")
            return False

    @classmethod
    def disable(cls) -> bool:
        """禁用开机自启"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, cls.REGISTRY_KEY, 0, winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, cls.APP_NAME)
            winreg.CloseKey(key)
            logger.info("已禁用开机自启")
            return True
        except FileNotFoundError:
            # 键不存在，视为已禁用
            return True
        except Exception as e:
            logger.error(f"禁用开机自启失败: {e}")
            return False
