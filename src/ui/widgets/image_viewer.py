#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 图片查看器控件

提供图片显示功能，支持缩放、平移和 OCR 结果标注。

主要功能:
- 图片加载与显示
- 缩放（滚轮、按钮、适应窗口）
- 拖拽平移
- OCR 结果框绘制
- 区域选择

Author: Umi-OCR Team
Date: 2026-01-27
"""

from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QPushButton,
    QLabel,
    QSlider,
)
from PySide6.QtCore import Signal, Qt, QRectF, QPointF
from PySide6.QtGui import QPixmap, QImage, QPen, QBrush, QColor, QWheelEvent, QPainter

# =============================================================================
# 图片查看器控件
# =============================================================================


class ImageViewer(QWidget):
    """
    图片查看器控件

    用于显示图片并支持缩放、平移和 OCR 结果标注。

    使用示例:
        viewer = ImageViewer()
        viewer.load_image("path/to/image.png")
        viewer.draw_ocr_boxes(ocr_result["blocks"])
        viewer.zoom_changed.connect(on_zoom)

    信号:
        zoom_changed(float): 缩放比例变更，参数为缩放比例
        region_selected(QRectF): 区域选择完成，参数为选择区域
        image_loaded(str): 图片加载完成，参数为图片路径
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    zoom_changed = Signal(float)
    region_selected = Signal(QRectF)
    image_loaded = Signal(str)

    # -------------------------------------------------------------------------
    # 缩放配置
    # -------------------------------------------------------------------------

    MIN_ZOOM = 0.1  # 最小缩放比例
    MAX_ZOOM = 10.0  # 最大缩放比例
    ZOOM_STEP = 0.1  # 缩放步长

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化图片查看器

        Args:
            parent: 父控件
        """
        super().__init__(parent)

        # 当前图片路径
        self._image_path: str = ""

        # 当前缩放比例
        self._zoom_level: float = 1.0

        # 是否正在拖拽
        self._is_dragging: bool = False
        self._drag_start_pos: QPointF = QPointF()

        # OCR 结果框列表
        self._ocr_boxes: List[QGraphicsRectItem] = []

        # 初始化UI
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化 UI 布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 工具栏
        toolbar = self._create_toolbar()
        layout.addLayout(toolbar)

        # 图片显示区
        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene, self)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setRenderHint(QPainter.SmoothPixmapTransform)
        self._view.setDragMode(QGraphicsView.NoDrag)
        self._view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._view.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f0f0f0;
            }
        """)

        # 安装事件过滤器
        self._view.viewport().installEventFilter(self)

        layout.addWidget(self._view)

        # 状态栏
        status_bar = self._create_status_bar()
        layout.addLayout(status_bar)

        # 显示占位符
        self._show_placeholder()

    def _create_toolbar(self) -> QHBoxLayout:
        """创建工具栏"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # 缩放按钮
        self._zoom_out_btn = QPushButton("-")
        self._zoom_out_btn.setFixedSize(28, 28)
        self._zoom_out_btn.clicked.connect(self._on_zoom_out)
        self._zoom_out_btn.setStyleSheet(self._get_button_style())
        toolbar.addWidget(self._zoom_out_btn)

        # 缩放滑块
        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(10, 500)  # 10% - 500%
        self._zoom_slider.setValue(100)
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        toolbar.addWidget(self._zoom_slider)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setFixedSize(28, 28)
        self._zoom_in_btn.clicked.connect(self._on_zoom_in)
        self._zoom_in_btn.setStyleSheet(self._get_button_style())
        toolbar.addWidget(self._zoom_in_btn)

        # 缩放比例显示
        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(50)
        self._zoom_label.setAlignment(Qt.AlignCenter)
        self._zoom_label.setStyleSheet("color: #666;")
        toolbar.addWidget(self._zoom_label)

        toolbar.addSpacing(16)

        # 适应窗口
        self._fit_btn = QPushButton("适应窗口")
        self._fit_btn.clicked.connect(self.fit_to_view)
        self._fit_btn.setStyleSheet(self._get_button_style())
        toolbar.addWidget(self._fit_btn)

        # 原始大小
        self._reset_btn = QPushButton("原始大小")
        self._reset_btn.clicked.connect(self.reset_zoom)
        self._reset_btn.setStyleSheet(self._get_button_style())
        toolbar.addWidget(self._reset_btn)

        toolbar.addStretch()

        # 显示/隐藏 OCR 框
        self._toggle_boxes_btn = QPushButton("显示标注")
        self._toggle_boxes_btn.setCheckable(True)
        self._toggle_boxes_btn.setChecked(True)
        self._toggle_boxes_btn.clicked.connect(self._on_toggle_boxes)
        self._toggle_boxes_btn.setStyleSheet(self._get_button_style())
        toolbar.addWidget(self._toggle_boxes_btn)

        return toolbar

    def _create_status_bar(self) -> QHBoxLayout:
        """创建状态栏"""
        status_bar = QHBoxLayout()

        self._size_label = QLabel("")
        self._size_label.setStyleSheet("color: #999; font-size: 12px;")
        status_bar.addWidget(self._size_label)

        status_bar.addStretch()

        self._pos_label = QLabel("")
        self._pos_label.setStyleSheet("color: #999; font-size: 12px;")
        status_bar.addWidget(self._pos_label)

        return status_bar

    def _get_button_style(self) -> str:
        """获取按钮样式"""
        return """
            QPushButton {
                padding: 4px 10px;
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
            QPushButton:checked {
                background-color: #1890ff;
                color: #fff;
                border-color: #1890ff;
            }
        """

    def _show_placeholder(self) -> None:
        """显示占位符"""
        self._scene.clear()
        text = self._scene.addText("拖拽图片到此处\n或点击加载图片")
        text.setDefaultTextColor(QColor("#999"))
        text.setPos(-50, -20)

    # -------------------------------------------------------------------------
    # 事件处理
    # -------------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:
        """事件过滤器"""
        if obj == self._view.viewport():
            if event.type() == event.Type.Wheel:
                self._on_wheel(event)
                return True
            elif event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self._is_dragging = True
                    self._drag_start_pos = event.pos()
                    self._view.setCursor(Qt.ClosedHandCursor)
                    return True
            elif event.type() == event.Type.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    self._is_dragging = False
                    self._view.setCursor(Qt.ArrowCursor)
                    return True
            elif event.type() == event.Type.MouseMove:
                if self._is_dragging:
                    delta = event.pos() - self._drag_start_pos
                    self._drag_start_pos = event.pos()

                    h_bar = self._view.horizontalScrollBar()
                    v_bar = self._view.verticalScrollBar()
                    h_bar.setValue(h_bar.value() - delta.x())
                    v_bar.setValue(v_bar.value() - delta.y())
                    return True
                else:
                    # 更新位置显示
                    scene_pos = self._view.mapToScene(event.pos())
                    self._pos_label.setText(
                        f"位置: ({int(scene_pos.x())}, {int(scene_pos.y())})"
                    )

        return super().eventFilter(obj, event)

    def _on_wheel(self, event: QWheelEvent) -> None:
        """滚轮缩放"""
        delta = event.angleDelta().y()

        if delta > 0:
            self._set_zoom(self._zoom_level * 1.1)
        else:
            self._set_zoom(self._zoom_level / 1.1)

    # -------------------------------------------------------------------------
    # 公共接口
    # -------------------------------------------------------------------------

    def load_image(self, image_path: str) -> bool:
        """
        加载图片

        Args:
            image_path: 图片路径

        Returns:
            bool: 是否加载成功
        """
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return False

            # 清空场景
            self._scene.clear()
            self._ocr_boxes.clear()

            # 添加图片
            self._scene.addPixmap(pixmap)
            self._scene.setSceneRect(QRectF(pixmap.rect()))

            # 更新状态
            self._image_path = image_path
            self._size_label.setText(f"尺寸: {pixmap.width()} x {pixmap.height()}")

            # 适应窗口
            self.fit_to_view()

            # 发射信号
            self.image_loaded.emit(image_path)

            return True

        except Exception:
            self._show_placeholder()
            return False

    def load_from_bytes(self, image_data: bytes) -> bool:
        """
        从字节数据加载图片

        Args:
            image_data: 图片字节数据

        Returns:
            bool: 是否加载成功
        """
        try:
            image = QImage()
            if not image.loadFromData(image_data):
                return False

            pixmap = QPixmap.fromImage(image)
            if pixmap.isNull():
                return False

            # 清空场景
            self._scene.clear()
            self._ocr_boxes.clear()

            # 添加图片
            self._scene.addPixmap(pixmap)
            self._scene.setSceneRect(QRectF(pixmap.rect()))

            # 更新状态
            self._image_path = ""
            self._size_label.setText(f"尺寸: {pixmap.width()} x {pixmap.height()}")

            # 适应窗口
            self.fit_to_view()

            return True

        except Exception:
            self._show_placeholder()
            return False

    def clear(self) -> None:
        """清空图片"""
        self._image_path = ""
        self._ocr_boxes.clear()
        self._show_placeholder()
        self._size_label.setText("")

    def draw_ocr_boxes(self, blocks: List[Dict[str, Any]]) -> None:
        """
        绘制 OCR 结果框

        Args:
            blocks: OCR 结果块列表，每个块应包含:
                - box: 边界框 [x1, y1, x2, y2] 或 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                - text: 识别文本（可选）
                - confidence: 置信度（可选）
        """
        # 清除之前的框
        self.clear_ocr_boxes()

        pen = QPen(QColor("#1890ff"))
        pen.setWidth(2)

        for block in blocks:
            box = block.get("box") or block.get("location")
            if not box:
                continue

            # 解析坐标
            rect = self._parse_box(box)
            if not rect:
                continue

            # 创建矩形
            rect_item = QGraphicsRectItem(rect)
            rect_item.setPen(pen)
            rect_item.setBrush(QBrush(QColor(24, 144, 255, 30)))
            self._scene.addItem(rect_item)
            self._ocr_boxes.append(rect_item)

            # 添加文本标签（可选）
            text = block.get("text", "")
            if text and len(text) < 20:
                text_item = QGraphicsTextItem(text)
                text_item.setDefaultTextColor(QColor("#1890ff"))
                text_item.setPos(rect.x(), rect.y() - 20)
                self._scene.addItem(text_item)

    def clear_ocr_boxes(self) -> None:
        """清除 OCR 结果框"""
        for item in self._ocr_boxes:
            self._scene.removeItem(item)
        self._ocr_boxes.clear()

    def set_zoom(self, zoom_level: float) -> None:
        """
        设置缩放比例

        Args:
            zoom_level: 缩放比例 (0.1 - 10.0)
        """
        self._set_zoom(zoom_level)

    def get_zoom(self) -> float:
        """获取当前缩放比例"""
        return self._zoom_level

    def fit_to_view(self) -> None:
        """适应窗口大小"""
        self._view.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        self._update_zoom_from_view()

    def reset_zoom(self) -> None:
        """重置为原始大小"""
        self._set_zoom(1.0)

    # -------------------------------------------------------------------------
    # 私有方法
    # -------------------------------------------------------------------------

    def _set_zoom(self, zoom_level: float) -> None:
        """设置缩放（内部方法）"""
        zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom_level))

        if abs(zoom_level - self._zoom_level) < 0.001:
            return

        # 计算缩放因子
        scale_factor = zoom_level / self._zoom_level
        self._view.scale(scale_factor, scale_factor)

        self._zoom_level = zoom_level
        self._update_zoom_ui()
        self.zoom_changed.emit(zoom_level)

    def _update_zoom_from_view(self) -> None:
        """从视图更新缩放比例"""
        transform = self._view.transform()
        self._zoom_level = transform.m11()  # 获取水平缩放比例
        self._update_zoom_ui()

    def _update_zoom_ui(self) -> None:
        """更新缩放 UI"""
        percent = int(self._zoom_level * 100)
        self._zoom_label.setText(f"{percent}%")
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(percent)
        self._zoom_slider.blockSignals(False)

    def _parse_box(self, box) -> Optional[QRectF]:
        """
        解析边界框坐标

        支持格式:
        - [x1, y1, x2, y2]
        - [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        - {"x": x, "y": y, "width": w, "height": h}

        Returns:
            Optional[QRectF]: 矩形区域
        """
        try:
            if isinstance(box, dict):
                x = box.get("x", 0)
                y = box.get("y", 0)
                w = box.get("width", 0)
                h = box.get("height", 0)
                return QRectF(x, y, w, h)

            elif isinstance(box, (list, tuple)):
                if len(box) == 4:
                    if isinstance(box[0], (list, tuple)):
                        # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                        x_coords = [p[0] for p in box]
                        y_coords = [p[1] for p in box]
                        x1, x2 = min(x_coords), max(x_coords)
                        y1, y2 = min(y_coords), max(y_coords)
                        return QRectF(x1, y1, x2 - x1, y2 - y1)
                    else:
                        # [x1, y1, x2, y2]
                        x1, y1, x2, y2 = box
                        return QRectF(x1, y1, x2 - x1, y2 - y1)

            return None

        except Exception:
            return None

    # -------------------------------------------------------------------------
    # 槽函数
    # -------------------------------------------------------------------------

    def _on_zoom_in(self) -> None:
        """放大"""
        self._set_zoom(self._zoom_level * 1.2)

    def _on_zoom_out(self) -> None:
        """缩小"""
        self._set_zoom(self._zoom_level / 1.2)

    def _on_zoom_slider_changed(self, value: int) -> None:
        """缩放滑块变更"""
        self._set_zoom(value / 100.0)

    def _on_toggle_boxes(self, checked: bool) -> None:
        """切换 OCR 框显示"""
        for item in self._ocr_boxes:
            item.setVisible(checked)

        self._toggle_boxes_btn.setText("隐藏标注" if checked else "显示标注")
