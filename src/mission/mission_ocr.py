# ===============================================
# =============== OCR - 任务管理器 ===============
# ===============================================

"""
一种任务管理器为全局单例，不同标签页要执行同一种任务，要访问对应的任务管理器。
任务管理器中有一个引擎API实例，所有任务均使用该API。
标签页可以向任务管理器提交一组任务队列，其中包含了每一项任务的信息，及总体的参数和回调。

支持多种OCR引擎：
- pp_ocrv5: PP-OCRv5 标准识别
- paddle_vl: PaddleOCR-VL 视觉语言模型
- pp_structure: PP-StructureV3 文档结构化
- pp_chat: PP-ChatOCRv4 智能抽取
"""

import os
from typing import Dict, Any, Optional

from umi_log import logger
from .mission import Mission
from ..ocr.tbpu import getParser, IgnoreArea
from ..ocr.api import getApiOcr, getLocalOptions, getAvailableEngines, getDefaultEngine, getAllEngineOptions
from ..utils.utils import argdIntConvert
from ..utils.image_preprocessing import ImagePreprocessor

# 合法文件后缀
ImageSuf = [
    ".jpg",
    ".jpe",
    ".jpeg",
    ".jfif",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
]


class __MissionOcrClass(Mission):
    def __init__(self):
        super().__init__()
        self._apiKey = ""  # 当前api类型
        self._api = None  # 当前引擎api对象
        self._preprocessor = None  # 图像预处理器

    # ========================= 【重载】 =========================

    # msnInfo: { 回调函数"onXX", 参数"argd":{"tbpu.xx", "ocr.xx", "preprocessing.xx"} }
    # msnList: [ { "path", "bytes", "base64" } ]
    def addMissionList(self, msnInfo, msnList):  # 添加任务列表
        # 实例化 tbpu 文本后处理模块
        msnInfo["tbpu"] = []
        argd = msnInfo["argd"]
        # 忽略区域
        if "tbpu.ignoreArea" in argd:
            iArea = argd["tbpu.ignoreArea"]
            if isinstance(iArea, list) and len(iArea) > 0:
                msnInfo["tbpu"].append(IgnoreArea(iArea))
        # 获取排版解析器对象
        if "tbpu.parser" in argd:
            msnInfo["tbpu"].append(getParser(argd["tbpu.parser"]))
        
        # 初始化图像预处理器
        preprocessing_config = {k: v for k, v in argd.items() if k.startswith("preprocessing.")}
        if preprocessing_config.get("preprocessing.enabled", False):
            msnInfo["preprocessor"] = ImagePreprocessor(preprocessing_config)
        else:
            msnInfo["preprocessor"] = None
        
        # 检查任务合法性
        for i in range(len(msnList) - 1, -1, -1):
            if "path" in msnList[i]:
                p = msnList[i]["path"]
                if os.path.splitext(p)[-1].lower() not in ImageSuf:
                    logger.warning(f"添加OCR任务时，第{i}项的路径path不是图片：{p}")
                    del msnList[i]
            elif "bytes" not in msnList[i] and "base64" not in msnList[i]:
                logger.warning(f"添加OCR任务时，第{i}项不含 path、bytes、base64")
                del msnList[i]
        return super().addMissionList(msnInfo, msnList)

    def msnPreTask(self, msnInfo):  # 用于更新api和参数
        # 获取引擎类型
        argd = msnInfo.get("argd", {})
        engine_type = argd.get("ocr.engine_type", "")
        
        # 检查API对象
        if not self._api or (engine_type and engine_type != self._apiKey):
            # 使用指定引擎或默认引擎
            from ..ocr.api import _ensureInitialized
            _ensureInitialized()
            
            target_engine = engine_type if engine_type else getDefaultEngine()
            if not target_engine:
                target_engine = "pp_ocrv5"  # 回退到默认
            
            self._api = getApiOcr(target_engine, argd)
            if not self._api or isinstance(self._api, str):
                logger.error(
                    f"MissionOCR: Failed to initialize OCR engine {target_engine}: {self._api}"
                )
                return f"[Error] MissionOCR: Failed to initialize OCR engine: {self._api}"
            
            self._apiKey = target_engine

        # 设置预处理器（如果引擎支持）
        preprocessor = msnInfo.get("preprocessor")
        if preprocessor and hasattr(self._api, 'set_preprocessor'):
            self._api.set_preprocessor(preprocessor)

        # 传递配置
        short_argd = self._dictShortKey(argd)
        msg = self._api.start(short_argd)
        if msg.startswith("[Error]"):
            logger.error(f"OCR引擎启动失败： {msg}")
            return msg  # 更新失败，结束该队列
        else:
            return ""  # 更新成功

    def msnTask(self, msnInfo, msn):  # 执行msn
        if "path" in msn:
            res = self._api.runPath(msn["path"])
            res["path"] = msn["path"]  # 结果字典中补充参数
        elif "bytes" in msn:
            res = self._api.runBytes(msn["bytes"])
        elif "base64" in msn:
            res = self._api.runBase64(msn["base64"])
        else:
            res = {
                "code": 901,
                "data": f"[Error] Unknown task type.\n【异常】未知的任务类型。\n{str(msn)[:100]}",
            }
        # 任务成功时的后处理
        if res["code"] == 100:
            # 计算平均置信度
            score, num = 0, 0
            for r in res["data"]:
                score += r["score"]
                num += 1
            if num > 0:
                score /= num
            res["score"] = score
            # 执行 tbpu
            if msnInfo["tbpu"]:
                for tbpu in msnInfo["tbpu"]:
                    res["data"] = tbpu.run(res["data"])
                    # 如果忽略区域等处理将所有文本删除，则结束tbpu
                    if not res["data"]:
                        res["code"] = 101
                        res["data"] = ""
                        break
        return res

    # ========================= 【qml接口】 =========================

    def getStatus(self):  # 返回当前状态
        return {
            "apiKey": self._apiKey,
            "missionListsLength": self.getMissionListsLength(),
        }

    def setApi(self, apiKey, info):  # 设置api
        # 成功返回 [Success] ，失败返回 [Error] 开头的字符串
        self._apiKey = apiKey
        info = self._dictShortKey(info)
        # 如果api对象已启动，则先停止
        if self._api:
            self._api.stop()
        # 获取新api对象
        res = getApiOcr(apiKey, info)
        # 失败
        if isinstance(res, str):
            self._apiKey = ""
            self._api = None
            return res
        # 成功
        else:
            self._api = res
            return "[Success]"

    def getAvailableEngines(self):
        """获取所有可用的OCR引擎列表"""
        return getAvailableEngines()

    def getCurrentEngine(self):
        """获取当前使用的引擎"""
        return self._apiKey

    def setEngine(self, engine_type: str, config: Dict[str, Any] = None) -> str:
        """
        切换OCR引擎
        
        Args:
            engine_type: 引擎类型 (pp_ocrv5/paddle_vl/pp_structure/pp_chat)
            config: 引擎配置
            
        Returns:
            "[Success]" 或 "[Error]..."
        """
        if config is None:
            config = {}
        return self.setApi(engine_type, config)

    # 将字典中配置项的长key转为短key
    # 如： ocr.win32_PaddleOCR-json.path → path
    def _dictShortKey(self, d):
        newD = {}
        key1 = "ocr."
        key2 = key1 + self._apiKey + "."
        for k in d:
            if k.startswith(key2):
                newD[k[len(key2) :]] = d[k]
            elif k.startswith(key1):
                newD[k[len(key1) :]] = d[k]
        return newD

    # ========================= 【qml接口】 =========================

    def getLocalOptions(self):
        if self._apiKey:
            return getLocalOptions(self._apiKey)
        else:
            return {}

    def getAllEngineOptions(self):
        """获取所有引擎的配置选项，用于初始化OcrManager"""
        return getAllEngineOptions()


# 全局 OCR任务管理器
MissionOCR = __MissionOcrClass()
