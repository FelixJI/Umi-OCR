#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 二维码界面

Author: Umi-OCR Team
Date: 2026-01-27
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLabel,
    QComboBox,
    QPushButton,
    QFileDialog,
)
from PySide6.QtCore import Qt

from src.utils.logger import get_logger

logger = get_logger()


class QRCodeView(QWidget):
    """
    二维码界面
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化控制器（容错：缺失可选依赖时不阻塞主界面）
        try:
            from controllers.qrcode_controller import QrcodeController

            self._controller = QrcodeController()
        except ModuleNotFoundError as e:
            logger.warning(f"二维码控制器加载失败，部分功能不可用: {e}")
            self._controller = None

        # 创建UI
        self._setup_ui()

        # 连接信号
        self._connect_signals()

        logger.info("二维码界面初始化完成")

    def _setup_ui(self):
        """创建界面"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # 标题
        title_label = QLabel("二维码")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title_label)

        # 扫码部分
        scan_label = QLabel("扫码")
        scan_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        main_layout.addWidget(scan_label)

        # 扫码按钮
        scan_btn_layout = QHBoxLayout()

        btn_load_image = QPushButton("加载图片")
        btn_load_image.clicked.connect(self._on_load_image)
        scan_btn_layout.addWidget(btn_load_image)

        scan_btn_layout.addStretch()

        main_layout.addLayout(scan_btn_layout)

        # 扫码结果显示区
        scan_result_label = QLabel("扫码结果")
        scan_result_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        main_layout.addWidget(scan_result_label)

        self.scan_result_browser = QTextEdit()
        self.scan_result_browser.setReadOnly(True)
        self.scan_result_browser.setHtml("""
            <div class="empty">
                等待加载图片...
            </div>
        """)
        main_layout.addWidget(self.scan_result_browser)

        # 分隔线
        separator = QLabel("-" * 50)
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separator.setStyleSheet("color: #ccc;")
        main_layout.addWidget(separator)

        # 生成部分
        generate_label = QLabel("生成码")
        generate_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        main_layout.addWidget(generate_label)

        # 码型选择
        type_layout = QHBoxLayout()

        type_label = QLabel("码型:")
        type_layout.addWidget(type_label)

        self.combo_type = QComboBox()
        self.combo_type.addItems(
            [
                "QR Code",
                "CODE 128",
                "CODE 39",
                "EAN 13",
                "EAN 8",
                "UPC A",
                "UPC E",
                "Data Matrix",
                "PDF 417",
                "Aztec",
            ]
        )
        self.combo_type.setCurrentIndex(0)
        self.combo_type.currentTextChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.combo_type)

        type_layout.addStretch()

        main_layout.addLayout(type_layout)

        # 纠错级别选择
        correction_layout = QHBoxLayout()

        correction_label = QLabel("纠错级别:")
        correction_layout.addWidget(correction_label)

        self.combo_correction = QComboBox()
        self.combo_correction.addItems(["L (7%)", "M (15%)", "Q (25%)", "H (30%)"])
        self.combo_correction.setCurrentIndex(1)
        self.combo_correction.currentTextChanged.connect(self._on_correction_changed)
        correction_layout.addWidget(self.combo_correction)

        correction_layout.addStretch()

        main_layout.addLayout(correction_layout)

        # 输入框
        input_label = QLabel("输入内容:")
        main_layout.addWidget(input_label)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("请输入要生成码的内容...")
        main_layout.addWidget(self.text_input)

        # 生成按钮
        generate_btn_layout = QHBoxLayout()

        btn_generate = QPushButton("生成")
        btn_generate.clicked.connect(self._on_generate)
        generate_btn_layout.addWidget(btn_generate)

        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(self._on_clear)
        generate_btn_layout.addWidget(btn_clear)

        generate_btn_layout.addStretch()

        main_layout.addLayout(generate_btn_layout)

        main_layout.addStretch()

        self.setLayout(main_layout)

    def _connect_signals(self):
        """连接控制器信号"""
        if self._controller:
            self._controller.scan_started.connect(self._on_scan_started)
            self._controller.scan_completed.connect(self._on_scan_completed)
            self._controller.scan_failed.connect(self._on_scan_failed)
            self._controller.generate_started.connect(self._on_generate_started)
            self._controller.generate_completed.connect(self._on_generate_completed)
            self._controller.generate_failed.connect(self._on_generate_failed)

    def _on_load_image(self):
        """加载图片"""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*.*)",
        )

        if file_path:
            logger.info(f"加载图片: {file_path}")
            # 通过控制器扫码
            if self._controller:
                self._controller.scan_qr_code(file_path)

    def _on_generate(self):
        """生成二维码"""
        data = self.text_input.toPlainText()
        if not data:
            logger.warning("请输入内容")
            return

        # 获取选项
        code_type = self._get_code_type()
        correction = self._get_correction_level()

        # 通过控制器生成
        if self._controller:
            self._controller.generate_qr_code(
                data, code_type=code_type, correction=correction
            )

    def _on_clear(self):
        """清空输入"""
        self.text_input.clear()

    def _on_type_changed(self, type_text: str):
        """码型切换"""
        logger.info(f"切换码型: {type_text}")

    def _on_correction_changed(self, correction_text: str):
        """纠错级别切换"""
        logger.info(f"切换纠错级别: {correction_text}")

    def _get_code_type(self) -> str:
        """获取码型"""
        code_type_map = {
            "QR Code": "QR_CODE",
            "CODE 128": "CODE_128",
            "CODE 39": "CODE_39",
            "EAN 13": "EAN_13",
            "EAN 8": "EAN_8",
            "UPC A": "UPCE_A",
            "UPC E": "UPCE_E",
            "Data Matrix": "DATA_MATRIX",
            "PDF 417": "PDF_417",
            "Aztec": "AZTEC",
        }
        return code_type_map.get(self.combo_type.currentText(), "QR_CODE")

    def _get_correction_level(self) -> str:
        """获取纠错级别"""
        correction_map = {"L (7%)": "L", "M (15%)": "M", "Q (25%)": "Q", "H (30%)": "H"}
        return correction_map.get(self.combo_correction.currentText(), "M")

    def _on_scan_started(self):
        """扫码开始"""
        self.scan_result_browser.setHtml("""
        <div class="empty">
            正在扫码...
        </div>
        """)

    def _on_scan_completed(self, results):
        """扫码完成"""
        html = "<div class='results'>"
        for result in results:
            html += "<div class='result-item'>"
            html += f"<div><strong>类型:</strong> {result['type']}</div>"
            html += f"<div><strong>数据:</strong> {result['data']}</div>"
            html += "</div>"
        html += "</div>"

        self.scan_result_browser.setHtml(html)

    def _on_scan_failed(self, error):
        """扫码失败"""
        self.scan_result_browser.setHtml(f"""
        <div class="error">
            扫码失败: {error}
        </div>
        """)

    def _on_generate_started(self):
        """生成开始"""
        self.text_input.setEnabled(False)

    def _on_generate_completed(self, output_path: str):
        """生成完成"""
        self.text_input.setEnabled(True)
        logger.info(f"二维码生成完成: {output_path}")

    def _on_generate_failed(self, error):
        """生成失败"""
        self.text_input.setEnabled(True)
        logger.error(f"二维码生成失败: {error}")
