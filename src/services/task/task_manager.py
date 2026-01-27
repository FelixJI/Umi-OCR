#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 任务管理器

实现任务调度中心，整合队列、执行器，提供统一接口。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import threading
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .task_model import Task, TaskGroup, TaskType, TaskStatus, CancelMode
from .task_queue import TaskQueue
from .task_worker import TaskWorker, WorkerManager


logger = logging.getLogger(__name__)


# =============================================================================
# 任务管理器
# =============================================================================

class TaskManager(QObject):
    """
    任务管理器（单例）

    职责: 统一入口、管理 Worker 线程池、混合并发控制、聚合信号

    使用:
        manager = TaskManager.instance()
        group_id = manager.submit_ocr_tasks(image_paths, config)
        manager.pause_group(group_id)
    """

    # === Qt 信号（供 UI 层连接）===
    task_submitted = Signal(str)              # (group_id)
    task_started = Signal(str, str)           # (task_id, group_id)
    task_progress = Signal(str, float)        # (task_id, progress)
    task_completed = Signal(str, object)      # (task_id, result)
    task_failed = Signal(str, str)            # (task_id, error)
    group_progress = Signal(str, float)       # (group_id, progress)
    group_completed = Signal(str)             # (group_id)
    group_paused = Signal(str, str)           # (group_id, reason: "user"/"failure")
    group_cancelled = Signal(str)             # (group_id)
    queue_changed = Signal()                  # 队列状态变化

    _instance: Optional["TaskManager"] = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls) -> "TaskManager":
        """
        获取单例

        Returns:
            TaskManager: 唯一的任务管理器实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        """
        初始化任务管理器

        注意：由于单例模式，此方法只会被调用一次。
        """
        # 防止重复初始化
        if hasattr(self, "_initialized") and self._initialized:
            return

        super().__init__()
        self._initialized = True

        # 全局最大并发数
        self._global_max_concurrency = 3

        # 数据目录
        self._data_dir = Path("./UmiOCR-data")
        self._data_dir.mkdir(exist_ok=True)
        self._storage_path = self._data_dir / "tasks"

        # 任务队列
        self._queue = TaskQueue(self._storage_path)

        # Worker 管理器
        self._worker_manager = WorkerManager(self._queue, self._global_max_concurrency)

        # 连接信号
        self._connect_signals()

        logger.info("任务管理器初始化完成")

    def _connect_signals(self) -> None:
        """连接队列和 Worker 信号"""
        # 队列信号
        self._queue.queue_changed.connect(self.queue_changed.emit)
        self._queue.group_paused.connect(self._on_group_paused)
        self._queue.group_resumed.connect(self._on_group_resumed)

        # Worker 信号（通过 WorkerManager 转发）
        # 注意：这里需要在 WorkerManager 中添加信号转发

    # -------------------------------------------------------------------------
    # 初始化和启动
    # -------------------------------------------------------------------------

    def initialize(self) -> bool:
        """
        初始化任务管理器

        Returns:
            bool: 是否初始化成功
        """
        try:
            # 启动 Worker 线程池
            self._worker_manager.start()

            logger.info("任务管理器启动成功")
            return True

        except Exception as e:
            logger.error(f"任务管理器启动失败: {e}", exc_info=True)
            return False

    # -------------------------------------------------------------------------
    # 任务提交接口
    # -------------------------------------------------------------------------

    def submit_group(self, group: TaskGroup) -> str:
        """
        提交已构建的 TaskGroup

        Args:
            group: 任务组对象

        Returns:
            str: 任务组 ID
        """
        # 入队
        self._queue.enqueue(group)

        # 发射信号
        self.task_submitted.emit(group.id)

        logger.info(f"任务组已提交: {group.id}")
        return group.id

    def submit_ocr_tasks(
        self,
        image_paths: List[str],
        title: str = "OCR任务",
        priority: int = 0,
        max_concurrency: int = 1,
        engine_config: Optional[Dict] = None,
    ) -> str:
        """
        便捷方法：提交 OCR 任务组

        Args:
            image_paths: 图片路径列表
            title: 任务组标题
            priority: 优先级
            max_concurrency: 最大并发数
            engine_config: 引擎配置（可选）

        Returns:
            str: 任务组 ID
        """
        # 创建任务组
        import uuid
        group = TaskGroup(
            id=str(uuid.uuid4()),
            title=title,
            priority=priority,
            max_concurrency=max_concurrency
        )

        # 添加任务
        for image_path in image_paths:
            task = Task(
                id=str(uuid.uuid4()),
                task_type=TaskType.OCR,
                input_data={
                    "image_path": image_path,
                    "engine_config": engine_config or {}
                }
            )
            group.add_task(task)

        # 提交
        return self.submit_group(group)

    def submit_pdf_tasks(
        self,
        pdf_paths: List[str],
        title: str = "PDF识别",
        priority: int = 0,
    ) -> str:
        """
        便捷方法：提交 PDF 识别任务组（嵌套结构）

        生成结构:
        TaskGroup (总任务)
          ├── TaskGroup (PDF-1) -> [Task(第1页), Task(第2页)...]
          └── TaskGroup (PDF-2) -> [...]

        Args:
            pdf_paths: PDF 文件路径列表
            title: 任务组标题
            priority: 优先级

        Returns:
            str: 任务组 ID
        """
        import uuid
        # 创建根任务组
        root_group = TaskGroup(
            id=str(uuid.uuid4()),
            title=title,
            priority=priority
        )

        # 为每个 PDF 创建子任务组
        for pdf_path in pdf_paths:
            # 创建子任务组
            pdf_group = TaskGroup(
                id=str(uuid.uuid4()),
                title=Path(pdf_path).name,
                priority=priority,
                max_concurrency=1  # PDF 任务串行执行
            )

            # TODO: 这里应该解析 PDF 页数，为每页创建任务
            # 暂时创建一个示例任务
            task = Task(
                id=str(uuid.uuid4()),
                task_type=TaskType.PDF_PARSE,
                input_data={
                    "pdf_path": pdf_path,
                    "page_number": 1
                }
            )
            pdf_group.add_task(task)

            # 添加到根任务组
            root_group.add_group(pdf_group)

        # 提交
        return self.submit_group(root_group)

    # -------------------------------------------------------------------------
    # 控制接口
    # -------------------------------------------------------------------------

    def pause_group(self, group_id: str) -> None:
        """
        暂停任务组

        Args:
            group_id: 任务组 ID
        """
        self._queue.pause_group(group_id)
        logger.info(f"任务组暂停请求: {group_id}")

    def resume_group(self, group_id: str) -> None:
        """
        恢复任务组

        Args:
            group_id: 任务组 ID
        """
        self._queue.resume_group(group_id)
        logger.info(f"任务组恢复请求: {group_id}")

    def cancel_group(self, group_id: str, mode: CancelMode = CancelMode.GRACEFUL) -> None:
        """
        取消任务组
        GRACEFUL: 等待当前 Task 完成
        FORCE: 立即中断

        Args:
            group_id: 任务组 ID
            mode: 取消模式
        """
        # 获取组内所有任务
        group = self._queue.get_group(group_id)
        if not group:
            logger.warning(f"任务组不存在: {group_id}")
            return

        # 取消队列中的任务
        self._queue.cancel_group(group_id, mode)

        # 如果是 FORCE 模式，请求取消正在执行的任务
        if mode == CancelMode.FORCE:
            for worker in self._worker_manager._workers:
                if worker.get_current_group_id() == group_id:
                    worker.request_cancel(mode)

        self.group_cancelled.emit(group_id)
        logger.info(f"任务组已取消: {group_id} (mode={mode.value})")

    def retry_failed_tasks(self, group_id: str) -> None:
        """
        重试失败的任务（用户点击重试后调用）

        Args:
            group_id: 任务组 ID
        """
        group = self._queue.get_group(group_id)
        if not group:
            logger.warning(f"任务组不存在: {group_id}")
            return

        # 重置失败任务为 PENDING
        for task in group.get_all_tasks():
            if task.status == TaskStatus.FAILED:
                task.retry_count = 0
                task.transition_to(TaskStatus.PENDING)

        # 恢复任务组
        self.resume_group(group_id)

        logger.info(f"任务组失败任务已重试: {group_id}")

    def skip_failed_tasks(self, group_id: str) -> None:
        """
        跳过失败的任务，继续执行其他任务

        Args:
            group_id: 任务组 ID
        """
        group = self._queue.get_group(group_id)
        if not group:
            logger.warning(f"任务组不存在: {group_id}")
            return

        # 将失败任务标记为 CANCELLED
        for task in group.get_all_tasks():
            if task.status == TaskStatus.FAILED:
                try:
                    task.transition_to(TaskStatus.CANCELLED)
                except Exception:
                    pass  # 忽略状态转换错误

        # 恢复任务组
        self.resume_group(group_id)

        logger.info(f"任务组失败任务已跳过: {group_id}")

    def update_priority(self, group_id: str, new_priority: int) -> None:
        """
        动态调整优先级

        Args:
            group_id: 任务组 ID
            new_priority: 新优先级
        """
        self._queue.update_priority(group_id, new_priority)
        logger.info(f"任务组优先级已更新: {group_id} -> {new_priority}")

    # -------------------------------------------------------------------------
    # 查询接口
    # -------------------------------------------------------------------------

    def get_group(self, group_id: str) -> Optional[TaskGroup]:
        """
        获取任务组

        Args:
            group_id: 任务组 ID

        Returns:
            Optional[TaskGroup]: 任务组对象（不存在返回 None）
        """
        return self._queue.get_group(group_id)

    def get_all_groups(self) -> List[TaskGroup]:
        """
        获取所有任务组

        Returns:
            List[TaskGroup]: 任务组列表
        """
        return self._queue.get_all_groups()

    def get_history(self, limit: int = 100) -> List[TaskGroup]:
        """
        获取历史记录

        Args:
            limit: 最大记录数

        Returns:
            List[TaskGroup]: 历史任务组列表
        """
        return self._queue.load_history(limit)

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息:
        {
            "total_groups": int,
            "total_tasks": int,
            "completed_tasks": int,
            "pending_tasks": int,
            "active_workers": int,
        }

        Returns:
            Dict[str, Any]: 统计信息
        """
        groups = self.get_all_groups()

        total_tasks = sum(g.total_tasks for g in groups)
        completed_tasks = sum(g.completed_tasks for g in groups)
        pending_tasks = self._queue.get_pending_count()
        active_workers = self._worker_manager.get_active_workers_count()

        return {
            "total_groups": len(groups),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "active_workers": active_workers,
        }

    # -------------------------------------------------------------------------
    # 配置接口
    # -------------------------------------------------------------------------

    def set_global_concurrency(self, max_concurrency: int) -> None:
        """
        设置全局最大并发数

        Args:
            max_concurrency: 最大并发数
        """
        self._global_max_concurrency = max_concurrency
        self._worker_manager.set_max_workers(max_concurrency)
        logger.info(f"全局最大并发数已设置: {max_concurrency}")

    # -------------------------------------------------------------------------
    # 生命周期
    # -------------------------------------------------------------------------

    def shutdown(self) -> None:
        """
        关闭管理器，停止所有 Worker，保存队列状态
        """
        logger.info("任务管理器正在关闭...")

        # 停止 Worker
        self._worker_manager.stop()

        logger.info("任务管理器已关闭")

    # -------------------------------------------------------------------------
    # 信号回调
    # -------------------------------------------------------------------------

    def _on_group_paused(self, group_id: str) -> None:
        """任务组暂停回调"""
        self.group_paused.emit(group_id, "user")

    def _on_group_resumed(self, group_id: str) -> None:
        """任务组恢复回调"""
        logger.info(f"任务组已恢复: {group_id}")


# =============================================================================
# 全局任务管理器实例
# =============================================================================

_global_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """
    获取全局任务管理器

    Returns:
        TaskManager: 任务管理器单例
    """
    global _global_task_manager
    if _global_task_manager is None:
        _global_task_manager = TaskManager.instance()
    return _global_task_manager
