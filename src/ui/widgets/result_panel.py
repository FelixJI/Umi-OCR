#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 结果面板控件

提供 OCR 结果显示功能，支持多种视图模式和导出操作。

主要功能:
- 富文本显示 OCR 结果
- 支持纯文本/JSON/表格视图切换
- 复制/导出功能
- 搜索高亮
- 结果统计

Author: Umi-OCR Team
Date: 2026-01-27
"""

import json
from typing import Optional, Dict, Any
from enum import Enum

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QComboBox,
    QLabel,
    QLineEdit,
    QApplication,
    QMenu,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor, QAction

# =============================================================================
# 视图模式枚举
# =============================================================================


class ResultViewMode(Enum):
    """结果视图模式"""

    TEXT = "text"  # 纯文本模式
    JSON = "json"  # JSON 模式
    TABLE = "table"  # 表格模式（HTML 表格）


# =============================================================================
# 结果面板控件
# =============================================================================


class ResultPanel(QWidget):
    """
    OCR 结果面板控件

    用于显示 OCR 识别结果，支持多种视图模式和操作。

    使用示例:
        panel = ResultPanel()
        panel.set_result(ocr_result)
        panel.copy_requested.connect(on_copy)

    信号:
        copy_requested(): 复制请求
        export_requested(str): 导出请求，参数为格式类型
        search_text_changed(str): 搜索文本变更
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    copy_requested = Signal()
    export_requested = Signal(str)  # format: "txt", "json", "html"
    search_text_changed = Signal(str)

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化结果面板

        Args:
            parent: 父控件
        """
        super().__init__(parent)

        # 当前结果数据
        self._result_data: Optional[Dict[str, Any]] = None

        # 当前视图模式
        self._view_mode = ResultViewMode.TEXT

        # 搜索高亮格式
        self._highlight_format = QTextCharFormat()
        self._highlight_format.setBackground(QColor("#ffff00"))

        # 初始化UI
        self._setup_ui()

        # 连接信号
        self._connect_signals()

    def _setup_ui(self) -> None:
        """初始化 UI 布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 工具栏
        toolbar = self._create_toolbar()
        layout.addLayout(toolbar)

        # 结果显示区
        self._text_browser = QTextEdit(self)
        self._text_browser.setReadOnly(True)
        self._text_browser.setStyleSheet("""
            QTextEdit {
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 14px;
                line-height: 1.6;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fafafa;
            }
        """)
        layout.addWidget(self._text_browser)

        # 状态栏
        status_bar = self._create_status_bar()
        layout.addLayout(status_bar)

    def _create_toolbar(self) -> QHBoxLayout:
        """创建工具栏"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # 视图模式选择
        mode_label = QLabel("视图:")
        mode_label.setStyleSheet("color: #666;")
        toolbar.addWidget(mode_label)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem("纯文本", ResultViewMode.TEXT)
        self._mode_combo.addItem("JSON", ResultViewMode.JSON)
        self._mode_combo.addItem("表格", ResultViewMode.TABLE)
        self._mode_combo.setFixedWidth(100)
        toolbar.addWidget(self._mode_combo)

        toolbar.addSpacing(16)

        # 搜索框
        search_label = QLabel("搜索:")
        search_label.setStyleSheet("color: #666;")
        toolbar.addWidget(search_label)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("输入搜索内容...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setMaximumWidth(200)
        toolbar.addWidget(self._search_input)

        toolbar.addStretch()

        # 操作按钮
        self._copy_btn = QPushButton("复制")
        self._copy_btn.setFixedWidth(60)
        self._copy_btn.setStyleSheet(self._get_button_style())
        toolbar.addWidget(self._copy_btn)

        self._export_btn = QPushButton("导出")
        self._export_btn.setFixedWidth(60)
        self._export_btn.setStyleSheet(self._get_button_style())
        toolbar.addWidget(self._export_btn)

        return toolbar

    def _create_status_bar(self) -> QHBoxLayout:
        """创建状态栏"""
        status_bar = QHBoxLayout()

        self._status_label = QLabel("等待识别结果...")
        self._status_label.setStyleSheet("color: #999; font-size: 12px;")
        status_bar.addWidget(self._status_label)

        status_bar.addStretch()

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet("color: #666; font-size: 12px;")
        status_bar.addWidget(self._stats_label)

        return status_bar

    def _get_button_style(self) -> str:
        """获取按钮样式"""
        return """
            QPushButton {
                padding: 5px 10px;
                font-size: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f5f5f5;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border-color: #999;
            }
            QPushButton:pressed {
                background-color: #ddd;
            }
        """

    def _connect_signals(self) -> None:
        """连接信号"""
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self._search_input.textChanged.connect(self._on_search_changed)
        self._copy_btn.clicked.connect(self._on_copy_clicked)
        self._export_btn.clicked.connect(self._on_export_clicked)

    # -------------------------------------------------------------------------
    # 公共接口
    # -------------------------------------------------------------------------

    def set_result(self, result: Dict[str, Any]) -> None:
        """
        设置 OCR 结果

        Args:
            result: OCR 结果字典，应包含:
                - text: 识别文本
                - blocks: 文本块列表（可选）
                - confidence: 置信度（可选）
                - engine_name: 引擎名称（可选）
                - duration_ms: 耗时毫秒（可选）
        """
        self._result_data = result
        self._refresh_display()
        self._update_stats()

    def set_text(self, text: str) -> None:
        """
        简单设置纯文本结果

        Args:
            text: 识别文本
        """
        self._result_data = {"text": text}
        self._refresh_display()
        self._update_stats()

    def clear(self) -> None:
        """清空结果"""
        self._result_data = None
        self._text_browser.clear()
        self._status_label.setText("等待识别结果...")
        self._stats_label.setText("")

    def set_loading(self, message: str = "正在识别...") -> None:
        """
        设置加载状态

        Args:
            message: 加载提示信息
        """
        self._text_browser.setHtml(f"""
            <div style="text-align: center; color: #999; padding: 50px;">
                {message}
            </div>
        """)
        self._status_label.setText(message)

    def set_error(self, error: str) -> None:
        """
        设置错误状态

        Args:
            error: 错误信息
        """
        self._text_browser.setHtml(f"""
            <div style="text-align: center; color: #ff4d4f; padding: 50px;">
                <strong>识别失败</strong><br><br>
                {error}
            </div>
        """)
        self._status_label.setText("识别失败")

    def get_text(self) -> str:
        """
        获取当前显示的纯文本

        Returns:
            str: 纯文本内容
        """
        return self._text_browser.toPlainText()

    def set_view_mode(self, mode: ResultViewMode) -> None:
        """
        设置视图模式

        Args:
            mode: 视图模式
        """
        self._view_mode = mode
        index = self._mode_combo.findData(mode)
        if index >= 0:
            self._mode_combo.setCurrentIndex(index)
        self._refresh_display()

    # -------------------------------------------------------------------------
    # 私有方法
    # -------------------------------------------------------------------------

    def _refresh_display(self) -> None:
        """刷新显示内容"""
        if not self._result_data:
            return

        if self._view_mode == ResultViewMode.TEXT:
            self._display_text_mode()
        elif self._view_mode == ResultViewMode.JSON:
            self._display_json_mode()
        elif self._view_mode == ResultViewMode.TABLE:
            self._display_table_mode()

        # 应用搜索高亮
        search_text = self._search_input.text()
        if search_text:
            self._highlight_search(search_text)

    def _display_text_mode(self) -> None:
        """显示纯文本模式"""
        text = self._result_data.get("text", "")

        # 如果有 blocks，从 blocks 中提取文本
        if not text and "blocks" in self._result_data:
            lines = []
            for block in self._result_data["blocks"]:
                if isinstance(block, dict):
                    lines.append(block.get("text", ""))
                else:
                    lines.append(str(block))
            text = "\n".join(lines)

        self._text_browser.setPlainText(text)

    def _display_json_mode(self) -> None:
        """显示 JSON 模式"""
        try:
            json_str = json.dumps(self._result_data, ensure_ascii=False, indent=2)
            self._text_browser.setPlainText(json_str)
        except Exception as e:
            self._text_browser.setPlainText(f"JSON 格式化失败: {e}")

    def _display_table_mode(self) -> None:
        """显示表格模式"""
        blocks = self._result_data.get("blocks", [])

        if not blocks:
            # 无 blocks 数据，显示纯文本
            self._display_text_mode()
            return

        # 构建 HTML 表格
        html = """
        <style>
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f5f5f5; }
            tr:nth-child(even) { background-color: #fafafa; }
        </style>
        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">#</th>
                    <th>文本</th>
                    <th style="width: 80px;">置信度</th>
                </tr>
            </thead>
            <tbody>
        """

        for i, block in enumerate(blocks, 1):
            if isinstance(block, dict):
                text = block.get("text", "")
                confidence = block.get("confidence", 0)
                conf_str = (
                    f"{confidence:.2f}"
                    if isinstance(confidence, (int, float))
                    else str(confidence)
                )
            else:
                text = str(block)
                conf_str = "-"

            html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{text}</td>
                    <td>{conf_str}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        """

        self._text_browser.setHtml(html)

    def _update_stats(self) -> None:
        """更新统计信息"""
        if not self._result_data:
            self._status_label.setText("等待识别结果...")
            self._stats_label.setText("")
            return

        # 计算统计
        text = self._result_data.get("text", "")
        if not text and "blocks" in self._result_data:
            text = "\n".join(
                b.get("text", "") if isinstance(b, dict) else str(b)
                for b in self._result_data["blocks"]
            )

        char_count = len(text)
        line_count = len(text.split("\n")) if text else 0
        block_count = len(self._result_data.get("blocks", []))

        # 更新状态
        engine_name = self._result_data.get("engine_name", "")
        duration = self._result_data.get("duration_ms", 0)

        if engine_name:
            self._status_label.setText(f"引擎: {engine_name} | 耗时: {duration}ms")
        else:
            self._status_label.setText("识别完成")

        self._stats_label.setText(
            f"{char_count} 字符 | {line_count} 行 | {block_count} 块"
        )

    def _highlight_search(self, text: str) -> None:
        """
        高亮搜索文本

        Args:
            text: 搜索文本
        """
        if not text:
            return

        # 清除之前的高亮
        cursor = self._text_browser.textCursor()
        cursor.select(QTextCursor.Document)
        plain_format = QTextCharFormat()
        cursor.setCharFormat(plain_format)

        # 查找并高亮
        cursor = self._text_browser.textCursor()
        cursor.setPosition(0)

        while True:
            cursor = self._text_browser.document().find(text, cursor)
            if cursor.isNull():
                break
            cursor.mergeCharFormat(self._highlight_format)

    # -------------------------------------------------------------------------
    # 槽函数
    # -------------------------------------------------------------------------

    def _on_mode_changed(self, index: int) -> None:
        """视图模式变更"""
        self._view_mode = self._mode_combo.currentData()
        self._refresh_display()

    def _on_search_changed(self, text: str) -> None:
        """搜索文本变更"""
        self._refresh_display()
        self.search_text_changed.emit(text)

    def _on_copy_clicked(self) -> None:
        """复制按钮点击"""
        text = self._text_browser.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
        self.copy_requested.emit()

    def _on_export_clicked(self) -> None:
        """导出按钮点击"""
        menu = QMenu(self)

        txt_action = QAction("导出为 TXT", self)
        txt_action.triggered.connect(lambda: self._export_to_file("txt"))
        menu.addAction(txt_action)

        json_action = QAction("导出为 JSON", self)
        json_action.triggered.connect(lambda: self._export_to_file("json"))
        menu.addAction(json_action)

        html_action = QAction("导出为 HTML", self)
        html_action.triggered.connect(lambda: self._export_to_file("html"))
        menu.addAction(html_action)

        menu.exec(self._export_btn.mapToGlobal(self._export_btn.rect().bottomLeft()))

    def _export_to_file(self, format_type: str) -> None:
        """
        导出到文件

        Args:
            format_type: 格式类型 ("txt", "json", "html")
        """
        # 选择保存路径
        filter_map = {
            "txt": "文本文件 (*.txt)",
            "json": "JSON 文件 (*.json)",
            "html": "HTML 文件 (*.html)",
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出结果", "", filter_map.get(format_type, "所有文件 (*)")
        )

        if not file_path:
            return

        try:
            if format_type == "txt":
                content = self._text_browser.toPlainText()
            elif format_type == "json":
                content = json.dumps(self._result_data, ensure_ascii=False, indent=2)
            elif format_type == "html":
                content = self._text_browser.toHtml()
            else:
                content = self._text_browser.toPlainText()

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.export_requested.emit(format_type)

        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出失败: {e}")
