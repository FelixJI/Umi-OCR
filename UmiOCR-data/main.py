#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix main.py entry point for new directory structure
"""

import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "UmiOCR-data"
ABOUT_FILE = DATA_DIR / "about.json"
SOURCE_DIR = PROJECT_ROOT / "src"
RESOURCES_DIR = PROJECT_ROOT / "resources"


def main():
    # Initialize runtime environment
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Set up paths
    for n in [".", "src", "site-packages"]:
        path = os.path.abspath(os.path.join(script_dir, n))
        if os.path.exists(path):
            os.addsitedir(path)

    # Set QML import paths
    try:
        import PySide6

        pyside_path = os.path.dirname(PySide6.__file__)
        qml_path = os.path.join(pyside_path, "qml")
        resources_path = str(RESOURCES_DIR.absolute())
        os.environ["QML2_IMPORT_PATH"] = (
            resources_path + os.pathsep + os.path.abspath("resources/qml")
        )
    except Exception:
        pass

    # Log setup
    try:
        from src.imports.umi_log import get_qt_message_handler, logger

        qInstallMessageHandler(get_qt_message_handler())
    except Exception:
        pass

    # OpenGL sharing
    from PySide6.QtCore import Qt

    try:
        QGuiApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
        QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    except Exception:
        pass

    # Import and start main program
    try:
        from src.run import main

        main(app_path="", engineAddImportPath=None)
    except Exception as e:
        logger.critical(
            f"Failed to startup main program!", exc_info=True, stack_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
