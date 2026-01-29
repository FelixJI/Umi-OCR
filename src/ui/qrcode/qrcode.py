#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 二维码界面

Author: Umi-OCR Team
Date: 2026-01-27
"""

import os
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLabel,
    QComboBox,
    QPushButton,
    QFileDialog,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QColorDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QSizePolicy,
    QSpinBox,
    QMenu,
    QApplication,
)
from PySide6.QtCore import Qt, QMimeData, QUrl, QTimer, QSize
from PySide6.QtGui import (
    QPixmap,
    QDragEnterEvent,
    QDropEvent,
    QImage,
    QPainter,
    QColor,
    QClipboard,
    QDesktopServices,
    QIcon,
    QGuiApplication,
)

from src.utils.logger import get_logger

logger = get_logger()


class PreviewWidget(QWidget):
    """
    图片预览组件
    支持拖拽、粘贴、点击复制、保存
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumWidth(300)
        
        # 内部状态
        self._pixmap: Optional[QPixmap] = None
        self._image_path: Optional[str] = None
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 图片显示区域
        self.image_label = QLabel("拖入图片 / 粘贴图片 / 点击选择")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #cccccc;
                border-radius: 5px;
                background-color: #f9f9f9;
                color: #888888;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #aaaaaa;
                background-color: #f0f0f0;
            }
        """)
        self.image_label.setCursor(Qt.CursorShape.PointingHandCursor)
        # 启用鼠标点击事件
        self.image_label.mousePressEvent = self._on_image_click
        layout.addWidget(self.image_label, 1)

        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.btn_copy = QPushButton("复制")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self.copy_image)
        btn_layout.addWidget(self.btn_copy)
        
        self.btn_save = QPushButton("保存")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_image)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)
        
        # 浮窗提示 (Overlay)
        self.tip_label = QLabel("", self)
        self.tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tip_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: white;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 13px;
        """)
        self.tip_label.hide()
        self.tip_timer = QTimer(self)
        self.tip_timer.setSingleShot(True)
        self.tip_timer.timeout.connect(self._hide_tip)

    def set_pixmap(self, pixmap: QPixmap, path: Optional[str] = None):
        """设置显示的图片"""
        self._pixmap = pixmap
        self._image_path = path
        if pixmap:
            # 缩放图片以适应标签
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setText("")  # 清除文字
            self.image_label.setStyleSheet("border: 1px solid #ddd; background-color: #fff;")
        else:
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("拖入图片 / 粘贴图片 / 点击选择")
            self.image_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed #cccccc;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                    color: #888888;
                }
            """)

    def get_pixmap(self) -> Optional[QPixmap]:
        return self._pixmap

    def resizeEvent(self, event):
        """窗口大小改变时重新缩放图片"""
        if self._pixmap:
            self.set_pixmap(self._pixmap, self._image_path)
        super().resizeEvent(event)
        
        # 调整提示框位置
        if self.tip_label.isVisible():
            self._center_tip()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if self._is_image_file(file_path):
                    self.load_image_file(file_path)
                    
        elif mime_data.hasImage():
            image = mime_data.imageData()
            if isinstance(image, QImage):
                pixmap = QPixmap.fromImage(image)
                self.set_pixmap(pixmap)
                # 触发外部识别
                if hasattr(self.parent(), "on_pixmap_loaded"):
                    self.parent().on_pixmap_loaded(pixmap)
                elif hasattr(self.parent().parent(), "on_pixmap_loaded"):
                     self.parent().parent().on_pixmap_loaded(pixmap)

    def _is_image_file(self, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']

    def load_image_file(self, path: str):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.set_pixmap(pixmap, path)
            # 发送信号给外部使用
            if hasattr(self.parent(), "on_image_loaded"):
                self.parent().on_image_loaded(path)
            elif hasattr(self.parent().parent(), "on_image_loaded"): # QRCodeView
                 self.parent().parent().on_image_loaded(path)

    def _on_image_click(self, event):
        """点击图片：如果有图片则复制，否则弹出选择框"""
        if self._pixmap:
            self.copy_image()
        else:
            self._open_file_dialog()

    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*.*)",
        )
        if file_path:
            self.load_image_file(file_path)

    def copy_image(self):
        if self._pixmap:
            clipboard = QGuiApplication.clipboard()
            clipboard.setPixmap(self._pixmap)
            self.show_tip("复制成功")

    def save_image(self):
        if not self._pixmap:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存图片",
            "qrcode.png",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        
        if file_path:
            self._pixmap.save(file_path)
            self.show_tip("保存成功")

    def show_tip(self, text: str):
        self.tip_label.setText(text)
        self.tip_label.adjustSize()
        self._center_tip()
        self.tip_label.show()
        self.tip_label.raise_()
        self.tip_timer.start(2000)  # 2秒后消失

    def _hide_tip(self):
        self.tip_label.hide()
        
    def _center_tip(self):
        x = (self.width() - self.tip_label.width()) // 2
        y = (self.height() - self.tip_label.height()) // 2 + 50
        self.tip_label.move(x, y)


class QRCodeView(QWidget):
    """
    二维码界面
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化控制器
        try:
            from src.controllers.qrcode_controller import QrcodeController
            self._controller = QrcodeController()
        except ModuleNotFoundError as e:
            logger.warning(f"二维码控制器加载失败: {e}")
            self._controller = None
        except ImportError as e:
            # Fallback for relative import if running directly
            try:
                from controllers.qrcode_controller import QrcodeController
                self._controller = QrcodeController()
            except Exception:
                self._controller = None

        # 状态记录
        self._last_scan_pixmap = None
        self._last_gen_pixmap = None
        self._last_gen_path = None

        self._setup_ui()
        self._connect_signals()
        
        # 加载历史记录
        if self._controller:
            self._update_history_list()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)

        # --- 左侧：图片预览 ---
        self.preview_widget = PreviewWidget(self)
        main_layout.addWidget(self.preview_widget, 4)  # 占40%

        # --- 右侧：功能标签页 ---
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tabs, 6)  # 占60%

        # Tab 1: 识别
        self.tab_scan = QWidget()
        self._setup_scan_tab()
        self.tabs.addTab(self.tab_scan, "识别")

        # Tab 2: 生成
        self.tab_gen = QWidget()
        self._setup_gen_tab()
        self.tabs.addTab(self.tab_gen, "生成")

        # Tab 3: 历史记录
        self.tab_history = QWidget()
        self._setup_history_tab()
        self.tabs.addTab(self.tab_history, "历史记录")

    def _setup_scan_tab(self):
        layout = QVBoxLayout(self.tab_scan)
        
        # 结果显示
        layout.addWidget(QLabel("识别结果:"))
        self.scan_text = QTextEdit()
        self.scan_text.setPlaceholderText("等待识别...")
        layout.addWidget(self.scan_text)
        
        # 元数据
        self.scan_meta_label = QLabel("类型: -")
        self.scan_meta_label.setStyleSheet("color: #666;")
        layout.addWidget(self.scan_meta_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        btn_copy = QPushButton("复制文本")
        btn_copy.clicked.connect(self._copy_scan_text)
        btn_layout.addWidget(btn_copy)
        
        btn_open = QPushButton("打开链接/搜索")
        btn_open.clicked.connect(self._open_scan_link)
        btn_layout.addWidget(btn_open)
        
        layout.addLayout(btn_layout)

    def _setup_gen_tab(self):
        layout = QVBoxLayout(self.tab_gen)
        
        # 1. 码型
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("码型:"))
        self.combo_type = QComboBox()
        self.combo_type.addItems([
            "QR Code", "CODE 128", "CODE 39", "EAN 13", "EAN 8", 
            "UPC A", "UPC E", "Data Matrix", "PDF 417", "Aztec"
        ])
        row1.addWidget(self.combo_type)
        row1.addStretch()
        layout.addLayout(row1)
        
        # 2. 纠错 & 尺寸
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("纠错:"))
        self.combo_correction = QComboBox()
        self.combo_correction.addItems(["L (7%)", "M (15%)", "Q (25%)", "H (30%)"])
        self.combo_correction.setCurrentIndex(1)
        row2.addWidget(self.combo_correction)
        
        row2.addSpacing(20)
        row2.addWidget(QLabel("尺寸:"))
        self.spin_size = QSpinBox()
        self.spin_size.setRange(100, 2000)
        self.spin_size.setValue(300)
        self.spin_size.setSingleStep(50)
        row2.addWidget(self.spin_size)
        row2.addStretch()
        layout.addLayout(row2)
        
        # 3. 颜色设置
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("前景色:"))
        self.btn_color_fill = QPushButton()
        self.btn_color_fill.setFixedSize(24, 24)
        self.btn_color_fill.setStyleSheet("background-color: black; border: 1px solid #ccc;")
        self.btn_color_fill.clicked.connect(lambda: self._pick_color(self.btn_color_fill))
        row3.addWidget(self.btn_color_fill)
        
        row3.addSpacing(20)
        row3.addWidget(QLabel("背景色:"))
        self.btn_color_back = QPushButton()
        self.btn_color_back.setFixedSize(24, 24)
        self.btn_color_back.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        self.btn_color_back.clicked.connect(lambda: self._pick_color(self.btn_color_back))
        row3.addWidget(self.btn_color_back)
        row3.addStretch()
        layout.addLayout(row3)
        
        # 4. 输入内容
        layout.addWidget(QLabel("内容:"))
        self.gen_input = QTextEdit()
        self.gen_input.setPlaceholderText("输入要生成的内容...")
        layout.addWidget(self.gen_input)
        
        # 5. 生成按钮
        btn_gen = QPushButton("生成二维码")
        btn_gen.setStyleSheet("background-color: #0078d7; color: white; padding: 8px; font-weight: bold;")
        btn_gen.clicked.connect(self._on_generate)
        layout.addWidget(btn_gen)

    def _setup_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self._on_history_item_clicked)
        layout.addWidget(self.history_list)
        
        btn_layout = QHBoxLayout()
        btn_del = QPushButton("删除选中")
        btn_del.clicked.connect(self._delete_history)
        btn_layout.addWidget(btn_del)
        
        btn_clear = QPushButton("清空所有")
        btn_clear.clicked.connect(self._clear_history)
        btn_layout.addWidget(btn_clear)
        
        layout.addLayout(btn_layout)

    def _connect_signals(self):
        if self._controller:
            self._controller.scan_completed.connect(self._on_scan_completed)
            self._controller.scan_failed.connect(self._on_scan_failed)
            self._controller.generate_completed.connect(self._on_generate_completed)
            self._controller.generate_failed.connect(self._on_generate_failed)
            self._controller.history_changed.connect(self._update_history_list)

    # --- 交互逻辑 ---

    def on_image_loaded(self, path: str):
        """PreviewWidget 加载图片后的回调"""
        # 保存到识别记录
        self._last_scan_pixmap = QPixmap(path)
        
        # 自动切换到识别标签
        self.tabs.setCurrentWidget(self.tab_scan)
        if self._controller:
            self._controller.scan_qr_code(path)

    def on_pixmap_loaded(self, pixmap: QPixmap):
        """PreviewWidget 加载Pixmap后的回调"""
        # 保存到识别记录
        self._last_scan_pixmap = pixmap

        self.tabs.setCurrentWidget(self.tab_scan)
        if self._controller:
            self._controller.scan_pixmap(pixmap)

    def _on_tab_changed(self, index):
        """标签页切换联动"""
        current_widget = self.tabs.currentWidget()
        
        if current_widget == self.tab_scan:
            # 切换到识别页：恢复识别图片
            if self._last_scan_pixmap:
                self.preview_widget.set_pixmap(self._last_scan_pixmap)
            else:
                self.preview_widget.set_pixmap(None)
                
        elif current_widget == self.tab_gen:
            # 切换到生成页：恢复生成图片
            if self._last_gen_pixmap:
                self.preview_widget.set_pixmap(self._last_gen_pixmap, self._last_gen_path)
            else:
                self.preview_widget.set_pixmap(None)
                
        elif current_widget == self.tab_history:
             pass

    # --- 扫描相关 ---

    def _on_scan_completed(self, results):
        if not results:
            self.scan_text.setText("未识别到二维码")
            self.scan_meta_label.setText("类型: -")
            return

        # 取第一个结果
        res = results[0]
        self.scan_text.setText(res.data)
        self.scan_meta_label.setText(f"类型: {res.type}")
        
        # 切换到识别页
        self.tabs.setCurrentWidget(self.tab_scan)

    def _on_scan_failed(self, error):
        self.scan_text.setText(f"识别失败: {error}")

    def _copy_scan_text(self):
        text = self.scan_text.toPlainText()
        if text:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(text)
            self.preview_widget.show_tip("文本已复制")

    def _open_scan_link(self):
        text = self.scan_text.toPlainText().strip()
        if text:
            if not (text.startswith("http://") or text.startswith("https://")):
                # 如果不是网址，则搜索
                url = QUrl(f"https://www.google.com/search?q={text}")
            else:
                url = QUrl(text)
            QDesktopServices.openUrl(url)

    # --- 生成相关 ---

    def _pick_color(self, btn: QPushButton):
        # 获取当前颜色
        style = btn.styleSheet()
        current_color = "black"
        if "background-color:" in style:
            current_color = style.split("background-color:")[1].split(";")[0].strip()
            
        color = QColorDialog.getColor(QColor(current_color), self, "选择颜色")
        if color.isValid():
            btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #ccc;")

    def _get_color_from_btn(self, btn: QPushButton) -> str:
        style = btn.styleSheet()
        if "background-color:" in style:
            return style.split("background-color:")[1].split(";")[0].strip()
        return "black"

    def _on_generate(self):
        data = self.gen_input.toPlainText()
        if not data:
            self.preview_widget.show_tip("请输入内容")
            return

        # 获取参数
        code_type_map = {
            "QR Code": "QR_CODE", "CODE 128": "CODE_128", "CODE 39": "CODE_39",
            "EAN 13": "EAN_13", "EAN 8": "EAN_8", "UPC A": "UPCE_A",
            "UPC E": "UPCE_E", "Data Matrix": "DATA_MATRIX", "PDF 417": "PDF_417", "Aztec": "AZTEC"
        }
        code_type = code_type_map.get(self.combo_type.currentText(), "QR_CODE")
        
        correction_map = {"L (7%)": "L", "M (15%)": "M", "Q (25%)": "Q", "H (30%)": "H"}
        correction = correction_map.get(self.combo_correction.currentText(), "M")
        
        size = self.spin_size.value()
        fill_color = self._get_color_from_btn(self.btn_color_fill)
        back_color = self._get_color_from_btn(self.btn_color_back)

        if self._controller:
            self._controller.generate_qr_code(
                data, 
                code_type=code_type, 
                correction=correction, 
                size=size,
                fill_color=fill_color,
                back_color=back_color
            )

    def _on_generate_completed(self, path: str):
        self.preview_widget.show_tip("生成成功")
        
        # 加载并显示图片，但不触发扫描
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self._last_gen_pixmap = pixmap
            self._last_gen_path = path
            
            # 如果当前在生成页，直接显示
            if self.tabs.currentWidget() == self.tab_gen:
                self.preview_widget.set_pixmap(pixmap, path)

    def _on_generate_failed(self, error):
        self.preview_widget.show_tip(f"生成失败: {error}")

    # --- 历史记录相关 ---

    def _update_history_list(self):
        if not self._controller:
            return
            
        history = self._controller.get_history()
        self.history_list.clear()
        
        for idx, item in enumerate(history):
            # 格式: [类型] 摘要... 时间
            import datetime
            time_str = datetime.datetime.fromtimestamp(item['timestamp']).strftime("%Y-%m-%d %H:%M")
            data_preview = item['data'][:30].replace("\n", " ") + ("..." if len(item['data']) > 30 else "")
            
            type_text = "生成" if item['type'] == 'generate' else "识别"
            display_text = f"[{type_text}] {data_preview}\n{time_str}"
            
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, idx)  # 存储索引
            self.history_list.addItem(list_item)

    def _on_history_item_clicked(self, item):
        idx = item.data(Qt.UserRole)
        history = self._controller.get_history()
        if 0 <= idx < len(history):
            record = history[idx]
            
            # 如果是生成记录，尝试重新生成预览
            # 这里的逻辑是：如果历史记录里有文件路径最好，但目前只有数据。
            # 简单起见，我们把数据填回“生成”页，并模拟点击生成（或者只生成不保存？）
            # 或者，更简单：如果是识别记录，就把文本填到识别页；如果是生成记录，填到生成页。
            # 用户需求：“左侧显示历史记录中选中的条目的预览”。这意味着必须要在左侧显示图片。
            
            # 方案：调用 generate 但不保存文件？或者临时文件？
            # 由于 generate_qr_code 是异步且保存文件的，我们可以直接调用它，覆盖当前预览。
            # 为了避免污染“最近生成”的文件，我们可以不做特殊处理，就当是用户重新生成了一次。
            
            if record['type'] == 'generate':
                self.tabs.setCurrentWidget(self.tab_gen)
                self.gen_input.setText(record['data'])
                # 自动触发生成以便预览
                self._on_generate()
            else:
                self.tabs.setCurrentWidget(self.tab_scan)
                self.scan_text.setText(record['data'])
                self.scan_meta_label.setText("类型: 历史记录")
                # 扫描记录可能没有原图了，左侧清空或显示默认
                self.preview_widget.set_pixmap(None)
                self.preview_widget.show_tip("历史扫描记录，无原图")

    def _delete_history(self):
        row = self.history_list.currentRow()
        if row >= 0 and self._controller:
            # 获取实际索引（因为列表可能是倒序显示的，但这里我们是按顺序添加的）
            item = self.history_list.item(row)
            idx = item.data(Qt.UserRole)
            self._controller.delete_history(idx)

    def _clear_history(self):
        if self._controller:
            self._controller.clear_history()

    # --- 全局粘贴 ---
    def keyPressEvent(self, event):
        if event.matches(Qt.Key.Paste):
            clipboard = QGuiApplication.clipboard()
            mime_data = clipboard.mimeData()
            if mime_data.hasImage():
                pixmap = QPixmap.fromImage(mime_data.imageData())
                self.preview_widget.set_pixmap(pixmap)
                self.on_pixmap_loaded(pixmap)
            elif mime_data.hasUrls():
                path = mime_data.urls()[0].toLocalFile()
                self.preview_widget.load_image_file(path)
        super().keyPressEvent(event)
