// ==============================================
// =============== 表格识别的配置项 ===============
// ==============================================

import QtQuick 2.15
import "../../Configs"

Configs {
    category_: "TableOCR"

    configDict: {
        // 结构化参数
        "structure": {
            "title": qsTr("表格识别设置"),
            "type": "group",

            "output_format": {
                "title": qsTr("输出格式"),
                "toolTip": qsTr("识别结果的默认输出格式"),
                "optionsList": [
                    ["markdown", "Markdown"],
                    ["json", "JSON"],
                    ["html", "HTML"],
                    ["excel", "Excel"],
                ],
            },
            "table_recognition": {
                "title": qsTr("启用表格识别"),
                "toolTip": qsTr("识别图片中的表格结构"),
                "default": true,
            },
            "layout_analysis": {
                "title": qsTr("启用版式分析"),
                "toolTip": qsTr("分析文档的版式布局"),
                "default": true,
            },
        },

        // 图像预处理
        "preprocessing": {
            "title": qsTr("图像预处理"),
            "type": "group",
            "enabledFold": true,
            "fold": true,

            "enabled": {
                "title": qsTr("启用预处理"),
                "toolTip": qsTr("对图像进行预处理以提高识别准确率"),
                "default": false,
            },
            "denoise": {
                "title": qsTr("降噪强度"),
                "toolTip": qsTr("0=禁用, 1-9奇数值"),
                "default": 0,
                "min": 0,
                "max": 9,
            },
            "sharpen": {
                "title": qsTr("锐化系数"),
                "toolTip": qsTr("1.0=不变"),
                "default": 1.0,
                "min": 0.0,
                "max": 3.0,
                "step": 0.1,
            },
            "contrast": {
                "title": qsTr("对比度"),
                "toolTip": qsTr("1.0=不变"),
                "default": 1.0,
                "min": 0.5,
                "max": 2.0,
                "step": 0.1,
            },
        },

        // 任务参数
        "mission": {
            "title": qsTr("批量任务"),
            "type": "group",

            "recurrence": {
                "title": qsTr("递归读取子文件夹"),
                "toolTip": qsTr("导入文件夹时，导入子文件夹中全部文件"),
                "default": false,
            },
            "dirType": {
                "title": qsTr("保存到"),
                "optionsList": [
                    ["source", qsTr("文件原目录")],
                    ["specify", qsTr("指定目录")],
                ],
            },
            "dir": {
                "title": qsTr("指定目录"),
                "toolTip": qsTr("必须先指定"保存到指定目录"才生效"),
                "type": "file",
                "selectExisting": true,
                "selectFolder": true,
                "dialogTitle": qsTr("表格识别结果保存目录"),
            },
        },

        // 其他设置
        "other": {
            "title": qsTr("其他"),
            "type": "group",
            "enabledFold": true,
            "fold": true,

            "simpleNotificationType": {
                "title": qsTr("完成后通知"),
                "optionsList": [
                    ["default", qsTr("弹出通知")],
                    ["onlyError", qsTr("仅异常时通知")],
                    ["none", qsTr("不通知")],
                ],
            },
        },
    }
}
