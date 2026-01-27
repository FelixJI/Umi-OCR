#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 任务数据模型

定义任务系统的核心数据结构，包括：
- 任务状态枚举和转换规则
- 单个原子任务（Task）
- 可嵌套的任务组（TaskGroup）
- 序列化/反序列化支持

设计要点：
- Task 和 TaskGroup 支持树形嵌套
- 动态优先级仅作用于 TaskGroup 级别
- 数据模型包含轻量业务逻辑（状态验证、进度聚合）
- 完整的序列化支持（用于持久化和恢复）

Author: Umi-OCR Team
Date: 2026-01-27
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union, Set
from enum import Enum
from datetime import datetime
import uuid
import json


# =============================================================================
# 枚举类型定义
# =============================================================================

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"        # 等待执行
    RUNNING = "running"        # 执行中
    PAUSED = "paused"          # 已暂停（仅 TaskGroup 支持）
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败（重试耗尽）
    CANCELLED = "cancelled"    # 已取消


class CancelMode(Enum):
    """取消模式"""
    GRACEFUL = "graceful"      # 优雅取消：等待当前 Task 完成
    FORCE = "force"            # 强制取消：立即中断


class TaskType(Enum):
    """任务类型（用于处理器注册分发）"""
    OCR = "ocr"                # OCR 识别
    EXPORT = "export"          # 导出任务
    QRCODE = "qrcode"          # 二维码识别/生成
    PDF_PARSE = "pdf_parse"    # PDF 解析
    CUSTOM = "custom"          # 自定义扩展


# =============================================================================
# 异常类定义
# =============================================================================

class InvalidStateTransition(Exception):
    """非法状态转换异常"""
    pass


class InvalidTaskStructure(Exception):
    """非法任务结构异常"""
    pass


# =============================================================================
# 前向声明
# =============================================================================

# 用于类型注解的前向声明
TaskGroupType = "TaskGroup"


# =============================================================================
# 任务数据模型
# =============================================================================

@dataclass
class Task:
    """
    单个原子任务（不可再分的最小执行单元）

    职责: 持有数据、状态验证、序列化
    不包含: 执行逻辑（由 TaskHandler 处理）

    使用示例:
        >>> task = Task(
        ...     task_type=TaskType.OCR,
        ...     input_data={"image_path": "/path/to/image.jpg"},
        ...     created_at=datetime.now()
        ... )
        >>> task.transition_to(TaskStatus.RUNNING)
        >>> task.transition_to(TaskStatus.COMPLETED)
    """

    # 基本字段
    id: str                              # 唯一标识 (UUID)
    task_type: TaskType                  # 任务类型
    input_data: Dict[str, Any]           # 输入数据

    # 状态字段
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0                # 进度 0.0 ~ 1.0
    result: Optional[Any] = None        # 执行结果
    error: Optional[str] = None         # 错误信息

    # 重试配置
    retry_count: int = 0
    max_retries: int = 3

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据

    def __post_init__(self):
        """初始化后处理"""
        # 如果未提供 ID，自动生成
        if not self.id:
            self.id = str(uuid.uuid4())

        # 确保进度在 0.0 ~ 1.0 之间
        self.progress = max(0.0, min(1.0, self.progress))

    # -------------------------------------------------------------------------
    # 状态查询方法
    # -------------------------------------------------------------------------

    def is_terminal(self) -> bool:
        """是否处于终态"""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def is_retryable(self) -> bool:
        """是否可重试"""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries

    def is_active(self) -> bool:
        """是否处于活跃状态"""
        return self.status in (TaskStatus.PENDING, TaskStatus.RUNNING)

    # -------------------------------------------------------------------------
    # 状态转换规则
    # -------------------------------------------------------------------------

    _VALID_TRANSITIONS = {
        TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
        TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
        TaskStatus.FAILED: {TaskStatus.PENDING},  # 重试时回到 PENDING
        TaskStatus.PAUSED: {TaskStatus.PENDING},  # 恢复时回到 PENDING
    }

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """
        检查是否可以转换到新状态

        Args:
            new_status: 目标状态

        Returns:
            bool: 是否可以转换
        """
        if new_status == self.status:
            return True  # 状态不变，允许

        valid_states = self._VALID_TRANSITIONS.get(self.status, set())
        return new_status in valid_states

    def transition_to(self, new_status: TaskStatus) -> None:
        """
        转换到新状态（自动更新时间戳）

        Args:
            new_status: 目标状态

        Raises:
            InvalidStateTransition: 非法状态转换
        """
        if not self.can_transition_to(new_status):
            raise InvalidStateTransition(
                f"任务 {self.id} 无法从 {self.status.value} 转换到 {new_status.value}"
            )

        old_status = self.status
        self.status = new_status

        # 更新时间戳
        now = datetime.now()
        if new_status == TaskStatus.RUNNING and self.started_at is None:
            self.started_at = now
        elif new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            self.finished_at = now

        # 重置进度（如果回到 PENDING）
        if new_status == TaskStatus.PENDING and old_status != TaskStatus.PENDING:
            self.progress = 0.0

    # -------------------------------------------------------------------------
    # 序列化方法
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（用于 JSON 序列化）

        Returns:
            Dict[str, Any]: 任务字典
        """
        result = asdict(self)

        # 转换枚举类型
        result["task_type"] = self.task_type.value
        result["status"] = self.status.value

        # 转换 datetime 对象
        for time_field in ["created_at", "started_at", "finished_at"]:
            if result[time_field]:
                result[time_field] = getattr(self, time_field).isoformat()

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """
        从字典创建任务对象（用于反序列化）

        Args:
            data: 任务字典

        Returns:
            Task: 任务对象
        """
        # 转换枚举类型
        data = data.copy()
        if isinstance(data.get("task_type"), str):
            data["task_type"] = TaskType(data["task_type"])
        if isinstance(data.get("status"), str):
            data["status"] = TaskStatus(data["status"])

        # 转换 datetime 对象
        for time_field in ["created_at", "started_at", "finished_at"]:
            if data.get(time_field) and isinstance(data[time_field], str):
                data[time_field] = datetime.fromisoformat(data[time_field])

        return cls(**data)

    def to_json(self, indent: int = 2) -> str:
        """
        转换为 JSON 字符串

        Args:
            indent: 缩进空格数

        Returns:
            str: JSON 字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "Task":
        """
        从 JSON 字符串创建任务对象

        Args:
            json_str: JSON 字符串

        Returns:
            Task: 任务对象
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


# =============================================================================
# 任务组数据模型
# =============================================================================

@dataclass
class TaskGroup:
    """
    任务组（可嵌套，支持包含子 TaskGroup 或 Task）

    层级结构示例:
        TaskGroup (批量处理多个PDF)
          ├── TaskGroup (PDF-1)
          │     ├── Task (第1页OCR)
          │     └── Task (第2页OCR)
          └── TaskGroup (PDF-2)
                └── Task (第1页OCR)

    使用示例:
        >>> group = TaskGroup(id="group-1", title="批量OCR")
        >>> task1 = Task(task_type=TaskType.OCR, input_data={"path": "img1.jpg"})
        >>> group.add_task(task1)
        >>> print(group.progress)  # 聚合进度
    """

    # 基本字段
    id: str                              # 唯一标识 (UUID)
    title: str                            # 任务组标题

    # 树形结构
    children: List[Union[TaskGroupType, Task]] = field(default_factory=list)

    # 优先级和并发控制
    priority: int = 0                    # 动态优先级（运行时可调，数字越大优先级越高）
    max_concurrency: int = 1             # 组内最大并发数

    # 状态字段
    status: TaskStatus = TaskStatus.PENDING

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据

    def __post_init__(self):
        """初始化后处理"""
        # 如果未提供 ID，自动生成
        if not self.id:
            self.id = str(uuid.uuid4())

    # -------------------------------------------------------------------------
    # 树形结构操作
    # -------------------------------------------------------------------------

    def add_task(self, task: Task) -> None:
        """
        添加单个任务

        Args:
            task: 任务对象
        """
        if not isinstance(task, Task):
            raise InvalidTaskStructure("只能添加 Task 对象")
        self.children.append(task)

    def add_group(self, group: TaskGroupType) -> None:
        """
        添加子任务组

        Args:
            group: 任务组对象
        """
        if not isinstance(group, TaskGroup):
            raise InvalidTaskStructure("只能添加 TaskGroup 对象")
        self.children.append(group)

    def get_all_tasks(self) -> List[Task]:
        """
        递归获取所有任务（扁平化）

        Returns:
            List[Task]: 所有任务列表
        """
        tasks = []
        for child in self.children:
            if isinstance(child, Task):
                tasks.append(child)
            elif isinstance(child, TaskGroup):
                tasks.extend(child.get_all_tasks())
        return tasks

    def get_all_groups(self, include_self: bool = True) -> List[TaskGroupType]:
        """
        递归获取所有任务组

        Args:
            include_self: 是否包含自身

        Returns:
            List[TaskGroup]: 所有任务组列表
        """
        groups = [self] if include_self else []
        for child in self.children:
            if isinstance(child, TaskGroup):
                groups.append(child)
                groups.extend(child.get_all_groups(include_self=False))
        return groups

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        根据 ID 查找任务

        Args:
            task_id: 任务 ID

        Returns:
            Optional[Task]: 任务对象（未找到返回 None）
        """
        for child in self.children:
            if isinstance(child, Task) and child.id == task_id:
                return child
            elif isinstance(child, TaskGroup):
                task = child.get_task_by_id(task_id)
                if task:
                    return task
        return None

    def get_group_by_id(self, group_id: str) -> Optional[TaskGroupType]:
        """
        根据 ID 查找任务组

        Args:
            group_id: 任务组 ID

        Returns:
            Optional[TaskGroup]: 任务组对象（未找到返回 None）
        """
        if self.id == group_id:
            return self

        for child in self.children:
            if isinstance(child, TaskGroup):
                group = child.get_group_by_id(group_id)
                if group:
                    return group

        return None

    # -------------------------------------------------------------------------
    # 进度聚合
    # -------------------------------------------------------------------------

    @property
    def progress(self) -> float:
        """
        聚合计算整体进度

        Returns:
            float: 整体进度 (0.0 ~ 1.0)
        """
        all_tasks = self.get_all_tasks()
        if not all_tasks:
            return 0.0
        return sum(t.progress for t in all_tasks) / len(all_tasks)

    @property
    def total_tasks(self) -> int:
        """总任务数"""
        return len(self.get_all_tasks())

    @property
    def completed_tasks(self) -> int:
        """已完成任务数"""
        return len([t for t in self.get_all_tasks() if t.status == TaskStatus.COMPLETED])

    @property
    def failed_tasks(self) -> int:
        """失败任务数"""
        return len([t for t in self.get_all_tasks() if t.status == TaskStatus.FAILED])

    @property
    def running_tasks(self) -> int:
        """运行中任务数"""
        return len([t for t in self.get_all_tasks() if t.status == TaskStatus.RUNNING])

    @property
    def pending_tasks(self) -> int:
        """等待中任务数"""
        return len([t for t in self.get_all_tasks() if t.status == TaskStatus.PENDING])

    # -------------------------------------------------------------------------
    # 状态计算
    # -------------------------------------------------------------------------

    def compute_status(self) -> TaskStatus:
        """
        根据子任务状态计算组状态

        规则:
            - 所有任务完成 → COMPLETED
            - 任何任务失败且重试耗尽 → PAUSED（等待用户决定）
            - 任何任务运行中 → RUNNING
            - 任何任务等待中 → PENDING
            - 所有任务取消 → CANCELLED

        Returns:
            TaskStatus: 组状态
        """
        all_tasks = self.get_all_tasks()

        if not all_tasks:
            # 空任务组，保持当前状态
            return self.status

        statuses = [t.status for t in all_tasks]

        # 检查是否有任务失败且重试耗尽
        failed_no_retry = [t for t in all_tasks if t.status == TaskStatus.FAILED and not t.is_retryable()]
        if failed_no_retry:
            return TaskStatus.PAUSED

        # 检查所有任务是否完成
        if all(s == TaskStatus.COMPLETED for s in statuses):
            return TaskStatus.COMPLETED

        # 检查是否有任务运行中
        if TaskStatus.RUNNING in statuses:
            return TaskStatus.RUNNING

        # 检查是否有任务等待中
        if TaskStatus.PENDING in statuses:
            return TaskStatus.PENDING

        # 所有任务已取消
        if all(s == TaskStatus.CANCELLED for s in statuses):
            return TaskStatus.CANCELLED

        # 其他情况保持当前状态
        return self.status

    def update_status(self) -> None:
        """更新组状态"""
        new_status = self.compute_status()
        if new_status != self.status:
            old_status = self.status
            self.status = new_status

            # 更新时间戳
            now = datetime.now()
            if new_status == TaskStatus.RUNNING and self.started_at is None:
                self.started_at = now
            elif new_status in (TaskStatus.COMPLETED, TaskStatus.PAUSED, TaskStatus.CANCELLED):
                self.finished_at = now

    # -------------------------------------------------------------------------
    # 终态检查
    # -------------------------------------------------------------------------

    def is_terminal(self) -> bool:
        """是否处于终态"""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def is_complete(self) -> bool:
        """是否完全完成（所有子任务都完成）"""
        return self.status == TaskStatus.COMPLETED and self.completed_tasks == self.total_tasks

    # -------------------------------------------------------------------------
    # 序列化方法
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（用于 JSON 序列化）

        Returns:
            Dict[str, Any]: 任务组字典
        """
        result = {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "max_concurrency": self.max_concurrency,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "metadata": self.metadata,
            "children": []
        }

        # 递归序列化子节点
        for child in self.children:
            if isinstance(child, Task):
                result["children"].append({
                    "type": "task",
                    "data": child.to_dict()
                })
            elif isinstance(child, TaskGroup):
                result["children"].append({
                    "type": "group",
                    "data": child.to_dict()
                })

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskGroupType:
        """
        从字典创建任务组对象（用于反序列化）

        Args:
            data: 任务组字典

        Returns:
            TaskGroup: 任务组对象
        """
        # 转换 datetime 对象
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        started_at = datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        finished_at = datetime.fromisoformat(data["finished_at"]) if data.get("finished_at") else None

        # 创建任务组
        group = cls(
            id=data["id"],
            title=data["title"],
            priority=data.get("priority", 0),
            max_concurrency=data.get("max_concurrency", 1),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            created_at=created_at,
            started_at=started_at,
            finished_at=finished_at,
            metadata=data.get("metadata", {})
        )

        # 递归反序列化子节点
        for child_data in data.get("children", []):
            if child_data["type"] == "task":
                task = Task.from_dict(child_data["data"])
                group.add_task(task)
            elif child_data["type"] == "group":
                child_group = cls.from_dict(child_data["data"])
                group.add_group(child_group)

        return group

    def to_json(self, indent: int = 2) -> str:
        """
        转换为 JSON 字符串

        Args:
            indent: 缩进空格数

        Returns:
            str: JSON 字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> TaskGroupType:
        """
        从 JSON 字符串创建任务组对象

        Args:
            json_str: JSON 字符串

        Returns:
            TaskGroup: 任务组对象
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


# =============================================================================
# 辅助函数
# =============================================================================

def create_simple_task(
    task_type: TaskType,
    input_data: Dict[str, Any],
    max_retries: int = 3,
    **kwargs
) -> Task:
    """
    创建简单任务的便捷函数

    Args:
        task_type: 任务类型
        input_data: 输入数据
        max_retries: 最大重试次数
        **kwargs: 其他 Task 参数（不包括 id，会自动生成）

    Returns:
        Task: 任务对象
    """
    # 生成唯一ID
    import uuid
    task_id = kwargs.pop('id', str(uuid.uuid4()))
    
    return Task(
        id=task_id,
        task_type=task_type,
        input_data=input_data,
        max_retries=max_retries,
        **kwargs
    )


def create_simple_task_group(
    title: str,
    tasks: List[Task],
    priority: int = 0,
    max_concurrency: int = 1,
    **kwargs
) -> TaskGroup:
    """
    创建简单任务组的便捷函数

    Args:
        title: 任务组标题
        tasks: 任务列表
        priority: 优先级
        max_concurrency: 最大并发数
        **kwargs: 其他 TaskGroup 参数（不包括 id，会自动生成）

    Returns:
        TaskGroup: 任务组对象
    """
    # 生成唯一ID
    import uuid
    group_id = kwargs.pop('id', str(uuid.uuid4()))
    
    group = TaskGroup(
        id=group_id,
        title=title,
        priority=priority,
        max_concurrency=max_concurrency,
        **kwargs
    )
    for task in tasks:
        group.add_task(task)
    return group
