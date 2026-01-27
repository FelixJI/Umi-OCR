#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 任务处理器

实现任务处理器基类和注册表。

Author: Umi-OCR Team
Date: 2026-01-27
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional
import threading

from .task_model import Task, TaskType


class TaskHandler(ABC):
    """
    任务处理器抽象基类

    实现者需要:
    1. 实现 execute() 方法
    2. 在执行过程中定期调用 report_progress()
    3. 在耗时操作前检查 is_cancelled()
    """

    def __init__(self):
        """初始化处理器"""
        self._task: Optional[Task] = None
        self._cancel_event = threading.Event()
        self._progress_lock = threading.Lock()
        self._last_progress_time: float = 0.0

    @abstractmethod
    def execute(self, task: Task) -> Any:
        """
        执行任务，返回结果，失败抛异常

        Args:
            task: 任务对象

        Returns:
            Any: 执行结果
        """
        pass

    def report_progress(self, progress: float) -> None:
        """
        报告进度 (0.0 ~ 1.0)

        Args:
            progress: 进度值
        """
        # 确保进度在 0.0 ~ 1.0 之间
        progress = max(0.0, min(1.0, progress))

        if self._task:
            with self._progress_lock:
                self._task.progress = progress

    def is_cancelled(self) -> bool:
        """
        检查是否已取消

        Returns:
            bool: 是否已取消
        """
        return self._cancel_event.is_set()

    def request_cancel(self) -> None:
        """请求取消"""
        self._cancel_event.set()

    def set_task(self, task: Task) -> None:
        """
        设置当前任务

        Args:
            task: 任务对象
        """
        self._task = task
        # 重置取消标志
        self._cancel_event.clear()
        with self._progress_lock:
            self._last_progress_time = 0.0


class TaskHandlerRegistry:
    """
    任务处理器注册表（单例）

    使用:
        TaskHandlerRegistry.register(TaskType.OCR, OCRTaskHandler)
        handler = TaskHandlerRegistry.get(TaskType.OCR)
    """
    _handlers: Dict[TaskType, Type[TaskHandler]] = {}

    @classmethod
    def register(cls, task_type: TaskType, handler_class: Type[TaskHandler]) -> None:
        """
        注册任务处理器

        Args:
            task_type: 任务类型
            handler_class: 处理器类
        """
        cls._handlers[task_type] = handler_class

    @classmethod
    def get(cls, task_type: TaskType) -> Optional[TaskHandler]:
        """
        获取任务处理器实例

        Args:
            task_type: 任务类型

        Returns:
            Optional[TaskHandler]: 处理器实例（未注册返回 None）
        """
        handler_class = cls._handlers.get(task_type)
        if handler_class:
            return handler_class()
        return None

    @classmethod
    def get_all_types(cls) -> list:
        """
        获取所有已注册的任务类型

        Returns:
            list: 任务类型列表
        """
        return list(cls._handlers.keys())


# =============================================================================
# OCR 任务处理器示例
# =============================================================================

class OCRTaskHandler(TaskHandler):
    """OCR 任务处理器示例"""

    def execute(self, task: Task) -> Dict[str, Any]:
        """
        执行 OCR 任务

        Args:
            task: 任务对象

        Returns:
            Dict[str, Any]: OCR 结果
        """
        # 检查取消
        if self.is_cancelled():
            raise TaskCancelledException()

        # 获取引擎管理器
        from src.services.ocr.engine_manager import get_engine_manager
        engine_manager = get_engine_manager()

        # 执行识别
        image_path = task.input_data.get("image_path")
        result = engine_manager.recognize(image_path, task_id=task.id)

        # 报告完成
        self.report_progress(1.0)

        # 返回结果
        if result.success:
            return result.to_dict()
        else:
            raise Exception(result.error_message or "OCR 识别失败")


class TaskCancelledException(Exception):
    """任务被取消异常"""
    pass


# =============================================================================
# 注册内置处理器
# =============================================================================

TaskHandlerRegistry.register(TaskType.OCR, OCRTaskHandler)
