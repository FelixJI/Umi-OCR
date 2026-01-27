#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 进度卡片控件

提供任务进度可视化功能，支持状态指示和操作控制。

主要功能:
- 任务进度可视化
- 状态指示（等待/运行/完成/失败/已取消）
- 暂停/恢复/取消操作
- 子任务展开/收起
- 时间统计

Author: Umi-OCR Team
Date: 2026-01-27
"""

from typing import Optional
from enum import Enum
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QColor


# =============================================================================
# 进度状态枚举
# =============================================================================

class ProgressStatus(Enum):
    """进度状态"""
    PENDING = "pending"       # 等待中
    RUNNING = "running"       # 运行中
    PAUSED = "paused"        # 已暂停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


# 状态颜色映射
STATUS_COLORS = {
    ProgressStatus.PENDING: "#faad14",    # 黄色
    ProgressStatus.RUNNING: "#1890ff",    # 蓝色
    ProgressStatus.PAUSED: "#722ed1",     # 紫色
    ProgressStatus.COMPLETED: "#52c41a",  # 绿色
    ProgressStatus.FAILED: "#ff4d4f",     # 红色
    ProgressStatus.CANCELLED: "#8c8c8c",  # 灰色
}

# 状态文本映射
STATUS_TEXT = {
    ProgressStatus.PENDING: "等待中",
    ProgressStatus.RUNNING: "运行中",
    ProgressStatus.PAUSED: "已暂停",
    ProgressStatus.COMPLETED: "已完成",
    ProgressStatus.FAILED: "失败",
    ProgressStatus.CANCELLED: "已取消",
}


# =============================================================================
# 进度卡片控件
# =============================================================================

class ProgressCard(QFrame):
    """
    进度卡片控件

    用于显示任务进度和控制操作。

    使用示例:
        card = ProgressCard()
        card.set_title("OCR 任务")
        card.set_progress(0.5)
        card.set_status(ProgressStatus.RUNNING)
        card.pause_clicked.connect(on_pause)

    信号:
        pause_clicked(str): 暂停按钮点击，参数为任务ID
        resume_clicked(str): 恢复按钮点击，参数为任务ID
        cancel_clicked(str): 取消按钮点击，参数为任务ID
        retry_clicked(str): 重试按钮点击，参数为任务ID
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    pause_clicked = Signal(str)
    resume_clicked = Signal(str)
    cancel_clicked = Signal(str)
    retry_clicked = Signal(str)

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化进度卡片

        Args:
            parent: 父控件
        """
        super().__init__(parent)

        # 任务ID
        self._task_id: str = ""

        # 当前状态
        self._status = ProgressStatus.PENDING

        # 进度值 (0.0 - 1.0)
        self._progress: float = 0.0

        # 统计信息
        self._total_count: int = 0
        self._completed_count: int = 0
        self._failed_count: int = 0

        # 开始时间
        self._start_time: Optional[datetime] = None

        # 初始化UI
        self._setup_ui()

        # 时间更新定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_elapsed_time)

    def _setup_ui(self) -> None:
        """初始化 UI 布局"""
        # 设置卡片样式
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            ProgressCard {
                background-color: #fff;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 标题行
        title_row = QHBoxLayout()

        self._title_label = QLabel("任务")
        self._title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_row.addWidget(self._title_label)

        title_row.addStretch()

        # 状态指示器
        self._status_indicator = QLabel()
        self._status_indicator.setFixedSize(10, 10)
        self._status_indicator.setStyleSheet("""
            border-radius: 5px;
            background-color: #faad14;
        """)
        title_row.addWidget(self._status_indicator)

        self._status_label = QLabel("等待中")
        self._status_label.setStyleSheet("color: #666; font-size: 12px;")
        title_row.addWidget(self._status_label)

        layout.addLayout(title_row)

        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #f0f0f0;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background-color: #1890ff;
            }
        """)
        layout.addWidget(self._progress_bar)

        # 统计行
        stats_row = QHBoxLayout()

        self._stats_label = QLabel("0 / 0")
        self._stats_label.setStyleSheet("color: #999; font-size: 12px;")
        stats_row.addWidget(self._stats_label)

        stats_row.addStretch()

        self._time_label = QLabel("")
        self._time_label.setStyleSheet("color: #999; font-size: 12px;")
        stats_row.addWidget(self._time_label)

        layout.addLayout(stats_row)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._pause_btn = QPushButton("暂停")
        self._pause_btn.setFixedWidth(60)
        self._pause_btn.clicked.connect(self._on_pause_clicked)
        self._pause_btn.setStyleSheet(self._get_button_style())
        btn_row.addWidget(self._pause_btn)

        self._resume_btn = QPushButton("恢复")
        self._resume_btn.setFixedWidth(60)
        self._resume_btn.clicked.connect(self._on_resume_clicked)
        self._resume_btn.setStyleSheet(self._get_button_style())
        self._resume_btn.hide()
        btn_row.addWidget(self._resume_btn)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setFixedWidth(60)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        self._cancel_btn.setStyleSheet(self._get_button_style("#ff4d4f"))
        btn_row.addWidget(self._cancel_btn)

        self._retry_btn = QPushButton("重试")
        self._retry_btn.setFixedWidth(60)
        self._retry_btn.clicked.connect(self._on_retry_clicked)
        self._retry_btn.setStyleSheet(self._get_button_style("#faad14"))
        self._retry_btn.hide()
        btn_row.addWidget(self._retry_btn)

        btn_row.addStretch()

        layout.addLayout(btn_row)

    def _get_button_style(self, color: str = "#1890ff") -> str:
        """获取按钮样式"""
        return f"""
            QPushButton {{
                padding: 4px 8px;
                font-size: 12px;
                border: 1px solid {color};
                border-radius: 4px;
                background-color: #fff;
                color: {color};
            }}
            QPushButton:hover {{
                background-color: {color};
                color: #fff;
            }}
            QPushButton:pressed {{
                background-color: {color};
                opacity: 0.8;
            }}
        """

    # -------------------------------------------------------------------------
    # 公共接口
    # -------------------------------------------------------------------------

    def set_task_id(self, task_id: str) -> None:
        """
        设置任务ID

        Args:
            task_id: 任务ID
        """
        self._task_id = task_id

    def get_task_id(self) -> str:
        """获取任务ID"""
        return self._task_id

    def set_title(self, title: str) -> None:
        """
        设置标题

        Args:
            title: 标题文本
        """
        self._title_label.setText(title)

    def set_progress(self, progress: float) -> None:
        """
        设置进度

        Args:
            progress: 进度值 (0.0 - 1.0)
        """
        self._progress = max(0.0, min(1.0, progress))
        self._progress_bar.setValue(int(self._progress * 100))

    def get_progress(self) -> float:
        """获取进度"""
        return self._progress

    def set_status(self, status: ProgressStatus) -> None:
        """
        设置状态

        Args:
            status: 进度状态
        """
        self._status = status

        # 更新状态指示器
        color = STATUS_COLORS.get(status, "#999")
        self._status_indicator.setStyleSheet(f"""
            border-radius: 5px;
            background-color: {color};
        """)

        # 更新状态文本
        text = STATUS_TEXT.get(status, "未知")
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; font-size: 12px;")

        # 更新进度条颜色
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: #f0f0f0;
                height: 8px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                border-radius: 4px;
                background-color: {color};
            }}
        """)

        # 更新按钮可见性
        self._update_buttons()

        # 管理计时器
        if status == ProgressStatus.RUNNING:
            if not self._start_time:
                self._start_time = datetime.now()
            self._timer.start(1000)
        else:
            self._timer.stop()

    def get_status(self) -> ProgressStatus:
        """获取状态"""
        return self._status

    def set_counts(self, total: int, completed: int, failed: int = 0) -> None:
        """
        设置计数

        Args:
            total: 总数
            completed: 完成数
            failed: 失败数
        """
        self._total_count = total
        self._completed_count = completed
        self._failed_count = failed

        if failed > 0:
            self._stats_label.setText(f"{completed} / {total} (失败: {failed})")
        else:
            self._stats_label.setText(f"{completed} / {total}")

    def set_elapsed_time(self, seconds: int) -> None:
        """
        设置已用时间

        Args:
            seconds: 秒数
        """
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            self._time_label.setText(f"用时: {hours}:{minutes:02d}:{secs:02d}")
        else:
            self._time_label.setText(f"用时: {minutes}:{secs:02d}")

    # -------------------------------------------------------------------------
    # 私有方法
    # -------------------------------------------------------------------------

    def _update_buttons(self) -> None:
        """更新按钮可见性"""
        is_running = self._status == ProgressStatus.RUNNING
        is_paused = self._status == ProgressStatus.PAUSED
        is_failed = self._status == ProgressStatus.FAILED
        is_terminal = self._status in (
            ProgressStatus.COMPLETED,
            ProgressStatus.FAILED,
            ProgressStatus.CANCELLED
        )

        # 暂停按钮：运行中显示
        self._pause_btn.setVisible(is_running)

        # 恢复按钮：暂停时显示
        self._resume_btn.setVisible(is_paused)

        # 取消按钮：非终止状态显示
        self._cancel_btn.setVisible(not is_terminal)

        # 重试按钮：失败时显示
        self._retry_btn.setVisible(is_failed)

    def _update_elapsed_time(self) -> None:
        """更新已用时间"""
        if self._start_time:
            elapsed = (datetime.now() - self._start_time).total_seconds()
            self.set_elapsed_time(int(elapsed))

    # -------------------------------------------------------------------------
    # 槽函数
    # -------------------------------------------------------------------------

    def _on_pause_clicked(self) -> None:
        """暂停按钮点击"""
        self.pause_clicked.emit(self._task_id)

    def _on_resume_clicked(self) -> None:
        """恢复按钮点击"""
        self.resume_clicked.emit(self._task_id)

    def _on_cancel_clicked(self) -> None:
        """取消按钮点击"""
        self.cancel_clicked.emit(self._task_id)

    def _on_retry_clicked(self) -> None:
        """重试按钮点击"""
        self.retry_clicked.emit(self._task_id)
