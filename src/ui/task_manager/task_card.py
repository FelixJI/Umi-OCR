# src/ui/task_manager/task_card.py

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QPushButton, QTreeWidget, QTreeWidgetItem, QWidget
)
from PySide6.QtCore import Qt, Signal

from services.task.task_model import TaskGroup, TaskStatus

class TaskGroupCard(QFrame):
    """
    任务组卡片
    
    显示: 标题、进度条、状态、操作按钮
    可展开: 显示子任务列表 (QTreeWidget)
    """
    
    pause_clicked = Signal(str)   # group_id
    resume_clicked = Signal(str)
    cancel_clicked = Signal(str)
    retry_clicked = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.group_id = None
        self._is_expanded = False
        
        self._init_ui()
        
    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # 顶部：标题 + 状态 + 按钮
        top_layout = QHBoxLayout()
        
        # 展开/收起按钮
        self.btn_expand = QPushButton("▼")
        self.btn_expand.setFixedSize(24, 24)
        self.btn_expand.setCheckable(True)
        self.btn_expand.clicked.connect(self._toggle_expand)
        top_layout.addWidget(self.btn_expand)
        
        # 标题
        self.lbl_title = QLabel("任务组标题")
        self.lbl_title.setStyleSheet("font-weight: bold;")
        top_layout.addWidget(self.lbl_title)
        
        top_layout.addStretch()
        
        # 状态
        self.lbl_status = QLabel("等待中")
        top_layout.addWidget(self.lbl_status)
        
        # 按钮
        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setToolTip("暂停")
        self.btn_pause.clicked.connect(lambda: self.pause_clicked.emit(self.group_id))
        top_layout.addWidget(self.btn_pause)
        
        self.btn_resume = QPushButton("▶")
        self.btn_resume.setToolTip("恢复")
        self.btn_resume.clicked.connect(lambda: self.resume_clicked.emit(self.group_id))
        self.btn_resume.hide() # 初始隐藏
        top_layout.addWidget(self.btn_resume)
        
        self.btn_cancel = QPushButton("✖")
        self.btn_cancel.setToolTip("取消")
        self.btn_cancel.clicked.connect(lambda: self.cancel_clicked.emit(self.group_id))
        top_layout.addWidget(self.btn_cancel)
        
        self.layout.addLayout(top_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)
        
        # 详情列表 (初始隐藏)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["任务", "状态", "进度"])
        self.tree_widget.hide()
        self.layout.addWidget(self.tree_widget)
        
    def set_group(self, group: TaskGroup):
        """设置任务组数据"""
        self.group_id = group.id
        self.lbl_title.setText(group.title)
        self.update_status(group.status)
        self.update_progress(group.progress)
        
        # 更新子任务列表
        # 这里为了性能，可以只在展开时刷新
        if self._is_expanded:
            self._refresh_task_list(group)
            
    def update_progress(self, progress: float):
        """更新进度 (0.0 ~ 1.0)"""
        self.progress_bar.setValue(int(progress * 100))
        
    def update_status(self, status: TaskStatus):
        """更新状态显示和按钮可见性"""
        status_text_map = {
            TaskStatus.PENDING: "等待中",
            TaskStatus.RUNNING: "执行中",
            TaskStatus.PAUSED: "已暂停",
            TaskStatus.COMPLETED: "已完成",
            TaskStatus.FAILED: "失败",
            TaskStatus.CANCELLED: "已取消"
        }
        self.lbl_status.setText(status_text_map.get(status, str(status)))
        
        if status == TaskStatus.RUNNING or status == TaskStatus.PENDING:
            self.btn_pause.show()
            self.btn_resume.hide()
        elif status == TaskStatus.PAUSED:
            self.btn_pause.hide()
            self.btn_resume.show()
        else:
            # 终态
            self.btn_pause.hide()
            self.btn_resume.hide()
            self.btn_cancel.setEnabled(False)

    def _toggle_expand(self, checked: bool):
        self._is_expanded = checked
        if checked:
            self.tree_widget.show()
            self.btn_expand.setText("▲")
            # 触发刷新列表请求（可以在 controller 处理，或者这里直接传入 group）
        else:
            self.tree_widget.hide()
            self.btn_expand.setText("▼")
            
    def _refresh_task_list(self, group: TaskGroup):
        """刷新子任务列表"""
        self.tree_widget.clear()
        
        def add_items(parent_item, children):
            for child in children:
                if isinstance(child, TaskGroup):
                    item = QTreeWidgetItem(parent_item)
                    item.setText(0, child.title)
                    item.setText(1, child.status.value)
                    item.setText(2, f"{child.progress:.0%}")
                    add_items(item, child.children)
                else: # Task
                    item = QTreeWidgetItem(parent_item)
                    name = str(child.input_data.get("path", "任务")) # 简化显示
                    if "image_path" in child.input_data:
                        name = Path(child.input_data["image_path"]).name
                    elif "pdf_path" in child.input_data:
                        name = f"Page {child.input_data.get('page_num', '?')}"
                        
                    item.setText(0, name)
                    item.setText(1, child.status.value)
                    item.setText(2, f"{child.progress:.0%}")

        # Top level items
        # 这里的 group 是 TaskGroup 对象，可能包含 Task 或 TaskGroup
        # 我们只显示顶层 children
        # 注意：这里需要递归遍历吗？ TreeWidget 支持层级
        
        # 简单实现：只显示一层
        # 实际应该递归添加
        pass # 需要完整 group 数据才能刷新，建议由 controller 调用
