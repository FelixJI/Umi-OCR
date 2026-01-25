#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 主程序入口

这是新架构的主程序入口文件，负责：
1. 初始化 QApplication
2. 加载配置
3. 启动主窗口
4. 处理命令行参数（如 CLI 模式）

Author: Umi-OCR Team
Date: 2025-01-25
"""

import sys
import os
from pathlib import Path

# 将项目根目录添加到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.app import UmiApplication


def parse_command_line_args():
    """
    解析命令行参数

    Returns:
        dict: 命令行参数字典
    """
    args = {
        "cli_mode": False,
        "cli_input": None,
        "cli_output": None,
        "cli_format": "txt",
        "debug": False,
    }

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg in ["--cli", "-c"]:
                args["cli_mode"] = True
            elif arg in ["--debug", "-d"]:
                args["debug"] = True
            elif arg.startswith("--input="):
                args["cli_input"] = arg.split("=", 1)[1]
            elif arg.startswith("--output="):
                args["cli_output"] = arg.split("=", 1)[1]
            elif arg.startswith("--format="):
                args["cli_format"] = arg.split("=", 1)[1]

    return args


def main():
    """
    主函数

    创建 QApplication 实例并启动应用程序
    """
    # 解析命令行参数
    args = parse_command_line_args()

    # 创建 QApplication 实例
    app = UmiApplication(sys.argv)

    # 如果是 CLI 模式，处理命令行任务
    if args["cli_mode"]:
        from src.services.server.cli_handler import CliHandler

        cli_handler = CliHandler()
        sys.exit(cli_handler.handle(
            input_path=args["cli_input"],
            output_path=args["cli_output"],
            output_format=args["cli_format"]
        ))

    # 否则启动 GUI
    # TODO: 在后续阶段中创建主窗口
    # from src.ui.main_window.main_window import MainWindow
    # main_window = MainWindow()
    # main_window.show()

    # 暂时显示一个空白窗口用于测试
    from PySide6.QtWidgets import QWidget
    test_window = QWidget()
    test_window.setWindowTitle("Umi-OCR - 重构中")
    test_window.resize(800, 600)
    test_window.show()

    # 进入事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
