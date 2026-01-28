#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI Compilation Script

This script compiles .ui files to .py files using pyside6-uic.
Run this script after modifying any .ui file in Qt Designer.
"""

import subprocess
from pathlib import Path

# List of UI files to compile
# Format: (source_ui_file, target_py_file)
# Paths are relative to the project root
UI_FILES = [
    ("src/ui/main_window/main_window.ui", "src/ui/main_window/ui_main_window.py"),
    ("src/ui/floating_bar/floating_bar.ui", "src/ui/floating_bar/ui_floating_bar.py"),
]


def compile_ui():
    project_root = Path(__file__).parent.parent
    success_count = 0
    fail_count = 0

    print(f"Project root: {project_root}")
    print("-" * 50)

    for ui_rel, py_rel in UI_FILES:
        ui_path = project_root / ui_rel
        py_path = project_root / py_rel

        if not ui_path.exists():
            print(f"[SKIP] UI file not found: {ui_rel}")
            fail_count += 1
            continue

        print(f"Compiling {ui_rel} -> {py_rel} ...")

        try:
            # Check if pyside6-uic is available
            cmd = ["pyside6-uic", str(ui_path), "-o", str(py_path)]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"[OK] Generated {py_rel}")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to compile {ui_rel}")
            print(e.stderr)
            fail_count += 1
        except FileNotFoundError:
            print(
                "[ERROR] pyside6-uic command not found. Please ensure PySide6 is installed."
            )
            return

    print("-" * 50)
    print(f"Compilation finished. Success: {success_count}, Failed: {fail_count}")


if __name__ == "__main__":
    compile_ui()
