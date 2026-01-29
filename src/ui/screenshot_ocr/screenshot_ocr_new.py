#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 截图OCR界面 (新版)

左侧图片预览 + 右侧功能Tab布局。
包含识别设置、结果展示和历史记录。

Author: Umi-OCR Team
Date: 2026-01-29
"""

import datetime
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QTabWidget,
    QComboBox,
    QRadioButton,
    QButtonGroup,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QStackedWidget,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QPixmap, QColor, QIcon, QClipboard, QGuiApplication, QTextCharFormat, QBrush

from src.utils.logger import get_logger
from src.ui.widgets.image_viewer import ImageViewer
from src.services.ocr.engine_manager import get_engine_manager

logger = get_logger()

class PreviewContainer(QWidget):
    """
    预览容器
    
    无图时显示点击提示，有图时显示 ImageViewer。
    """
    
    clicked = Signal() # 无图时的点击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._has_image = False
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Page 0: 空状态 (点击截图)
        self.empty_page = QFrame()
        self.empty_page.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border: 2px dashed #cccccc;
                border-radius: 5px;
            }
            QFrame:hover {
                background-color: #f0f0f0;
                border-color: #aaaaaa;
            }
        """)
        self.empty_page.setCursor(Qt.PointingHandCursor)
        self.empty_page.mousePressEvent = lambda e: self.clicked.emit()
        
        empty_layout = QVBoxLayout(self.empty_page)
        label = QLabel("点击截图\n(快捷键: F1)")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 16px; font-weight: bold;")
        empty_layout.addWidget(label)
        
        self.stack.addWidget(self.empty_page)
        
        # Page 1: 图片查看器
        self.viewer = ImageViewer()
        self.stack.addWidget(self.viewer)

        # 默认显示空状态
        self.show_empty()
        
    def show_image(self, image_path: str, ocr_boxes: List[Dict] = None):
        """显示图片"""
        if self.viewer.load_image(image_path):
            self._has_image = True
            self.stack.setCurrentIndex(1)
            if ocr_boxes:
                self.viewer.draw_ocr_boxes(ocr_boxes)
        else:
            self.show_empty()
            
    def show_empty(self):
        """显示空状态"""
        self._has_image = False
        self.stack.setCurrentIndex(0)
        self.viewer.clear()


class ScreenshotOCRNewView(QWidget):
    """
    新版截图OCR界面
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化控制器
        try:
            from src.controllers.screenshot_controller import ScreenshotController
            self._controller = ScreenshotController.instance()
        except ModuleNotFoundError as e:
            logger.warning(f"截图控制器加载失败: {e}")
            self._controller = None
            
        # 内部状态
        self._history: List[Dict] = [] # 历史记录
        self._current_image_path: Optional[str] = None
        
        self._setup_ui()
        self._connect_signals()
        self._refresh_engines()
        
    def _setup_ui(self):
        # 设置背景色
        self.setStyleSheet("background-color: #ffffff;")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 分割器 (左: 预览, 右: 设置/结果)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # --- 左侧: 图片预览 ---
        self.preview_container = PreviewContainer()
        self.preview_container.clicked.connect(self._on_start_capture)
        splitter.addWidget(self.preview_container)
        
        # --- 右侧: 功能区 ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs)
        
        # Tab 1: 识别
        self.tab_scan = QWidget()
        self._setup_scan_tab()
        self.tabs.addTab(self.tab_scan, "识别")
        
        # Tab 2: 记录
        self.tab_history = QWidget()
        self._setup_history_tab()
        self.tabs.addTab(self.tab_history, "记录")
        
        splitter.addWidget(right_widget)
        
        # 设置初始比例 4:6
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        
    def _setup_scan_tab(self):
        layout = QVBoxLayout(self.tab_scan)
        layout.setSpacing(10)
        
        # 1. 设置区域 (Group Box)
        settings_group = QFrame()
        settings_group.setStyleSheet(".QFrame { background-color: #f5f5f5; border-radius: 5px; }")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        
        # 引擎选择
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("OCR 引擎:"))
        self.combo_engine = QComboBox()
        # 只有可用引擎，数据稍后加载
        row1.addWidget(self.combo_engine, 1)
        settings_layout.addLayout(row1)
        
        # 识别内容 (文字 / 表格)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("识别内容:"))
        self.radio_text = QRadioButton("文字")
        self.radio_text.setChecked(True)
        self.radio_table = QRadioButton("表格")
        
        self.bg_content = QButtonGroup(self)
        self.bg_content.addButton(self.radio_text)
        self.bg_content.addButton(self.radio_table)
        
        row2.addWidget(self.radio_text)
        row2.addWidget(self.radio_table)
        row2.addStretch()
        settings_layout.addLayout(row2)
        
        # 段落合并
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("段落处理:"))
        self.combo_paragraph = QComboBox()
        self.combo_paragraph.addItems(["保持原样", "合并成一段", "智能分段 (版面分析)"])
        self.combo_paragraph.setToolTip("智能分段会利用版面分析功能尝试还原段落结构")
        row3.addWidget(self.combo_paragraph, 1)
        settings_layout.addLayout(row3)
        
        layout.addWidget(settings_group)
        
        # 2. 结果编辑区
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("等待识别结果...")
        layout.addWidget(self.text_edit)
        
        # 3. 底部信息栏
        bottom_layout = QHBoxLayout()
        
        self.lbl_stats = QLabel("字符数: 0 | 置信度: 0%")
        self.lbl_stats.setStyleSheet("color: #666;")
        bottom_layout.addWidget(self.lbl_stats)
        
        bottom_layout.addStretch()
        
        self.btn_copy = QPushButton("复制")
        self.btn_copy.setIcon(QIcon.fromTheme("edit-copy"))
        self.btn_copy.clicked.connect(self._copy_result)
        bottom_layout.addWidget(self.btn_copy)
        
        layout.addLayout(bottom_layout)
        
    def _setup_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self._on_history_clicked)
        layout.addWidget(self.history_list)
        
        btn_clear = QPushButton("清空记录")
        btn_clear.clicked.connect(self._clear_history)
        layout.addWidget(btn_clear)
        
    def _connect_signals(self):
        if self._controller:
            self._controller.capture_started.connect(self._on_capture_started)
            self._controller.ocr_result_ready.connect(self._on_ocr_result)
            self._controller.ocr_failed.connect(self._on_ocr_failed)
            
    def _refresh_engines(self):
        """刷新可用引擎列表"""
        try:
            manager = get_engine_manager()
            engines = manager.get_available_engines()
            self.combo_engine.clear()
            for eng in engines:
                # 获取更友好的名称 (这里简化直接用 type)
                self.combo_engine.addItem(eng, eng)
                
            # 选中默认引擎
            current = manager.get_current_engine_type()
            if current:
                idx = self.combo_engine.findData(current)
                if idx >= 0:
                    self.combo_engine.setCurrentIndex(idx)
        except Exception as e:
            logger.error(f"刷新引擎列表失败: {e}", exc_info=True)
            self.combo_engine.addItem("无可用引擎")
            self.combo_engine.setEnabled(False)
                
    # --- 交互逻辑 ---
    
    def _on_start_capture(self):
        """触发截图"""
        if self._controller:
            # 应用设置
            self._apply_settings()
            self._controller.start_capture()
            
    def _apply_settings(self):
        """将当前UI设置应用到全局配置或本次任务"""
        # 注意：这里我们可能需要修改 EngineManager 的配置，或者传参给 controller
        # 目前 ScreenshotController 主要是触发截图，然后调用 EngineManager.recognize
        # 为了支持动态参数，我们需要一种方式将 UI 参数传递下去。
        
        # 切换引擎
        selected_engine = self.combo_engine.currentData()
        manager = get_engine_manager()
        if selected_engine and manager.get_current_engine_type() != selected_engine:
            manager.switch_engine(selected_engine)
            
        # 设置参数
        # 1. 识别内容 (文字/表格)
        use_table = self.radio_table.isChecked()
        
        # 2. 段落处理
        para_mode = self.combo_paragraph.currentIndex()
        use_structure = (para_mode == 2) # 智能分段 = 版面分析
        
        # 更新当前引擎配置
        if selected_engine:
            config = manager.get_engine_config(selected_engine)
            config['use_table'] = use_table
            config['use_structure'] = use_structure
            manager.set_engine_config(selected_engine, config)
            
        # 另外：合并成一段 是后处理逻辑，不是引擎参数。我们需要在收到结果后处理。
        self._merge_para_mode = para_mode
            
    def _on_capture_started(self):
        self.text_edit.setPlaceholderText("正在截图...")
        
    def _on_ocr_result(self, result: Dict):
        """处理 OCR 结果"""
        logger.info(f"收到 OCR 结果: {result.get('text', '')[:20]}...")
        
        # 1. 显示图片
        # 截图结果通常包含 image_path 或 pixmap
        # 这里假设 ScreenshotController 会保存临时文件并传回路径，或者我们可以访问最后一次截图
        # 根据现有 controller 逻辑，result 中应该包含相关信息
        
        # 注意：现有的 ScreenshotController 可能不直接返回图片路径。
        # 我们可能需要修改 controller 或者利用 recent_capture 机制。
        # 暂时假设 result 中包含 'image_path' (如果不包含，我们需要去 controller 找)
        
        # 检查 result 结构
        image_path = result.get('image_path')
        if not image_path and self._controller:
            # 尝试从 controller 获取最后一次截图路径 (如果有这个接口)
            pass
            
        if image_path:
            self._current_image_path = image_path
            self.preview_container.show_image(image_path, result.get('blocks', []))
        
        # 2. 处理文本 (支持高亮)
        blocks = result.get('blocks', [])
        full_text = ""
        
        # 清空文本框
        self.text_edit.clear()
        
        # 智能分段 / 合并处理
        if self._merge_para_mode == 1: # 合并成一段
            # 简单拼接，忽略换行
            texts = [b['text'] for b in blocks]
            full_text = "".join(texts)
            self._set_text_with_highlight(blocks, merge=True)
        else:
            # 保持原样 (智能分段已由引擎处理，体现在 blocks 结构中)
            full_text = result.get('text', "")
            self._set_text_with_highlight(blocks, merge=False)
            
        # 3. 更新统计
        confidence = result.get('confidence', 0) * 100
        count = len(full_text)
        self.lbl_stats.setText(f"字符数: {count} | 置信度: {confidence:.0f}%")
        
        # 4. 添加到历史
        self._add_to_history(result, image_path)
        
        # 切换到识别Tab
        self.tabs.setCurrentWidget(self.tab_scan)
        
    def _set_text_with_highlight(self, blocks: List[Dict], merge: bool = False):
        """
        设置文本并高亮低置信度字符
        
        Args:
            blocks: OCR 结果块
            merge: 是否合并为单行 (忽略块之间的换行)
        """
        cursor = self.text_edit.textCursor()
        cursor.beginEditBlock()
        
        fmt_normal = QTextCharFormat()
        
        fmt_low_conf = QTextCharFormat()
        fmt_low_conf.setBackground(QBrush(QColor(255, 255, 0, 80))) # 黄色背景
        
        LOW_CONF_THRESHOLD = 0.6
        
        for i, block in enumerate(blocks):
            text = block.get('text', '')
            # 这里的置信度通常是整个块的平均值。如果我们要字粒度高亮，需要 'chars' 字段。
            # PaddleOCR 通常不返回字粒度置信度，除非特定设置。
            # 这里先按块粒度高亮。
            
            conf = block.get('confidence', 1.0)
            fmt = fmt_low_conf if conf < LOW_CONF_THRESHOLD else fmt_normal
            
            cursor.setCharFormat(fmt)
            cursor.insertText(text)
            
            if not merge and i < len(blocks) - 1:
                cursor.setCharFormat(fmt_normal)
                cursor.insertText("\n")
                
        cursor.endEditBlock()
        
    def _on_ocr_failed(self, error: str):
        self.text_edit.setText(f"识别失败: {error}")
        self.preview_container.show_empty()
        
    def _copy_result(self):
        text = self.text_edit.toPlainText()
        if text:
            QGuiApplication.clipboard().setText(text)
            self.lbl_stats.setText(self.lbl_stats.text() + " (已复制)")
            
    # --- 历史记录 ---
    
    def _add_to_history(self, result: Dict, image_path: str):
        if not image_path:
            return
            
        item_data = {
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "text": result.get("text", "")[:50].replace("\n", " "),
            "full_result": result,
            "image_path": image_path
        }
        
        self._history.insert(0, item_data)
        if len(self._history) > 20: # 限制20条
            self._history.pop()
            
        self._refresh_history_list()
        
    def _refresh_history_list(self):
        self.history_list.clear()
        for idx, item in enumerate(self._history):
            display = f"[{item['timestamp']}] {item['text']}..."
            list_item = QListWidgetItem(display)
            list_item.setData(Qt.UserRole, idx)
            self.history_list.addItem(list_item)
            
    def _on_history_clicked(self, item):
        idx = item.data(Qt.UserRole)
        if 0 <= idx < len(self._history):
            record = self._history[idx]
            # 恢复状态
            self._on_ocr_result(record['full_result'])
            
    def _clear_history(self):
        self._history.clear()
        self.history_list.clear()
