// =======================================
// =============== 系统托盘 ===============
// =======================================

import QtQuick 2.15
import SystemTray 1.0

SystemTrayIcon {

    // ========================= 【接口】 =========================

    // 显示托盘图标
    function show() {
        systemTrayRoot.show()
    }

    // 隐藏托盘图标
    function hide() {
        systemTrayRoot.hide()
    }

    // ========================= 【布局】 =========================

    id: systemTrayRoot
    // 不设置 visible 绑定，避免与 show() 方法产生循环调用
    // 初始状态由 Python 端管理
    iconSource: "../images/icons/umiocr.ico"  // 使用ico文件
    tooltip: "Umi-OCR"

    Component.onCompleted: {
        // 设置qmlapp引用，用于pubsub
        systemTrayRoot.setQmlApp(qmlapp)
        // 初始化基础菜单
        systemTrayRoot.addMenuItem("<<mainWin.open>>", qsTr("打开主窗口"))
        systemTrayRoot.addMenuItem("<<mainWin.quit>>", qsTr("退出 Umi-OCR"))
    }

    onActivated: {
        if(reason === SystemTrayIcon.DoubleClick)
            qmlapp.mainWin.setVisibility(true) // 主窗可见
    }
}
