// ==========================================
// =============== 控制按钮 ===============
// ==========================================

import QtQuick 2.15
import QtQuick.Layouts 1.15

Button_ {
    id: btn
    property string icon_: ""
    property string text_: ""
    property color iconColor: theme.subTextColor

    width: btnText.contentWidth + size_.line + size_.smallSpacing * 3
    implicitWidth: width

    contentItem: Item {
        anchors.fill: parent
        Icon_ {
            id: btnIcon
            icon: icon_
            height: size_.line * 0.7
            width: size_.line * 0.7
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: size_.smallSpacing
            color: btn.iconColor
        }
        Text_ {
            id: btnText
            anchors.left: btnIcon.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.leftMargin: size_.smallSpacing * 0.5
            anchors.rightMargin: size_.smallSpacing
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            text: text_
            color: btn.iconColor
        }
    }
}
