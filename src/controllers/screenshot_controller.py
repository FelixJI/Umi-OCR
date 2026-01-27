#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 截图OCR控制器

连接截图OCR界面和服务层,集成任务管理器。

主要功能：
- 响应快捷键触发截图
- 处理区域选择结果
- 提交OCR任务到任务管理器
- 显示OCR结果

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QRect

from services.screenshot.region_selector import RegionSelector
from services.screenshot.screen_capture import ScreenCapture
from services.task.task_manager import TaskManager
from utils.logger import get_logger

logger = get_logger()


class ScreenshotController(QObject):
    """
    截图OCR控制器

    流程:
    1. 快捷键触发 -> start_capture()
    2. RegionSelector选区 -> region_selected
    3. 创建Task提交到TaskManager
    4. 监听结果 -> 显示在UI
    """

    # 信号定义
    capture_started = Signal()           # 开始截图
    capture_cancelled = Signal()         # 取消截图
    ocr_result_ready = Signal(object)    # OCR结果就绪
    ocr_failed = Signal(str)            # OCR失败

    def __init__(self):
        """初始化截图OCR控制器"""
        super().__init__()

        # 创建服务组件
        self._selector = RegionSelector()
        self._screen_capture = ScreenCapture()
        self._task_manager = TaskManager.instance()

        # 临时文件
        self._temp_file: Optional[Path] = None

        # 连接信号
        self._connect_signals()

        logger.info("截图OCR控制器初始化完成")

    def _connect_signals(self) -> None:
        """连接内部信号"""
        # 选区完成
        self._selector.region_selected.connect(self._on_region_selected)
        # 选区取消
        self._selector.selection_cancelled.connect(self._on_selection_cancelled)

        # 监听任务管理器信号
        self._task_manager.task_completed.connect(self._on_task_completed)
        self._task_manager.task_failed.connect(self._on_task_failed)

    def start_capture(self) -> None:
        """
        开始截图

        触发区域选择。
        """
        logger.info("开始截图")
        self.capture_started.emit()
        self._selector.start()

    def _on_region_selected(self, rect: QRect) -> None:
        """
        选区完成后处理

        流程:
        1. 截取图像
        2. 保存为临时文件
        3. 创建OCR任务提交

        Args:
            rect: 选区矩形
        """
        logger.info(f"选区完成: {rect}")

        # 截取图像
        image = self._screen_capture.capture_region(rect)

        if image.isNull():
            logger.error("截图失败")
            self._selector.stop()
            return

        # 保存临时文件
        self._temp_file = self._save_temp_image(image)

        if not self._temp_file:
            logger.error("保存临时文件失败")
            self._selector.stop()
            return

        # 提交OCR任务(单张图也走任务系统)
        group_id = self._task_manager.submit_ocr_tasks(
            image_paths=[str(self._temp_file)],
            title="截图OCR",
            priority=10,  # 截图优先级较高
        )

        logger.info(f"已提交OCR任务组: {group_id}")

        # 停止选择器
        self._selector.stop()

    def _on_selection_cancelled(self) -> None:
        """选区取消处理"""
        logger.info("选区取消")
        self._selector.stop()
        self.capture_cancelled.emit()

    def _on_task_completed(self, task_id: str, result: dict) -> None:
        """
        任务完成处理

        Args:
            task_id: 任务ID
            result: OCR结果
        """
        logger.debug(f"任务完成: {task_id}")

        # 发送结果信号
        self.ocr_result_ready.emit(result)

        # 清理临时文件
        self._cleanup_temp_file()

    def _on_task_failed(self, task_id: str, error: str) -> None:
        """
        任务失败处理

        Args:
            task_id: 任务ID
            error: 错误信息
        """
        logger.error(f"任务失败: {task_id}, {error}")

        # 发送失败信号
        self.ocr_failed.emit(error)

        # 清理临时文件
        self._cleanup_temp_file()

    def _save_temp_image(self, image) -> Optional[Path]:
        """
        保存临时图像

        Args:
            image: 图像对象

        Returns:
            Optional[Path]: 临时文件路径
        """
        try:
            # 创建临时文件
            temp_dir = Path(tempfile.gettempdir()) / "umi_ocr"
            temp_dir.mkdir(parents=True, exist_ok=True)

            temp_file = temp_dir / f"screenshot_{id(image)}.png"
            image.save(str(temp_file), "PNG")

            logger.debug(f"临时文件已保存: {temp_file}")
            return temp_file

        except Exception as e:
            logger.error(f"保存临时文件失败: {e}", exc_info=True)
            return None

    def _cleanup_temp_file(self) -> None:
        """清理临时文件"""
        if self._temp_file and self._temp_file.exists():
            try:
                self._temp_file.unlink()
                logger.debug(f"临时文件已删除: {self._temp_file}")
                self._temp_file = None
            except Exception as e:
                logger.error(f"删除临时文件失败: {e}", exc_info=True)
