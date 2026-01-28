# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'floating_bar.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout


class Ui_FloatingBar(object):
    def setupUi(self, FloatingBar):
        if not FloatingBar.objectName():
            FloatingBar.setObjectName("FloatingBar")
        FloatingBar.resize(50, 200)
        FloatingBar.setStyleSheet(
            "#FloatingBar {\n"
            "	background-color: rgba(255, 255, 255, 240);\n"
            "	border: 1px solid #ccc;\n"
            "	border-radius: 5px;\n"
            "}\n"
            "QPushButton {\n"
            "	border: none;\n"
            "	border-radius: 4px;\n"
            "	padding: 5px;\n"
            "}\n"
            "QPushButton:hover {\n"
            "	background-color: #f0f0f0;\n"
            "}"
        )
        self.verticalLayout = QVBoxLayout(FloatingBar)
        self.verticalLayout.setSpacing(5)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(5, 5, 5, 5)
        self.btn_screenshot = QPushButton(FloatingBar)
        self.btn_screenshot.setObjectName("btn_screenshot")

        self.verticalLayout.addWidget(self.btn_screenshot)

        self.btn_clipboard = QPushButton(FloatingBar)
        self.btn_clipboard.setObjectName("btn_clipboard")

        self.verticalLayout.addWidget(self.btn_clipboard)

        self.btn_batch = QPushButton(FloatingBar)
        self.btn_batch.setObjectName("btn_batch")

        self.verticalLayout.addWidget(self.btn_batch)

        self.btn_settings = QPushButton(FloatingBar)
        self.btn_settings.setObjectName("btn_settings")

        self.verticalLayout.addWidget(self.btn_settings)

        self.verticalSpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.verticalLayout.addItem(self.verticalSpacer)

        self.lbl_grip = QLabel(FloatingBar)
        self.lbl_grip.setObjectName("lbl_grip")
        self.lbl_grip.setAlignment(Qt.AlignCenter)
        self.lbl_grip.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))

        self.verticalLayout.addWidget(self.lbl_grip)

        self.retranslateUi(FloatingBar)

        QMetaObject.connectSlotsByName(FloatingBar)

    # setupUi

    def retranslateUi(self, FloatingBar):
        FloatingBar.setWindowTitle(
            QCoreApplication.translate(
                "FloatingBar", "\u60ac\u6d6e\u5de5\u5177\u680f", None
            )
        )
        # if QT_CONFIG(tooltip)
        self.btn_screenshot.setToolTip(
            QCoreApplication.translate("FloatingBar", "\u622a\u56fe OCR", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.btn_screenshot.setText(
            QCoreApplication.translate("FloatingBar", "\U0001f4f7", None)
        )
        # if QT_CONFIG(tooltip)
        self.btn_clipboard.setToolTip(
            QCoreApplication.translate("FloatingBar", "\u526a\u8d34\u677f OCR", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.btn_clipboard.setText(
            QCoreApplication.translate("FloatingBar", "\U0001f4cb", None)
        )
        # if QT_CONFIG(tooltip)
        self.btn_batch.setToolTip(
            QCoreApplication.translate("FloatingBar", "\u6279\u91cf OCR", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.btn_batch.setText(
            QCoreApplication.translate("FloatingBar", "\U0001f4c2", None)
        )
        # if QT_CONFIG(tooltip)
        self.btn_settings.setToolTip(
            QCoreApplication.translate("FloatingBar", "\u8bbe\u7f6e", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.btn_settings.setText(
            QCoreApplication.translate("FloatingBar", "\u2699\ufe0f", None)
        )
        self.lbl_grip.setText(QCoreApplication.translate("FloatingBar", "\u283f", None))

    # retranslateUi
