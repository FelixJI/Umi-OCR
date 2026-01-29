#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 模型下载设置面板

Author: Umi-OCR Team
Date: 2026-01-28
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QScrollArea,
    QDialog,
    QGridLayout,
    QMessageBox,
    QProgressBar,
)
from PySide6.QtCore import Qt, QThread, Signal

from src.services.ocr.model_download_config import (
    MODEL_PRESETS,
    ALL_MODELS,
    get_model_by_id,
    get_preset_by_id,
)
from src.services.ocr.models.model_manager_core import get_model_manager


class ModelDownloadThread(QThread):
    """
    模型下载线程
    """

    progress_update = Signal(str, int, int, float)
    download_finished = Signal(str, bool, str)
    all_finished = Signal(bool, str)

    def __init__(self, model_names):
        super().__init__()
        self.model_names = model_names
        self.manager = get_model_manager()
        self.manager.download_progress.connect(self._on_progress)
        self.manager.download_completed.connect(self._on_completed)
        self.downloaded_count = 0
        self.total_count = len(model_names)
        self.failed_models = []

    def _on_progress(self, model_name, current, total, speed):
        self.progress_update.emit(model_name, current, total, speed)

    def _on_completed(self, model_name, success, message):
        self.downloaded_count += 1
        self.download_finished.emit(model_name, success, message)
        if not success:
            self.failed_models.append(model_name)
        if self.downloaded_count >= self.total_count:
            success_all = len(self.failed_models) == 0
            message = f"成功下载 {self.downloaded_count - len(self.failed_models)} 个模型，失败 {len(self.failed_models)} 个"
            self.all_finished.emit(success_all, message)

    def run(self):
        for model_name in self.model_names:
            self.manager.download_model(model_name)


class ModelSelectionDialog(QDialog):
    """
    模型选择对话框
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模型选择")
        self.setMinimumSize(600, 500)
        self.selected_models = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 预设组合选择
        group_presets = QGroupBox("推荐模型组合")
        layout_presets = QVBoxLayout(group_presets)

        self.preset_tree = QTreeWidget()
        self.preset_tree.setHeaderLabels(["组合名称", "描述", "大小(MB)", "推荐场景"])
        self.preset_tree.setColumnWidth(0, 120)
        self.preset_tree.setColumnWidth(1, 200)
        self.preset_tree.setColumnWidth(2, 80)
        self.preset_tree.setColumnWidth(3, 150)

        # 添加预设组合
        for preset in MODEL_PRESETS.values():
            item = QTreeWidgetItem(
                [
                    preset.name,
                    preset.description,
                    f"{preset.total_size_mb}",
                    preset.recommended_for,
                ]
            )
            item.setData(0, Qt.UserRole, preset.id)
            self.preset_tree.addTopLevelItem(item)

        layout_presets.addWidget(self.preset_tree)
        layout.addWidget(group_presets)

        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_select = QPushButton("选择此组合")
        btn_select.clicked.connect(self._on_select_preset)
        btn_layout.addWidget(btn_select)

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _on_select_preset(self):
        selected_item = self.preset_tree.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "警告", "请选择一个模型组合")
            return

        preset_id = selected_item.data(0, Qt.UserRole)
        preset = get_preset_by_id(preset_id)
        if preset:
            self.selected_models = preset.models
            self.accept()


class ModelDownloadSettingsPanel(QWidget):
    """
    模型下载设置面板
    """

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller
        self._init_ui()

    def _init_ui(self):
        # 设置统一的背景色
        self.setStyleSheet("background-color: #ffffff;")

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

        # 模型下载区域
        group_download = QGroupBox("模型管理")
        layout_download = QVBoxLayout(group_download)

        # 模型组合选择
        hbox_preset = QHBoxLayout()
        hbox_preset.addWidget(QLabel("推荐模型组合:"))

        self.combo_preset = QComboBox()
        for preset in MODEL_PRESETS.values():
            self.combo_preset.addItem(
                f"{preset.name} ({preset.total_size_mb}MB)", preset.id
            )
        hbox_preset.addWidget(self.combo_preset)
        hbox_preset.addStretch()
        layout_download.addLayout(hbox_preset)

        # 模型详情
        self.label_preset_info = QLabel("请选择一个模型组合查看详情")
        self.label_preset_info.setWordWrap(True)
        self.label_preset_info.setStyleSheet("color: #666;")
        layout_download.addWidget(self.label_preset_info)

        # 连接信号
        self.combo_preset.currentIndexChanged.connect(self._on_preset_changed)

        # 下载按钮
        self.btn_download = QPushButton("下载所选模型")
        self.btn_download.clicked.connect(self._on_download)
        layout_download.addWidget(self.btn_download)

        # 下载进度
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout_download.addWidget(self.progress_bar)

        self.label_progress = QLabel("")
        self.label_progress.setVisible(False)
        layout_download.addWidget(self.label_progress)

        layout.addWidget(group_download)

        # 添加stretch确保内容从顶部开始
        layout.addStretch()

        # 将滚动区域添加到主布局
        main_layout.addWidget(scroll_area)

        # 触发一次初始化
        self._on_preset_changed(0)

    def _on_preset_changed(self, index):
        preset_id = self.combo_preset.itemData(index)
        preset = get_preset_by_id(preset_id)
        if preset:
            info = f"描述: {preset.description}\n"
            info += f"包含模型: {len(preset.models)} 个\n"
            info += f"总大小: {preset.total_size_mb} MB\n"
            info += f"推荐场景: {preset.recommended_for}"
            self.label_preset_info.setText(info)

    def _on_download(self):
        preset_id = self.combo_preset.currentData()
        preset = get_preset_by_id(preset_id)
        if not preset:
            return

        # 确认下载
        reply = QMessageBox.question(
            self,
            "确认下载",
            f"确定要下载 '{preset.name}' 组合吗？\n总大小: {preset.total_size_mb} MB\n包含 {len(preset.models)} 个模型",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._start_download(preset.models)

    def _start_download(self, model_names):
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(model_names))
        self.progress_bar.setValue(0)
        self.label_progress.setVisible(True)
        self.btn_download.setEnabled(False)

        self.thread = ModelDownloadThread(model_names)
        self.thread.progress_update.connect(self._on_download_progress)
        self.thread.download_finished.connect(self._on_download_completed)
        self.thread.all_finished.connect(self._on_all_download_finished)
        self.thread.start()

    def _on_download_progress(self, model_name, current, total, speed):
        self.label_progress.setText(
            f"下载中: {model_name} - {current}/{total} ({speed:.1f} MB/s)"
        )

    def _on_download_completed(self, model_name, success, message):
        current_value = self.progress_bar.value()
        self.progress_bar.setValue(current_value + 1)
        status = "成功" if success else "失败"
        self.label_progress.setText(f"{model_name}: {status}")

    def _on_all_download_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.label_progress.setVisible(False)
        self.btn_download.setEnabled(True)

        if success:
            QMessageBox.information(self, "下载完成", message)
        else:
            QMessageBox.warning(self, "下载完成", message)
