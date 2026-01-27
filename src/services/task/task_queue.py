#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 任务队列与调度

实现支持动态优先级的任务队列，提供持久化能力。

设计要点：
- 优先级队列（堆实现），支持运行时动态调整优先级
- 队列操作线程安全
- 支持按 TaskGroup 暂停/恢复
- 持久化：进行中任务保存 + 历史记录

Author: Umi-OCR Team
Date: 2026-01-27
"""

import heapq
import threading
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from .task_model import (
    Task,
    TaskGroup,
    TaskStatus,
    CancelMode
)


logger = logging.getLogger(__name__)


# =============================================================================
# 任务队列
# =============================================================================

class TaskQueue(QObject):
    """
    优先级任务队列

    职责: 入队/出队、优先级排序、暂停/恢复、持久化
    不包含: 执行逻辑
    线程安全: 所有公共方法加锁
    """

    # Qt 信号
    queue_changed = Signal()              # 队列变化
    group_paused = Signal(str)            # (group_id)
    group_resumed = Signal(str)           # (group_id)

    def __init__(self, storage_path: Path):
        """
        初始化任务队列

        Args:
            storage_path: 存储路径
        """
        super().__init__()

        self._lock = threading.RLock()
        self._heap: List[tuple] = []      # (-priority, created_at, group)
        self._groups: Dict[str, TaskGroup] = {}
        self._paused_groups: Set[str] = set()
        self._storage_path = storage_path

        # 确保存储目录存在
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # 启动时恢复队列
        self._restore_from_storage()

    # -------------------------------------------------------------------------
    # 入队操作
    # -------------------------------------------------------------------------

    def enqueue(self, group: TaskGroup) -> None:
        """
        入队任务组

        Args:
            group: 任务组对象
        """
        with self._lock:
            # 存储任务组
            self._groups[group.id] = group

            # 计算入队时间戳（确保优先级相同时按创建时间排序）
            created_at_timestamp = group.created_at.timestamp() if group.created_at else datetime.now().timestamp()

            # 使用负优先级实现最大堆（priority 越大越优先）
            heap_item = (-group.priority, created_at_timestamp, group)
            heapq.heappush(self._heap, heap_item)

            # 持久化队列
            self._persist_queue()

            # 发射信号
            self.queue_changed.emit()

            logger.info(f"任务组入队: {group.id} (priority={group.priority})")

    # -------------------------------------------------------------------------
    # 出队操作
    # -------------------------------------------------------------------------

    def dequeue(self) -> Optional[Task]:
        """
        获取下一个待执行的 Task

        逻辑: 跳过已暂停的 TaskGroup，返回最高优先级组中的第一个 PENDING Task

        Returns:
            Optional[Task]: 任务对象（无待执行任务返回 None）
        """
        with self._lock:
            while self._heap:
                # 获取最高优先级任务组
                _, _, group = self._heap[0]

                # 检查是否暂停
                if group.id in self._paused_groups:
                    # 跳过已暂停的任务组
                    heapq.heappop(self._heap)
                    continue

                # 查找第一个 PENDING 状态的 Task
                task = self._find_next_pending_task(group)
                if task:
                    return task

                # 没有待执行任务，从堆中移除
                heapq.heappop(self._heap)

            # 队列为空
            return None

    def _find_next_pending_task(self, group: TaskGroup) -> Optional[Task]:
        """
        在任务组中查找下一个待执行的任务

        Args:
            group: 任务组对象

        Returns:
            Optional[Task]: 任务对象（无待执行任务返回 None）
        """
        for task in group.get_all_tasks():
            if task.status == TaskStatus.PENDING:
                return task

        return None

    # -------------------------------------------------------------------------
    # 优先级调整
    # -------------------------------------------------------------------------

    def update_priority(self, group_id: str, new_priority: int) -> None:
        """
        动态调整优先级，重建堆

        Args:
            group_id: 任务组 ID
            new_priority: 新优先级
        """
        with self._lock:
            if group_id not in self._groups:
                logger.warning(f"任务组不存在: {group_id}")
                return

            group = self._groups[group_id]

            # 更新优先级
            old_priority = group.priority
            group.priority = new_priority

            # 重建堆
            self._rebuild_heap()

            # 持久化队列
            self._persist_queue()

            # 发射信号
            self.queue_changed.emit()

            logger.info(f"任务组优先级更新: {group_id} {old_priority} -> {new_priority}")

    def _rebuild_heap(self) -> None:
        """重建堆（用于优先级更新后）"""
        # 收集所有任务组
        groups = [item[2] for item in self._heap]

        # 清空堆
        self._heap.clear()

        # 重新入队
        for group in groups:
            created_at_timestamp = group.created_at.timestamp() if group.created_at else datetime.now().timestamp()
            heap_item = (-group.priority, created_at_timestamp, group)
            heapq.heappush(self._heap, heap_item)

    # -------------------------------------------------------------------------
    # 暂停/恢复
    # -------------------------------------------------------------------------

    def pause_group(self, group_id: str) -> None:
        """
        暂停 TaskGroup（不会中断正在执行的 Task）

        Args:
            group_id: 任务组 ID
        """
        with self._lock:
            if group_id not in self._groups:
                logger.warning(f"任务组不存在: {group_id}")
                return

            # 添加到暂停集合
            self._paused_groups.add(group_id)

            # 发射信号
            self.group_paused.emit(group_id)

            logger.info(f"任务组已暂停: {group_id}")

    def resume_group(self, group_id: str) -> None:
        """
        恢复 TaskGroup

        Args:
            group_id: 任务组 ID
        """
        with self._lock:
            if group_id not in self._paused_groups:
                return  # 未暂停，无需恢复

            # 从暂停集合移除
            self._paused_groups.remove(group_id)

            # 发射信号
            self.group_resumed.emit(group_id)

            logger.info(f"任务组已恢复: {group_id}")

    # -------------------------------------------------------------------------
    # 取消
    # -------------------------------------------------------------------------

    def cancel_group(self, group_id: str, mode: CancelMode) -> CancelMode:
        """
        取消 TaskGroup，返回 mode 供 TaskManager 决定如何处理正在执行的 Task

        Args:
            group_id: 任务组 ID
            mode: 取消模式

        Returns:
            CancelMode: 取消模式
        """
        with self._lock:
            if group_id not in self._groups:
                logger.warning(f"任务组不存在: {group_id}")
                return mode

            group = self._groups[group_id]

            # 取消所有 PENDING 状态的 Task
            for task in group.get_all_tasks():
                if task.status == TaskStatus.PENDING:
                    try:
                        task.transition_to(TaskStatus.CANCELLED)
                    except Exception:
                        pass  # 忽略状态转换错误

            # 从堆中移除（如果存在）
            self._remove_from_heap(group_id)

            # 持久化队列
            self._persist_queue()

            logger.info(f"任务组已取消: {group_id} (mode={mode.value})")

            return mode

    def _remove_from_heap(self, group_id: str) -> None:
        """
        从堆中移除任务组

        Args:
            group_id: 任务组 ID
        """
        # 标记需要移除的项
        to_remove = []

        for i, (_, _, group) in enumerate(self._heap):
            if group.id == group_id:
                to_remove.append(i)

        # 从后往前移除（避免索引变化）
        for i in reversed(to_remove):
            del self._heap[i]

        # 如果移除了元素，重建堆
        if to_remove:
            heapq.heapify(self._heap)

    # -------------------------------------------------------------------------
    # 查询
    # -------------------------------------------------------------------------

    def get_group(self, group_id: str) -> Optional[TaskGroup]:
        """
        获取任务组

        Args:
            group_id: 任务组 ID

        Returns:
            Optional[TaskGroup]: 任务组对象（不存在返回 None）
        """
        with self._lock:
            return self._groups.get(group_id)

    def get_all_groups(self) -> List[TaskGroup]:
        """
        获取所有任务组

        Returns:
            List[TaskGroup]: 任务组列表
        """
        with self._lock:
            return list(self._groups.values())

    def get_pending_count(self) -> int:
        """
        获取待执行任务数

        Returns:
            int: 待执行任务数
        """
        with self._lock:
            count = 0
            for group in self._groups.values():
                if group.id in self._paused_groups:
                    continue
                for task in group.get_all_tasks():
                    if task.status == TaskStatus.PENDING:
                        count += 1
            return count

    # -------------------------------------------------------------------------
    # 持久化
    # -------------------------------------------------------------------------

    def _persist_queue(self) -> None:
        """保存队列状态到 task_queue.json"""
        try:
            queue_file = self._storage_path / "task_queue.json"

            # 收集队列中的任务组 ID
            queue_group_ids = [group.id for _, _, group in self._heap]

            # 保存队列数据
            queue_data = {
                "queue_group_ids": queue_group_ids,
                "paused_groups": list(self._paused_groups)
            }

            # 写入文件
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump(queue_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"队列持久化失败: {e}", exc_info=True)

    def _restore_from_storage(self) -> None:
        """
        从文件恢复队列状态

        注意: RUNNING 状态的任务重置为 PENDING（程序重启后需重新执行）
        """
        try:
            queue_file = self._storage_path / "task_queue.json"

            if not queue_file.exists():
                logger.info("队列持久化文件不存在，跳过恢复")
                return

            # 读取队列数据
            with open(queue_file, "r", encoding="utf-8") as f:
                queue_data = json.load(f)

            # 读取所有任务组文件
            self._load_groups_from_storage()

            # 恢复队列顺序和暂停状态
            queue_group_ids = queue_data.get("queue_group_ids", [])
            self._paused_groups = set(queue_data.get("paused_groups", []))

            # 重建堆
            self._heap.clear()
            for group_id in queue_group_ids:
                if group_id in self._groups:
                    group = self._groups[group_id]

                    # 重置 RUNNING 任务为 PENDING
                    for task in group.get_all_tasks():
                        if task.status == TaskStatus.RUNNING:
                            task.status = TaskStatus.PENDING
                            task.started_at = None

                    # 入队
                    created_at_timestamp = group.created_at.timestamp() if group.created_at else datetime.now().timestamp()
                    heap_item = (-group.priority, created_at_timestamp, group)
                    heapq.heappush(self._heap, heap_item)

            logger.info(f"队列恢复完成: {len(self._groups)} 个任务组, {len(self._paused_groups)} 个已暂停")

        except Exception as e:
            logger.error(f"队列恢复失败: {e}", exc_info=True)

    def _load_groups_from_storage(self) -> None:
        """从存储加载所有任务组"""
        try:
            for group_file in self._storage_path.glob("group_*.json"):
                with open(group_file, "r", encoding="utf-8") as f:
                    group_data = json.load(f)
                    group = TaskGroup.from_dict(group_data)
                    self._groups[group.id] = group

        except Exception as e:
            logger.error(f"加载任务组失败: {e}", exc_info=True)

    def _save_group_to_storage(self, group: TaskGroup) -> None:
        """
        保存单个任务组到文件

        Args:
            group: 任务组对象
        """
        try:
            group_file = self._storage_path / f"group_{group.id}.json"
            with open(group_file, "w", encoding="utf-8") as f:
                f.write(group.to_json())

        except Exception as e:
            logger.error(f"保存任务组失败: {group.id}, {e}", exc_info=True)

    def save_to_history(self, group: TaskGroup) -> None:
        """
        保存已完成的 TaskGroup 到 task_history.jsonl

        Args:
            group: 任务组对象
        """
        try:
            history_file = self._storage_path / "task_history.jsonl"

            # 追加到历史文件
            with open(history_file, "a", encoding="utf-8") as f:
                f.write(group.to_json() + "\n")

            # 删除任务组文件
            group_file = self._storage_path / f"group_{group.id}.json"
            if group_file.exists():
                group_file.unlink()

            # 从内存移除
            self._groups.pop(group.id, None)

            logger.info(f"任务组已保存到历史: {group.id}")

        except Exception as e:
            logger.error(f"保存历史记录失败: {group.id}, {e}", exc_info=True)

    def load_history(self, limit: int = 100) -> List[TaskGroup]:
        """
        加载历史记录

        Args:
            limit: 最大记录数

        Returns:
            List[TaskGroup]: 历史任务组列表
        """
        try:
            history_file = self._storage_path / "task_history.jsonl"

            if not history_file.exists():
                return []

            groups = []
            with open(history_file, "r", encoding="utf-8") as f:
                for line in f:
                    if len(groups) >= limit:
                        break
                    line = line.strip()
                    if line:
                        group_data = json.loads(line)
                        group = TaskGroup.from_dict(group_data)
                        groups.append(group)

            # 按创建时间倒序（最新的在前）
            groups.sort(key=lambda g: g.created_at.timestamp(), reverse=True)

            return groups

        except Exception as e:
            logger.error(f"加载历史记录失败: {e}", exc_info=True)
            return []

    # -------------------------------------------------------------------------
    # 清理
    # -------------------------------------------------------------------------

    def clear(self) -> None:
        """清空队列"""
        with self._lock:
            self._heap.clear()
            self._groups.clear()
            self._paused_groups.clear()

            # 持久化队列
            self._persist_queue()

            logger.info("队列已清空")

    def clear_completed_groups(self) -> None:
        """清理已完成的任务组"""
        with self._lock:
            to_remove = []

            for group_id, group in self._groups.items():
                if group.is_terminal():
                    to_remove.append(group_id)

            for group_id in to_remove:
                group = self._groups.pop(group_id)
                self._remove_from_heap(group_id)
                self.save_to_history(group)

            logger.info(f"已清理 {len(to_remove)} 个已完成任务组")
