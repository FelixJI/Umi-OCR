#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 导出设置面板

Author: Umi-OCR Team
Date: 2026-01-27
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QCheckBox, QSpinBox, QGroupBox)
from PySide6.QtCore import Qt

from src.models.config_model import OutputFormat
from src.controllers.settings_controller import SettingsController


class ExportSettingsPanel(QWidget):
    """导出设置面板"""

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller or SettingsController()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # === 常规导出 ===
        group_general = QGroupBox("常规")
        layout_general = QVBoxLayout(group_general)
        
        # 默认格式
        hbox_fmt = QHBoxLayout()
        hbox_fmt.addWidget(QLabel("默认导出格式:"))
        self.combo_format = QComboBox()
        for fmt in OutputFormat:
            self.combo_format.addItem(fmt.value, fmt.value)
        
        current_fmt = self.controller.get_config("export.default_format", OutputFormat.TXT.value)
        idx = self.combo_format.findData(current_fmt)
        if idx >= 0:
            self.combo_format.setCurrentIndex(idx)
        self.combo_format.currentIndexChanged.connect(self._on_format_changed)
        
        hbox_fmt.addWidget(self.combo_format)
        hbox_fmt.addStretch()
        layout_general.addLayout(hbox_fmt)
        
        # 自动复制
        self.cb_copy = QCheckBox("识别后自动复制到剪贴板")
        self.cb_copy.setChecked(self.controller.get_config("export.auto_copy", True))
        self.cb_copy.toggled.connect(lambda v: self.controller.set_config("export.auto_copy", v))
        layout_general.addWidget(self.cb_copy)
        
        layout.addWidget(group_general)

        # === TXT 设置 ===
        group_txt = QGroupBox("文本 (TXT)")
        layout_txt = QVBoxLayout(group_txt)
        
        self.cb_conf = QCheckBox("包含置信度信息")
        self.cb_conf.setChecked(self.controller.get_config("export.txt_with_confidence", False))
        self.cb_conf.toggled.connect(lambda v: self.controller.set_config("export.txt_with_confidence", v))
        layout_txt.addWidget(self.cb_conf)
        
        layout.addWidget(group_txt)

        # === JSON 设置 ===
        group_json = QGroupBox("JSON")
        layout_json = QVBoxLayout(group_json)
        
        hbox_indent = QHBoxLayout()
        hbox_indent.addWidget(QLabel("缩进空格数:"))
        self.spin_indent = QSpinBox()
        self.spin_indent.setRange(0, 8)
        self.spin_indent.setValue(self.controller.get_config("export.json_indent", 2))
        self.spin_indent.valueChanged.connect(lambda v: self.controller.set_config("export.json_indent", v))
        hbox_indent.addWidget(self.spin_indent)
        hbox_indent.addStretch()
        layout_json.addLayout(hbox_indent)
        
        layout.addWidget(group_json)
        
        # === PDF 设置 ===
        group_pdf = QGroupBox("PDF")
        layout_pdf = QVBoxLayout(group_pdf)
        
        hbox_quality = QHBoxLayout()
        hbox_quality.addWidget(QLabel("图片质量 (1-100):"))
        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(1, 100)
        self.spin_quality.setValue(self.controller.get_config("export.pdf_image_quality", 90))
        self.spin_quality.valueChanged.connect(lambda v: self.controller.set_config("export.pdf_image_quality", v))
        hbox_quality.addWidget(self.spin_quality)
        hbox_quality.addStretch()
        layout_pdf.addLayout(hbox_quality)
        
        layout.addWidget(group_pdf)

    def _on_format_changed(self, index):
        fmt = self.combo_format.itemData(index)
        self.controller.set_config("export.default_format", fmt)
