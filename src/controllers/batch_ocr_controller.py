#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 批量图片OCR控制器

连接批量OCR界面和服务层,集成任务管理器。

主要功能：
- 处理图片导入
- 提交批量OCR任务
- 显示进度和结果

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
import os
from pathlib import Path
from typing import List, Set

from PySide6.QtCore import QObject, Signal

from services.task.task_manager import TaskManager
from utils.logger import get_logger

logger = get_logger()


class BatchOcrController(QObject):
    """
    批量图片OCR控制器

    功能:
    - 导入图片列表
    - 提交批量OCR任务
    - 显示进度和结果
    """

    # 支持的图片格式
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff"}

    # 信号定义
    tasks_submitted = Signal(str)        # 任务已提交(group_id)
    progress_updated = Signal(str, float) # 进度更新(group_id, progress)
    tasks_completed = Signal(str)        # 任务完成(group_id)
    tasks_failed = Signal(str, str)      # 任务失败(group_id, error)

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """初始化批量OCR控制器"""
        if hasattr(self, "_initialized"):
            return
            
        super().__init__()
        self._initialized = True

        self._task_manager = TaskManager.instance()

        # 待处理文件集合
        self._pending_files: Set[str] = set()
        self._submitted_groups: Set[str] = set()

        # 连接信号
        self._connect_signals()

        logger.info("批量OCR控制器初始化完成")

    def _connect_signals(self) -> None:
        """连接任务管理器信号"""
        self._task_manager.group_progress.connect(self._on_group_progress)
        self._task_manager.group_completed.connect(self._on_group_completed)
        self._task_manager.group_paused.connect(self._on_group_paused)

    def submit_batch_ocr(
        self,
        image_paths: List[str],
        title: str = "批量OCR",
        priority: int = 0
    ) -> str:
        """
        提交批量OCR任务

        Args:
            image_paths: 图片路径列表
            title: 任务标题
            priority: 优先级

        Returns:
            str: 任务组ID
        """
        logger.info(f"提交批量OCR任务: {len(image_paths)} 张图片")

        # 添加到待处理文件集合
        self.add_files(image_paths)

        # 提交到任务管理器
        group_id = self._task_manager.submit_ocr_tasks(
            image_paths=list(self._pending_files),
            title=title,
            priority=priority
        )
        
        self._submitted_groups.add(group_id)

        # 发送信号
        self.tasks_submitted.emit(group_id)

        return group_id

    def add_files(self, paths: List[str]) -> None:
        """
        添加文件到待处理列表

        Args:
            paths: 文件路径列表
        """
        for path in paths:
            if os.path.isfile(path):
                if self._is_supported(path):
                    self._pending_files.add(path)
                    logger.debug(f"添加文件: {path}")
            elif os.path.isdir(path):
                self._expand_folder(path)

    def _expand_folder(self, folder_path: str) -> None:
        """
        展开文件夹,添加所有支持的文件

        Args:
            folder_path: 文件夹路径
        """
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if self._is_supported(file):
                    file_path = os.path.join(root, file)
                    if file_path not in self._pending_files:
                        self._pending_files.add(file_path)
                        logger.debug(f"添加文件: {file_path}")

    def _is_supported(self, file_path: str) -> bool:
        """
        检查文件是否支持

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否支持
        """
        return Path(file_path).suffix.lower() in self.SUPPORTED_FORMATS

    def clear_files(self) -> None:
        """
        清空文件列表
        """
        self._pending_files.clear()
        logger.info("文件列表已清空")

    def pause_ocr(self) -> None:
        """
        暂停批量OCR

        取消所有任务组
        """
        logger.info("暂停批量OCR")
        for group_id in self._submitted_groups:
            self._task_manager.pause_group(group_id)

    def resume_ocr(self) -> None:
        """
        恢复批量OCR

        恢复所有暂停的任务组
        """
        logger.info("恢复批量OCR")
        for group_id in self._submitted_groups:
            self._task_manager.resume_group(group_id)

    def cancel_batch(self, group_id: str) -> None:
        """
        取消批量任务

        Args:
            group_id: 任务组ID
        """
        logger.info(f"取消批量任务: {group_id}")
        self._task_manager.cancel_group(group_id)

    def _on_group_progress(self, group_id: str, progress: float) -> None:
        """
        任务组进度更新

        Args:
            group_id: 任务组ID
            progress: 进度(0.0~1.0)
        """
        self.progress_updated.emit(group_id, progress)
        logger.debug(f"任务组进度: {group_id} - {progress:.2%}")

    def _on_group_completed(self, group_id: str) -> None:
        """
        任务组完成

        Args:
            group_id: 任务组ID
        """
        logger.info(f"任务组完成: {group_id}")
        self.tasks_completed.emit(group_id)

    def _on_group_paused(self, group_id: str, reason: str) -> None:
        """
        任务组暂停（包括失败）

        Args:
            group_id: 任务组ID
            reason: 暂停原因（"user" 或 "failure"）
        """
        if reason == "failure":
            logger.error(f"任务组失败: {group_id}")
            self.tasks_failed.emit(group_id, "任务执行失败")
        else:
            logger.info(f"任务组暂停: {group_id}, 原因: {reason}")

    def export_results(self, group_id: str, output_path: str, format_text: str) -> bool:
        """
        导出结果
        
        Args:
            group_id: 任务组ID
            output_path: 输出文件路径
            format_text: 格式描述 (TXT/JSON/CSV)
            
        Returns:
            bool: 是否成功
        """
        group = self._task_manager.get_group(group_id)
        if not group:
            logger.warning(f"任务组不存在: {group_id}")
            return False
            
        try:
            logger.info(f"开始导出: {group_id} -> {output_path}")
            
            # 收集结果
            results = []
            for task in group.get_all_tasks():
                if task.status.value == "completed" and task.result:
                    # 假设 result 是字典，包含 text 字段
                    text = task.result.get("text", "")
                    filename = Path(task.input_data.get("image_path", "")).name
                    results.append(f"--- {filename} ---\n{text}")
            
            # 格式化输出 (这里仅实现简单的 TXT 拼接，后续可扩展 JSON/CSV)
            if "JSON" in format_text:
                import json
                content = json.dumps(results, ensure_ascii=False, indent=2)
            else:
                content = "\n\n".join(results)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            logger.info(f"导出成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出失败: {e}", exc_info=True)
            return False

