# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QMenu, QMenuBar, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QStackedWidget, QStatusBar,
    QToolBar, QVBoxLayout, QWidget)
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1000, 700)
        self.actionOpenFile = QAction(MainWindow)
        self.actionOpenFile.setObjectName(u"actionOpenFile")
        self.actionOpenFolder = QAction(MainWindow)
        self.actionOpenFolder.setObjectName(u"actionOpenFolder")
        self.actionExport = QAction(MainWindow)
        self.actionExport.setObjectName(u"actionExport")
        self.actionExit = QAction(MainWindow)
        self.actionExit.setObjectName(u"actionExit")
        self.actionCopy = QAction(MainWindow)
        self.actionCopy.setObjectName(u"actionCopy")
        self.actionPaste = QAction(MainWindow)
        self.actionPaste.setObjectName(u"actionPaste")
        self.actionSettings = QAction(MainWindow)
        self.actionSettings.setObjectName(u"actionSettings")
        self.actionToggleSidebar = QAction(MainWindow)
        self.actionToggleSidebar.setObjectName(u"actionToggleSidebar")
        self.actionToggleSidebar.setCheckable(True)
        self.actionToggleSidebar.setChecked(True)
        self.actionToggleToolbar = QAction(MainWindow)
        self.actionToggleToolbar.setObjectName(u"actionToggleToolbar")
        self.actionToggleToolbar.setCheckable(True)
        self.actionToggleToolbar.setChecked(True)
        self.actionFullscreen = QAction(MainWindow)
        self.actionFullscreen.setObjectName(u"actionFullscreen")
        self.actionFullscreen.setCheckable(True)
        self.actionScreenshot = QAction(MainWindow)
        self.actionScreenshot.setObjectName(u"actionScreenshot")
        self.actionTaskManager = QAction(MainWindow)
        self.actionTaskManager.setObjectName(u"actionTaskManager")
        self.actionCheckUpdate = QAction(MainWindow)
        self.actionCheckUpdate.setObjectName(u"actionCheckUpdate")
        self.actionDocumentation = QAction(MainWindow)
        self.actionDocumentation.setObjectName(u"actionDocumentation")
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        self.menuBar = QMenuBar(MainWindow)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 1000, 24))
        self.menuFile = QMenu(self.menuBar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuEdit = QMenu(self.menuBar)
        self.menuEdit.setObjectName(u"menuEdit")
        self.menuView = QMenu(self.menuBar)
        self.menuView.setObjectName(u"menuView")
        self.menuTools = QMenu(self.menuBar)
        self.menuTools.setObjectName(u"menuTools")
        self.menuHelp = QMenu(self.menuBar)
        self.menuHelp.setObjectName(u"menuHelp")
        MainWindow.setMenuBar(self.menuBar)
        self.mainToolBar = QToolBar(MainWindow)
        self.mainToolBar.setObjectName(u"mainToolBar")
        MainWindow.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.mainToolBar)
        self.centralWidget = QWidget(MainWindow)
        self.centralWidget.setObjectName(u"centralWidget")
        self.horizontalLayout = QHBoxLayout(self.centralWidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.sidebarListWidget = QListWidget(self.centralWidget)
        QListWidgetItem(self.sidebarListWidget)
        QListWidgetItem(self.sidebarListWidget)
        QListWidgetItem(self.sidebarListWidget)
        QListWidgetItem(self.sidebarListWidget)
        QListWidgetItem(self.sidebarListWidget)
        QListWidgetItem(self.sidebarListWidget)
        self.sidebarListWidget.setObjectName(u"sidebarListWidget")
        self.sidebarListWidget.setMinimumSize(QSize(180, 0))
        self.sidebarListWidget.setMaximumSize(QSize(250, 16777215))
        self.sidebarListWidget.setFocusPolicy(Qt.NoFocus)
        self.sidebarListWidget.setFrameShape(QFrame.NoFrame)
        self.sidebarListWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.sidebarListWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sidebarListWidget.setIconSize(QSize(24, 24))

        self.horizontalLayout.addWidget(self.sidebarListWidget)

        self.separatorLine = QFrame(self.centralWidget)
        self.separatorLine.setObjectName(u"separatorLine")
        self.separatorLine.setFrameShape(QFrame.Shape.VLine)
        self.separatorLine.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout.addWidget(self.separatorLine)

        self.contentStackedWidget = QStackedWidget(self.centralWidget)
        self.contentStackedWidget.setObjectName(u"contentStackedWidget")
        self.contentStackedWidget.setFocusPolicy(Qt.NoFocus)
        self.pageScreenshotOcr = QWidget()
        self.pageScreenshotOcr.setObjectName(u"pageScreenshotOcr")
        self.verticalLayoutScreenshot = QVBoxLayout(self.pageScreenshotOcr)
        self.verticalLayoutScreenshot.setObjectName(u"verticalLayoutScreenshot")
        self.labelScreenshotPlaceholder = QLabel(self.pageScreenshotOcr)
        self.labelScreenshotPlaceholder.setObjectName(u"labelScreenshotPlaceholder")
        self.labelScreenshotPlaceholder.setAlignment(Qt.AlignCenter)

        self.verticalLayoutScreenshot.addWidget(self.labelScreenshotPlaceholder)

        self.contentStackedWidget.addWidget(self.pageScreenshotOcr)
        self.pageBatchOcr = QWidget()
        self.pageBatchOcr.setObjectName(u"pageBatchOcr")
        self.verticalLayoutBatchOcr = QVBoxLayout(self.pageBatchOcr)
        self.verticalLayoutBatchOcr.setObjectName(u"verticalLayoutBatchOcr")
        self.labelBatchOcrPlaceholder = QLabel(self.pageBatchOcr)
        self.labelBatchOcrPlaceholder.setObjectName(u"labelBatchOcrPlaceholder")
        self.labelBatchOcrPlaceholder.setAlignment(Qt.AlignCenter)

        self.verticalLayoutBatchOcr.addWidget(self.labelBatchOcrPlaceholder)

        self.contentStackedWidget.addWidget(self.pageBatchOcr)
        self.pageBatchDoc = QWidget()
        self.pageBatchDoc.setObjectName(u"pageBatchDoc")
        self.verticalLayoutBatchDoc = QVBoxLayout(self.pageBatchDoc)
        self.verticalLayoutBatchDoc.setObjectName(u"verticalLayoutBatchDoc")
        self.labelBatchDocPlaceholder = QLabel(self.pageBatchDoc)
        self.labelBatchDocPlaceholder.setObjectName(u"labelBatchDocPlaceholder")
        self.labelBatchDocPlaceholder.setAlignment(Qt.AlignCenter)

        self.verticalLayoutBatchDoc.addWidget(self.labelBatchDocPlaceholder)

        self.contentStackedWidget.addWidget(self.pageBatchDoc)
        self.pageQrcode = QWidget()
        self.pageQrcode.setObjectName(u"pageQrcode")
        self.verticalLayoutQrcode = QVBoxLayout(self.pageQrcode)
        self.verticalLayoutQrcode.setObjectName(u"verticalLayoutQrcode")
        self.labelQrcodePlaceholder = QLabel(self.pageQrcode)
        self.labelQrcodePlaceholder.setObjectName(u"labelQrcodePlaceholder")
        self.labelQrcodePlaceholder.setAlignment(Qt.AlignCenter)

        self.verticalLayoutQrcode.addWidget(self.labelQrcodePlaceholder)

        self.contentStackedWidget.addWidget(self.pageQrcode)
        self.pageTaskManager = QWidget()
        self.pageTaskManager.setObjectName(u"pageTaskManager")
        self.verticalLayout_TaskManager = QVBoxLayout(self.pageTaskManager)
        self.verticalLayout_TaskManager.setObjectName(u"verticalLayout_TaskManager")
        self.horizontalLayout_TM_Header = QHBoxLayout()
        self.horizontalLayout_TM_Header.setObjectName(u"horizontalLayout_TM_Header")
        self.label_title = QLabel(self.pageTaskManager)
        self.label_title.setObjectName(u"label_title")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.label_title.setFont(font)

        self.horizontalLayout_TM_Header.addWidget(self.label_title)

        self.horizontalSpacer_TM = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_TM_Header.addItem(self.horizontalSpacer_TM)

        self.btn_pause_all = QPushButton(self.pageTaskManager)
        self.btn_pause_all.setObjectName(u"btn_pause_all")

        self.horizontalLayout_TM_Header.addWidget(self.btn_pause_all)

        self.btn_resume_all = QPushButton(self.pageTaskManager)
        self.btn_resume_all.setObjectName(u"btn_resume_all")

        self.horizontalLayout_TM_Header.addWidget(self.btn_resume_all)

        self.btn_clear_completed = QPushButton(self.pageTaskManager)
        self.btn_clear_completed.setObjectName(u"btn_clear_completed")

        self.horizontalLayout_TM_Header.addWidget(self.btn_clear_completed)


        self.verticalLayout_TaskManager.addLayout(self.horizontalLayout_TM_Header)

        self.scrollArea = QScrollArea(self.pageTaskManager)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.NoFrame)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 782, 542))
        self.verticalLayout_cards = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_cards.setSpacing(10)
        self.verticalLayout_cards.setObjectName(u"verticalLayout_cards")
        self.verticalSpacer_TM = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_cards.addItem(self.verticalSpacer_TM)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_TaskManager.addWidget(self.scrollArea)

        self.contentStackedWidget.addWidget(self.pageTaskManager)
        self.pageSettings = QWidget()
        self.pageSettings.setObjectName(u"pageSettings")
        self.horizontalLayout_Settings = QHBoxLayout(self.pageSettings)
        self.horizontalLayout_Settings.setObjectName(u"horizontalLayout_Settings")
        self.listWidget_sidebar = QListWidget(self.pageSettings)
        self.listWidget_sidebar.setObjectName(u"listWidget_sidebar")
        self.listWidget_sidebar.setMaximumSize(QSize(200, 16777215))

        self.horizontalLayout_Settings.addWidget(self.listWidget_sidebar)

        self.stackedWidget_pages = QStackedWidget(self.pageSettings)
        self.stackedWidget_pages.setObjectName(u"stackedWidget_pages")
        self.page_general = QWidget()
        self.page_general.setObjectName(u"page_general")
        self.verticalLayout_general = QVBoxLayout(self.page_general)
        self.verticalLayout_general.setObjectName(u"verticalLayout_general")
        self.label_general = QLabel(self.page_general)
        self.label_general.setObjectName(u"label_general")
        font1 = QFont()
        font1.setPointSize(12)
        font1.setBold(True)
        self.label_general.setFont(font1)

        self.verticalLayout_general.addWidget(self.label_general)

        self.verticalSpacer_general = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_general.addItem(self.verticalSpacer_general)

        self.stackedWidget_pages.addWidget(self.page_general)
        self.page_ocr_engine = QWidget()
        self.page_ocr_engine.setObjectName(u"page_ocr_engine")
        self.verticalLayout_engine = QVBoxLayout(self.page_ocr_engine)
        self.verticalLayout_engine.setObjectName(u"verticalLayout_engine")
        self.label_engine = QLabel(self.page_ocr_engine)
        self.label_engine.setObjectName(u"label_engine")
        self.label_engine.setFont(font1)

        self.verticalLayout_engine.addWidget(self.label_engine)

        self.verticalSpacer_engine = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_engine.addItem(self.verticalSpacer_engine)

        self.stackedWidget_pages.addWidget(self.page_ocr_engine)
        self.page_cloud = QWidget()
        self.page_cloud.setObjectName(u"page_cloud")
        self.verticalLayout_cloud = QVBoxLayout(self.page_cloud)
        self.verticalLayout_cloud.setObjectName(u"verticalLayout_cloud")
        self.label_cloud = QLabel(self.page_cloud)
        self.label_cloud.setObjectName(u"label_cloud")
        self.label_cloud.setFont(font1)

        self.verticalLayout_cloud.addWidget(self.label_cloud)

        self.verticalSpacer_cloud = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_cloud.addItem(self.verticalSpacer_cloud)

        self.stackedWidget_pages.addWidget(self.page_cloud)

        self.horizontalLayout_Settings.addWidget(self.stackedWidget_pages)

        self.contentStackedWidget.addWidget(self.pageSettings)

        self.horizontalLayout.addWidget(self.contentStackedWidget)

        MainWindow.setCentralWidget(self.centralWidget)
        self.statusBar = QStatusBar(MainWindow)
        self.statusBar.setObjectName(u"statusBar")
        self.statusBar.setSizeGripEnabled(False)
        MainWindow.setStatusBar(self.statusBar)

        self.menuBar.addAction(self.menuFile.menuAction())
        self.menuBar.addAction(self.menuEdit.menuAction())
        self.menuBar.addAction(self.menuView.menuAction())
        self.menuBar.addAction(self.menuTools.menuAction())
        self.menuBar.addAction(self.menuHelp.menuAction())
        self.menuFile.addAction(self.actionOpenFile)
        self.menuFile.addAction(self.actionOpenFolder)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExport)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExit)
        # 简化菜单栏，移除与侧边栏重复的功能
        self.menuEdit.addAction(self.actionCopy)
        self.menuEdit.addAction(self.actionPaste)
        self.menuView.addAction(self.actionToggleSidebar)
        self.menuView.addAction(self.actionFullscreen)
        self.menuTools.addAction(self.actionCheckUpdate)
        self.menuHelp.addAction(self.actionDocumentation)
        self.menuHelp.addAction(self.actionAbout)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Umi-OCR", None))
        self.actionOpenFile.setText(QCoreApplication.translate("MainWindow", u"\u6253\u5f00\u6587\u4ef6...", None))
#if QT_CONFIG(shortcut)
        self.actionOpenFile.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+O", None))
#endif // QT_CONFIG(shortcut)
        self.actionOpenFolder.setText(QCoreApplication.translate("MainWindow", u"\u6253\u5f00\u6587\u4ef6\u5939...", None))
        self.actionExport.setText(QCoreApplication.translate("MainWindow", u"\u5bfc\u51fa\u7ed3\u679c...", None))
#if QT_CONFIG(shortcut)
        self.actionExport.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+E", None))
#endif // QT_CONFIG(shortcut)
        self.actionExit.setText(QCoreApplication.translate("MainWindow", u"\u9000\u51fa", None))
#if QT_CONFIG(shortcut)
        self.actionExit.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Q", None))
#endif // QT_CONFIG(shortcut)
        self.actionCopy.setText(QCoreApplication.translate("MainWindow", u"\u590d\u5236", None))
#if QT_CONFIG(shortcut)
        self.actionCopy.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+C", None))
#endif // QT_CONFIG(shortcut)
        self.actionPaste.setText(QCoreApplication.translate("MainWindow", u"\u7c98\u8d34", None))
#if QT_CONFIG(shortcut)
        self.actionPaste.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+V", None))
#endif // QT_CONFIG(shortcut)
        self.actionSettings.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e...", None))
#if QT_CONFIG(shortcut)
        self.actionSettings.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+,", None))
#endif // QT_CONFIG(shortcut)
        self.actionToggleSidebar.setText(QCoreApplication.translate("MainWindow", u"\u663e\u793a\u4fa7\u8fb9\u680f", None))
        self.actionToggleToolbar.setText(QCoreApplication.translate("MainWindow", u"\u663e\u793a\u5de5\u5177\u680f", None))
        self.actionFullscreen.setText(QCoreApplication.translate("MainWindow", u"\u5168\u5c4f\u6a21\u5f0f", None))
#if QT_CONFIG(shortcut)
        self.actionFullscreen.setShortcut(QCoreApplication.translate("MainWindow", u"F11", None))
#endif // QT_CONFIG(shortcut)
        self.actionScreenshot.setText(QCoreApplication.translate("MainWindow", u"\u622a\u56feOCR", None))
#if QT_CONFIG(shortcut)
        self.actionScreenshot.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+A", None))
#endif // QT_CONFIG(shortcut)
        self.actionTaskManager.setText(QCoreApplication.translate("MainWindow", u"\u4efb\u52a1\u7ba1\u7406\u5668", None))
#if QT_CONFIG(shortcut)
        self.actionTaskManager.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+T", None))
#endif // QT_CONFIG(shortcut)
        self.actionCheckUpdate.setText(QCoreApplication.translate("MainWindow", u"\u68c0\u67e5\u66f4\u65b0...", None))
        self.actionDocumentation.setText(QCoreApplication.translate("MainWindow", u"\u6587\u6863...", None))
        self.actionAbout.setText(QCoreApplication.translate("MainWindow", u"\u5173\u4e8e...", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"\u6587\u4ef6(&F)", None))
        self.menuEdit.setTitle(QCoreApplication.translate("MainWindow", u"\u7f16\u8f91(&E)", None))
        self.menuView.setTitle(QCoreApplication.translate("MainWindow", u"\u89c6\u56fe(&V)", None))
        self.menuTools.setTitle(QCoreApplication.translate("MainWindow", u"\u5de5\u5177(&T)", None))
        self.menuHelp.setTitle(QCoreApplication.translate("MainWindow", u"\u5e2e\u52a9(&H)", None))
        self.mainToolBar.setWindowTitle(QCoreApplication.translate("MainWindow", u"\u5de5\u5177\u680f", None))

        __sortingEnabled = self.sidebarListWidget.isSortingEnabled()
        self.sidebarListWidget.setSortingEnabled(False)
        ___qlistwidgetitem = self.sidebarListWidget.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("MainWindow", u"\u622a\u56feOCR", None));
        ___qlistwidgetitem1 = self.sidebarListWidget.item(1)
        ___qlistwidgetitem1.setText(QCoreApplication.translate("MainWindow", u"\u6279\u91cf\u56fe\u7247", None));
        ___qlistwidgetitem2 = self.sidebarListWidget.item(2)
        ___qlistwidgetitem2.setText(QCoreApplication.translate("MainWindow", u"\u6279\u91cf\u6587\u6863", None));
        ___qlistwidgetitem3 = self.sidebarListWidget.item(3)
        ___qlistwidgetitem3.setText(QCoreApplication.translate("MainWindow", u"\u4e8c\u7ef4\u7801", None));
        ___qlistwidgetitem4 = self.sidebarListWidget.item(4)
        ___qlistwidgetitem4.setText(QCoreApplication.translate("MainWindow", u"\u4efb\u52a1\u7ba1\u7406", None));
        ___qlistwidgetitem5 = self.sidebarListWidget.item(5)
        ___qlistwidgetitem5.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e", None));
        self.sidebarListWidget.setSortingEnabled(__sortingEnabled)

        self.labelScreenshotPlaceholder.setText(QCoreApplication.translate("MainWindow", u"\u622a\u56fe OCR \u529f\u80fd\u6a21\u5757 - \u5f85\u5b9e\u73b0", None))
        self.labelBatchOcrPlaceholder.setText(QCoreApplication.translate("MainWindow", u"\u6279\u91cf\u56fe\u7247 OCR \u529f\u80fd\u6a21\u5757 - \u5f85\u5b9e\u73b0", None))
        self.labelBatchDocPlaceholder.setText(QCoreApplication.translate("MainWindow", u"\u6279\u91cf\u6587\u6863 OCR \u529f\u80fd\u6a21\u5757 - \u5f85\u5b9e\u73b0", None))
        self.labelQrcodePlaceholder.setText(QCoreApplication.translate("MainWindow", u"\u4e8c\u7ef4\u7801\u529f\u80fd\u6a21\u5757 - \u5f85\u5b9e\u73b0", None))
        self.label_title.setText(QCoreApplication.translate("MainWindow", u"\u4efb\u52a1\u7ba1\u7406\u5668", None))
        self.btn_pause_all.setText(QCoreApplication.translate("MainWindow", u"\u6682\u505c\u5168\u90e8", None))
        self.btn_resume_all.setText(QCoreApplication.translate("MainWindow", u"\u6062\u590d\u5168\u90e8", None))
        self.btn_clear_completed.setText(QCoreApplication.translate("MainWindow", u"\u6e05\u7a7a\u5df2\u5b8c\u6210", None))
        self.label_general.setText(QCoreApplication.translate("MainWindow", u"\u5e38\u89c4\u8bbe\u7f6e", None))
        self.label_engine.setText(QCoreApplication.translate("MainWindow", u"OCR \u5f15\u64ce\u8bbe\u7f6e", None))
        self.label_cloud.setText(QCoreApplication.translate("MainWindow", u"\u4e91\u670d\u52a1\u8bbe\u7f6e", None))
    # retranslateUi

