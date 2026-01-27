#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 批量文档OCR控制器

连接批量文档OCR界面和服务层,集成任务管理器。

主要功能：
- 处理PDF文件导入
- 提交PDF识别任务
- 显示进度和结果

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from services.pdf.pdf_parser import PDFParser, PDFInfo
from services.task.task_manager import TaskManager
from utils.logger import get_logger

logger = get_logger()


class BatchDocController(QObject):
    """
    批量文档OCR控制器

    功能:
    - 导入PDF文件列表
    - 提交PDF识别任务(嵌套结构)
    - 显示进度和结果
    """

    # 信号定义
    tasks_submitted = Signal(str)        # 任务已提交(group_id)
    progress_updated = Signal(str, float) # 进度更新(group_id, progress)
    tasks_completed = Signal(str)        # 任务完成(group_id)
    tasks_failed = Signal(str, str)      # 任务失败(group_id, error)

    def __init__(self):
        """初始化批量文档OCR控制器"""
        super().__init__()

        self._pdf_parser = PDFParser()
        self._task_manager = TaskManager.instance()

        # 连接信号
        self._connect_signals()

        logger.info("批量文档OCR控制器初始化完成")

    def _connect_signals(self) -> None:
        """连接任务管理器信号"""
        self._task_manager.group_progress.connect(self._on_group_progress)
        self._task_manager.group_completed.connect(self._on_group_completed)
        self._task_manager.group_failed.connect(self._on_group_failed)

    def submit_pdf_batch(
        self,
        pdf_paths: List[str],
        title: str = "批量文档OCR",
        priority: int = 0,
        dpi: int = 200
    ) -> str:
        """
        提交PDF批量识别任务

        Args:
            pdf_paths: PDF文件路径列表
            title: 任务标题
            priority: 优先级
            dpi: DPI

        Returns:
            str: 任务组ID
        """
        logger.info(f"提交PDF批量识别任务: {len(pdf_paths)} 个文件")

        # 提交到任务管理器(使用内置的submit_pdf_tasks方法)
        group_id = self._task_manager.submit_pdf_tasks(
            pdf_paths=pdf_paths,
            title=title,
            priority=priority
        )

        # 发送信号
        self.tasks_submitted.emit(group_id)

        return group_id

    def parse_pdf(self, file_path: str) -> Optional[PDFInfo]:
        """
        解析PDF文件

        Args:
            file_path: PDF文件路径

        Returns:
            Optional[PDFInfo]: PDF信息
        """
        return self._pdf_parser.parse_pdf(file_path)

    def cancel_batch(self, group_id: str) -> None:
        """
        取消批量任务

        Args:
            group_id: 任务组ID
        """
        logger.info(f"取消批量任务: {group_id}")
        self._task_manager.cancel_group(group_id)

    def pause_ocr(self) -> None:
        """
        暂停批量OCR
        """
        logger.info("暂停批量文档OCR")
        # TODO: 实现暂停逻辑

    def resume_ocr(self) -> None:
        """
        恢复批量OCR
        """
        logger.info("恢复批量文档OCR")
        # TODO: 实现恢复逻辑

    def process_pdfs(self, pdf_paths: List[str]) -> str:
        """
        处理PDF文件（UI调用的方法）

        Args:
            pdf_paths: PDF路径列表

        Returns:
            str: 任务组ID
        """
        return self.submit_pdf_batch(pdf_paths)

    def export_as_searchable_pdf(self, group_id: str, output_path: str) -> None:
        """
        导出为可搜索PDF

        Args:
            group_id: 任务组ID
            output_path: 输出路径
        """
        logger.info(f"导出为可搜索PDF: {group_id}")
        # TODO: 实现导出逻辑，需要调用导出服务

    def export_as_word(self, group_id: str, output_path: str) -> None:
        """
        导出为Word

        Args:
            group_id: 任务组ID
            output_path: 输出路径
        """
        logger.info(f"导出为Word: {group_id}")
        # TODO: 实现导出逻辑，需要调用导出服务

    def export_as_excel(self, group_id: str, output_path: str) -> None:
        """
        导出为Excel

        Args:
            group_id: 任务组ID
            output_path: 输出路径
        """
        logger.info(f"导出为Excel: {group_id}")
        # TODO: 实现导出逻辑，需要调用导出服务

    def _on_group_progress(self, group_id: str, progress: float) -> None:
        """任务组进度更新"""
        self.progress_updated.emit(group_id, progress)
        logger.debug(f"任务组进度: {group_id} - {progress:.2%}")

    def _on_group_completed(self, group_id: str) -> None:
        """任务组完成"""
        logger.info(f"任务组完成: {group_id}")
        self.tasks_completed.emit(group_id)

    def _on_group_failed(self, group_id: str, error: str) -> None:
        """任务组失败"""
        logger.error(f"任务组失败: {group_id}, {error}")
        self.tasks_failed.emit(group_id, error)
