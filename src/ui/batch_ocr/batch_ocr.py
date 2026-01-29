#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 批量图片OCR界面

Author: Umi-OCR Team
Date: 2026-01-27
"""

import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QLabel,
    QProgressBar,
    QComboBox,
    QTextEdit,
    QFileDialog,
    QAbstractItemView,
    QScrollArea,
)
from PySide6.QtCore import QSize, Qt

from src.utils.logger import get_logger

logger = get_logger()


class BatchOCRView(QWidget):
    """
    批量图片OCR界面

    文件拖拽、批量识别、导出结果。
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化控制器
        try:
            from controllers.batch_ocr_controller import BatchOcrController

            self._controller = BatchOcrController.instance()
        except ModuleNotFoundError as e:
            logger.warning(f"批量图片控制器加载失败，部分功能不可用: {e}")
            self._controller = None

        # 待处理文件列表
        self._pending_files = []

        # 创建UI
        self._setup_ui()

        # 连接信号
        self._connect_signals()

        logger.info("批量OCR界面初始化完成")

    def _setup_ui(self):
        """创建界面"""
        # 设置统一的背景色
        self.setStyleSheet("background-color: #ffffff;")

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 创建滚动区域的容器widget
        scroll_content = QWidget()
        scroll_area.setWidget(scroll_content)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        btn_add_files = QPushButton("添加文件")
        btn_add_files.clicked.connect(self._on_add_files)
        toolbar_layout.addWidget(btn_add_files)

        btn_clear_all = QPushButton("清空")
        btn_clear_all.clicked.connect(self._on_clear_files)
        toolbar_layout.addWidget(btn_clear_all)

        btn_start = QPushButton("开始识别")
        btn_start.clicked.connect(self._on_start_ocr)
        toolbar_layout.addWidget(btn_start)

        toolbar_layout.addStretch()

        # 导出格式下拉框
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(
            ["纯文本(TXT)", "结构化数据(JSON)", "Excel(CSV)"]
        )
        self.export_format_combo.setCurrentIndex(0)
        toolbar_layout.addWidget(self.export_format_combo)

        # 导出按钮
        btn_export = QPushButton("导出结果")
        btn_export.clicked.connect(self._on_export)
        toolbar_layout.addWidget(btn_export)

        main_layout.addLayout(toolbar_layout)

        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setIconSize(QSize(120, 120))
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        main_layout.addWidget(self.file_list)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        main_layout.addWidget(self.progress_bar)

        # 结果显示区标题
        result_label = QLabel("识别结果")
        result_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        main_layout.addWidget(result_label)

        # 结果显示区
        self.result_browser = QTextEdit()
        self.result_browser.setReadOnly(True)
        main_layout.addWidget(self.result_browser)

        # 暂停按钮
        btn_pause = QPushButton("暂停")
        btn_pause.setEnabled(False)
        btn_pause.clicked.connect(self._on_pause)
        main_layout.addWidget(btn_pause)

        # 保存按钮引用
        self.btn_start = btn_start
        self.btn_pause = btn_pause

        main_layout.addStretch()

        # 设置滚动内容的布局
        scroll_content.setLayout(main_layout)

        # 设置主布局
        outer_layout = QVBoxLayout()
        outer_layout.addWidget(scroll_area)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outer_layout)

    def _connect_signals(self):
        """连接控制器信号"""
        if self._controller:
            self._controller.tasks_submitted.connect(self._on_tasks_submitted)
            self._controller.progress_updated.connect(self._on_progress_updated)
            self._controller.tasks_completed.connect(self._on_tasks_completed)
            self._controller.tasks_failed.connect(self._on_tasks_failed)

    def _on_add_files(self):
        """添加文件对话框"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片文件",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff);;All Files (*.*)",
        )

        if files:
            for file_path in files:
                if os.path.isfile(file_path):
                    if file_path not in self._pending_files:
                        self._pending_files.append(file_path)
                        self.file_list.addItem(file_path)
                        logger.debug(f"添加文件: {file_path}")
            logger.info(f"添加 {len(files)} 个文件")

    def _on_clear_files(self):
        """清空文件列表"""
        self._pending_files.clear()
        self.file_list.clear()
        logger.info("文件列表已清空")

    def _on_start_ocr(self):
        """开始识别"""
        if not self._pending_files:
            logger.warning("没有待处理的文件")
            return

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)

        if self._controller:
            group_id = self._controller.submit_batch_ocr(self._pending_files.copy())
            logger.info(f"已提交任务组: {group_id}")

    def _on_pause(self):
        """暂停/恢复"""
        if self.btn_pause.text() == "暂停":
            # 暂停
            self._controller.pause_ocr()
            self.btn_pause.setText("继续")
            logger.info("批量OCR已暂停")
        else:
            # 继续
            self._controller.resume_ocr()
            self.btn_pause.setText("暂停")
            logger.info("批量OCR已恢复")

    def _on_tasks_submitted(self, group_id):
        """任务已提交"""
        logger.info(f"任务已提交: {group_id}")
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("暂停")

    def _on_progress_updated(self, group_id, progress):
        """进度更新"""
        logger.debug(f"进度: {group_id} - {progress:.1%}")
        total = self.file_list.count()
        if total > 0:
            current = int(progress * total)
            self.progress_bar.setValue(current)

    def _on_tasks_completed(self, group_id):
        """任务完成"""
        logger.info(f"任务完成: {group_id}")
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("暂停")
        self.result_browser.append(f"\n任务完成: {group_id}\n")

    def _on_tasks_failed(self, group_id, error):
        """任务失败"""
        logger.error(f"任务失败: {group_id}, {error}")
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("暂停")
        self.result_browser.append(f"\n任务失败: {group_id}\n错误: {error}\n")

    def _on_export(self):
        """执行导出"""
        format_text = self.export_format_combo.currentText()
        logger.info(f"导出: {format_text}")

        # 获取保存路径
        file_filter = "All Files (*.*)"
        default_ext = ".txt"
        if "TXT" in format_text:
            file_filter = "Text Files (*.txt)"
            default_ext = ".txt"
        elif "JSON" in format_text:
            file_filter = "JSON Files (*.json)"
            default_ext = ".json"
        elif "CSV" in format_text:
            file_filter = "CSV Files (*.csv)"
            default_ext = ".csv"

        output_path, _ = QFileDialog.getSaveFileName(
            self, "保存导出文件", "", file_filter
        )

        if not output_path:
            logger.info("取消导出")
            return

        # 确保文件扩展名
        if not output_path.endswith(default_ext):
            output_path += default_ext

        # 调用控制器导出
        if self._current_group_id:
            if self._controller.export_results(
                self._current_group_id, output_path, format_text
            ):
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.information(
                    self, "导出成功", f"结果已保存到:\n{output_path}"
                )
            else:
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    self, "导出失败", "导出过程中发生错误，请查看日志。"
                )
        else:
            logger.warning("没有可导出的任务组")
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "提示", "请先执行识别任务。")
