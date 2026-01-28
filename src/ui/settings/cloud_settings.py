#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QScrollArea,
    QMessageBox,
)
from src.controllers.settings_controller import SettingsController


class CloudSettingsPanel(QWidget):
    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller if controller else SettingsController()
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        # 优化滚动条策略：按需显示垂直滚动条，隐藏水平滚动条
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(15)

        # Baidu: API Key, Secret Key
        self.baidu_group = self._create_provider_group(
            "baidu", "百度云 OCR", {"api_key": "API Key", "secret_key": "Secret Key"}
        )
        self.content_layout.addWidget(self.baidu_group)

        # Tencent: SecretId, SecretKey
        self.tencent_group = self._create_provider_group(
            "tencent",
            "腾讯云 OCR",
            {"secret_id": "SecretId", "secret_key": "SecretKey"},
        )
        self.content_layout.addWidget(self.tencent_group)

        # Aliyun: AccessKeyId, AccessKeySecret
        self.aliyun_group = self._create_provider_group(
            "aliyun",
            "阿里云 OCR",
            {"access_key_id": "AccessKeyId", "access_key_secret": "AccessKeySecret"},
        )
        self.content_layout.addWidget(self.aliyun_group)

        self.content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _create_provider_group(self, provider_id, title, fields_map):
        group = QGroupBox(title)
        group.setCheckable(True)
        group.setChecked(False)

        layout = QFormLayout(group)

        inputs = {}
        for key, label in fields_map.items():
            line_edit = QLineEdit()
            line_edit.setEchoMode(QLineEdit.Password)
            layout.addRow(label + ":", line_edit)
            inputs[key] = line_edit

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        # test_btn = QPushButton("测试连接") 
        # Test logic to be implemented later or via controller

        btn_layout.addWidget(save_btn)
        # btn_layout.addWidget(test_btn)
        btn_layout.addStretch()

        layout.addRow(btn_layout)

        # Store metadata
        group.provider_id = provider_id
        group.inputs = inputs
        group.save_btn = save_btn

        save_btn.clicked.connect(lambda: self._on_save(group))

        return group

    def _on_save(self, group):
        provider = group.provider_id
        data = {}
        for key, widget in group.inputs.items():
            data[key] = widget.text().strip()

        if self.controller.save_cloud_credentials(provider, **data):
            QMessageBox.information(self, "成功", f"{group.title()} 凭证已保存")
        else:
            QMessageBox.critical(self, "失败", f"保存 {group.title()} 凭证失败")

    def _load_data(self):
        groups = [self.baidu_group, self.tencent_group, self.aliyun_group]
        for group in groups:
            creds = self.controller.load_cloud_credentials(group.provider_id)
            if creds:
                # If we have creds, expand the group
                group.setChecked(True)
                for key, widget in group.inputs.items():
                    if key in creds:
                        widget.setText(creds[key])
