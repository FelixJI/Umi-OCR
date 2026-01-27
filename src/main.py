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
import argparse
from pathlib import Path

# 将项目根目录添加到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.app import UmiApplication


def parse_args():
    """使用 argparse 解析命令行参数"""
    parser = argparse.ArgumentParser(description="Umi-OCR: Open Source OCR Software")
    
    # 模式选择
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no GUI)")
    parser.add_argument("--server", action="store_true", help="Start HTTP server")
    
    # OCR 任务参数
    parser.add_argument("--image", nargs="+", help="Image paths to perform OCR on")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument("--format", choices=["txt", "json"], default="txt", help="Output format")
    
    # 调试
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    return parser.parse_args()


def main():
    """
    主函数
    """
    args = parse_args()
    
    # 决定是否启用 GUI
    # 如果指定了 image 或 server 且 headless，则不显示 GUI
    is_gui = not args.headless
    
    # 创建 Application
    # 即使是 CLI 模式，为了使用 Qt 信号槽机制（EngineManager等依赖），
    # 我们仍然需要一个 QCoreApplication 或 QApplication
    # UmiApplication 继承自 QApplication
    
    # 如果完全不需要 GUI 模块，可以使用 QCoreApplication，但考虑到代码复用，
    # 且 UmiApplication 可能初始化了一些通用配置，直接用它通常没问题，
    # 只要不调用 main_window.show() 即可。
    # 注意：如果是 headless server 环境（无 X11/Display），需要设置 platform 为 offscreen
    if not is_gui:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        
    app = UmiApplication(sys.argv)
    
    # 设置全局应用程序实例
    from src.app import set_app_instance
    set_app_instance(app)
    
    # CLI 逻辑
    if args.image or args.server:
        from src.cli_handler import CliHandler
        handler = CliHandler(args)
        exit_code = handler.run()
        sys.exit(exit_code)
    else:
        # GUI 模式
        from src.ui.main_window.main_window import MainWindow
        
        main_window = MainWindow()
        main_window.show()
        
        app.logger.info("应用程序初始化完成，进入事件循环")
        exit_code = app.exec()
        
        app.logger.info("应用程序退出，保存配置")
        app.config_manager.save()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
