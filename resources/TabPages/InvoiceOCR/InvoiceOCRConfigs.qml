// ==============================================
// =============== 发票识别的配置项 ===============
// ==============================================

import QtQuick 2.15
import "../../Configs"

Configs {
    category_: "InvoiceOCR"

    configDict: {
        // OCR 引擎选择
        "ocr": qmlapp.globalConfigs.ocrManager.deploy(this, "ocr"),

        // 后处理
        "tbpu": {
            "title": qsTr("OCR文本后处理"),
            "type": "group",

            "parser": qmlapp.globalConfigs.utilsDicts.getTbpuParser(),
        },

        // 发票识别参数
        "invoice": {
            "title": qsTr("发票识别设置"),
            "type": "group",

            "type": {
                "title": qsTr("发票类型"),
                "toolTip": qsTr("选择要识别的发票类型"),
                "optionsList": [
                    ["vat_invoice", qsTr("增值税发票")],
                    ["invoice", qsTr("通用发票识别")],
                    ["train_ticket", qsTr("火车票")],
                    ["taxi_invoice", qsTr("出租车发票")],
                    ["air_ticket", qsTr("机票行程单")],
                    ["quota_invoice", qsTr("定额发票")],
                    ["receipt", qsTr("收据/小票")],
                ],
            },
            "engine": {
                "title": qsTr("识别引擎"),
                "toolTip": qsTr("选择云OCR服务商"),
                "optionsList": [
                    ["baidu_ocr", qsTr("百度智能云OCR")],
                    ["tencent_ocr", qsTr("腾讯云OCR")],
                    ["alibaba_ocr", qsTr("阿里云OCR")],
                ],
            },
        },

        // API配置
        "api": {
            "title": qsTr("API配置"),
            "type": "group",

            "api_key": {
                "title": qsTr("API Key / AccessKey ID"),
                "toolTip": qsTr("云服务商的API密钥"),
                "type": "text",
                "default": "",
                "isPassword": true,
            },
            "secret_key": {
                "title": qsTr("Secret Key / AccessKey Secret"),
                "toolTip": qsTr("云服务商的密钥Secret"),
                "type": "text",
                "default": "",
                "isPassword": true,
            },
            "region": {
                "title": qsTr("服务区域"),
                "toolTip": qsTr("云服务的地域节点"),
                "optionsList": [
                    ["", qsTr("默认")],
                    ["cn-hangzhou", qsTr("杭州")],
                    ["cn-shanghai", qsTr("上海")],
                    ["cn-beijing", qsTr("北京")],
                    ["ap-guangzhou", qsTr("广州")],
                ],
            },
        },

        // 批量任务
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
                "toolTip": qsTr("必须先指定「保存到指定目录」才生效"),
                "type": "file",
                "selectExisting": true,
                "selectFolder": true,
                "dialogTitle": qsTr("发票识别结果保存目录"),
            },
        },

        // 导出设置
        "export": {
            "title": qsTr("导出设置"),
            "type": "group",
            "enabledFold": true,
            "fold": true,

            "format": {
                "title": qsTr("默认导出格式"),
                "toolTip": qsTr("批量导出时的默认格式"),
                "optionsList": [
                    ["excel", "Excel (.xlsx)"],
                    ["csv", "CSV (.csv)"],
                    ["json", "JSON (.json)"],
                ],
            },
            "include_path": {
                "title": qsTr("包含文件路径"),
                "toolTip": qsTr("导出结果中包含原始文件路径"),
                "default": true,
            },
            "merge_results": {
                "title": qsTr("合并同类发票"),
                "toolTip": qsTr("将相同类型的发票合并到同一工作表"),
                "default": false,
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
