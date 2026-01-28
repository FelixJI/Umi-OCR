#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 设置搜索

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal

from src.controllers.settings_controller import SettingsController

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果"""
    key: str              # 配置键路径，如 "ocr.engine_type"
    value: Any            # 配置值
    label: str            # 显示标签
    description: str      # 描述信息
    matched_fields: List[str]  # 匹配的字段列表


class SettingsSearch(QObject):
    """设置搜索逻辑"""

    search_completed = Signal(list)  # 搜索完成信号，返回 SearchResult 列表

    def __init__(self):
        super().__init__()
        self._controller = SettingsController()
        self._config_cache: Optional[Dict[str, Any]] = None

    def search(self, query: str) -> List[SearchResult]:
        """
        搜索配置项

        Args:
            query: 搜索查询字符串

        Returns:
            List[SearchResult]: 匹配的配置项列表
        """
        if not query or not query.strip():
            return []

        query = query.strip().lower()
        results = []

        # 获取所有配置
        config_dict = self._get_all_config_as_dict()

        # 定义可搜索的配置项
        search_items = self._get_searchable_items()

        # 搜索配置项
        for item in search_items:
            key = item["key"]
            label = item["label"]
            description = item.get("description", "")

            # 获取当前值
            value = self._get_config_value(key)

            # 搜索匹配
            matched_fields = []
            if query in key.lower():
                matched_fields.append("key")
            if query in label.lower():
                matched_fields.append("label")
            if description and query in description.lower():
                matched_fields.append("description")

            # 搜索值（如果是字符串）
            if isinstance(value, str) and query in value.lower():
                matched_fields.append("value")

            # 如果有任何匹配
            if matched_fields:
                result = SearchResult(
                    key=key,
                    value=value,
                    label=label,
                    description=description,
                    matched_fields=matched_fields
                )
                results.append(result)

        # 发送搜索完成信号
        self.search_completed.emit(results)

        return results

    def _get_all_config_as_dict(self) -> Dict[str, Any]:
        """
        获取所有配置为字典格式

        Returns:
            Dict[str, Any]: 配置字典
        """
        if self._config_cache is None:
            # 从 controller 获取配置
            self._config_cache = {}
            # 这里我们直接通过 controller 的 get_config 方法按需获取
            # 不一次性缓存所有配置，因为可能有很多嵌套对象

        return self._config_cache

    def _get_config_value(self, key: str) -> Any:
        """
        获取配置值

        Args:
            key: 配置键路径

        Returns:
            Any: 配置值
        """
        return self._controller.get_config(key)

    def _get_searchable_items(self) -> List[Dict[str, str]]:
        """
        获取可搜索的配置项列表

        Returns:
            List[Dict[str, str]]: 配置项列表，每个项包含 key, label, description
        """
        return [
            # OCR 配置
            {"key": "ocr.engine_type", "label": "OCR 引擎类型", "description": "选择本地 OCR 引擎或云服务 OCR"},
            {"key": "ocr.paddle.det_model_name", "label": "检测模型", "description": "PaddleOCR 文字检测模型名称"},
            {"key": "ocr.paddle.rec_model_name", "label": "识别模型", "description": "PaddleOCR 文字识别模型名称"},
            {"key": "ocr.paddle.use_gpu", "label": "使用 GPU", "description": "是否启用 GPU 加速"},
            {"key": "ocr.paddle.cpu_threads", "label": "CPU 线程数", "description": "OCR 识别时的 CPU 线程数"},
            {"key": "ocr.paddle.lang", "label": "识别语言", "description": "OCR 识别的语言类型"},
            {"key": "ocr.confidence_threshold", "label": "置信度阈值", "description": "识别结果的最低置信度要求"},

            # 云服务配置
            {"key": "ocr.baidu.api_key", "label": "百度云 API Key", "description": "百度云 OCR 服务 API 密钥"},
            {"key": "ocr.baidu.secret_key", "label": "百度云 Secret Key", "description": "百度云 OCR 服务密钥"},
            {"key": "ocr.tencent.secret_id", "label": "腾讯云 Secret ID", "description": "腾讯云 OCR 服务密钥 ID"},
            {"key": "ocr.aliyun.access_key_id", "label": "阿里云 Access Key ID", "description": "阿里云 OCR 服务访问密钥 ID"},

            # 界面配置
            {"key": "ui.language", "label": "界面语言", "description": "应用程序界面显示语言"},
            {"key": "ui.theme.mode", "label": "主题模式", "description": "界面主题：亮色/暗色/自动"},
            {"key": "ui.theme.font_family", "label": "字体", "description": "界面字体设置"},
            {"key": "ui.theme.font_size", "label": "字体大小", "description": "界面文字大小"},
            {"key": "ui.show_tray_icon", "label": "显示托盘图标", "description": "是否在系统托盘显示图标"},
            {"key": "ui.minimize_to_tray", "label": "最小化到托盘", "description": "最小化时是否隐藏到托盘"},
            {"key": "ui.close_to_tray", "label": "关闭到托盘", "description": "关闭窗口时是否隐藏到托盘"},

            # 快捷键配置
            {"key": "hotkeys.screenshot", "label": "截图快捷键", "description": "触发截图 OCR 的快捷键"},
            {"key": "hotkeys.clipboard", "label": "剪贴板快捷键", "description": "触发剪贴板 OCR 的快捷键"},
            {"key": "hotkeys.batch", "label": "批量识别快捷键", "description": "批量 OCR 快捷键"},
            {"key": "hotkeys.show_hide", "label": "显示/隐藏窗口", "description": "显示或隐藏主窗口的快捷键"},

            # 导出配置
            {"key": "export.default_format", "label": "默认导出格式", "description": "识别结果默认导出的文件格式"},
            {"key": "export.auto_copy", "label": "自动复制到剪贴板", "description": "识别完成后自动复制结果到剪贴板"},
            {"key": "export.export_dir", "label": "导出目录", "description": "默认导出文件的保存目录"},

            # 系统配置
            {"key": "system.log_level", "label": "日志级别", "description": "应用程序日志记录级别"},
            {"key": "system.log_to_file", "label": "日志写入文件", "description": "是否将日志写入文件"},
            {"key": "system.startup_launch", "label": "开机自启", "description": "系统启动时自动运行 Umi-OCR"},
            {"key": "system.http_server_enabled", "label": "启用 HTTP 服务", "description": "是否启用 HTTP API 服务"},
            {"key": "system.http_server_port", "label": "HTTP 服务端口", "description": "HTTP API 服务监听端口"},

            # 任务配置
            {"key": "task.max_workers", "label": "最大并发数", "description": "同时执行的最大 OCR 任务数"},
            {"key": "task.max_retry", "label": "最大重试次数", "description": "任务失败时的最大重试次数"},
        ]
