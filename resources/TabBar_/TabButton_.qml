// ==================================================
// =============== 水平标签栏的标签按钮 ===============
// ==================================================

import QtQuick 2.15
import QtQuick.Layouts 1.15
import Qt5Compat.GraphicalEffects // 阴影

import "../Widgets"

Rectangle {
    id: btn

    // 设定值
    property string title: "Unknown TabBtn" // 显示的标题
    property int index: -1 // 在标签栏中的序号
    property bool isHovered: false // 自定义悬停状态
    property bool checked: false // 是否选中状态

    // 默认值
    height: size_.hTabBarHeight

    // 背景颜色
    color: checked ? theme.bgColor : (
        isHovered ? theme.coverColor1 : "#00000000"
    )

    // 拖拽时改变透明度和 z-index
    opacity: mouseArea.isDragging ? 0.5 : 1.0
    z: mouseArea.isDragging ? 100 : (checked? 10 : 0)

    // 点击和拖拽处理
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
        cursorShape: Qt.PointingHandCursor
        drag.target: parent // 使用默认拖拽机制，拖拽对象为父级Rectangle
        drag.axis: Drag.XAxis
        drag.threshold: 10
        drag.minimumX: -1000
        drag.maximumX: 10000
        hoverEnabled: true // 启用悬停检测
        preventStealing: false // 允许拖拽事件传播

        property bool isDragging: false
        property real startX: 0
        property real originalX: 0
        property bool leftButtonPressed: false // 跟踪左键是否按下

        onEntered: {
            isHovered = true
        }
        onExited: {
            isHovered = false
        }

        onPressed: function(mouse) {
            if(mouse.button === Qt.LeftButton) {
                leftButtonPressed = true
                isDragging = false
                startX = mouse.x
                originalX = btn.x
            }
        }

        onPositionChanged: function(mouse) {
            // 使用 mouse.buttons 检查当前按下的按钮（复数形式）
            // 或使用我们自己跟踪的 leftButtonPressed 状态
            if(leftButtonPressed && (mouse.buttons & Qt.LeftButton)) {
                // 如果移动距离超过阈值，开始拖拽
                if(!isDragging && Math.abs(mouse.x - startX) > 10) {
                    isDragging = true
                    qmlapp.tab.bar.dragStart(index)
                }
                if(isDragging) {
                    // 更新拖拽指示器位置（基于当前实际位置）
                    qmlapp.tab.bar.dragMoving(index, btn.x)
                }
            }
        }

        onReleased: function(mouse) {
            if(mouse.button === Qt.LeftButton) {
                if(isDragging) {
                    // 拖拽结束
                    qmlapp.tab.bar.dragFinish(index)
                    isDragging = false
                } else {
                    // 点击事件
                    qmlapp.tab.showTabPage(index)
                }
                leftButtonPressed = false
            }
        }

        onClicked: function(mouse) {
            if(mouse.button === Qt.MiddleButton && !qmlapp.tab.barIsLock) {
                qmlapp.tab.closeTabPage(index)
            }
        }
    }

    // 内容布局
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: size_.line*0.2

        // 标题
        Text_ {
            text: title // 外部传入的title

            elide: Text.ElideRight // 隐藏超出宽度
            Layout.fillWidth: true // 填充宽度
            height: btn.height // 适应整个按钮的高度
            color: (isHovered || checked)?theme.textColor:theme.subTextColor
            font.bold: checked
        }

        // 关闭按钮
        Item {
            // 未锁定，且主按钮悬停或选中时才显示
            visible: !qmlapp.tab.barIsLock && (isHovered || checked)
            Layout.alignment: Qt.AlignRight
            Layout.rightMargin: size_.hTabBarHeight * 0.2

            property real size: size_.hTabBarHeight * 0.7
            implicitWidth: size
            implicitHeight: size

            // 关闭按钮图标
            Icon_ {
                anchors.fill: parent
                anchors.margins: parent.size * 0.2
                icon: "no"
                color: theme.textColor
            }

            // 关闭按钮的MouseArea，阻止事件向上传播
            MouseArea {
                id: closeBtnMouseArea
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                hoverEnabled: true

                onClicked: {
                    mouse.accepted = true
                    qmlapp.tab.closeTabPage(index)
                }
            }
        }
    }

    // 侧边小条
    Rectangle{
        visible: !checked
        height: size_.line
        width: 1
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        color: theme.coverColor4
    }

    // 边缘阴影
    layer.enabled: checked
    layer.effect: DropShadow {
        transparentBorder: true
        color: theme.coverColor3
        samples: size_.hTabBarHeight
    }

    // 选中时的放大动画
    property bool enabledAni: false // true是允许动画
    property bool runAni: false
    Timer { // 计时器，保证初始化的一段时间内不允许动画
        running: true
        interval: 300
        onTriggered: enabledAni=true
    }
    onCheckedChanged: {
        if(enabledAni) runAni = checked
    }
    SequentialAnimation{ // 串行动画
        running: qmlapp.enabledEffect && runAni
        // 动画1：放大
        NumberAnimation{
            target: btn
            property: "scale"
            to: 1.2
            duration: 80
            easing.type: Easing.OutCubic
        }
        // 动画2：缩小
        NumberAnimation{
            target: btn
            property: "scale"
            to: 1
            duration: 150
            easing.type: Easing.InCubic
        }
    }
}