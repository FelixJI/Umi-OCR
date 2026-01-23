// =========================================
// =============== 文件选择窗 ===============
// =========================================

import QtQuick.Dialogs

FileDialog {
    property var fileUrls_: [] // 缓存处理好的 fileUrls

    // Qt5 到 Qt6 兼容属性（仅作为接口，Qt6 使用 fileMode）
    property bool selectExisting: true
    property bool selectFolder: false
    property bool selectMultiple: false

    onAccepted: {
        fileUrls_ = qmlapp.utilsConnector.QUrl2String(fileUrls)
    }
}
