#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 文件拖拽区域控件

提供文件拖拽接收功能，支持文件类型过滤和列表管理。

主要功能:
- 拖拽文件接收
- 文件类型过滤
- 拖拽状态视觉反馈
- 文件列表显示
- 批量添加/删除

Author: Umi-OCR Team
Date: 2026-01-27
"""

from typing import Optional, List, Set
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QLabel, QListWidgetItem, QFileDialog,
    QAbstractItemView, QMenu, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QAction


# =============================================================================
# 默认支持的文件类型
# =============================================================================

DEFAULT_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif"}
DEFAULT_DOC_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}


# =============================================================================
# 文件拖拽区域控件
# =============================================================================

class FileDropZone(QWidget):
    """
    文件拖拽区域控件

    用于接收拖拽的文件，支持文件类型过滤和列表管理。

    使用示例:
        drop_zone = FileDropZone()
        drop_zone.set_accepted_suffixes({".png", ".jpg", ".pdf"})
        drop_zone.files_added.connect(on_files_added)

    信号:
        files_added(list): 文件添加时发射，参数为文件路径列表
        files_removed(list): 文件移除时发射，参数为文件路径列表
        files_changed(): 文件列表变更时发射
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    files_added = Signal(list)
    files_removed = Signal(list)
    files_changed = Signal()

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化文件拖拽区域

        Args:
            parent: 父控件
        """
        super().__init__(parent)

        # 文件路径列表
        self._file_paths: List[str] = []

        # 允许的文件后缀（小写）
        self._accepted_suffixes: Set[str] = DEFAULT_IMAGE_SUFFIXES.copy()

        # 是否处于拖拽状态
        self._is_dragging = False

        # 初始化UI
        self._setup_ui()

        # 启用拖拽
        self.setAcceptDrops(True)

    def _setup_ui(self) -> None:
        """初始化 UI 布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 拖拽提示区域
        self._drop_hint = QLabel(self)
        self._drop_hint.setAlignment(Qt.AlignCenter)
        self._drop_hint.setText("将文件拖拽到此处\n或点击下方按钮选择文件")
        self._drop_hint.setMinimumHeight(80)
        self._drop_hint.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background-color: #fafafa;
                color: #999;
                font-size: 14px;
                padding: 20px;
            }
        """)
        layout.addWidget(self._drop_hint)

        # 文件列表
        self._file_list = QListWidget(self)
        self._file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._file_list.customContextMenuRequested.connect(self._show_context_menu)
        self._file_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fff;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e6f7ff;
                color: #1890ff;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        layout.addWidget(self._file_list)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._add_btn = QPushButton("添加文件")
        self._add_btn.clicked.connect(self._on_add_clicked)
        self._add_btn.setStyleSheet(self._get_button_style())
        btn_layout.addWidget(self._add_btn)

        self._add_folder_btn = QPushButton("添加文件夹")
        self._add_folder_btn.clicked.connect(self._on_add_folder_clicked)
        self._add_folder_btn.setStyleSheet(self._get_button_style())
        btn_layout.addWidget(self._add_folder_btn)

        btn_layout.addStretch()

        self._remove_btn = QPushButton("移除选中")
        self._remove_btn.clicked.connect(self._on_remove_clicked)
        self._remove_btn.setStyleSheet(self._get_button_style())
        btn_layout.addWidget(self._remove_btn)

        self._clear_btn = QPushButton("清空")
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        self._clear_btn.setStyleSheet(self._get_button_style())
        btn_layout.addWidget(self._clear_btn)

        layout.addLayout(btn_layout)

        # 状态标签
        self._status_label = QLabel("共 0 个文件")
        self._status_label.setStyleSheet("color: #999; font-size: 12px;")
        layout.addWidget(self._status_label)

    def _get_button_style(self) -> str:
        """获取按钮样式"""
        return """
            QPushButton {
                padding: 6px 12px;
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

    # -------------------------------------------------------------------------
    # 拖拽事件处理
    # -------------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag_state(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """拖拽离开事件"""
        self._set_drag_state(False)

    def dropEvent(self, event: QDropEvent) -> None:
        """放置事件"""
        self._set_drag_state(False)

        urls = event.mimeData().urls()
        file_paths = []

        for url in urls:
            path = url.toLocalFile()
            if path:
                file_paths.extend(self._collect_files(path))

        if file_paths:
            self.add_files(file_paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _set_drag_state(self, is_dragging: bool) -> None:
        """设置拖拽状态"""
        self._is_dragging = is_dragging

        if is_dragging:
            self._drop_hint.setStyleSheet("""
                QLabel {
                    border: 2px dashed #1890ff;
                    border-radius: 8px;
                    background-color: #e6f7ff;
                    color: #1890ff;
                    font-size: 14px;
                    padding: 20px;
                }
            """)
            self._drop_hint.setText("释放以添加文件")
        else:
            self._drop_hint.setStyleSheet("""
                QLabel {
                    border: 2px dashed #ccc;
                    border-radius: 8px;
                    background-color: #fafafa;
                    color: #999;
                    font-size: 14px;
                    padding: 20px;
                }
            """)
            self._drop_hint.setText("将文件拖拽到此处\n或点击下方按钮选择文件")

    # -------------------------------------------------------------------------
    # 公共接口
    # -------------------------------------------------------------------------

    def set_accepted_suffixes(self, suffixes: Set[str]) -> None:
        """
        设置允许的文件后缀

        Args:
            suffixes: 后缀集合，如 {".png", ".jpg"}
        """
        self._accepted_suffixes = {s.lower() for s in suffixes}

    def get_accepted_suffixes(self) -> Set[str]:
        """获取允许的文件后缀"""
        return self._accepted_suffixes.copy()

    def add_files(self, file_paths: List[str]) -> None:
        """
        添加文件

        Args:
            file_paths: 文件路径列表
        """
        added = []

        for path in file_paths:
            # 检查是否已存在
            if path in self._file_paths:
                continue

            # 检查文件后缀
            suffix = Path(path).suffix.lower()
            if self._accepted_suffixes and suffix not in self._accepted_suffixes:
                continue

            # 添加到列表
            self._file_paths.append(path)
            self._add_list_item(path)
            added.append(path)

        if added:
            self._update_status()
            self.files_added.emit(added)
            self.files_changed.emit()

    def remove_files(self, file_paths: List[str]) -> None:
        """
        移除文件

        Args:
            file_paths: 文件路径列表
        """
        removed = []

        for path in file_paths:
            if path in self._file_paths:
                self._file_paths.remove(path)
                removed.append(path)

                # 从列表中移除
                for i in range(self._file_list.count()):
                    item = self._file_list.item(i)
                    if item.data(Qt.UserRole) == path:
                        self._file_list.takeItem(i)
                        break

        if removed:
            self._update_status()
            self.files_removed.emit(removed)
            self.files_changed.emit()

    def clear(self) -> None:
        """清空所有文件"""
        if self._file_paths:
            removed = self._file_paths.copy()
            self._file_paths.clear()
            self._file_list.clear()
            self._update_status()
            self.files_removed.emit(removed)
            self.files_changed.emit()

    def get_files(self) -> List[str]:
        """
        获取所有文件路径

        Returns:
            List[str]: 文件路径列表
        """
        return self._file_paths.copy()

    def get_file_count(self) -> int:
        """
        获取文件数量

        Returns:
            int: 文件数量
        """
        return len(self._file_paths)

    # -------------------------------------------------------------------------
    # 私有方法
    # -------------------------------------------------------------------------

    def _collect_files(self, path: str) -> List[str]:
        """
        收集文件（支持文件夹递归）

        Args:
            path: 文件或文件夹路径

        Returns:
            List[str]: 文件路径列表
        """
        p = Path(path)
        files = []

        if p.is_file():
            if not self._accepted_suffixes or p.suffix.lower() in self._accepted_suffixes:
                files.append(str(p))
        elif p.is_dir():
            for item in p.rglob("*"):
                if item.is_file():
                    if not self._accepted_suffixes or item.suffix.lower() in self._accepted_suffixes:
                        files.append(str(item))

        return files

    def _add_list_item(self, file_path: str) -> None:
        """添加列表项"""
        p = Path(file_path)
        item = QListWidgetItem(p.name)
        item.setToolTip(file_path)
        item.setData(Qt.UserRole, file_path)
        self._file_list.addItem(item)

    def _update_status(self) -> None:
        """更新状态标签"""
        count = len(self._file_paths)
        self._status_label.setText(f"共 {count} 个文件")

    def _show_context_menu(self, pos) -> None:
        """显示右键菜单"""
        menu = QMenu(self)

        remove_action = QAction("移除选中", self)
        remove_action.triggered.connect(self._on_remove_clicked)
        menu.addAction(remove_action)

        open_folder_action = QAction("打开所在文件夹", self)
        open_folder_action.triggered.connect(self._on_open_folder)
        menu.addAction(open_folder_action)

        menu.addSeparator()

        clear_action = QAction("清空全部", self)
        clear_action.triggered.connect(self._on_clear_clicked)
        menu.addAction(clear_action)

        menu.exec(self._file_list.mapToGlobal(pos))

    # -------------------------------------------------------------------------
    # 槽函数
    # -------------------------------------------------------------------------

    def _on_add_clicked(self) -> None:
        """添加文件按钮点击"""
        # 构建过滤器
        if self._accepted_suffixes:
            suffix_str = " ".join(f"*{s}" for s in self._accepted_suffixes)
            filter_str = f"支持的文件 ({suffix_str});;所有文件 (*)"
        else:
            filter_str = "所有文件 (*)"

        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "", filter_str
        )

        if files:
            self.add_files(files)

    def _on_add_folder_clicked(self) -> None:
        """添加文件夹按钮点击"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            files = self._collect_files(folder)
            if files:
                self.add_files(files)

    def _on_remove_clicked(self) -> None:
        """移除选中按钮点击"""
        selected = self._file_list.selectedItems()
        if selected:
            paths = [item.data(Qt.UserRole) for item in selected]
            self.remove_files(paths)

    def _on_clear_clicked(self) -> None:
        """清空按钮点击"""
        self.clear()

    def _on_open_folder(self) -> None:
        """打开所在文件夹"""
        import subprocess
        import sys

        selected = self._file_list.selectedItems()
        if selected:
            path = selected[0].data(Qt.UserRole)
            folder = str(Path(path).parent)

            if sys.platform == "win32":
                subprocess.Popen(["explorer", folder])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
