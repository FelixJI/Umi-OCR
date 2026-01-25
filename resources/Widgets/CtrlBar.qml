// ==========================================
// =============== 控制按钮栏 ===============
// ==========================================

import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: barRoot
    implicitHeight: size_.line * 2

    // 状态管理：stop, run, pause
    property string state_: "stop"

    // 任务进度相关
    property int msnTotal: 0
    property int msnFinished: 0

    // 状态切换方法
    function runStarted() { state_ = "run" }
    function pauseStarted() { state_ = "pause" }
    function resumeFinished() { state_ = "run" }
    function stopStarted() { state_ = "stop" }
    function stopFinished() {
        state_ = "stop"
        msnFinished = 0
        msnTotal = 0
    }

    // 任务进度步进
    function msnStep(step = 1) {
        msnFinished += step
    }

    // 子组件会自动添加到这里
    default property alias content: rowItem.children

    Row {
        id: rowItem
        anchors.fill: parent
        spacing: size_.smallSpacing
    }
}
