#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语法检查脚本
检查项目所有Python文件的语法错误（排除paddle_doc目录）

使用说明:
    python check_syntax.py

功能:
    1. 检查所有Python文件（排除paddle_doc目录）
    2. 使用ruff进行语法检查
    3. 输出详细的错误信息
    4. 支持自定义排除目录

Author: Umi-OCR Team
Date: 2026-01-28
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

# =============================================================================
# 配置区域
# =============================================================================

# 排除的目录（不检查这些目录下的文件）
EXCLUDE_DIRS = [
    "paddle_doc",      # Paddle文档目录
    "__pycache__",     # Python缓存目录
    ".git",            # Git版本控制目录
    ".mypy_cache",     # MyPy类型检查缓存
    ".pytest_cache",    # PyTest测试缓存
    ".venv",           # 虚拟环境目录
    "venv",            # 虚拟环境目录（另一种命名）
    "build",           # 构建目录
    "dist",            # 分发目录
    "*.egg-info",      # 包信息目录
]

# 排除的文件模式
EXCLUDE_PATTERNS = [
    "test_",           # 测试文件
    "_test.py",        # 测试文件（另一种命名）
]


# =============================================================================
# 工具函数
# =============================================================================

def find_python_files(root_dir: Path) -> List[Path]:
    """
    查找所有需要检查的Python文件

    Args:
        root_dir: 项目根目录

    Returns:
        Python文件路径列表
    """
    python_files = []

    for root, dirs, files in os.walk(root_dir):
        root_path = Path(root)

        # 过滤排除的目录
        dirs[:] = [
            d for d in dirs
            if not any(
                (root_path / d).match(pattern) or d == pattern
                for pattern in EXCLUDE_DIRS
            )
        ]

        for file in files:
            if file.endswith(".py"):
                file_path = root_path / file
                # 过滤排除的文件
                if not any(
                    pattern in file
                    for pattern in EXCLUDE_PATTERNS
                ):
                    python_files.append(file_path)

    return python_files


def check_syntax_with_ruff(files: List[Path]) -> Tuple[bool, str]:
    """
    使用ruff检查语法

    Args:
        files: Python文件路径列表

    Returns:
        (是否通过, 错误输出)
    """
    print(f"使用ruff检查 {len(files)} 个文件的语法...")

    # 转换为相对路径
    root_dir = Path.cwd()
    file_paths = [str(f.relative_to(root_dir)) for f in files]

    # 运行ruff检查
    # E: pycodestyle错误
    # F: PyFlakes错误
    result = subprocess.run(
        ["ruff", "check", "--select=E,F", "--output-format=concise", *file_paths],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )

    if result.returncode == 0:
        print("[OK] 所有文件语法检查通过")
        return True, ""

    # 解析ruff输出
    print("\n发现语法错误：")
    # 安全地打印输出，避免特殊字符问题
    for line in result.stdout.split('\n'):
        if line.strip():
            try:
                print(line)
            except UnicodeEncodeError:
                print(line.encode('ascii', 'ignore').decode('ascii'))

    return False, result.stdout


# =============================================================================
# 主函数
# =============================================================================

def main():
    """主函数"""
    root_dir = Path.cwd()
    print("=" * 70)
    print("语法检查工具")
    print("=" * 70)
    print(f"项目根目录: {root_dir}")
    print(f"排除目录: {EXCLUDE_DIRS}")
    print()

    # 查找所有Python文件
    python_files = find_python_files(root_dir)
    print(f"找到 {len(python_files)} 个Python文件\n")

    if not python_files:
        print("未找到需要检查的Python文件")
        return 0

    # 执行语法检查
    success, output = check_syntax_with_ruff(python_files)

    if success:
        print("\n" + "=" * 70)
        print("[OK] 语法检查完成，所有文件通过")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print("[FAIL] 语法检查失败，请修复上述错误")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
