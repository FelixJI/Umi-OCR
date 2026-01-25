// ===========================================
// =============== 发票识别结果视图 ===============
// ===========================================

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../Widgets"

Item {
    id: root
    
    ListModel { id: resultsModel }
    
    // ========================= 【对外接口】 =========================
    
    // 添加发票识别结果
    function addInvoiceResult(res) {
        resultsModel.append({
            "title": res.title || "",
            "invoiceType": res.invoiceType || qsTr("未知类型"),
            "content": res.content || "",
            "timestamp": Date.now(),
        })
        
        // 自动滚动到底部
        if(autoToBottom && listView.count > 0) {
            listView.positionViewAtEnd()
        }
    }
    
    // 清空结果
    function clear() {
        resultsModel.clear()
    }
    
    // 获取结果数量
    property alias count: resultsModel.count
    property alias model: resultsModel
    
    // ========================= 【布局】 =========================
    
    anchors.fill: parent
    clip: true
    property bool autoToBottom: true
    
    // 空状态提示
    Text {
        anchors.centerIn: parent
        visible: resultsModel.count === 0
        text: qsTr("将发票图片拖入此处\n或点击"添加文件"按钮")
        color: theme.subTextColor
        font.pixelSize: size_.text * 1.2
        horizontalAlignment: Text.AlignHCenter
    }
    
    // 结果列表
    ListView {
        id: listView
        anchors.fill: parent
        anchors.margins: size_.spacing
        model: resultsModel
        spacing: size_.spacing
        clip: true
        
        delegate: Rectangle {
            width: listView.width - (scrollBar.visible ? scrollBar.width + size_.spacing : 0)
            height: contentColumn.height + size_.spacing * 2
            color: theme.bgColor
            border.color: theme.coverColor2
            border.width: 1
            radius: size_.btnRadius
            
            Column {
                id: contentColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: size_.spacing
                spacing: size_.smallSpacing
                
                // 标题栏
                RowLayout {
                    width: parent.width
                    spacing: size_.spacing
                    
                    // 文件名
                    Text {
                        text: model.title
                        color: theme.textColor
                        font.pixelSize: size_.text
                        font.bold: true
                        elide: Text.ElideMiddle
                        Layout.fillWidth: true
                    }
                    
                    // 发票类型标签
                    Rectangle {
                        color: theme.specialBgColor
                        radius: size_.btnRadius / 2
                        implicitWidth: typeLabel.width + size_.spacing
                        implicitHeight: typeLabel.height + size_.smallSpacing
                        
                        Text {
                            id: typeLabel
                            anchors.centerIn: parent
                            text: model.invoiceType
                            color: theme.specialTextColor
                            font.pixelSize: size_.smallText
                        }
                    }
                    
                    // 复制按钮
                    IconTextButton {
                        icon_: "copy"
                        text_: ""
                        toolTip: qsTr("复制内容")
                        onClicked: {
                            qmlapp.utilsConnector.copyText(model.content)
                            qmlapp.popup.simple(qsTr("已复制"), "", "success")
                        }
                    }
                }
                
                // 分隔线
                Rectangle {
                    width: parent.width
                    height: 1
                    color: theme.coverColor2
                }
                
                // 内容区域
                TextArea {
                    width: parent.width
                    text: model.content
                    color: theme.subTextColor
                    font.pixelSize: size_.smallText
                    font.family: "Consolas, Monaco, monospace"
                    wrapMode: TextArea.Wrap
                    readOnly: true
                    selectByMouse: true
                    background: null
                    padding: 0
                    
                    // 限制最大高度
                    implicitHeight: Math.min(contentHeight, 300)
                }
            }
        }
        
        // 滚动条
        ScrollBar.vertical: ScrollBar {
            id: scrollBar
            active: true
            policy: ScrollBar.AsNeeded
        }
    }
    
    // 底部控制栏
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: visible ? bottomBar.height + size_.spacing * 2 : 0
        visible: resultsModel.count > 0
        color: theme.bgColor
        border.color: theme.coverColor2
        border.width: 1
        
        RowLayout {
            id: bottomBar
            anchors.centerIn: parent
            spacing: size_.spacing
            
            Text {
                text: qsTr("共 %1 条识别结果").arg(resultsModel.count)
                color: theme.subTextColor
                font.pixelSize: size_.smallText
            }
            
            Button_ {
                text_: qsTr("全部复制")
                onClicked: {
                    let allContent = []
                    for(let i = 0; i < resultsModel.count; i++) {
                        let item = resultsModel.get(i)
                        allContent.push("=== " + item.title + " (" + item.invoiceType + ") ===")
                        allContent.push(item.content)
                        allContent.push("")
                    }
                    qmlapp.utilsConnector.copyText(allContent.join("\n"))
                    qmlapp.popup.simple(qsTr("已复制全部结果"), "", "success")
                }
            }
            
            Button_ {
                text_: qsTr("清空")
                onClicked: {
                    resultsModel.clear()
                }
            }
        }
    }
}
