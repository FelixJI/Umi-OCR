#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 任务执行器

实现基于 QThread 的任务执行器，支持处理器注册模式。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import threading
import time
import logging
from typing import Optional, List

from PySide6.QtCore import QThread, Signal

from .task_model import Task, TaskStatus, CancelMode
from .task_handler import TaskHandler, TaskHandlerRegistry, TaskCancelledException
from .task_queue import TaskQueue

logger = logging.getLogger(__name__)


# =============================================================================
# 任务执行器
# =============================================================================


class TaskWorker(QThread):
    """
    任务执行器（单个工作线程）

    职责: 从队列取任务并执行、管理生命周期、发射信号、处理重试
    由 TaskManager 创建和管理多个 Worker 实例
    """

    # Qt 信号
    task_started = Signal(str, str)  # (task_id, group_id)
    task_progress = Signal(str, float)  # (task_id, progress) - 节流后
    task_completed = Signal(str, object)  # (task_id, result)
    task_failed = Signal(str, str)  # (task_id, error_message)
    task_cancelled = Signal(str)  # (task_id)
    group_paused_by_failure = Signal(str)  # (group_id) 因失败暂停

    PROGRESS_THROTTLE_MS = 100  # 进度节流间隔（毫秒）

    def __init__(self, task_queue: TaskQueue, worker_id: int):
        """
        初始化任务执行器

        Args:
            task_queue: 任务队列
            worker_id: 工作线程 ID
        """
        super().__init__()

        self._queue = task_queue
        self._worker_id = worker_id

        # 运行标志
        self._running = True

        # 当前任务信息
        self._current_task: Optional[Task] = None
        self._current_group_id: Optional[str] = None
        self._current_handler: Optional[TaskHandler] = None

        # 进度节流
        self._progress_lock = threading.Lock()
        self._last_progress_time: float = 0.0

        # 取消模式
        self._cancel_mode: Optional[CancelMode] = None

    # -------------------------------------------------------------------------
    # 线程主循环
    # -------------------------------------------------------------------------

    def run(self) -> None:
        """
        工作线程主循环:
        while running:
            task = queue.dequeue()
            if task: execute_task(task)
            else: sleep(100ms)
        """
        logger.info(f"任务执行器启动: Worker-{self._worker_id}")

        while self._running:
            try:
                # 从队列获取任务
                task = self._queue.dequeue()

                if task:
                    # 查找任务所属的组
                    group = self._queue.get_group(task.id)
                    group_id = group.id if group else "unknown"

                    # 执行任务
                    self._execute_task(task, group_id)
                else:
                    # 队列为空，休眠 100ms
                    time.sleep(0.1)

            except Exception as e:
                logger.error(
                    f"任务执行器异常: Worker-{self._worker_id}, {e}", exc_info=True
                )

        logger.info(f"任务执行器停止: Worker-{self._worker_id}")

    # -------------------------------------------------------------------------
    # 任务执行
    # -------------------------------------------------------------------------

    def _execute_task(self, task: Task, group_id: str) -> None:
        """
        执行单个任务:
        1. 状态 PENDING -> RUNNING, emit task_started
        2. 获取 Handler 并执行
        3. 成功: 状态 -> COMPLETED, emit task_completed
        4. 失败: 调用 _handle_failure()
        5. 取消: 状态 -> CANCELLED, emit task_cancelled

        Args:
            task: 任务对象
            group_id: 任务组 ID
        """
        self._current_task = task
        self._current_group_id = group_id

        try:
            # 状态转换: PENDING -> RUNNING
            task.transition_to(TaskStatus.RUNNING)
            self.task_started.emit(task.id, group_id)

            logger.info(f"任务开始执行: {task.id} (Worker-{self._worker_id})")

            # 获取 Handler
            handler = TaskHandlerRegistry.get(task.task_type)
            if not handler:
                raise Exception(f"未注册的任务处理器: {task.task_type.value}")

            self._current_handler = handler
            handler.set_task(task)

            # 连接进度回调
            self._connect_progress_signals(handler)

            # 执行任务
            result = handler.execute(task)

            # 成功: 状态 -> COMPLETED
            task.transition_to(TaskStatus.COMPLETED)
            task.result = result

            self.task_completed.emit(task.id, result)
            logger.info(f"任务完成: {task.id}")

        except TaskCancelledException:
            # 取消: 状态 -> CANCELLED
            task.transition_to(TaskStatus.CANCELLED)
            self.task_cancelled.emit(task.id)
            logger.info(f"任务已取消: {task.id}")

        except Exception as e:
            # 失败: 处理异常
            error_message = str(e)
            self._handle_failure(task, group_id, error_message)

        finally:
            # 清理
            self._current_task = None
            self._current_group_id = None
            self._current_handler = None

    def _connect_progress_signals(self, handler: TaskHandler) -> None:
        """
        连接进度信号（带节流）

        Args:
            handler: 任务处理器
        """

        # 通过轮询方式实现节流
        def progress_watcher():
            if self._current_task and self._current_handler:
                progress = self._current_task.progress
                self._emit_progress_throttled(self._current_task.id, progress)

        # 这里简化实现，实际应该在执行过程中定期调用
        # 也可以使用定时器实现节流
        pass

    def _emit_progress_throttled(self, task_id: str, progress: float) -> None:
        """
        发射进度信号（带节流）

        Args:
            task_id: 任务 ID
            progress: 进度值
        """
        with self._progress_lock:
            current_time = time.time() * 1000  # 毫秒

            # 检查是否超过节流间隔
            if current_time - self._last_progress_time >= self.PROGRESS_THROTTLE_MS:
                self.task_progress.emit(task_id, progress)
                self._last_progress_time = current_time

    # -------------------------------------------------------------------------
    # 失败处理
    # -------------------------------------------------------------------------

    def _handle_failure(self, task: Task, group_id: str, error: str) -> None:
        """
        失败处理（混合重试策略）:
        1. retry_count < max_retries: 重置为 PENDING 等待重试
        2. 否则: 标记 FAILED, 整个 TaskGroup 暂停, emit group_paused_by_failure

        Args:
            task: 任务对象
            group_id: 任务组 ID
            error: 错误信息
        """
        task.error = error

        logger.error(f"任务失败: {task.id}, {error}")

        # 增加重试次数
        task.retry_count += 1

        if task.is_retryable():
            # 可重试: 状态 -> PENDING
            task.transition_to(TaskStatus.PENDING)
            self.task_failed.emit(
                task.id,
                f"任务失败，将重试 ({task.retry_count}/{task.max_retries}): {error}",
            )

            logger.info(
                f"任务将重试: {task.id} ({task.retry_count}/{task.max_retries})"
            )

        else:
            # 不可重试: 状态 -> FAILED
            task.transition_to(TaskStatus.FAILED)
            self.task_failed.emit(task.id, error)

            # 检查任务组是否应该暂停
            group = self._queue.get_group(group_id)
            if group:
                group.update_status()
                if group.status == TaskStatus.PAUSED:
                    self.group_paused_by_failure.emit(group_id)
                    logger.warning(f"任务组因失败暂停: {group_id}")

    # -------------------------------------------------------------------------
    # 取消处理
    # -------------------------------------------------------------------------

    def request_cancel(self, mode: CancelMode) -> None:
        """
        请求取消当前任务

        Args:
            mode: 取消模式（GRACEFUL 或 FORCE）
        """
        self._cancel_mode = mode

        if self._current_handler:
            self._current_handler.request_cancel()

        logger.info(
            f"请求取消任务: {self._current_task.id if self._current_task else 'None'} "
            f"(mode={mode.value})"
        )

    # -------------------------------------------------------------------------
    # 生命周期管理
    # -------------------------------------------------------------------------

    def stop(self) -> None:
        """
        停止工作线程
        """
        logger.info(f"停止任务执行器: Worker-{self._worker_id}")

        self._running = False

        # 如果 FORCE 模式，请求立即取消
        if self._cancel_mode == CancelMode.FORCE and self._current_handler:
            self._current_handler.request_cancel()

    def is_running(self) -> bool:
        """
        检查工作线程是否运行中

        Returns:
            bool: 是否运行中
        """
        return self._running

    def get_current_task(self) -> Optional[Task]:
        """
        获取当前正在执行的任务

        Returns:
            Optional[Task]: 当前任务（空闲返回 None）
        """
        return self._current_task

    def get_current_group_id(self) -> Optional[str]:
        """
        获取当前任务组 ID

        Returns:
            Optional[str]: 任务组 ID（空闲返回 None）
        """
        return self._current_group_id


# =============================================================================
# Worker 管理器
# =============================================================================


class WorkerManager:
    """
    Worker 管理器

    管理多个 TaskWorker 实例的生命周期。
    """

    def __init__(self, task_queue: TaskQueue, max_workers: int = 3):
        """
        初始化 Worker 管理器

        Args:
            task_queue: 任务队列
            max_workers: 最大 Worker 数量
        """
        self._queue = task_queue
        self._max_workers = max_workers
        self._workers: List[TaskWorker] = []

    def start(self) -> None:
        """启动所有 Worker"""
        for i in range(self._max_workers):
            worker = TaskWorker(self._queue, worker_id=i)
            worker.finished.connect(self._on_worker_finished)
            worker.start()
            self._workers.append(worker)

        logger.info(f"启动 {self._max_workers} 个 Worker")

    def stop(self) -> None:
        """停止所有 Worker"""
        for worker in self._workers:
            worker.stop()

        # 等待所有 Worker 结束
        for worker in self._workers:
            worker.wait()

        self._workers.clear()
        logger.info("所有 Worker 已停止")

    def _on_worker_finished(self) -> None:
        """Worker 结束回调"""
        logger.debug("Worker 已结束")

    def set_max_workers(self, max_workers: int) -> None:
        """
        设置最大 Worker 数量

        Args:
            max_workers: 最大 Worker 数量
        """
        self._max_workers = max_workers

        # 如果 Worker 数量不足，启动新的 Worker
        while len(self._workers) < self._max_workers:
            worker_id = len(self._workers)
            worker = TaskWorker(self._queue, worker_id=worker_id)
            worker.finished.connect(self._on_worker_finished)
            worker.start()
            self._workers.append(worker)

        logger.info(f"Worker 数量更新: {max_workers}")

    def get_active_workers_count(self) -> int:
        """
        获取活跃 Worker 数量

        Returns:
            int: 活跃 Worker 数量
        """
        count = 0
        for worker in self._workers:
            if worker.is_running():
                count += 1
        return count

    def get_current_tasks(self) -> List[Optional[Task]]:
        """
        获取所有 Worker 当前执行的任务

        Returns:
            List[Optional[Task]]: 任务列表
        """
        return [worker.get_current_task() for worker in self._workers]
