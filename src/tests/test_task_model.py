#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 任务数据模型单元测试

测试任务数据模型的各项功能：
- 状态转换规则
- 进度聚合计算
- 序列化/反序列化
- 嵌套结构操作
- 树形结构查询

Author: Umi-OCR Team
Date: 2026-01-27
"""

import pytest
from datetime import datetime
from src.services.task.task_model import (
    Task,
    TaskGroup,
    TaskStatus,
    TaskType,
    CancelMode,
    InvalidStateTransition,
    InvalidTaskStructure,
    create_simple_task,
    create_simple_task_group
)


# =============================================================================
# 测试 Task 类
# =============================================================================

class TestTask:
    """测试 Task 类"""

    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            task_type=TaskType.OCR,
            input_data={"image_path": "/test/image.jpg"}
        )

        assert task.id  # ID 应该自动生成
        assert task.task_type == TaskType.OCR
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0.0
        assert task.retry_count == 0
        assert isinstance(task.created_at, datetime)

    def test_task_auto_id_generation(self):
        """测试任务 ID 自动生成"""
        task1 = Task(task_type=TaskType.OCR, input_data={})
        task2 = Task(task_type=TaskType.OCR, input_data={})

        assert task1.id != task2.id  # 两个任务的 ID 应该不同

    def test_task_progress_clamping(self):
        """测试进度值的限制"""
        # 测试过大的进度值
        task = Task(
            task_type=TaskType.OCR,
            input_data={},
            progress=1.5
        )
        assert task.progress == 1.0

        # 测试负进度值
        task2 = Task(
            task_type=TaskType.OCR,
            input_data={},
            progress=-0.5
        )
        assert task2.progress == 0.0

    def test_task_status_query(self):
        """测试任务状态查询"""
        task = Task(task_type=TaskType.OCR, input_data={})

        # PENDING 状态
        assert not task.is_terminal()
        assert not task.is_retryable()
        assert task.is_active()

        # RUNNING 状态
        task.transition_to(TaskStatus.RUNNING)
        assert not task.is_terminal()
        assert not task.is_retryable()
        assert task.is_active()

        # COMPLETED 状态
        task.transition_to(TaskStatus.COMPLETED)
        assert task.is_terminal()
        assert not task.is_active()

    def test_task_retryable(self):
        """测试任务可重试状态"""
        task = Task(
            task_type=TaskType.OCR,
            input_data={},
            max_retries=3
        )

        # 第一次失败，可重试
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.FAILED)
        assert task.is_retryable()
        assert task.retry_count == 0

        # 增加重试次数，仍然可重试
        task.retry_count = 2
        assert task.is_retryable()

        # 超过重试次数，不可重试
        task.retry_count = 3
        assert not task.is_retryable()

    def test_valid_state_transitions(self):
        """测试合法的状态转换"""
        task = Task(task_type=TaskType.OCR, input_data={})

        # PENDING -> RUNNING
        assert task.can_transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.RUNNING)
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

        # RUNNING -> COMPLETED
        assert task.can_transition_to(TaskStatus.COMPLETED)
        task.transition_to(TaskStatus.COMPLETED)
        assert task.status == TaskStatus.COMPLETED
        assert task.finished_at is not None

    def test_invalid_state_transitions(self):
        """测试非法的状态转换"""
        task = Task(task_type=TaskType.OCR, input_data={})

        # PENDING -> COMPLETED（不合法）
        with pytest.raises(InvalidStateTransition):
            task.transition_to(TaskStatus.COMPLETED)

        # RUNNING -> PENDING（不合法）
        task.transition_to(TaskStatus.RUNNING)
        with pytest.raises(InvalidStateTransition):
            task.transition_to(TaskStatus.PENDING)

    def test_task_serialization(self):
        """测试任务序列化"""
        task = Task(
            task_type=TaskType.OCR,
            input_data={"image_path": "/test/image.jpg"},
            max_retries=3,
            metadata={"tag": "test"}
        )

        # 转换为字典
        task_dict = task.to_dict()
        assert task_dict["task_type"] == "ocr"
        assert task_dict["status"] == "pending"
        assert task_dict["input_data"] == {"image_path": "/test/image.jpg"}

        # 从字典恢复
        restored_task = Task.from_dict(task_dict)
        assert restored_task.task_type == TaskType.OCR
        assert restored_task.input_data == task.input_data
        assert restored_task.metadata == task.metadata

    def test_task_json_serialization(self):
        """测试任务 JSON 序列化"""
        task = Task(
            task_type=TaskType.OCR,
            input_data={"path": "/test.jpg"}
        )

        # 转换为 JSON
        json_str = task.to_json()
        assert isinstance(json_str, str)

        # 从 JSON 恢复
        restored_task = Task.from_json(json_str)
        assert restored_task.task_type == task.task_type
        assert restored_task.input_data == task.input_data


# =============================================================================
# 测试 TaskGroup 类
# =============================================================================

class TestTaskGroup:
    """测试 TaskGroup 类"""

    def test_group_creation(self):
        """测试任务组创建"""
        group = TaskGroup(
            id="group-1",
            title="测试任务组",
            priority=5,
            max_concurrency=2
        )

        assert group.id == "group-1"
        assert group.title == "测试任务组"
        assert group.priority == 5
        assert group.max_concurrency == 2
        assert group.status == TaskStatus.PENDING
        assert isinstance(group.created_at, datetime)

    def test_group_add_task(self):
        """测试添加任务"""
        group = TaskGroup(id="group-1", title="测试")
        task = Task(task_type=TaskType.OCR, input_data={})

        group.add_task(task)

        assert len(group.children) == 1
        assert group.total_tasks == 1

    def test_group_add_group(self):
        """测试添加子任务组"""
        parent = TaskGroup(id="parent", title="父组")
        child = TaskGroup(id="child", title="子组")

        parent.add_group(child)

        assert len(parent.children) == 1
        assert parent.get_all_groups() == [parent, child]

    def test_group_add_invalid_type(self):
        """测试添加非法类型"""
        group = TaskGroup(id="group-1", title="测试")

        # 不能添加非 Task/TaskGroup 对象
        with pytest.raises(InvalidTaskStructure):
            group.add_task("invalid")

        with pytest.raises(InvalidTaskStructure):
            group.add_group("invalid")

    def test_group_get_all_tasks(self):
        """测试获取所有任务"""
        group = TaskGroup(id="group-1", title="测试")

        # 添加任务
        for i in range(3):
            task = Task(task_type=TaskType.OCR, input_data={"index": i})
            group.add_task(task)

        all_tasks = group.get_all_tasks()
        assert len(all_tasks) == 3

    def test_group_progress_aggregation(self):
        """测试进度聚合"""
        group = TaskGroup(id="group-1", title="测试")

        # 添加任务
        task1 = Task(task_type=TaskType.OCR, input_data={})
        task2 = Task(task_type=TaskType.OCR, input_data={})
        task3 = Task(task_type=TaskType.OCR, input_data={})

        group.add_task(task1)
        group.add_task(task2)
        group.add_task(task3)

        # 初始进度为 0
        assert group.progress == 0.0

        # 更新任务进度
        task1.progress = 0.5
        task2.progress = 1.0
        task3.progress = 0.0

        # 计算聚合进度：(0.5 + 1.0 + 0.0) / 3 = 0.5
        assert group.progress == 0.5

    def test_group_task_count_properties(self):
        """测试任务计数属性"""
        group = TaskGroup(id="group-1", title="测试")

        # 添加 5 个任务
        for i in range(5):
            task = Task(task_type=TaskType.OCR, input_data={})
            group.add_task(task)

        assert group.total_tasks == 5
        assert group.pending_tasks == 5
        assert group.completed_tasks == 0
        assert group.failed_tasks == 0
        assert group.running_tasks == 0

        # 更新任务状态
        tasks = group.get_all_tasks()
        tasks[0].transition_to(TaskStatus.COMPLETED)
        tasks[1].transition_to(TaskStatus.COMPLETED)
        tasks[2].transition_to(TaskStatus.RUNNING)
        tasks[3].transition_to(TaskStatus.FAILED)

        assert group.completed_tasks == 2
        assert group.running_tasks == 1
        assert group.failed_tasks == 1
        assert group.pending_tasks == 1

    def test_group_status_computation(self):
        """测试组状态计算"""
        group = TaskGroup(id="group-1", title="测试")

        # 添加任务
        task1 = Task(task_type=TaskType.OCR, input_data={})
        task2 = Task(task_type=TaskType.OCR, input_data={})
        group.add_task(task1)
        group.add_task(task2)

        # 初始状态：所有任务 PENDING → 组状态 PENDING
        group.update_status()
        assert group.status == TaskStatus.PENDING

        # 一个任务 RUNNING → 组状态 RUNNING
        task1.transition_to(TaskStatus.RUNNING)
        group.update_status()
        assert group.status == TaskStatus.RUNNING

        # 所有任务 COMPLETED → 组状态 COMPLETED
        task1.transition_to(TaskStatus.COMPLETED)
        task2.transition_to(TaskStatus.COMPLETED)
        group.update_status()
        assert group.status == TaskStatus.COMPLETED

    def test_group_failed_and_paused(self):
        """测试失败后暂停"""
        group = TaskGroup(id="group-1", title="测试")

        # 添加任务（重试次数耗尽）
        task = Task(
            task_type=TaskType.OCR,
            input_data={},
            max_retries=0
        )
        group.add_task(task)

        # 任务失败
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.FAILED)

        # 组状态应该变为 PAUSED（等待用户决定）
        group.update_status()
        assert group.status == TaskStatus.PAUSED

    def test_group_get_task_by_id(self):
        """测试根据 ID 查找任务"""
        group = TaskGroup(id="group-1", title="测试")

        task = Task(task_type=TaskType.OCR, input_data={})
        group.add_task(task)

        found_task = group.get_task_by_id(task.id)
        assert found_task == task

        # 查找不存在的任务
        not_found = group.get_task_by_id("non-existent")
        assert not_found is None

    def test_group_get_group_by_id(self):
        """测试根据 ID 查找任务组"""
        parent = TaskGroup(id="parent", title="父组")
        child = TaskGroup(id="child", title="子组")

        parent.add_group(child)

        found_group = parent.get_group_by_id("child")
        assert found_group == child

        found_parent = parent.get_group_by_id("parent")
        assert found_parent == parent

    def test_group_serialization(self):
        """测试任务组序列化"""
        group = TaskGroup(
            id="group-1",
            title="测试任务组",
            priority=3,
            max_concurrency=2
        )

        # 添加任务
        task = Task(task_type=TaskType.OCR, input_data={"path": "/test.jpg"})
        group.add_task(task)

        # 转换为字典
        group_dict = group.to_dict()
        assert group_dict["id"] == "group-1"
        assert group_dict["title"] == "测试任务组"
        assert group_dict["priority"] == 3
        assert len(group_dict["children"]) == 1
        assert group_dict["children"][0]["type"] == "task"

        # 从字典恢复
        restored_group = TaskGroup.from_dict(group_dict)
        assert restored_group.id == group.id
        assert restored_group.title == group.title
        assert restored_group.priority == group.priority
        assert len(restored_group.children) == 1

    def test_group_json_serialization(self):
        """测试任务组 JSON 序列化"""
        group = TaskGroup(id="group-1", title="测试")
        task = Task(task_type=TaskType.OCR, input_data={})
        group.add_task(task)

        # 转换为 JSON
        json_str = group.to_json()
        assert isinstance(json_str, str)

        # 从 JSON 恢复
        restored_group = TaskGroup.from_json(json_str)
        assert restored_group.id == group.id
        assert len(restored_group.children) == 1


# =============================================================================
# 测试嵌套结构
# =============================================================================

class TestNestedStructure:
    """测试嵌套结构"""

    def test_three_level_nesting(self):
        """测试三层嵌套结构"""
        # 创建三层嵌套结构
        root = TaskGroup(id="root", title="根组")

        # 第一层子组
        level1_a = TaskGroup(id="level1-a", title="第一层A")
        level1_b = TaskGroup(id="level1-b", title="第一层B")
        root.add_group(level1_a)
        root.add_group(level1_b)

        # 第二层子组（在 level1-a 下）
        level2_a = TaskGroup(id="level2-a", title="第二层A")
        level1_a.add_group(level2_a)

        # 添加任务到不同层级
        task1 = Task(task_type=TaskType.OCR, input_data={})
        task2 = Task(task_type=TaskType.OCR, input_data={})
        task3 = Task(task_type=TaskType.OCR, input_data={})

        root.add_task(task1)
        level1_b.add_task(task2)
        level2_a.add_task(task3)

        # 验证结构
        all_tasks = root.get_all_tasks()
        assert len(all_tasks) == 3

        all_groups = root.get_all_groups(include_self=False)
        assert len(all_groups) == 3  # level1-a, level1-b, level2-a

        # 验证进度聚合
        task1.progress = 1.0
        task2.progress = 0.5
        task3.progress = 0.0

        # (1.0 + 0.5 + 0.0) / 3 = 0.5
        assert root.progress == 0.5

    def test_deep_nesting_progress(self):
        """测试深层嵌套的进度聚合"""
        root = TaskGroup(id="root", title="根组")

        # 创建深层嵌套
        current = root
        for i in range(10):
            child = TaskGroup(id=f"level-{i}", title=f"第{i}层")
            current.add_group(child)
            current = child

        # 在最底层添加任务
        task = Task(task_type=TaskType.OCR, input_data={})
        current.add_task(task)

        # 更新任务进度
        task.progress = 0.8

        # 验证进度聚合到根组
        assert root.progress == 0.8

    def test_nested_serialization(self):
        """测试嵌套结构序列化"""
        root = TaskGroup(id="root", title="根组")

        # 创建嵌套结构
        level1 = TaskGroup(id="level1", title="第一层")
        root.add_group(level1)

        task = Task(task_type=TaskType.OCR, input_data={})
        level1.add_task(task)

        # 序列化
        json_str = root.to_json()

        # 反序列化
        restored_root = TaskGroup.from_json(json_str)

        # 验证结构
        assert restored_root.id == root.id
        assert len(restored_root.children) == 1
        assert len(restored_root.get_all_tasks()) == 1


# =============================================================================
# 测试便捷函数
# =============================================================================

class TestUtilityFunctions:
    """测试便捷函数"""

    def test_create_simple_task(self):
        """测试创建简单任务"""
        task = create_simple_task(
            task_type=TaskType.OCR,
            input_data={"path": "/test.jpg"},
            max_retries=5
        )

        assert task.task_type == TaskType.OCR
        assert task.input_data == {"path": "/test.jpg"}
        assert task.max_retries == 5

    def test_create_simple_task_group(self):
        """测试创建简单任务组"""
        tasks = [
            Task(task_type=TaskType.OCR, input_data={"path": f"/test{i}.jpg"})
            for i in range(3)
        ]

        group = create_simple_task_group(
            title="批量OCR",
            tasks=tasks,
            priority=10,
            max_concurrency=2
        )

        assert group.title == "批量OCR"
        assert group.priority == 10
        assert group.max_concurrency == 2
        assert group.total_tasks == 3


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
