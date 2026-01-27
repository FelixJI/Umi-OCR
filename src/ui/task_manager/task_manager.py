# src/ui/task_manager/task_manager.py

import logging
from pathlib import Path
from typing import Dict

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QScrollArea
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, Slot

from services.task.task_manager import TaskManager
from services.task.task_model import TaskStatus, TaskGroup, CancelMode
from .task_card import TaskGroupCard

logger = logging.getLogger(__name__)

class TaskManagerView(QWidget):
    """
    任务管理器界面
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._task_manager = TaskManager.instance()
        self._cards: Dict[str, TaskGroupCard] = {} # group_id -> card
        
        self._load_ui()
        self._connect_signals()
        
        # 加载现有任务
        self._load_tasks()
        
    def _load_ui(self):
        try:
            ui_file = Path(__file__).parent / "task_manager.ui"
            loader = QUiLoader()
            self.ui = loader.load(str(ui_file), self)
            
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.ui)
            
            # Find widgets
            self.cards_layout = self.ui.findChild(QVBoxLayout, "verticalLayout_cards")
            
            self.btn_pause_all = self.ui.findChild(QPushButton, "btn_pause_all")
            self.btn_resume_all = self.ui.findChild(QPushButton, "btn_resume_all")
            self.btn_clear_completed = self.ui.findChild(QPushButton, "btn_clear_completed")
            
        except Exception as e:
            logger.error(f"加载任务管理器 UI 失败: {e}")

    def _connect_signals(self):
        # 按钮信号
        self.btn_pause_all.clicked.connect(self._on_pause_all)
        self.btn_resume_all.clicked.connect(self._on_resume_all)
        self.btn_clear_completed.clicked.connect(self._on_clear_completed)
        
        # 任务管理器信号
        self._task_manager.task_submitted.connect(self._on_task_submitted)
        self._task_manager.group_progress.connect(self._on_group_progress)
        self._task_manager.group_completed.connect(self._on_group_status_changed) # 完成也是状态改变
        self._task_manager.group_paused.connect(self._on_group_status_changed_wrapper)
        self._task_manager.group_cancelled.connect(self._on_group_status_changed)
        
    def _load_tasks(self):
        """加载当前所有任务组"""
        groups = self._task_manager.get_all_groups()
        for group in groups:
            self._add_card(group)
            
    def _add_card(self, group: TaskGroup):
        if group.id in self._cards:
            return
            
        card = TaskGroupCard()
        card.set_group(group)
        
        # 连接卡片信号
        card.pause_clicked.connect(self._task_manager.pause_group)
        card.resume_clicked.connect(self._task_manager.resume_group)
        card.cancel_clicked.connect(lambda gid: self._task_manager.cancel_group(gid, CancelMode.GRACEFUL))
        
        # 插入到布局顶部 (spacer 之前)
        self.cards_layout.insertWidget(0, card)
        self._cards[group.id] = card
        
    def _on_task_submitted(self, group_id: str):
        """新任务提交"""
        group = self._task_manager.get_group(group_id)
        if group:
            self._add_card(group)
            
    def _on_group_progress(self, group_id: str, progress: float):
        """任务组进度更新"""
        if group_id in self._cards:
            self._cards[group_id].update_progress(progress)
            
    def _on_group_status_changed(self, group_id: str):
        """任务组状态更新"""
        group = self._task_manager.get_group(group_id)
        if group and group_id in self._cards:
            self._cards[group_id].update_status(group.status)
            
    def _on_group_status_changed_wrapper(self, group_id: str, reason: str):
        """适配 group_paused 信号"""
        self._on_group_status_changed(group_id)

    def _on_pause_all(self):
        # 简单的全部暂停实现
        for gid in self._cards.keys():
            self._task_manager.pause_group(gid)
            
    def _on_resume_all(self):
        for gid in self._cards.keys():
            self._task_manager.resume_group(gid)
            
    def _on_clear_completed(self):
        """清空已完成/取消的卡片"""
        to_remove = []
        for gid, card in self._cards.items():
            group = self._task_manager.get_group(gid)
            if group and group.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                self.cards_layout.removeWidget(card)
                card.deleteLater()
                to_remove.append(gid)
                
        for gid in to_remove:
            del self._cards[gid]
