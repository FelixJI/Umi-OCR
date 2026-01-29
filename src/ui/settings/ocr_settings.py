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
    QDoubleSpinBox,
    QSpinBox,
    QScrollArea,
    QPushButton,
)
from PySide6.QtCore import Qt

from src.models.config_model import OcrEngineType
from src.controllers.settings_controller import SettingsController
from .style import PANEL_STYLESHEET


class OcrSettingsPanel(QWidget):
    """OCR 设置面板"""

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller or SettingsController()
        self._init_ui()

    def _init_ui(self):
        # 设置统一的背景色
        self.setStyleSheet(PANEL_STYLESHEET)

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 创建滚动区域的容器widget
        scroll_content = QWidget()
        scroll_area.setWidget(scroll_content)

        # 创建内容布局
        layout = QVBoxLayout(scroll_content)
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

        self.cb_table = QCheckBox("表格识别 (PP-TableMagic)")
        self.cb_table.setChecked(
            self.controller.get_config("ocr.paddle.use_table", False)
        )
        self.cb_table.toggled.connect(
            lambda v: self.controller.set_config("ocr.paddle.use_table", v)
        )
        layout_paddle.addWidget(self.cb_table)

        self.cb_structure = QCheckBox("版面结构分析")
        self.cb_structure.setChecked(
            self.controller.get_config("ocr.paddle.use_structure", False)
        )
        self.cb_structure.toggled.connect(
            lambda v: self.controller.set_config("ocr.paddle.use_structure", v)
        )
        layout_paddle.addWidget(self.cb_structure)

        layout.addWidget(group_paddle)

        # === 图像预处理 ===
        group_pre = QGroupBox("图像预处理")
        layout_pre = QVBoxLayout(group_pre)

        # 全选按钮
        hbox_select_all_pre = QHBoxLayout()
        self.btn_select_all_pre = QPushButton("全选")
        self.btn_select_all_pre.setCheckable(True)
        self.btn_select_all_pre.clicked.connect(self._on_select_all_preprocessing)
        hbox_select_all_pre.addWidget(self.btn_select_all_pre)
        hbox_select_all_pre.addStretch()
        layout_pre.addLayout(hbox_select_all_pre)

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

        # 对比度增强
        hbox_contrast = QHBoxLayout()
        self.cb_contrast = QCheckBox("启用对比度增强")
        self.cb_contrast.setChecked(
            self.controller.get_config(
                "ocr.preprocessing.enable_contrast_enhance", False
            )
        )
        self.cb_contrast.toggled.connect(
            lambda v: self.controller.set_config(
                "ocr.preprocessing.enable_contrast_enhance", v
            )
        )
        hbox_contrast.addWidget(self.cb_contrast)

        hbox_contrast.addWidget(QLabel("因子:"))
        self.spin_contrast = QDoubleSpinBox()
        self.spin_contrast.setRange(0.1, 10.0)
        self.spin_contrast.setSingleStep(0.1)
        self.spin_contrast.setValue(
            self.controller.get_config("ocr.preprocessing.contrast_factor", 1.5)
        )
        self.spin_contrast.valueChanged.connect(
            lambda v: self.controller.set_config("ocr.preprocessing.contrast_factor", v)
        )
        hbox_contrast.addWidget(self.spin_contrast)
        hbox_contrast.addStretch()
        layout_pre.addLayout(hbox_contrast)

        # 锐度增强
        hbox_sharpness = QHBoxLayout()
        self.cb_sharpness = QCheckBox("启用锐度增强")
        self.cb_sharpness.setChecked(
            self.controller.get_config(
                "ocr.preprocessing.enable_sharpness_enhance", False
            )
        )
        self.cb_sharpness.toggled.connect(
            lambda v: self.controller.set_config(
                "ocr.preprocessing.enable_sharpness_enhance", v
            )
        )
        hbox_sharpness.addWidget(self.cb_sharpness)

        hbox_sharpness.addWidget(QLabel("因子:"))
        self.spin_sharpness = QDoubleSpinBox()
        self.spin_sharpness.setRange(0.1, 10.0)
        self.spin_sharpness.setSingleStep(0.1)
        self.spin_sharpness.setValue(
            self.controller.get_config("ocr.preprocessing.sharpness_factor", 1.5)
        )
        self.spin_sharpness.valueChanged.connect(
            lambda v: self.controller.set_config(
                "ocr.preprocessing.sharpness_factor", v
            )
        )
        hbox_sharpness.addWidget(self.spin_sharpness)
        hbox_sharpness.addStretch()
        layout_pre.addLayout(hbox_sharpness)

        # 亮度调整
        hbox_brightness = QHBoxLayout()
        self.cb_brightness = QCheckBox("启用亮度调整")
        self.cb_brightness.setChecked(
            self.controller.get_config("ocr.preprocessing.enable_brightness", False)
        )
        self.cb_brightness.toggled.connect(
            lambda v: self.controller.set_config(
                "ocr.preprocessing.enable_brightness", v
            )
        )
        hbox_brightness.addWidget(self.cb_brightness)

        hbox_brightness.addWidget(QLabel("因子:"))
        self.spin_brightness = QDoubleSpinBox()
        self.spin_brightness.setRange(0.1, 3.0)
        self.spin_brightness.setSingleStep(0.1)
        self.spin_brightness.setValue(
            self.controller.get_config("preprocessing.brightness", 1.0)
        )
        self.spin_brightness.valueChanged.connect(
            lambda v: self.controller.set_config("preprocessing.brightness", v)
        )
        hbox_brightness.addWidget(self.spin_brightness)
        hbox_brightness.addStretch()
        layout_pre.addLayout(hbox_brightness)

        # 自动旋转
        self.cb_auto_rotate = QCheckBox("自动旋转 (基于EXIF)")
        self.cb_auto_rotate.setChecked(
            self.controller.get_config("preprocessing.auto_rotate", False)
        )
        self.cb_auto_rotate.toggled.connect(
            lambda v: self.controller.set_config("preprocessing.auto_rotate", v)
        )
        layout_pre.addWidget(self.cb_auto_rotate)

        # 灰度转换
        self.cb_grayscale = QCheckBox("转换为灰度图")
        self.cb_grayscale.setChecked(
            self.controller.get_config("preprocessing.grayscale", False)
        )
        self.cb_grayscale.toggled.connect(
            lambda v: self.controller.set_config("preprocessing.grayscale", v)
        )
        layout_pre.addWidget(self.cb_grayscale)

        # 图像尺寸限制
        hbox_size = QHBoxLayout()
        hbox_size.addWidget(QLabel("尺寸限制:"))

        hbox_size.addWidget(QLabel("最小:"))
        self.spin_min_size = QSpinBox()
        self.spin_min_size.setRange(0, 10000)
        self.spin_min_size.setValue(
            self.controller.get_config("preprocessing.min_size", 0)
        )
        self.spin_min_size.setSuffix(" px")
        self.spin_min_size.valueChanged.connect(
            lambda v: self.controller.set_config("preprocessing.min_size", v)
        )
        hbox_size.addWidget(self.spin_min_size)

        hbox_size.addWidget(QLabel("最大:"))
        self.spin_max_size = QSpinBox()
        self.spin_max_size.setRange(0, 10000)
        self.spin_max_size.setValue(
            self.controller.get_config("preprocessing.max_size", 0)
        )
        self.spin_max_size.setSuffix(" px")
        self.spin_max_size.valueChanged.connect(
            lambda v: self.controller.set_config("preprocessing.max_size", v)
        )
        hbox_size.addWidget(self.spin_max_size)

        hbox_size.addWidget(QLabel("缩放:"))
        self.spin_resize_factor = QDoubleSpinBox()
        self.spin_resize_factor.setRange(0.1, 3.0)
        self.spin_resize_factor.setSingleStep(0.1)
        self.spin_resize_factor.setValue(
            self.controller.get_config("preprocessing.scale", 1.0)
        )
        self.spin_resize_factor.valueChanged.connect(
            lambda v: self.controller.set_config("preprocessing.scale", v)
        )
        hbox_size.addWidget(self.spin_resize_factor)

        hbox_size.addStretch()
        layout_pre.addLayout(hbox_size)

        layout.addWidget(group_pre)

        # === PaddleOCR官方预处理 ===
        group_paddle_pre = QGroupBox("PaddleOCR官方预处理")
        layout_paddle_pre = QVBoxLayout(group_paddle_pre)

        # 全选按钮
        hbox_select_all_paddle = QHBoxLayout()
        self.btn_select_all_paddle = QPushButton("全选")
        self.btn_select_all_paddle.setCheckable(True)
        self.btn_select_all_paddle.clicked.connect(self._on_select_all_paddle_preprocessing)
        hbox_select_all_paddle.addWidget(self.btn_select_all_paddle)
        hbox_select_all_paddle.addStretch()
        layout_paddle_pre.addLayout(hbox_select_all_paddle)

        # 文档方向分类
        self.cb_doc_orientation = QCheckBox("文档方向分类")
        self.cb_doc_orientation.setChecked(
            self.controller.get_config(
                "ocr.preprocessing.enable_doc_orientation_classify", False
            )
        )
        self.cb_doc_orientation.toggled.connect(
            lambda v: self.controller.set_config(
                "ocr.preprocessing.enable_doc_orientation_classify", v
            )
        )
        layout_paddle_pre.addWidget(self.cb_doc_orientation)

        # 文档纠平
        self.cb_doc_unwarping = QCheckBox("文档纠平 (UVDoc)")
        self.cb_doc_unwarping.setChecked(
            self.controller.get_config("ocr.preprocessing.enable_doc_unwarping", False)
        )
        self.cb_doc_unwarping.toggled.connect(
            lambda v: self.controller.set_config(
                "ocr.preprocessing.enable_doc_unwarping", v
            )
        )
        layout_paddle_pre.addWidget(self.cb_doc_unwarping)

        # 官方检测resize
        self.cb_det_resize = QCheckBox("使用官方检测Resize")
        self.cb_det_resize.setChecked(
            self.controller.get_config("ocr.preprocessing.enable_det_resize_img", False)
        )
        self.cb_det_resize.toggled.connect(
            lambda v: self.controller.set_config(
                "ocr.preprocessing.enable_det_resize_img", v
            )
        )
        layout_paddle_pre.addWidget(self.cb_det_resize)

        # 官方识别resize
        self.cb_rec_resize = QCheckBox("使用官方识别Resize")
        self.cb_rec_resize.setChecked(
            self.controller.get_config("ocr.preprocessing.enable_rec_resize_img", False)
        )
        self.cb_rec_resize.toggled.connect(
            lambda v: self.controller.set_config(
                "ocr.preprocessing.enable_rec_resize_img", v
            )
        )
        layout_paddle_pre.addWidget(self.cb_rec_resize)

        layout.addWidget(group_paddle_pre)

        # === 高级图像预处理 ===
        group_advanced_pre = QGroupBox("高级图像预处理")
        layout_advanced_pre = QVBoxLayout(group_advanced_pre)

        # CLAHE对比度增强
        hbox_clahe = QHBoxLayout()
        self.cb_clahe = QCheckBox("启用CLAHE对比度增强")
        self.cb_clahe.setChecked(
            self.controller.get_config("preprocessing.enable_clahe", False)
        )
        self.cb_clahe.toggled.connect(
            lambda v: self.controller.set_config("preprocessing.enable_clahe", v)
        )
        hbox_clahe.addWidget(self.cb_clahe)

        hbox_clahe.addWidget(QLabel("裁剪限:"))
        self.spin_clahe_clip = QDoubleSpinBox()
        self.spin_clahe_clip.setRange(0.5, 10.0)
        self.spin_clahe_clip.setSingleStep(0.5)
        self.spin_clahe_clip.setValue(
            self.controller.get_config("preprocessing.clahe_clip_limit", 2.0)
        )
        self.spin_clahe_clip.valueChanged.connect(
            lambda v: self.controller.set_config("preprocessing.clahe_clip_limit", v)
        )
        hbox_clahe.addWidget(self.spin_clahe_clip)

        hbox_clahe.addWidget(QLabel("网格:"))
        self.spin_clahe_tile = QComboBox()
        self.spin_clahe_tile.addItems(["4", "8", "16"])
        self.spin_clahe_tile.setCurrentText(
            str(self.controller.get_config("preprocessing.clahe_tile_size", 8))
        )
        self.spin_clahe_tile.currentTextChanged.connect(
            lambda v: self.controller.set_config(
                "preprocessing.clahe_tile_size", int(v)
            )
        )
        hbox_clahe.addWidget(self.spin_clahe_tile)

        hbox_clahe.addStretch()
        layout_advanced_pre.addLayout(hbox_clahe)

        # 双边滤波
        hbox_bilateral = QHBoxLayout()
        self.cb_bilateral = QCheckBox("启用双边滤波降噪")
        self.cb_bilateral.setChecked(
            self.controller.get_config("preprocessing.enable_bilateral", False)
        )
        self.cb_bilateral.toggled.connect(
            lambda v: self.controller.set_config("preprocessing.enable_bilateral", v)
        )
        hbox_bilateral.addWidget(self.cb_bilateral)

        hbox_bilateral.addWidget(QLabel("直径d:"))
        self.spin_bilateral_d = QSpinBox()
        self.spin_bilateral_d.setRange(5, 25)
        self.spin_bilateral_d.setSingleStep(2)
        self.spin_bilateral_d.setValue(
            self.controller.get_config("preprocessing.bilateral_d", 9)
        )
        self.spin_bilateral_d.valueChanged.connect(
            lambda v: self.controller.set_config("preprocessing.bilateral_d", v)
        )
        hbox_bilateral.addWidget(self.spin_bilateral_d)

        hbox_bilateral.addWidget(QLabel("颜色σ:"))
        self.spin_bilateral_sigma_color = QSpinBox()
        self.spin_bilateral_sigma_color.setRange(50, 150)
        self.spin_bilateral_sigma_color.setSingleStep(5)
        self.spin_bilateral_sigma_color.setValue(
            self.controller.get_config("preprocessing.bilateral_sigma_color", 75)
        )
        self.spin_bilateral_sigma_color.valueChanged.connect(
            lambda v: self.controller.set_config(
                "preprocessing.bilateral_sigma_color", v
            )
        )
        hbox_bilateral.addWidget(self.spin_bilateral_sigma_color)

        hbox_bilateral.addWidget(QLabel("空间σ:"))
        self.spin_bilateral_sigma_space = QSpinBox()
        self.spin_bilateral_sigma_space.setRange(50, 150)
        self.spin_bilateral_sigma_space.setSingleStep(5)
        self.spin_bilateral_sigma_space.setValue(
            self.controller.get_config("preprocessing.bilateral_sigma_space", 75)
        )
        self.spin_bilateral_sigma_space.valueChanged.connect(
            lambda v: self.controller.set_config(
                "preprocessing.bilateral_sigma_space", v
            )
        )
        hbox_bilateral.addWidget(self.spin_bilateral_sigma_space)

        hbox_bilateral.addStretch()
        layout_advanced_pre.addLayout(hbox_bilateral)

        layout.addWidget(group_advanced_pre)

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

        # 添加stretch确保内容从顶部开始
        layout.addStretch()

        # 将滚动区域添加到主布局
        main_layout.addWidget(scroll_area)

    def _on_engine_changed(self, index):
        engine = self.combo_engine.itemData(index)
        self.controller.set_config("ocr.engine_type", engine)

    def _on_select_all_preprocessing(self, checked):
        """全选/取消全选通用预处理"""
        select_all = bool(checked)
        self.cb_denoise.setChecked(select_all)
        self.cb_binarize.setChecked(select_all)
        self.cb_deskew.setChecked(select_all)
        self.cb_contrast.setChecked(select_all)
        self.cb_sharpness.setChecked(select_all)
        self.cb_brightness.setChecked(select_all)
        self.cb_auto_rotate.setChecked(select_all)
        self.cb_grayscale.setChecked(select_all)

    def _on_select_all_paddle_preprocessing(self, checked):
        """全选/取消全选PaddleOCR官方预处理"""
        select_all = bool(checked)
        self.cb_doc_orientation.setChecked(select_all)
        self.cb_doc_unwarping.setChecked(select_all)
        self.cb_det_resize.setChecked(select_all)
        self.cb_rec_resize.setChecked(select_all)
