#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR Windows Runtime Environment Initialization Entry Point
"""

import os
import sys
import json
import site
import subprocess
from pathlib import Path

# Configuration paths
PROJECT_ROOT = Path(__file__).parent
SOURCE_DIR = PROJECT_ROOT / "src"
RESOURCES_DIR = PROJECT_ROOT / "resources"
DATA_DIR = PROJECT_ROOT / "UmiOCR-data"

# Configuration file paths (kept in UmiOCR-data for now)
ABOUT_FILE = DATA_DIR / "about.json"
SETTINGS_FILE = DATA_DIR / ".settings"
THEMES_FILE = DATA_DIR / "themes.json"


def MessageBox(msg, type_="error"):
    """Display message box for errors (Windows only)"""
    info = "Umi-OCR Message"
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
    """Initialize runtime environment"""
    # Set working directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Add Python search paths
    paths_to_add = [".", "src", "src/imports", "site-packages"]
    for n in paths_to_add:
        path = os.path.abspath(os.path.join(script_dir, n))
        if os.path.exists(path):
            site.addsitedir(path)

    # Set QML import paths
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

    # Log setup - moved to src/run.py to avoid duplicate handler installation
    pass

    # OpenGL sharing (Qt6 handles this automatically)
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication

    try:
        # Qt6 handles OpenGL context sharing automatically
        # High DPI scaling is also handled automatically in Qt6
        pass
    except Exception:
        pass


def main():
    """Main entry point"""
    try:
        # Initialize runtime environment
        initRuntimeEnvironment()

        # Get PYSTAND environment variable, or use current script path
        app_path = os.environ.get("PYSTAND", "")
        if not app_path:
            # Use the current script path when not running from PyStand
            app_path = os.path.abspath(__file__)

        # Import and start main program
        from src.run import main

        main(app_path=app_path, engineAddImportPath="")

    except Exception as e:
        # Try to import logger for error reporting
        try:
            from src.imports.umi_log import logger
        except Exception:
            logger = None

        if logger:
            logger.critical(
                f"Failed to startup main program!", exc_info=True, stack_info=True
            )
        msg = f"Failed to startup main program!\n{e}"
        MessageBox(msg)

        sys.exit(1)


if __name__ == "__main__":
    main()
