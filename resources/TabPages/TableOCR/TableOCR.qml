// ==============================================
// =============== 功能页：表格识别 ===============
// ==============================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import ".."
import "../../Widgets"
import "../../Widgets/ResultLayout"

TabPage {
    id: tabPage

    // ========================= 【逻辑】 =========================

    property int errorNum: 0
    property string msnID: ""
    property var results: []

    Component.onCompleted: {
    }

    // 异步加载文件路径
    function addImages(paths) {
        if(ctrlPanel.state_ !== "stop") return
        if(paths.length <= 0) return
        const isRecurrence = configsComp.getValue("mission.recurrence")
        qmlapp.asynFilesLoader.run(paths, "image", isRecurrence, onAddImages)
    }

    function onAddImages(paths) {
        for(let i in paths) {
            filesTableView.add({ path: paths[i], time: "", state: "" })
        }
    }

    // 运行表格识别
    function ocrStart() {
        let msnLength = filesTableView.rowCount
        if(msnLength <= 0) {
            ctrlPanel.stopFinished()
            return
        }
        for(let i = 0; i < msnLength; i++) {
            filesTableView.set(i, { time: "", state: qsTr("排队") })
        }
        errorNum = 0
        results = []
        const paths = filesTableView.getColumnsValue("path")
        const argd = configsComp.getValueDict()
        msnID = tabPage.callPy("msnPaths", paths, argd)
        if(tabPanel.indexChangeNum < 2)
            tabPanel.currentIndex = 1
        ctrlPanel.runFinished(msnLength)
    }

    // 停止识别
    function ocrStop() {
        _ocrStop()
        tabPage.callPy("cancelMsn")
        ctrlPanel.stopFinished()
    }

    function _ocrStop() {
        msnID = ""
        let msnLength = filesTableView.rowCount
        for(let i = 0; i < msnLength; i++) {
            const row = filesTableView.get(i)
            if(row.time === "") {
                filesTableView.setProperty(i, "state", "")
            }
        }
    }

    // 关闭页面
    function closePage() {
        if(ctrlPanel.state_ !== "stop") {
            const argd = { yesText: qsTr("依然关闭") }
            const callback = (flag)=>{
                if(flag) {
                    ocrStop()
                    delPage()
                }
            }
            qmlapp.popup.dialog("", qsTr("任务正在进行中。\n要结束任务并关闭页面吗？"), callback, "warning", argd)
        }
        else {
            delPage()
        }
    }

    // ========================= 【python调用qml】 =========================

    function onStart(count) {
        console.log("表格识别开始，共 " + count + " 个文件")
    }

    function onReady(path) {
        filesTableView.setProperty(path, "state", qsTr("处理"))
    }

    function onGet(path, res) {
        let time = "0.00"
        if(res.time) {
            time = res.time.toFixed(2)
        }
        let state = ""
        switch(res.code){
            case 100:
                state = "√";break
            case 101:
                state = "√ 空";break
            default:
                state = "× "+res.code
                errorNum++
                break
        }
        filesTableView.set(path, { "time": time, "state": state })
        
        // 添加到结果
        if(res.code === 100) {
            results.push({
                path: path,
                data: res.data,
                format: res.format || "markdown"
            })
            // 显示结果
            resultsTableView.addResult({
                title: path.split("/").pop().split("\\").pop(),
                content: typeof res.data === "string" ? res.data : JSON.stringify(res.data, null, 2)
            })
        }
        
        ctrlPanel.msnStep(1)
    }

    function onEnd(msg) {
        _ocrStop()
        if(!msg || msg === "") {
            let errMsg = ""
            if(errorNum > 0) {
                errMsg = qsTr("%1 个文件识别失败！").arg(errorNum)
            }
            qmlapp.popup.simple(qsTr("表格识别完成"), errMsg, "success")
        }
        else if(msg.startsWith("[Error]")) {
            qmlapp.popup.message(qsTr("识别任务异常"), msg, "error")
        }
        ctrlPanel.stopFinished()
    }

    // ========================= 【布局】 =========================

    // 顶栏控制面板
    CtrlBar {
        id: ctrlPanel
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right

        // 添加文件按钮
        CtrlBarButton {
            text_: qsTr("添加文件")
            icon_: "file"
            enabled: ctrlPanel.state_ === "stop"
            onClicked: {
                qmlapp.utilsConnector.selectFile(qsTr("选择图片"), "", [
                    qsTr("图片")+"(*.jpg *.jpe *.jpeg *.jfif *.png *.webp *.bmp *.tif *.tiff)",
                    qsTr("PDF文档")+"(*.pdf)",
                    qsTr("所有文件")+"(*.*)"
                ], tabPage.addImages, true)
            }
        }

        // 清空按钮
        CtrlBarButton {
            text_: qsTr("清空")
            icon_: "delete"
            enabled: ctrlPanel.state_ === "stop"
            onClicked: {
                filesTableView.clear()
                results = []
            }
        }

        // 开始/停止按钮
        CtrlBarButton {
            text_: ctrlPanel.state_ === "stop" ? qsTr("开始识别") : qsTr("停止")
            icon_: ctrlPanel.state_ === "stop" ? "play" : "stop"
            onClicked: {
                if(ctrlPanel.state_ === "stop") {
                    ctrlPanel.runStarted()
                    ocrStart()
                }
                else {
                    ctrlPanel.stopStarted()
                    ocrStop()
                }
            }
        }

        // 导出按钮
        CtrlBarButton {
            text_: qsTr("导出Excel")
            icon_: "save"
            enabled: ctrlPanel.state_ === "stop" && results.length > 0
            onClicked: {
                qmlapp.utilsConnector.selectFile(qsTr("导出表格识别结果"), "", [
                    qsTr("Excel文件")+" (*.xlsx)",
                    qsTr("CSV文件")+" (*.csv)",
                    qsTr("JSON文件")+" (*.json)"
                ], function(filePath) {
                    if(filePath) {
                        let format = "excel"
                        if(filePath.endsWith(".csv")) format = "csv"
                        else if(filePath.endsWith(".json")) format = "json"

                        const result = tabPage.callPy("exportResults", filePath, format)
                        if(result.code === 100) {
                            qmlapp.popup.simple(qsTr("导出成功"), result.data, "success")
                        } else {
                            qmlapp.popup.message(qsTr("导出失败"), result.data, "error")
                        }
                    }
                }, false, true)  // selectExisting=false, saveMode=true
            }
        }
    }

    // 拖入图片的回调
    DropArea_ {
        anchors.fill: mainContainer
        enable: ctrlPanel.state_ === "stop"
        callback: tabPage.addImages
    }

    // 主区域容器
    Item {
        id: mainContainer
        anchors.top: ctrlPanel.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom

        // 分割线拖动组件
        SplitView {
            anchors.fill: parent
            orientation: Qt.Horizontal

            // 左侧面板
            Item {
                SplitView.preferredWidth: parent.width * 0.35
                SplitView.minimumWidth: 200

                // 双层切换面板
                TabPanel {
                    id: tabPanel
                    anchors.fill: parent

                    // 文件面板
                    tabsModel: [
                        {title: qsTr("文件"), component: filesPanel},
                        {title: qsTr("设置"), component: configsPanel},
                    ]
                }
            }

            // 右侧：结果面板
            Item {
                SplitView.fillWidth: true

                ResultsTableView {
                    id: resultsTableView
                    anchors.fill: parent
                }
            }
        }
    }

    // ========================= 【面板组件】 =========================

    // 文件面板
    Component {
        id: filesPanel

        FilesTableView {
            id: filesTableView
        }
    }

    // 设置面板
    Component {
        id: configsPanel

        TableOCRConfigs {
            id: configsComp
        }
    }

    // 组件别名
    property alias filesTableView: tabPanel.firstLoader.item
    property alias configsComp: tabPanel.lastLoader.item
}
