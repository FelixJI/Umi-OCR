#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR OCR设置面板

Author: Umi-OCR Team
Date: 2026-01-27
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QGroupBox,
)
from PySide6.QtCore import Qt

from src.models.config_model import OcrEngineType
from src.controllers.settings_controller import SettingsController


class OcrSettingsPanel(QWidget):
    """OCR 设置面板"""

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller or SettingsController()
        self._init_ui()

    def _init_ui(self):
        # 创建主布局并设置为自身的布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 如果有父widget，将自身添加到父widget的布局中
        if self.parent():
            parent_layout = self.parent().layout()
            if parent_layout:
                # 找到label的位置（通常是第一个元素），在它后面插入
                # 或者简单地在末尾添加
                parent_layout.insertWidget(1, self)

        # === 引擎选择 ===
        group_engine = QGroupBox("OCR 引擎")
        layout_engine = QVBoxLayout(group_engine)

        hbox_engine = QHBoxLayout()
        hbox_engine.addWidget(QLabel("默认引擎:"))
        self.combo_engine = QComboBox()
        # 添加枚举项
        for engine in OcrEngineType:
            self.combo_engine.addItem(engine.value, engine.value)

        # 设置当前值
        current_engine = self.controller.get_config(
            "ocr.engine_type", OcrEngineType.PADDLE.value
        )
        index = self.combo_engine.findData(current_engine)
        if index >= 0:
            self.combo_engine.setCurrentIndex(index)

        self.combo_engine.currentIndexChanged.connect(self._on_engine_changed)
        hbox_engine.addWidget(self.combo_engine)
        hbox_engine.addStretch()

        layout_engine.addLayout(hbox_engine)
        layout.addWidget(group_engine)

        # === PaddleOCR 设置 ===
        # 这里只做简单的展示，实际可以根据引擎选择动态显示
        group_paddle = QGroupBox("PaddleOCR (本地)")
        layout_paddle = QVBoxLayout(group_paddle)

        # 语言
        hbox_lang = QHBoxLayout()
        hbox_lang.addWidget(QLabel("语言:"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["ch", "en", "japan", "korean"])  # 示例语言
        self.combo_lang.setCurrentText(
            self.controller.get_config("ocr.paddle.lang", "ch")
        )
        self.combo_lang.currentTextChanged.connect(
            lambda v: self.controller.set_config("ocr.paddle.lang", v)
        )
        hbox_lang.addWidget(self.combo_lang)
        hbox_lang.addStretch()
        layout_paddle.addLayout(hbox_lang)

        # 性能
        self.cb_gpu = QCheckBox("使用 GPU 加速")
        self.cb_gpu.setChecked(self.controller.get_config("ocr.paddle.use_gpu", False))
        self.cb_gpu.toggled.connect(
            lambda v: self.controller.set_config("ocr.paddle.use_gpu", v)
        )
        layout_paddle.addWidget(self.cb_gpu)

        self.cb_mkldnn = QCheckBox("使用 MKL-DNN 加速 (CPU)")
        self.cb_mkldnn.setChecked(
            self.controller.get_config("ocr.paddle.enable_mkldnn", True)
        )
        self.cb_mkldnn.toggled.connect(
            lambda v: self.controller.set_config("ocr.paddle.enable_mkldnn", v)
        )
        layout_paddle.addWidget(self.cb_mkldnn)

        layout.addWidget(group_paddle)

        # === 图像预处理 ===
        group_pre = QGroupBox("图像预处理")
        layout_pre = QVBoxLayout(group_pre)

        # 降噪
        self.cb_denoise = QCheckBox("启用降噪")
        self.cb_denoise.setChecked(
            self.controller.get_config("ocr.preprocessing.enable_denoise", False)
        )
        self.cb_denoise.toggled.connect(
            lambda v: self.controller.set_config("ocr.preprocessing.enable_denoise", v)
        )
        layout_pre.addWidget(self.cb_denoise)

        # 二值化
        self.cb_binarize = QCheckBox("启用二值化")
        self.cb_binarize.setChecked(
            self.controller.get_config("ocr.preprocessing.enable_binarization", False)
        )
        self.cb_binarize.toggled.connect(
            lambda v: self.controller.set_config(
                "ocr.preprocessing.enable_binarization", v
            )
        )
        layout_pre.addWidget(self.cb_binarize)

        # 纠偏
        self.cb_deskew = QCheckBox("启用纠偏")
        self.cb_deskew.setChecked(
            self.controller.get_config("ocr.preprocessing.enable_deskew", False)
        )
        self.cb_deskew.toggled.connect(
            lambda v: self.controller.set_config("ocr.preprocessing.enable_deskew", v)
        )
        layout_pre.addWidget(self.cb_deskew)

        layout.addWidget(group_pre)

        # === 识别参数 ===
        group_param = QGroupBox("识别参数")
        layout_param = QVBoxLayout(group_param)

        # 合并相邻行
        self.cb_merge = QCheckBox("合并相邻行")
        self.cb_merge.setChecked(self.controller.get_config("ocr.merge_lines", True))
        self.cb_merge.toggled.connect(
            lambda v: self.controller.set_config("ocr.merge_lines", v)
        )
        layout_param.addWidget(self.cb_merge)

        layout.addWidget(group_param)

    def _on_engine_changed(self, index):
        engine = self.combo_engine.itemData(index)
        self.controller.set_config("ocr.engine_type", engine)
