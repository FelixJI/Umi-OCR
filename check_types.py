#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
类型注解检查脚本
检查项目所有Python文件的类型注解（排除paddle_doc目录）

使用说明:
    python check_types.py

功能:
    1. 检查所有Python文件（排除paddle_doc目录）
    2. 使用mypy进行类型检查
    3. 分析缺失的类型注解
    4. 生成详细的检查报告

注意事项:
    - mypy需要对模块有正确的导入路径
    - 某些第三方库的类型提示可能不完整
    - 建议在虚拟环境中运行

Author: Umi-OCR Team
Date: 2026-01-28
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

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


def check_type_annotations_with_mypy(files: List[Path]) -> Tuple[bool, Dict[str, Any]]:
    """
    使用mypy检查类型注解

    Args:
        files: Python文件路径列表

    Returns:
        (是否通过, 检查结果字典)
    """
    print(f"使用mypy检查 {len(files)} 个文件的类型注解...")

    # 创建mypy配置
    mypy_args = [
        "mypy",
        "--show-error-codes",
        "--no-error-summary",
        "--output=json",
        "--ignore-missing-imports",  # 忽略缺失的导入（第三方库）
        "--allow-untyped-defs",     # 允许未注解的函数定义，只报warning
        "--warn-return-any",         # 警告返回Any类型
        "--warn-unused-ignores",     # 警告未使用的ignore
        "--package", "src",  # 指定包路径，避免模块重复识别
    ]

    # 运行mypy检查
    result = subprocess.run(
        mypy_args,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )

    # 解析mypy输出
    errors = []
    warnings = []

    if result.stdout:
        try:
            mypy_output = json.loads(result.stdout)
            for item in mypy_output:
                error_info = {
                    "file": item.get("file", ""),
                    "line": item.get("line", 0),
                    "column": item.get("column", 0),
                    "severity": item.get("severity", "error"),
                    "message": item.get("message", ""),
                    "code": item.get("code", ""),
                }

                if error_info["severity"] == "error":
                    errors.append(error_info)
                else:
                    warnings.append(error_info)
        except json.JSONDecodeError:
            # 如果JSON解析失败，可能是其他输出
            print(f"无法解析mypy输出: {result.stdout}")

    # 输出结果
    if errors:
        print(f"\n发现 {len(errors)} 个类型错误：")
        for i, err in enumerate(errors, 1):
            print(f"{i}. {err['file']}:{err['line']}:{err['column']}")
            print(f"   [{err['code']}] {err['message']}\n")

    if warnings:
        print(f"\n发现 {len(warnings)} 个类型警告：")
        for i, warn in enumerate(warnings, 1):
            print(f"{i}. {warn['file']}:{warn['line']}:{warn['column']}")
            print(f"   [{warn['code']}] {warn['message']}\n")

    result_dict = {
        "errors": errors,
        "warnings": warnings,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

    # 只要有错误就算失败
    success = len(errors) == 0

    if success:
        print(f"[OK] 类型检查通过（{len(warnings)} 个警告）")

    return success, result_dict


def analyze_missing_annotations(files: List[Path]) -> Dict[str, List[str]]:
    """
    分析缺失的类型注解

    这是一个静态分析工具，通过简单的文本匹配来查找：
    1. 没有返回类型注解的函数/方法
    2. 没有类型注解的类变量

    注意：这不是完整的类型检查，只能作为参考。

    Args:
        files: Python文件路径列表

    Returns:
        缺失注解的分类字典
    """
    print("\n分析缺失的类型注解...")
    print("注意：这是静态分析，可能存在误报，仅供参考。\n")

    missing_annotations = {
        "functions": [],
        "methods": [],
        "variables": [],
    }

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单的静态分析，查找未注解的函数和变量
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                # 查找函数定义（没有返回类型注解）
                if stripped.startswith('def ') and '->' not in stripped:
                    # 排除一些特殊情况
                    # 魔术方法通常有固定的签名，不需要强类型注解
                    if '__' not in stripped:
                        # 判断是方法还是函数（通过是否包含self/cls）
                        if 'self' in stripped or 'cls' in stripped:
                            missing_annotations["methods"].append(f"{file_path}:{i}")
                        else:
                            missing_annotations["functions"].append(f"{file_path}:{i}")

                # 查找类级别变量（没有类型注解）
                # 跳过第一行（通常是注释或docstring）
                if i > 1 and '=' in stripped and not stripped.startswith('#'):
                    # 排除一些特殊情况
                    # 控制流语句、装饰器、类定义、函数定义等
                    if not stripped.startswith((
                        'def ', 'class ', '@', 'if ', 'for ', 
                        'while ', 'with ', 'except '
                    )):
                        # 检查是否在类定义内部
                        # 向上查找最近的类定义
                        prev_lines = '\n'.join(lines[max(0, i-50):i])
                        if 'class ' in prev_lines:
                            # 在类内部，但没有类型注解
                            # 赋值语句中，等号左边没有冒号就是缺失类型注解
                            if ':' not in stripped.split('=')[0]:
                                missing_annotations["variables"].append(f"{file_path}:{i}")

        except Exception as e:
            print(f"无法读取文件 {file_path}: {e}")

    # 输出统计
    total = (
        len(missing_annotations["functions"]) + 
        len(missing_annotations["methods"]) + 
        len(missing_annotations["variables"])
    )
    print(f"分析完成，共发现 {total} 处缺失类型注解：")
    print(f"  - 函数: {len(missing_annotations['functions'])} 个")
    print(f"  - 方法: {len(missing_annotations['methods'])} 个")
    print(f"  - 变量: {len(missing_annotations['variables'])} 个")

    return missing_annotations


# =============================================================================
# 主函数
# =============================================================================

def main():
    """主函数"""
    root_dir = Path.cwd()
    print("=" * 70)
    print("类型注解检查工具")
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

    # 执行类型注解检查
    success, type_check_result = check_type_annotations_with_mypy(python_files)

    # 分析缺失的注解
    missing_annotations = analyze_missing_annotations(python_files)

    # 保存结果到文件
    result = {
        "type_check": type_check_result,
        "missing_annotations": missing_annotations,
    }

    result_file = root_dir / "type_check_results.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n检查结果已保存到: {result_file}")
    print("\n" + "=" * 70)
    if success:
        print("[OK] 类型注解检查完成")
    else:
        print("[FAIL] 类型注解检查失败，请修复上述错误")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
