#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 引擎选择器 UI 控件

提供引擎选择功能，支持本地引擎和云引擎的实时切换。

主要功能:
- 下拉菜单显示所有可用引擎
- 显示配置状态（已配置/未配置）
- 实时切换引擎
- 引擎配置状态动态更新

Author: Umi-OCR Team
Date: 2026-01-27
"""

from typing import Dict, Any, Optional, List
from PySide6.QtWidgets import (
    QWidget, QComboBox, QLabel, QHBoxLayout, QVBoxLayout,
    QStyle, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap

from ...services.ocr.engine_manager import EngineManager, EngineInfo, EngineState
from ...utils.credential_manager import CredentialManager


# =============================================================================
# 引擎选择器控件
# =============================================================================

class EngineSelector(QWidget):
    """
    引擎选择器控件

    嵌入到 OCR 功能界面，支持实时切换引擎。

    布局:
    ┌──────────────────────────────────────────────────┐
    │  识别引擎: [▼ PaddleOCR (本地)   ]     │
    └──────────────────────────────────────────────────┘

    下拉选项:
    - PaddleOCR (本地)
    - 百度云 OCR      [已配置] → 可选
    - 腾讯云 OCR      [未配置] → 灰色不可选
    - 阿里云 OCR      [已配置] → 可选
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    # 引擎切换信号
    # 参数: engine_id (str)
    engine_changed = Signal(str)

    # 引擎配置状态变更信号
    # 参数: engine_id (str), configured (bool)
    config_status_changed = Signal(str, bool)

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化引擎选择器

        Args:
            parent: 父控件
        """
        super().__init__(parent)

        # UI 组件
        self._label = QLabel("识别引擎:", self)
        self._combo = QComboBox(self)
        self._status_indicator = QLabel(self)
        self._config_status_cache: Dict[str, bool] = {}

        # 获取引擎管理器
        self._engine_manager = EngineManager.get_instance()

        # 初始化UI
        self._setup_ui()

        # 加载可用引擎
        self._load_available_engines()

        # 连接信号
        self._connect_signals()

        # 启动状态更新定时器（每5秒检查一次）
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_config_status)
        self._status_timer.start(5000)  # 5秒

    # -------------------------------------------------------------------------
    # UI 设置
    # -------------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """初始化 UI 布局"""
        # 设置标签
        self._label.setObjectName("engine_label")
        self._label.setStyleSheet("""
            QLabel#engine_label {
                color: #666666;
                font-size: 13px;
                font-weight: 500;
            }
        """)

        # 设置下拉框
        self._combo.setObjectName("engine_combo")
        self._combo.setMinimumWidth(200)
        self._combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._combo.setStyleSheet("""
            QComboBox#engine_combo {
                padding: 4px 8px;
                font-size: 13px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fff;
            }
            QComboBox#engine_combo::drop-down {
                border: 1px solid #aaa;
            }
            QComboBox#engine_combo:hover {
                border-color: #4a90e2;
            }
        """)

        # 设置状态指示器
        self._status_indicator.setObjectName("status_indicator")
        self._status_indicator.setFixedSize(16, 16)
        self._status_indicator.setStyleSheet("""
            QLabel#status_indicator {
                border-radius: 8px;
            }
            QLabel#status_indicator[configured=true] {
                background-color: #52c41a;
                border: 1px solid #45a049;
            }
            QLabel#status_indicator[configured=false] {
                background-color: #95a5a6;
                border: 1px solid #7e8c93;
            }
        """)

        # 主布局
        main_layout = QHBoxLayout()
        main_layout.addWidget(self._label)
        main_layout.addSpacing(10)
        main_layout.addWidget(self._combo)
        main_layout.addWidget(self._status_indicator)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        self.setLayout(main_layout)

    def _connect_signals(self) -> None:
        """连接信号槽"""
        # 下拉框变更信号
        self._combo.currentIndexChanged.connect(self._on_engine_changed)

        # 连接引擎管理器信号
        self._engine_manager.engine_switched.connect(self._on_engine_manager_switched)
        self._engine_manager.engine_ready.connect(self._on_engine_ready)

    # -------------------------------------------------------------------------
    # 引擎加载
    # -------------------------------------------------------------------------

    def _load_available_engines(self) -> None:
        """
        加载可用引擎列表
        """
        # 清空现有选项
        self._combo.clear()

        # 获取所有已注册的引擎
        engines = self._engine_manager.get_available_engines()

        for engine_type in engines:
            engine_info = self._engine_manager.get_engine_info(engine_type)
            if not engine_info:
                continue

            # 获取引擎显示名称
            display_name = self._get_engine_display_name(engine_type, engine_info)

            # 检查是否已配置（云引擎需要检查凭证）
            is_configured = self._check_engine_configured(engine_type, engine_info)

            # 缓存配置状态
            self._config_status_cache[engine_type] = is_configured

            # 添加到下拉框
            self._combo.addItem(display_name, userData=engine_type)

            # 设置项的启用状态（云引擎未配置时禁用）
            index = self._combo.count() - 1
            if not engine_info.is_local and not is_configured:
                self._combo.setItemIcon(index, self._get_disabled_icon())
                self._combo.model().item(index).setFlags(
                    self._combo.model().item(index).flags() & ~Qt.ItemIsEnabled
                )
            else:
                self._combo.setItemIcon(index, self._get_check_icon(is_configured))

        # 设置当前选中的引擎
        current_engine_type = self._engine_manager.get_current_engine_type()
        if current_engine_type:
            index = self._combo.findData(current_engine_type)
            if index >= 0:
                self._combo.setCurrentIndex(index)
                self._update_status_indicator(current_engine_type)

    def _get_engine_display_name(self, engine_type: str, engine_info: EngineInfo) -> str:
        """
        获取引擎显示名称

        Args:
            engine_type: 引擎类型
            engine_info: 引擎信息

        Returns:
            str: 显示名称
        """
        if engine_info.is_local:
            # 本地引擎
            return f"{engine_info.engine_name} (本地)"
        else:
            # 云引擎
            provider_names = {
                'baidu_cloud': "百度云",
                'tencent_cloud': "腾讯云",
                'aliyun_cloud': "阿里云"
            }
            return provider_names.get(engine_type, engine_info.engine_name)

    def _check_engine_configured(self, engine_type: str, engine_info: EngineInfo) -> bool:
        """
        检查引擎是否已配置

        Args:
            engine_type: 引擎类型
            engine_info: 引擎信息

        Returns:
            bool: 是否已配置
        """
        # 本地引擎总是已配置
        if engine_info.is_local:
            return True

        # 云引擎检查凭证
        try:
            cred_manager = CredentialManager()
            return cred_manager.exists(engine_type.replace('_cloud', ''))
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # 图标
    # -------------------------------------------------------------------------

    def _get_check_icon(self, configured: bool) -> QIcon:
        """
        获取配置状态图标

        Args:
            configured: 是否已配置

        Returns:
            QIcon: 图标对象
        """
        # 使用样式表的标准图标
        style = self.style()

        if configured:
            # 绿色对勾
            icon = style.standardIcon(QStyle.SP_DialogApplyButton)
        else:
            # 灰色叉
            icon = style.standardIcon(QStyle.SP_DialogCancelButton)

        return icon

    def _get_disabled_icon(self) -> QIcon:
        """获取禁用状态图标"""
        style = self.style()
        return style.standardIcon(QStyle.SP_BrowserReload)

    # -------------------------------------------------------------------------
    # 信号槽
    # -------------------------------------------------------------------------

    def _on_engine_changed(self, index: int) -> None:
        """
        下拉框选择变更槽函数

        Args:
            index: 选中的索引
        """
        if index < 0:
            return

        engine_id = self._combo.itemData(index)
        if not engine_id:
            return

        # 发送引擎切换信号
        self.engine_changed.emit(engine_id)

        logging.info(f"用户选择引擎: {engine_id}")

    def _on_engine_manager_switched(self, old_engine: str, new_engine: str) -> None:
        """
        引擎管理器切换信号槽函数

        Args:
            old_engine: 旧引擎类型
            new_engine: 新引擎类型
        """
        if self._combo.itemData(self._combo.currentIndex()) == new_engine:
            # 已经是当前引擎，无需更新
            return

        # 更新下拉框选择
        index = self._combo.findData(new_engine)
        if index >= 0:
            self._combo.setCurrentIndex(index)
            self._update_status_indicator(new_engine)

        logging.info(f"引擎管理器切换: {old_engine} -> {new_engine}")

    def _on_engine_ready(self, engine_type: str, is_ready: bool) -> None:
        """
        引擎就绪状态变更信号槽函数

        Args:
            engine_type: 引擎类型
            is_ready: 是否就绪
        """
        # 查找对应的引擎项
        index = self._combo.findData(engine_type)
        if index < 0:
            return

        # 更新状态指示器
        self._update_status_indicator(engine_type)

    def _refresh_config_status(self) -> None:
        """
        刷新引擎配置状态

        定时检查云引擎的凭证配置状态
        """
        engines = self._engine_manager.get_available_engines()

        for i in range(self._combo.count()):
            engine_type = self._combo.itemData(i)
            if not engine_type:
                continue

            engine_info = self._engine_manager.get_engine_info(engine_type)
            if not engine_info:
                continue

            # 云引擎才需要检查配置
            if not engine_info.is_local:
                is_configured = self._check_engine_configured(engine_type, engine_info)

                # 更新状态缓存
                if self._config_status_cache.get(engine_type) != is_configured:
                    self._config_status_cache[engine_type] = is_configured
                    self.config_status_changed.emit(engine_type, is_configured)

                    # 更新图标和启用状态
                    if not is_configured:
                        self._combo.setItemIcon(i, self._get_disabled_icon())
                        self._combo.model().item(i).setFlags(
                            self._combo.model().item(i).flags() & ~Qt.ItemIsEnabled
                        )
                    else:
                        self._combo.setItemIcon(i, self._get_check_icon(True))
                        # 启用选项
                        self._combo.model().item(i).setFlags(
                            self._combo.model().item(i).flags() | Qt.ItemIsEnabled
                        )

    def _update_status_indicator(self, engine_type: str) -> None:
        """
        更新状态指示器

        Args:
            engine_type: 引擎类型
        """
        index = self._combo.findData(engine_type)
        if index < 0:
            return

        engine_info = self._engine_manager.get_engine_info(engine_type)
        if not engine_info:
            return

        # 更新状态指示器
        is_configured = self._config_status_cache.get(engine_type, engine_info.is_local)

        if is_configured:
            self._status_indicator.setProperty("configured", "true")
        else:
            self._status_indicator.setProperty("configured", "false")

        # 设置工具提示
        if engine_info.is_local:
            tooltip = f"{engine_info.engine_name} - 本地引擎"
        else:
            tooltip = f"{self._get_engine_display_name(engine_type, engine_info)} - {'已配置' if is_configured else '未配置'}"

        self._combo.setItemData(index, tooltip)

    # -------------------------------------------------------------------------
    # 公共接口
    # -------------------------------------------------------------------------

    def get_current_engine_id(self) -> Optional[str]:
        """
        获取当前选中的引擎 ID

        Returns:
            Optional[str]: 引擎 ID，未选择返回 None
        """
        index = self._combo.currentIndex()
        if index >= 0:
            return self._combo.itemData(index)
        return None

    def set_engine(self, engine_type: str) -> None:
        """
        设置当前引擎

        Args:
            engine_type: 引擎类型
        """
        index = self._combo.findData(engine_type)
        if index >= 0:
            self._combo.setCurrentIndex(index)
            self.engine_changed.emit(engine_type)

    def refresh(self) -> None:
        """刷新引擎列表"""
        self._load_available_engines()

        logging.info("引擎列表已刷新")


# =============================================================================
# 日志记录器
# =============================================================================

import logging
logger = logging.getLogger(__name__)
