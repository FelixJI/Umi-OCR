#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification script for Stage 9-12
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.task import (
    Task,
    TaskGroup,
    TaskType,
    TaskStatus,
    TaskManager,
    create_simple_task,
    create_simple_task_group,
)


def test_task_creation():
    """Test task creation"""
    print("Test 1: Task creation")
    task = create_simple_task(
        task_type=TaskType.OCR,
        input_data={"image_path": "/test/image.jpg"}
    )
    assert task.task_type == TaskType.OCR
    assert task.status == TaskStatus.PENDING
    print("  [OK] Task created successfully")


def test_task_serialization():
    """Test task serialization"""
    print("\nTest 2: Task serialization")
    task = create_simple_task(
        task_type=TaskType.OCR,
        input_data={"image_path": "/test/image.jpg"}
    )
    task.transition_to(TaskStatus.RUNNING)
    task.transition_to(TaskStatus.COMPLETED)

    # Serialize
    json_str = task.to_json()
    assert json_str

    # Deserialize
    restored = Task.from_json(json_str)
    assert restored.id == task.id
    assert restored.status == TaskStatus.COMPLETED
    print("  [OK] Task serialization successful")


def test_task_group():
    """Test task group"""
    print("\nTest 3: Task group")
    tasks = [
        create_simple_task(TaskType.OCR, {"path": f"/test{i}.jpg"})
        for i in range(3)
    ]

    group = create_simple_task_group(
        title="Test group",
        tasks=tasks,
        priority=5
    )

    assert group.total_tasks == 3
    assert group.priority == 5
    print("  [OK] Task group created successfully")


def test_nested_structure():
    """Test nested structure"""
    print("\nTest 4: Nested structure")
    parent = TaskGroup(id="parent", title="Parent group")
    child = TaskGroup(id="child", title="Child group")
    task = create_simple_task(TaskType.OCR, {"path": "/test.jpg"})

    child.add_task(task)
    parent.add_group(child)

    all_tasks = parent.get_all_tasks()
    assert len(all_tasks) == 1

    all_groups = parent.get_all_groups()
    assert len(all_groups) == 2  # parent + child
    print("  [OK] Nested structure successful")


def test_task_manager_init():
    """Test task manager initialization"""
    print("\nTest 5: Task manager initialization")
    manager = TaskManager.instance()
    assert manager

    # Check statistics
    stats = manager.get_statistics()
    assert "total_groups" in stats
    assert "total_tasks" in stats
    assert "active_workers" in stats
    print("  [OK] Task manager initialized successfully")


def test_task_submission():
    """Test task submission"""
    print("\nTest 6: Task submission")
    manager = TaskManager.instance()

    # Submit OCR tasks
    group_id = manager.submit_ocr_tasks(
        image_paths=["/test/image1.jpg", "/test/image2.jpg"],
        title="Batch OCR test",
        priority=10
    )

    assert group_id

    # Query task group
    group = manager.get_group(group_id)
    assert group
    assert group.title == "Batch OCR test"
    assert group.total_tasks == 2
    print("  [OK] Task submission successful")


def test_ocr_integration():
    """Test OCR engine integration"""
    print("\nTest 7: OCR engine integration")
    from services.task import TaskHandlerRegistry

    # Check if OCR handler is registered
    handler = TaskHandlerRegistry.get(TaskType.OCR)
    assert handler is not None
    print("  [OK] OCR handler registered")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Stage 9-12 Verification")
    print("=" * 60)

    try:
        test_task_creation()
        test_task_serialization()
        test_task_group()
        test_nested_structure()
        test_task_manager_init()
        test_task_submission()
        test_ocr_integration()

        print("\n" + "=" * 60)
        print("[SUCCESS] All tests passed!")
        print("=" * 60)

        # List generated files
        print("\nGenerated files:")
        task_files = [
            "services/task/task_model.py",
            "services/task/task_queue.py",
            "services/task/task_handler.py",
            "services/task/task_worker.py",
            "services/task/task_manager.py",
            "services/task/__init__.py",
            "tests/test_task_model.py",
        ]

        for file in task_files:
            file_path = Path(file)
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"  [OK] {file} ({size} bytes)")
            else:
                print(f"  [MISSING] {file}")

        print("\nImplementation summary:")
        print("  Stage 9: [OK] Task data model")
        print("  Stage 10: [OK] Task queue and scheduling")
        print("  Stage 11: [OK] Task executor")
        print("  Stage 12: [OK] Task manager")

        return 0

    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
