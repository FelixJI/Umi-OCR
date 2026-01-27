#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 批量文档OCR界面

Author: Umi-OCR Team
Date: 2026-01-27
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
                            QPushButton, QLabel, QProgressBar, QTextEdit, QFileDialog)
from PySide6.QtCore import Qt

from controllers.batch_doc_controller import BatchDocController
from utils.logger import get_logger

logger = get_logger()


class BatchDocView(QWidget):
    """
    批量文档OCR界面
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化控制器
        self._controller = BatchDocController()

        # 待处理文档列表
        self._pending_docs = []

        # 创建UI
        self._setup_ui()

        # 连接信号
        self._connect_signals()

        logger.info("批量文档OCR界面初始化完成")

    def _setup_ui(self):
        """创建界面"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        btn_add_docs = QPushButton("添加文档")
        btn_add_docs.clicked.connect(self._on_add_docs)
        toolbar_layout.addWidget(btn_add_docs)

        btn_clear_all = QPushButton("清空")
        btn_clear_all.clicked.connect(self._on_clear_docs)
        toolbar_layout.addWidget(btn_clear_all)

        btn_start = QPushButton("开始识别")
        btn_start.clicked.connect(self._on_start_ocr)
        toolbar_layout.addWidget(btn_start)

        btn_pause = QPushButton("暂停")
        btn_pause.setEnabled(False)
        btn_pause.clicked.connect(self._on_pause)
        toolbar_layout.addWidget(btn_pause)

        btn_cancel = QPushButton("取消")
        btn_cancel.setEnabled(False)
        btn_cancel.clicked.connect(self._on_cancel)
        toolbar_layout.addWidget(btn_cancel)

        toolbar_layout.addStretch()

        # 导出格式按钮
        btn_export_pdf = QPushButton("导出为可搜索PDF")
        btn_export_pdf.clicked.connect(lambda: self._on_export_pdf())
        toolbar_layout.addWidget(btn_export_pdf)

        btn_export_word = QPushButton("导出为Word")
        btn_export_word.clicked.connect(lambda: self._on_export_word())
        toolbar_layout.addWidget(btn_export_word)

        btn_export_excel = QPushButton("导出为Excel")
        btn_export_excel.clicked.connect(lambda: self._on_export_excel())
        toolbar_layout.addWidget(btn_export_excel)

        main_layout.addLayout(toolbar_layout)

        # 文档列表
        self.doc_list = QListWidget()
        main_layout.addWidget(self.doc_list)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        main_layout.addWidget(self.progress_bar)

        # 结果显示区
        result_label = QLabel("识别结果")
        result_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        main_layout.addWidget(result_label)

        self.result_browser = QTextEdit()
        self.result_browser.setReadOnly(True)
        main_layout.addWidget(self.result_browser)

        # 保存按钮引用
        self.btn_start = btn_start
        self.btn_pause = btn_pause
        self.btn_cancel = btn_cancel

        main_layout.addStretch()

        self.setLayout(main_layout)

    def _connect_signals(self):
        """连接控制器信号"""
        self._controller.tasks_submitted.connect(self._on_tasks_submitted)
        self._controller.progress_updated.connect(self._on_progress_updated)
        self._controller.tasks_completed.connect(self._on_tasks_completed)
        self._controller.tasks_failed.connect(self._on_tasks_failed)

    def _on_add_docs(self):
        """添加文档对话框"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择文档文件",
            "",
            "Documents (*.pdf *.xps *.epub *.mobi *.fb2 *.cbz);;All Files (*.*)"
        )

        if files:
            for file_path in files:
                if file_path not in self._pending_docs:
                    self._pending_docs.append(file_path)
                    self.doc_list.addItem(file_path)
                    logger.debug(f"添加文档: {file_path}")
            logger.info(f"添加 {len(files)} 个文档")

    def _on_clear_docs(self):
        """清空文档列表"""
        self._pending_docs.clear()
        self.doc_list.clear()
        logger.info("文档列表已清空")

    def _on_start_ocr(self):
        """开始识别"""
        if not self._pending_docs:
            logger.warning("没有待处理的文档")
            return

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)

        group_id = self._controller.process_pdfs(self._pending_docs.copy())
        logger.info(f"已提交任务组: {group_id}")

    def _on_pause(self):
        """暂停/恢复"""
        if self.btn_pause.text() == "暂停":
            # 暂停
            self._controller.pause_ocr()
            self.btn_pause.setText("继续")
            logger.info("批量文档OCR已暂停")
        else:
            # 继续
            self._controller.resume_ocr()
            self.btn_pause.setText("暂停")
            logger.info("批量文档OCR已恢复")

    def _on_cancel(self):
        """取消任务"""
        self._controller.cancel_batch()
        logger.info("批量文档OCR已取消")

    def _on_export_pdf(self):
        """导出为可搜索PDF"""
        logger.info("导出为可搜索PDF")
        logger.info("导出功能待实现: 需要添加导出器集成")

    def _on_export_word(self):
        """导出为Word"""
        logger.info("导出为Word")
        logger.info("导出功能待实现: 需要添加导出器集成")

    def _on_export_excel(self):
        """导出为Excel"""
        logger.info("导出为Excel")
        logger.info("导出功能待实现: 需要添加导出器集成")

    def _on_tasks_submitted(self, group_id):
        """任务已提交"""
        logger.info(f"任务已提交: {group_id}")

    def _on_progress_updated(self, group_id, progress):
        """进度更新"""
        logger.info(f"进度更新: {group_id} - {progress:.2%}")
        total = self.doc_list.count()
        if total > 0:
            current = int(progress * total)
            self.progress_bar.setValue(current)

    def _on_tasks_completed(self, group_id):
        """任务完成"""
        logger.info(f"任务完成: {group_id}")
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_pause.setText("暂停")
        self.result_browser.append(f"\n任务完成: {group_id}\n")

    def _on_tasks_failed(self, group_id, error):
        """任务失败"""
        logger.error(f"任务失败: {group_id}, {error}")
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_pause.setText("暂停")
        self.result_browser.append(f"\n任务失败: {group_id}\n错误: {error}\n")
