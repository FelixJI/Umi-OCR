#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 截图OCR界面

Author: Umi-OCR Team
Date: 2026-01-27
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from src.utils.logger import get_logger

logger = get_logger()


class ScreenshotOCRView(QWidget):
    """
    截图OCR界面

    显示OCR识别结果。
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化控制器（容错：缺失可选依赖时不阻塞主界面）
        try:
            from controllers.screenshot_controller import ScreenshotController
            self._controller = ScreenshotController()
        except ModuleNotFoundError as e:
            logger.warning(f"截图控制器加载失败，部分功能不可用: {e}")
            self._controller = None

        # 创建UI
        self._setup_ui()

        # 连接信号
        self._connect_signals()

        logger.info("截图OCR界面初始化完成")

    def _setup_ui(self):
        """创建界面"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 标题
        title_label = QLabel("截图 OCR")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 结果显示区
        self.result_browser = QTextEdit()
        self.result_browser.setReadOnly(True)
        self.result_browser.setHtml("""
            <!DOCTYPE html>
            <head>
            <style>
                body { font-family: Arial, sans-serif; padding: 10px; }
                .result { margin: 10px; padding: 10px; border: 1px solid #ddd; background: #f5f5f5; }
                .empty { text-align: center; color: #666; padding: 50px; }
            </style>
            </head>
            <body>
                <div class="empty">
                    等待截图结果...
                    <br>
                    快捷键: F1 开始截图
                    <br>
                    Esc 取消
                </div>
            </body>
            </html>
        """)
        layout.addWidget(self.result_browser)

        # 底部按钮区
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        start_btn = QPushButton("开始截图")
        start_btn.clicked.connect(self._on_start_capture)
        button_layout.addWidget(start_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _connect_signals(self):
        """连接控制器信号"""
        if self._controller:
            self._controller.capture_started.connect(self._on_capture_started)
            self._controller.capture_cancelled.connect(self._on_capture_cancelled)
            self._controller.ocr_result_ready.connect(self._on_ocr_result)
            self._controller.ocr_failed.connect(self._on_ocr_failed)

    def _on_start_capture(self):
        """开始截图"""
        if self._controller:
            self._controller.start_capture()

    def _on_capture_started(self):
        """截图开始"""
        self.result_browser.setHtml("""
            <!DOCTYPE html>
            <head>
            <style>
                body { font-family: Arial, sans-serif; padding: 10px; }
                .empty { text-align: center; color: #666; padding: 50px; }
            </style>
            </head>
            <body>
                <div class="empty">
                    正在截图...<br>
                    请选择识别区域
                </div>
            </body>
            </html>
        """)

    def _on_capture_cancelled(self):
        """截图取消"""
        self.result_browser.setHtml("""
            <!DOCTYPE html>
            <head>
            <style>
                body { font-family: Arial, sans-serif; padding: 10px; }
                .empty { text-align: center; color: #666; padding: 50px; }
            </style>
            </head>
            <body>
                <div class="empty">
                    截图已取消
                </div>
            </body>
            </html>
        """)

    def _on_ocr_result(self, result):
        """OCR结果"""
        logger.info(f"OCR结果: {result}")

        text = result.get("text", "")
        if text:
            html = f"""
                <!DOCTYPE html>
                <head>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 10px; }}
                    .result {{ margin: 10px; padding: 10px; border: 1px solid #ddd; background: #f5f5f5; }}
                    .text {{ line-height: 1.6; }}
                </style>
                </head>
                <body>
                    <div class="result">
                        <h3>识别结果:</h3>
                        <p>{text}</p>
                    </div>
                    <div class="metadata">
                        <p><strong>引擎:</strong> {result.get('engine_name', 'Unknown')}</p>
                        <p><strong>置信度:</strong> {result.get('confidence', 0):.0}</p>
                        <p><strong>耗时:</strong> {result.get('duration_ms', 0)}ms</p>
                    </div>
                </div>
            </body>
            </html>
            """
            self.result_browser.setHtml(html)
        else:
            self.result_browser.setHtml("""
                <!DOCTYPE html>
                <head>
                <style>
                    body { font-family: Arial, sans-serif; padding: 10px; }
                    .empty { text-align: center; color: #666; padding: 50px; }
                </style>
                </head>
                <body>
                    <div class="empty">
                    未识别到文字
                </div>
            </body>
            </html>
            """)

    def _on_ocr_failed(self, error):
        """OCR失败"""
        logger.error(f"OCR失败: {error}")
        self.result_browser.setHtml(f"""
            <!DOCTYPE html>
            <head>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 10px; }}
                    .result {{ margin: 10px; padding: 10px; border: 1px solid #ddd; background: #fffee; }}
                .error {{ color: #ff666; }}
                </style>
                </head>
                <body>
                    <h3>识别失败</h3>
                    <p>{error}</p>
                </div>
                </body>
            </html>
        """)
