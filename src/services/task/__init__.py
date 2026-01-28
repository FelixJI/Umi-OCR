#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 任务系统模块

导出任务系统的公共接口：
- 任务数据模型（Task, TaskGroup）
- 任务管理器（TaskManager）
- 任务处理器（TaskHandler, TaskHandlerRegistry）

Author: Umi-OCR Team
Date: 2026-01-27
"""

from .task_model import (
    Task,
    TaskGroup,
    TaskStatus,
    TaskType,
    CancelMode,
    InvalidStateTransition,
    InvalidTaskStructure,
    create_simple_task,
    create_simple_task_group,
)

from .task_queue import TaskQueue
from .task_handler import (
    TaskHandler,
    TaskHandlerRegistry,
    TaskCancelledException,
    OCRTaskHandler,
)
from .task_worker import TaskWorker, WorkerManager
from .task_manager import TaskManager, get_task_manager

__all__ = [
    # 数据模型
    "Task",
    "TaskGroup",
    "TaskStatus",
    "TaskType",
    "CancelMode",
    "InvalidStateTransition",
    "InvalidTaskStructure",
    "create_simple_task",
    "create_simple_task_group",
    # 任务队列
    "TaskQueue",
    # 任务处理器
    "TaskHandler",
    "TaskHandlerRegistry",
    "TaskCancelledException",
    "OCRTaskHandler",
    # 任务执行器
    "TaskWorker",
    "WorkerManager",
    # 任务管理器
    "TaskManager",
    "get_task_manager",
]
