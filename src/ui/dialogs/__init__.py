#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR OCR引擎安装向导对话框

引导用户安装OCR引擎依赖。

主要功能：
- 显示GPU检测结果
- 显示依赖状态
- 提供安装选项（CPU/GPU/跳过）
- 显示安装进度
- 支持取消安装

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QButtonGroup,
    QScrollArea,
    QWidget,
    QFrame,
    QTextEdit,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from src.utils.check_dependencies import (
    check_ocr_dependencies,
    OCRDependencyInfo,
    InstallOption,
    DependencyStatus,
)

from src.utils.dependency_installer import (
    get_installer,
    InstallConfig,
    InstallProgress,
)

logger = logging.getLogger(__name__)


# =============================================================================
# OCR引擎安装向导对话框
# =============================================================================


class OCREngineInstallDialog(QDialog):
    """
    OCR引擎安装向导对话框

    引导用户完成OCR引擎依赖的安装。
    """

    # 信号定义
    install_completed = Signal(bool)  # 安装完成 (成功/失败）
    skipped = Signal()  # 用户跳过安装

    def __init__(self, parent=None):
        """
        初始化对话框

        Args:
            parent: 父窗口
        """
        super().__init__(parent)

        self._dep_info: Optional[OCRDependencyInfo] = None
        self._selected_option: Optional[InstallOption] = None
        self._is_installing = False

        # 初始化UI
        self._init_ui()

        # 检测依赖
        self._check_dependencies()

    def _init_ui(self):
        """初始化UI"""
        # 对话框设置
        self.setWindowTitle("OCR引擎安装向导")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # 1. 标题部分
        title_layout = self._create_title_section()
        main_layout.addLayout(title_layout)

        # 2. 内容区域（可滚动）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        self._content_layout = QVBoxLayout(content_widget)
        self._content_layout.setSpacing(15)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # 3. 按钮区域
        button_layout = self._create_button_section()
        main_layout.addLayout(button_layout)

    def _create_title_section(self) -> QHBoxLayout:
        """创建标题部分"""
        layout = QHBoxLayout()

        # 图标
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        # TODO: 添加OCR图标
        # icon_label.setPixmap(
        #     QPixmap(":/icons/ocr.png").scaled(
        #         48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation
        #     )
        # )
        icon_label.setText("🔍")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 36px;")

        # 标题和描述
        title_label = QLabel("欢迎使用 Umi-OCR")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))

        desc_label = QLabel(
            "Umi-OCR需要安装OCR引擎才能正常工作。\n" "我们为您检测了最适合的安装方案。"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666;")

        # 布局
        title_vbox = QVBoxLayout()
        title_vbox.addWidget(title_label)
        title_vbox.addWidget(desc_label)
        title_vbox.addStretch()

        layout.addWidget(icon_label)
        layout.addLayout(title_vbox, 1)

        return layout

    def _create_button_section(self) -> QHBoxLayout:
        """创建按钮区域"""
        layout = QHBoxLayout()

        layout.addStretch()

        # 取消按钮
        self._cancel_button = QPushButton("取消")
        self._cancel_button.setMinimumWidth(100)
        self._cancel_button.clicked.connect(self._on_cancel)
        layout.addWidget(self._cancel_button)

        # 跳过按钮
        self._skip_button = QPushButton("跳过（使用云OCR）")
        self._skip_button.setMinimumWidth(150)
        self._skip_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self._skip_button.clicked.connect(self._on_skip)
        layout.addWidget(self._skip_button)

        # 安装按钮
        self._install_button = QPushButton("开始安装")
        self._install_button.setMinimumWidth(120)
        self._install_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #888;
            }
        """)
        self._install_button.clicked.connect(self._on_install)
        self._install_button.setEnabled(False)
        layout.addWidget(self._install_button)

        return layout

    def _check_dependencies(self):
        """检测依赖"""
        # 显示检测中
        self._add_message("正在检测系统环境...", "info")

        # 使用QTimer延迟执行，避免阻塞UI
        QTimer.singleShot(100, self._do_check_dependencies)

    def _do_check_dependencies(self):
        """执行依赖检测"""
        try:
            # 检测依赖
            self._dep_info = check_ocr_dependencies()

            # 显示检测结果
            self._show_dependency_info()

            # 如果都已安装，禁用安装按钮
            if (
                self._dep_info.paddlepaddle.status == DependencyStatus.INSTALLED
                and self._dep_info.paddleocr.status == DependencyStatus.INSTALLED
            ):
                self._install_button.setText("已安装")
                self._install_button.setEnabled(False)
                self._skip_button.setText("关闭")
            else:
                self._install_button.setEnabled(True)

        except Exception as e:
            logger.error(f"依赖检测失败: {e}", exc_info=True)
            self._add_message(f"依赖检测失败: {str(e)}", "error")

    def _show_dependency_info(self):
        """显示依赖信息"""
        # 清除检测中消息
        self._content_layout.takeAt(0).widget().deleteLater()

        # 1. GPU检测结果
        self._show_gpu_info()

        # 2. 依赖状态
        self._show_dependency_status()

        # 3. 安装选项
        self._show_install_options()

    def _show_gpu_info(self):
        """显示GPU信息"""
        # 创建分组框
        gpu_group = self._create_group_box("🖥️ GPU检测结果")

        if self._dep_info.gpu_info_list:
            # 显示检测到的GPU
            for gpu in self._dep_info.gpu_info_list:
                gpu_label = QLabel(
                    f"• {gpu.name}\n"
                    f"  显存: {gpu.memory_mb // 1024}GB\n"
                    f"  建议: {gpu.recommendation}"
                )
                gpu_label.setStyleSheet("margin-left: 10px; color: #333;")
                gpu_group.layout().addWidget(gpu_label)
        else:
            # 未检测到GPU
            gpu_label = QLabel("未检测到GPU，建议使用CPU版本")
            gpu_label.setStyleSheet("margin-left: 10px; color: #666;")
            gpu_group.layout().addWidget(gpu_label)

        self._content_layout.addWidget(gpu_group)

    def _show_dependency_status(self):
        """显示依赖状态"""
        # 创建分组框
        dep_group = self._create_group_box("📦 依赖状态")

        # PaddlePaddle状态
        paddle_status = self._format_dependency_status(self._dep_info.paddlepaddle)
        dep_group.layout().addWidget(QLabel(f"PaddlePaddle: {paddle_status}"))

        # PaddleOCR状态
        ocr_status = self._format_dependency_status(self._dep_info.paddleocr)
        dep_group.layout().addWidget(QLabel(f"PaddleOCR: {ocr_status}"))

        self._content_layout.addWidget(dep_group)

    def _format_dependency_status(self, dep_info) -> str:
        """
        格式化依赖状态

        Args:
            dep_info: 依赖信息

        Returns:
            str: 格式化的状态字符串
        """
        if dep_info.status == DependencyStatus.INSTALLED:
            return f"✅ 已安装 (版本: {dep_info.version})"
        elif dep_info.status == DependencyStatus.NOT_INSTALLED:
            return "❌ 未安装"
        elif dep_info.status == DependencyStatus.INCOMPATIBLE:
            return (
                f"⚠️ 版本不兼容 (已安装: {dep_info.version}, "
                f"需要: {dep_info.required_version})"
            )
        else:
            return "❓ 未知状态"

    def _show_install_options(self):
        """显示安装选项"""
        # 创建分组框
        option_group = self._create_group_box("⚙️ 安装选项")

        # 创建单选按钮组
        self._option_group = QButtonGroup(self)

        # CPU版本选项
        cpu_radio = QRadioButton("CPU版本（推荐）")
        cpu_radio.setDescription(
            "适合大多数用户\n" "下载大小: 约 200MB\n" "速度: 较慢，但稳定"
        )
        cpu_radio.setChecked(True)  # 默认选中
        self._option_group.addButton(cpu_radio, 0)
        option_group.layout().addWidget(cpu_radio)

        # GPU版本选项（如果有NVIDIA GPU）
        if self._dep_info.gpu_available:
            gpu_radio = QRadioButton("GPU版本（需要NVIDIA显卡）")
            gpu_radio.setDescription(
                "使用GPU加速，速度快\n"
                "下载大小: 约 1-2GB\n"
                "要求: NVIDIA显卡 + CUDA驱动"
            )
            self._option_group.addButton(gpu_radio, 1)
            option_group.layout().addWidget(gpu_radio)

        # 跳过选项
        skip_radio = QRadioButton("跳过安装（仅使用云OCR）")
        skip_radio.setDescription("稍后手动安装\n" "或仅使用在线OCR服务")
        self._option_group.addButton(skip_radio, 2)
        option_group.layout().addWidget(skip_radio)

        self._content_layout.addWidget(option_group)

    def _create_group_box(self, title: str) -> QFrame:
        """
        创建分组框

        Args:
            title: 分组标题

        Returns:
            QFrame: 分组框
        """
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                margin: 5px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(10)

        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_label.setStyleSheet("color: #333; padding: 5px;")
        layout.addWidget(title_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e0e0e0;")
        layout.addWidget(line)

        return frame

    def _add_message(self, message: str, msg_type: str = "info"):
        """
        添加消息

        Args:
            message: 消息内容
            msg_type: 消息类型（info/warning/error）
        """
        # 颜色映射
        colors = {
            "info": "#333",
            "warning": "#ff9800",
            "error": "#f44336",
            "success": "#4caf50",
        }

        color = colors.get(msg_type, "#333")

        message_label = QLabel(message)
        message_label.setStyleSheet(f"color: {color}; padding: 5px;")
        message_label.setWordWrap(True)
        self._content_layout.addWidget(message_label)

    def _on_install(self):
        """安装按钮点击事件"""
        # 获取选择的选项
        selected_id = self._option_group.checkedId()

        if selected_id == 0:
            option = InstallOption.CPU
        elif selected_id == 1:
            option = InstallOption.GPU
        elif selected_id == 2:
            # 跳过选项
            self._on_skip()
            return
        else:
            return

        self._selected_option = option
        logger.info(f"用户选择安装选项: {option.value}")

        # 确认对话框
        if option == InstallOption.GPU:
            reply = QMessageBox.question(
                self,
                "确认安装",
                "GPU版本需要NVIDIA显卡和CUDA驱动。\n"
                "如果安装失败，请手动卸载并安装CPU版本。\n\n"
                "确定要安装GPU版本吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.No:
                return

        # 开始安装
        self._start_install(option)

    def _start_install(self, option: InstallOption):
        """
        开始安装

        Args:
            option: 安装选项
        """
        # 清空内容区域
        self._clear_content()

        # 显示安装界面
        self._show_install_interface()

        # 创建安装配置
        config = InstallConfig(option=option)

        # 开始后台安装
        installer = get_installer()

        # 连接信号
        installer.progress.connect(self._on_install_progress)
        installer.finished.connect(self._on_install_finished)
        installer.error.connect(self._on_install_error)

        # 开始安装
        installer.start_install(config)

        self._is_installing = True
        self._update_button_state()

    def _show_install_interface(self):
        """显示安装界面"""
        # 进度标签
        self._progress_label = QLabel("准备安装...")
        self._progress_label.setAlignment(Qt.AlignCenter)
        self._progress_label.setStyleSheet("font-size: 14px; margin: 20px;")
        self._content_layout.addWidget(self._progress_label)

        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 30px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        self._content_layout.addWidget(self._progress_bar)

        # 详细信息（可展开）
        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setMaximumHeight(200)
        self._detail_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-family: Consolas, monospace;
                font-size: 11px;
                padding: 10px;
            }
        """)
        self._content_layout.addWidget(self._detail_text)

    def _clear_content(self):
        """清空内容区域"""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_install_progress(self, progress: InstallProgress):
        """
        安装进度回调

        Args:
            progress: 进度信息
        """
        # 更新进度条
        self._progress_bar.setValue(int(progress.percentage))

        # 更新标签
        self._progress_label.setText(progress.message)

        # 添加详细信息
        self._detail_text.append(f"[{progress.status.value}] {progress.message}")

        # 滚动到底部
        self._detail_text.verticalScrollBar().setValue(
            self._detail_text.verticalScrollBar().maximum()
        )

    def _on_install_finished(self, success: bool, message: str):
        """
        安装完成回调

        Args:
            success: 是否成功
            message: 完成消息
        """
        self._is_installing = False
        self._update_button_state()

        if success:
            # 安装成功
            self._detail_text.append(f"\n✅ {message}")
            QMessageBox.information(
                self,
                "安装成功",
                "OCR引擎安装成功！\n\n请重启程序以使用新安装的OCR引擎。",
            )
            self.install_completed.emit(True)
        else:
            # 安装失败
            self._detail_text.append(f"\n❌ {message}")
            QMessageBox.critical(
                self,
                "安装失败",
                f"OCR引擎安装失败：\n{message}\n\n" "请检查网络连接或尝试手动安装。",
            )
            self.install_completed.emit(False)

    def _on_install_error(self, error_message: str):
        """
        安装错误回调

        Args:
            error_message: 错误消息
        """
        self._detail_text.append(f"\n❌ 错误: {error_message}")
        QMessageBox.critical(self, "安装错误", f"安装过程中发生错误：\n{error_message}")

    def _on_skip(self):
        """跳过安装"""
        reply = QMessageBox.question(
            self,
            "确认跳过",
            "跳过安装将无法使用本地OCR引擎，\n"
            "只能使用在线OCR服务（需要网络）。\n\n"
            "确定要跳过吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.skipped.emit()
            self.accept()

    def _on_cancel(self):
        """取消按钮点击事件"""
        if self._is_installing:
            # 安装中，询问是否取消
            reply = QMessageBox.question(
                self,
                "确认取消",
                "安装正在进行中，确定要取消吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                # 取消安装
                installer = get_installer()
                installer.cancel_install()
        else:
            # 未安装，直接关闭
            self.reject()

    def _update_button_state(self):
        """更新按钮状态"""
        if self._is_installing:
            self._install_button.setText("安装中...")
            self._install_button.setEnabled(False)
            self._skip_button.setEnabled(False)
        else:
            self._install_button.setText("开始安装")
            self._skip_button.setEnabled(True)
