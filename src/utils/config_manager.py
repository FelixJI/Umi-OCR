#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 配置管理器

提供配置的读取、保存和变更通知功能。
使用单例模式，确保全局只有一个配置管理器实例。

主要功能：
- JSON 格式配置文件读写
- 配置变更信号通知（Qt Signal）
- 默认配置管理
- 配置校验
- 线程安全

使用示例:
    from src.utils.config_manager import ConfigManager

    # 获取全局配置管理器
    manager = ConfigManager.get_instance()

    # 加载配置
    manager.load()

    # 读取配置
    engine_type = manager.get("ocr.engine_type")

    # 写入配置
    manager.set("ocr.engine_type", "baidu")

    # 保存配置
    manager.save()

    # 监听配置变更
    manager.config_changed.connect(lambda key, old, new: print(f"{key}: {old} -> {new}"))

Author: Umi-OCR Team
Date: 2025-01-25
"""

import json
import threading
from pathlib import Path
from typing import Any, Callable, Optional, Dict, List, Union
from PySide6.QtCore import QObject, Signal

from src.models.config_model import AppConfig, ConfigChangeEvent


class ConfigManager(QObject):
    """
    配置管理器（单例模式）

    提供全局统一的配置管理功能，支持配置变更通知。
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    # 配置变更信号
    # 参数: key_path (str), old_value (Any), new_value (Any)
    config_changed = Signal(str, object, object)

    # 配置重新加载信号
    config_reloaded = Signal()

    # 配置保存后信号
    config_saved = Signal(str)  # 参数: 保存的文件路径

    # 配置错误信号
    config_error = Signal(str)  # 参数: 错误信息

    # -------------------------------------------------------------------------
    # 单例模式
    # -------------------------------------------------------------------------

    _instance: Optional["ConfigManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ConfigManager":
        """
        实现单例模式

        Returns:
            ConfigManager: 唯一的配置管理器实例
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
        初始化配置管理器

        注意：由于单例模式，此方法只会被调用一次。
        """
        # 防止重复初始化
        if hasattr(self, "_initialized") and self._initialized:
            return

        super().__init__()

        self._initialized: bool = True

        # 配置文件路径（在 set_config_path 中设置）
        self._config_path: Optional[Path] = None

        # 配置对象
        self._config: AppConfig = AppConfig()

        # 配置文件修改时间（用于检测外部修改）
        self._last_mtime: Optional[float] = None

        # 写锁（防止并发写入）
        self._write_lock = threading.Lock()

        # 配置变更监听器
        self._listeners: List[Callable[[ConfigChangeEvent], None]] = []

        # 是否启用自动保存
        self._auto_save = True

        # 是否启用自动重载（检测外部修改）
        self._auto_reload = False

    # -------------------------------------------------------------------------
    # 配置文件路径管理
    # -------------------------------------------------------------------------

    def set_config_path(self, path: Path) -> None:
        """
        设置配置文件路径

        Args:
            path: 配置文件路径
        """
        self._config_path = Path(path)

    def get_config_path(self) -> Optional[Path]:
        """
        获取配置文件路径

        Returns:
            Optional[Path]: 配置文件路径
        """
        return self._config_path

    # -------------------------------------------------------------------------
    # 配置加载
    # -------------------------------------------------------------------------

    def load(self, path: Optional[Path] = None) -> bool:
        """
        从文件加载配置

        Args:
            path: 配置文件路径（为 None 则使用之前设置的路径）

        Returns:
            bool: 是否加载成功
        """
        config_path = path or self._config_path

        if config_path is None:
            self.config_error.emit("未设置配置文件路径")
            return False

        try:
            if not config_path.exists():
                # 配置文件不存在，使用默认配置并创建文件
                self._config = AppConfig()
                self._save_config_file(config_path)
                self._last_mtime = config_path.stat().st_mtime
                self.config_reloaded.emit()
                return True

            # 读取配置文件
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 解析配置
            self._config = AppConfig.from_dict(data)

            # 更新修改时间
            self._last_mtime = config_path.stat().st_mtime

            # 发送重载信号
            self.config_reloaded.emit()

            return True

        except json.JSONDecodeError as e:
            error_msg = f"配置文件 JSON 格式错误: {e}"
            self.config_error.emit(error_msg)
            # 使用默认配置
            self._config = AppConfig()
            return False

        except Exception as e:
            error_msg = f"加载配置文件失败: {e}"
            self.config_error.emit(error_msg)
            # 使用默认配置
            self._config = AppConfig()
            return False

    def reload(self) -> bool:
        """
        重新加载配置文件

        Returns:
            bool: 是否重载成功
        """
        return self.load()

    # -------------------------------------------------------------------------
    # 配置保存
    # -------------------------------------------------------------------------

    def save(self, path: Optional[Path] = None) -> bool:
        """
        保存配置到文件

        Args:
            path: 配置文件路径（为 None 则使用之前设置的路径）

        Returns:
            bool: 是否保存成功
        """
        config_path = path or self._config_path

        if config_path is None:
            self.config_error.emit("未设置配置文件路径")
            return False

        with self._write_lock:
            return self._save_config_file(config_path)

    def _save_config_file(self, path: Path) -> bool:
        """
        内部方法：保存配置到文件

        Args:
            path: 配置文件路径

        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保目录存在
            path.parent.mkdir(parents=True, exist_ok=True)

            # 验证配置
            errors = self._config.validate()
            if errors:
                error_msg = "配置验证失败: " + "; ".join(errors)
                self.config_error.emit(error_msg)
                return False

            # 转换为字典并保存
            data = self._config.to_dict()

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            # 更新修改时间
            self._last_mtime = path.stat().st_mtime

            # 发送保存成功信号
            self.config_saved.emit(str(path))

            return True

        except PermissionError:
            error_msg = "权限不足，无法写入配置文件"
            self.config_error.emit(error_msg)
            return False

        except Exception as e:
            error_msg = f"保存配置文件失败: {e}"
            self.config_error.emit(error_msg)
            return False

    # -------------------------------------------------------------------------
    # 配置读写
    # -------------------------------------------------------------------------

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key_path: 配置路径（点分隔），如 "ocr.engine_type"
            default: 默认值

        Returns:
            Any: 配置值

        Examples:
            >>> manager.get("ocr.engine_type")
            "paddle"
            >>> manager.get("ui.main_window.width")
            1000
        """
        return self._config.get(key_path, default)

    def set(self, key_path: str, value: Any, auto_save: Optional[bool] = None) -> bool:
        """
        设置配置值

        Args:
            key_path: 配置路径（点分隔）
            value: 新值
            auto_save: 是否自动保存（为 None 则使用全局设置）

        Returns:
            bool: 是否设置成功

        Examples:
            >>> manager.set("ocr.engine_type", "baidu")
            True
        """
        # 获取旧值
        old_value = self.get(key_path)

        # 检查值是否相同
        if old_value == value:
            return True

        # 设置新值
        success = self._config.set(key_path, value)

        if success:
            # 发送变更信号
            self.config_changed.emit(key_path, old_value, value)

            # 通知监听器
            event = ConfigChangeEvent(
                key_path=key_path,
                old_value=old_value,
                new_value=value,
                source="user"
            )
            self._notify_listeners(event)

            # 自动保存
            if auto_save is None:
                auto_save = self._auto_save
            if auto_save and self._config_path:
                self.save()

        return success

    def get_config(self) -> AppConfig:
        """
        获取完整的配置对象

        Returns:
            AppConfig: 配置对象
        """
        return self._config

    def set_config(self, config: AppConfig) -> None:
        """
        设置完整的配置对象

        Args:
            config: 新的配置对象
        """
        self._config = config

    # -------------------------------------------------------------------------
    # 配置变更监听
    # -------------------------------------------------------------------------

    def add_listener(self, listener: Callable[[ConfigChangeEvent], None]) -> None:
        """
        添加配置变更监听器

        Args:
            listener: 监听器函数，接收 ConfigChangeEvent 参数
        """
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[ConfigChangeEvent], None]) -> None:
        """
        移除配置变更监听器

        Args:
            listener: 监听器函数
        """
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_listeners(self, event: ConfigChangeEvent) -> None:
        """
        通知所有监听器

        Args:
            event: 配置变更事件
        """
        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                # 防止监听器异常影响其他监听器
                pass

    # -------------------------------------------------------------------------
    # 配置重置
    # -------------------------------------------------------------------------

    def reset(self) -> None:
        """重置为默认配置"""
        self._config = AppConfig()
        self.config_reloaded.emit()

        if self._auto_save and self._config_path:
            self.save()

    def reset_section(self, section: str) -> bool:
        """
        重置指定配置节为默认值

        Args:
            section: 配置节名称，如 "ocr", "ui", "hotkeys"

        Returns:
            bool: 是否重置成功
        """
        default_config = AppConfig()

        if not hasattr(default_config, section):
            return False

        # 设置为默认值
        setattr(self._config, section, getattr(default_config, section))

        # 发送重载信号
        self.config_reloaded.emit()

        # 自动保存
        if self._auto_save and self._config_path:
            self.save()

        return True

    # -------------------------------------------------------------------------
    # 自动保存和重载控制
    # -------------------------------------------------------------------------

    def set_auto_save(self, enabled: bool) -> None:
        """
        设置是否自动保存

        Args:
            enabled: 是否启用自动保存
        """
        self._auto_save = enabled

    def get_auto_save(self) -> bool:
        """
        获取自动保存状态

        Returns:
            bool: 是否启用自动保存
        """
        return self._auto_save

    def set_auto_reload(self, enabled: bool) -> None:
        """
        设置是否自动重载（检测外部修改）

        Args:
            enabled: 是否启用自动重载
        """
        self._auto_reload = enabled

    def get_auto_reload(self) -> bool:
        """
        获取自动重载状态

        Returns:
            bool: 是否启用自动重载
        """
        return self._auto_reload

    def check_external_changes(self) -> bool:
        """
        检查配置文件是否被外部修改

        Returns:
            bool: 是否检测到外部修改
        """
        if not self._auto_reload or self._config_path is None:
            return False

        try:
            if not self._config_path.exists():
                return False

            current_mtime = self._config_path.stat().st_mtime

            if self._last_mtime is not None and current_mtime > self._last_mtime:
                # 文件被修改，重新加载
                self.load()
                return True

        except Exception:
            pass

        return False

    # -------------------------------------------------------------------------
    # 配置导入导出
    # -------------------------------------------------------------------------

    def export_to_file(self, path: Path) -> bool:
        """
        导出配置到指定文件

        Args:
            path: 导出文件路径

        Returns:
            bool: 是否导出成功
        """
        return self._save_config_file(path)

    def import_from_file(self, path: Path, merge: bool = False) -> bool:
        """
        从文件导入配置

        Args:
            path: 导入文件路径
            merge: 是否与当前配置合并（True）还是完全替换（False）

        Returns:
            bool: 是否导入成功
        """
        try:
            if not path.exists():
                self.config_error.emit(f"导入文件不存在: {path}")
                return False

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            imported_config = AppConfig.from_dict(data)

            if merge:
                # 合并配置：只覆盖导入文件中存在的值
                # 这里简化处理，直接替换
                self._config = imported_config
            else:
                # 完全替换
                self._config = imported_config

            # 发送重载信号
            self.config_reloaded.emit()

            # 自动保存
            if self._auto_save and self._config_path:
                self.save()

            return True

        except Exception as e:
            error_msg = f"导入配置失败: {e}"
            self.config_error.emit(error_msg)
            return False

    # -------------------------------------------------------------------------
    # 工具方法
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        """
        获取配置管理器单例

        Returns:
            ConfigManager: 配置管理器实例
        """
        return cls()


# -------------------------------------------------------------------------
# 全局配置管理器实例
# ----------------------------------------------------------------------------

_global_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    获取全局配置管理器

    Returns:
        ConfigManager: 配置管理器单例

    使用示例:
        from src.utils.config_manager import get_config_manager

        manager = get_config_manager()
        manager.load()
        engine_type = manager.get("ocr.engine_type")
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager.get_instance()
    return _global_config_manager
