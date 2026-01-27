#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR Windows 运行时环境初始化入口
"""

import os
import sys
import json
import argparse
import site
import subprocess
from pathlib import Path

# 配置路径
PROJECT_ROOT = Path(__file__).parent
SOURCE_DIR = PROJECT_ROOT / "src"
RESOURCES_DIR = PROJECT_ROOT / "resources"
DATA_DIR = PROJECT_ROOT / "UmiOCR-data"

# 配置文件路径（目前保留在 UmiOCR-data 中）
ABOUT_FILE = DATA_DIR / "about.json"
SETTINGS_FILE = DATA_DIR / ".settings"
THEMES_FILE = DATA_DIR / "themes.json"


def MessageBox(msg, type_="error"):
    """显示错误消息框（仅限 Windows）"""
    info = "Umi-OCR 消息"
    if type_ == "error":
        info = "【错误】 Umi-OCR Error"
    elif type_ == "warning":
        info = "【警告】 Umi-OCR Warning"
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, str(msg), str(info), 0)
    except Exception:
        msg_cmd = (
            msg.replace("^", "^^")
            .replace("&", "^&")
            .replace("<", "^<")
            .replace(">", "^>")
            .replace("|", "^|")
            .replace("\n\n", "___")
            .replace("\n", "___")
        )
        subprocess.Popen(["start", "cmd", "/k", f"echo {info}: {msg_cmd}"], shell=True)
    return 0


def initRuntimeEnvironment():
    """初始化运行时环境"""
    # 设置工作目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 添加 Python 搜索路径
    paths_to_add = [".", "src", "src/imports", "site-packages"]
    for n in paths_to_add:
        path = os.path.abspath(os.path.join(script_dir, n))
        if os.path.exists(path):
            site.addsitedir(path)

    # 设置 QML 导入路径
    try:
        import PySide6

        pyside_path = os.path.dirname(PySide6.__file__)
        qml_path = os.path.join(pyside_path, "qml")
        resources_qml = str(RESOURCES_DIR)  # QML文件直接在 resources/ 目录下
        os.environ["QML2_IMPORT_PATH"] = (
            qml_path + os.pathsep + os.path.abspath(resources_qml)
        )
    except Exception:
        pass

    # 日志设置 - 已移至 src/run.py 以避免重复安装处理器
    pass

    # OpenGL 共享（Qt6 自动处理）
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication

    try:
        # Qt6 自动处理 OpenGL 上下文共享
        # Qt6 自动处理高 DPI 缩放
        pass
    except Exception:
        pass


def parse_args():
    parser = argparse.ArgumentParser(description="Umi-OCR: 开源 OCR 软件")
    parser.add_argument("--headless", action="store_true", help="以无界面模式运行")
    parser.add_argument("--server", action="store_true", help="启动 HTTP 服务器")
    parser.add_argument("--image", nargs="+", help="要执行 OCR 的图像路径")
    parser.add_argument("--output", help="输出文件路径（默认：标准输出）")
    parser.add_argument("--format", choices=["txt", "json"], default="txt", help="输出格式")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    return parser.parse_args()


def main():
    try:
        initRuntimeEnvironment()
        args = parse_args()
        is_gui = not args.headless
        if not is_gui:
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from src.app import UmiApplication, set_app_instance
        app = UmiApplication(sys.argv)
        set_app_instance(app)
        if args.image or args.server:
            from src.cli_handler import CliHandler
            handler = CliHandler(args)
            exit_code = handler.run()
            sys.exit(exit_code)
        else:
            from src.ui.main_window.main_window import MainWindow
            main_window = MainWindow()
            main_window.show()
            app.logger.info("应用程序初始化完成，进入事件循环")
            exit_code = app.exec()
            app.logger.info("应用程序退出，保存配置")
            app.config_manager.save()
            sys.exit(exit_code)
    except Exception as e:
        try:
            from src.utils.logger import logger
        except Exception:
            logger = None
        if logger:
            logger.critical("主程序启动失败！", exc_info=True, stack_info=True)
        MessageBox(f"主程序启动失败！\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
