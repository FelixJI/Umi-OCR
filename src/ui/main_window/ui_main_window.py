# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1000, 700)

        # 中心部件
        self.centralWidget = QWidget(MainWindow)
        self.centralWidget.setObjectName("centralWidget")
        self.verticalLayout_main = QVBoxLayout(self.centralWidget)
        self.verticalLayout_main.setObjectName("verticalLayout_main")
        self.verticalLayout_main.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_main.setSpacing(0)

        # 标签页容器
        self.tabWidget = QTabWidget(self.centralWidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tabWidget.setFocusPolicy(Qt.NoFocus)

        # 截图 OCR 页面
        self.pageScreenshotOcr = QWidget()
        self.pageScreenshotOcr.setObjectName("pageScreenshotOcr")
        self.verticalLayoutScreenshot = QVBoxLayout(self.pageScreenshotOcr)
        self.verticalLayoutScreenshot.setObjectName("verticalLayoutScreenshot")
        self.verticalLayoutScreenshot.setContentsMargins(0, 0, 0, 0)
        self.verticalLayoutScreenshot.setSpacing(0)
        self.tabWidget.addTab(self.pageScreenshotOcr, "截图OCR")

        # 批量图片 OCR 页面
        self.pageBatchOcr = QWidget()
        self.pageBatchOcr.setObjectName("pageBatchOcr")
        self.verticalLayoutBatchOcr = QVBoxLayout(self.pageBatchOcr)
        self.verticalLayoutBatchOcr.setObjectName("verticalLayoutBatchOcr")
        self.verticalLayoutBatchOcr.setContentsMargins(0, 0, 0, 0)
        self.verticalLayoutBatchOcr.setSpacing(0)
        self.tabWidget.addTab(self.pageBatchOcr, "批量图片")

        # 批量文档 OCR 页面
        self.pageBatchDoc = QWidget()
        self.pageBatchDoc.setObjectName("pageBatchDoc")
        self.verticalLayoutBatchDoc = QVBoxLayout(self.pageBatchDoc)
        self.verticalLayoutBatchDoc.setObjectName("verticalLayoutBatchDoc")
        self.verticalLayoutBatchDoc.setContentsMargins(0, 0, 0, 0)
        self.verticalLayoutBatchDoc.setSpacing(0)
        self.tabWidget.addTab(self.pageBatchDoc, "批量文档")

        # 二维码页面
        self.pageQrcode = QWidget()
        self.pageQrcode.setObjectName("pageQrcode")
        self.verticalLayoutQrcode = QVBoxLayout(self.pageQrcode)
        self.verticalLayoutQrcode.setObjectName("verticalLayoutQrcode")
        self.verticalLayoutQrcode.setContentsMargins(0, 0, 0, 0)
        self.verticalLayoutQrcode.setSpacing(0)
        self.tabWidget.addTab(self.pageQrcode, "二维码")

        # 任务管理器页面
        self.pageTaskManager = QWidget()
        self.pageTaskManager.setObjectName("pageTaskManager")
        self.verticalLayout_TaskManager = QVBoxLayout(self.pageTaskManager)
        self.verticalLayout_TaskManager.setObjectName("verticalLayout_TaskManager")
        self.verticalLayout_TaskManager.setSpacing(10)
        self.verticalLayout_TaskManager.setContentsMargins(10, 10, 10, 10)

        self.horizontalLayout_TM_Header = QHBoxLayout()
        self.horizontalLayout_TM_Header.setObjectName("horizontalLayout_TM_Header")
        self.label_title = QLabel(self.pageTaskManager)
        self.label_title.setObjectName("label_title")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.label_title.setFont(font)
        self.horizontalLayout_TM_Header.addWidget(self.label_title)

        self.horizontalSpacer_TM = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout_TM_Header.addItem(self.horizontalSpacer_TM)

        self.btn_pause_all = QPushButton(self.pageTaskManager)
        self.btn_pause_all.setObjectName("btn_pause_all")
        self.horizontalLayout_TM_Header.addWidget(self.btn_pause_all)

        self.btn_resume_all = QPushButton(self.pageTaskManager)
        self.btn_resume_all.setObjectName("btn_resume_all")
        self.horizontalLayout_TM_Header.addWidget(self.btn_resume_all)

        self.btn_clear_completed = QPushButton(self.pageTaskManager)
        self.btn_clear_completed.setObjectName("btn_clear_completed")
        self.horizontalLayout_TM_Header.addWidget(self.btn_clear_completed)

        self.verticalLayout_TaskManager.addLayout(self.horizontalLayout_TM_Header)

        self.scrollArea = QScrollArea(self.pageTaskManager)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.NoFrame)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 782, 542))
        self.verticalLayout_cards = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_cards.setSpacing(10)
        self.verticalLayout_cards.setObjectName("verticalLayout_cards")
        self.verticalSpacer_TM = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.verticalLayout_cards.addItem(self.verticalSpacer_TM)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_TaskManager.addWidget(self.scrollArea)
        self.tabWidget.addTab(self.pageTaskManager, "任务管理")

        # 设置页面
        self.pageSettings = QWidget()
        self.pageSettings.setObjectName("pageSettings")
        self.horizontalLayout_Settings = QHBoxLayout(self.pageSettings)
        self.horizontalLayout_Settings.setObjectName("horizontalLayout_Settings")
        self.horizontalLayout_Settings.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_Settings.setSpacing(0)

        self.listWidget_sidebar = QListWidget(self.pageSettings)
        self.listWidget_sidebar.setObjectName("listWidget_sidebar")
        self.listWidget_sidebar.setMaximumSize(QSize(200, 16777215))
        self.horizontalLayout_Settings.addWidget(self.listWidget_sidebar)

        self.stackedWidget_pages = QStackedWidget(self.pageSettings)
        self.stackedWidget_pages.setObjectName("stackedWidget_pages")

        self.page_general = QWidget()
        self.page_general.setObjectName("page_general")
        self.verticalLayout_general = QVBoxLayout(self.page_general)
        self.verticalLayout_general.setObjectName("verticalLayout_general")
        self.label_general = QLabel(self.page_general)
        self.label_general.setObjectName("label_general")
        font1 = QFont()
        font1.setPointSize(12)
        font1.setBold(True)
        self.label_general.setFont(font1)
        self.verticalLayout_general.addWidget(self.label_general)
        self.verticalSpacer_general = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.verticalLayout_general.addItem(self.verticalSpacer_general)
        self.stackedWidget_pages.addWidget(self.page_general)

        self.page_ocr_engine = QWidget()
        self.page_ocr_engine.setObjectName("page_ocr_engine")
        self.verticalLayout_engine = QVBoxLayout(self.page_ocr_engine)
        self.verticalLayout_engine.setObjectName("verticalLayout_engine")
        self.label_engine = QLabel(self.page_ocr_engine)
        self.label_engine.setObjectName("label_engine")
        self.label_engine.setFont(font1)
        self.verticalLayout_engine.addWidget(self.label_engine)
        self.verticalSpacer_engine = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.verticalLayout_engine.addItem(self.verticalSpacer_engine)
        self.stackedWidget_pages.addWidget(self.page_ocr_engine)

        self.page_model = QWidget()
        self.page_model.setObjectName("page_model")
        self.verticalLayout_model = QVBoxLayout(self.page_model)
        self.verticalLayout_model.setObjectName("verticalLayout_model")
        self.label_model = QLabel(self.page_model)
        self.label_model.setObjectName("label_model")
        self.label_model.setFont(font1)
        self.verticalLayout_model.addWidget(self.label_model)
        self.verticalSpacer_model = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.verticalLayout_model.addItem(self.verticalSpacer_model)
        self.stackedWidget_pages.addWidget(self.page_model)

        self.page_cloud = QWidget()
        self.page_cloud.setObjectName("page_cloud")
        self.verticalLayout_cloud = QVBoxLayout(self.page_cloud)
        self.verticalLayout_cloud.setObjectName("verticalLayout_cloud")
        self.label_cloud = QLabel(self.page_cloud)
        self.label_cloud.setObjectName("label_cloud")
        self.label_cloud.setFont(font1)
        self.verticalLayout_cloud.addWidget(self.label_cloud)
        self.verticalSpacer_cloud = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.verticalLayout_cloud.addItem(self.verticalSpacer_cloud)
        self.stackedWidget_pages.addWidget(self.page_cloud)

        self.horizontalLayout_Settings.addWidget(self.stackedWidget_pages)
        self.tabWidget.addTab(self.pageSettings, "设置")

        self.verticalLayout_main.addWidget(self.tabWidget)
        MainWindow.setCentralWidget(self.centralWidget)

        # 状态栏
        self.statusBar = QStatusBar(MainWindow)
        self.statusBar.setObjectName("statusBar")
        self.statusBar.setSizeGripEnabled(False)
        MainWindow.setStatusBar(self.statusBar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)

    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(
            QCoreApplication.translate("MainWindow", "Umi-OCR", None)
        )
        self.label_title.setText(
            QCoreApplication.translate("MainWindow", "任务管理器", None)
        )
        self.btn_pause_all.setText(
            QCoreApplication.translate("MainWindow", "暂停全部", None)
        )
        self.btn_resume_all.setText(
            QCoreApplication.translate("MainWindow", "恢复全部", None)
        )
        self.btn_clear_completed.setText(
            QCoreApplication.translate("MainWindow", "清空已完成", None)
        )
        self.label_general.setText(
            QCoreApplication.translate("MainWindow", "常规设置", None)
        )
        self.label_engine.setText(
            QCoreApplication.translate("MainWindow", "OCR 引擎设置", None)
        )
        self.label_cloud.setText(
            QCoreApplication.translate("MainWindow", "云服务设置", None)
        )
        self.label_model.setText(
            QCoreApplication.translate("MainWindow", "模型管理", None)
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.pageScreenshotOcr),
            QCoreApplication.translate("MainWindow", "截图OCR", None),
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.pageBatchOcr),
            QCoreApplication.translate("MainWindow", "批量图片", None),
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.pageBatchDoc),
            QCoreApplication.translate("MainWindow", "批量文档", None),
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.pageQrcode),
            QCoreApplication.translate("MainWindow", "二维码", None),
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.pageTaskManager),
            QCoreApplication.translate("MainWindow", "任务管理", None),
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.pageSettings),
            QCoreApplication.translate("MainWindow", "设置", None),
        )

    # retranslateUi
