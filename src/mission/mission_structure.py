# ===============================================
# =============== 结构化识别 - 任务管理器 ===============
# ===============================================

"""
文档结构化识别任务管理器
用于处理表格识别、版式分析等结构化OCR任务
"""

import os
from typing import Dict, Any, List, Optional

from umi_log import logger
from .mission import Mission
from ..ocr.api import getApiOcr, _ensureInitialized
from ..ocr.output.table_converter import TableConverter

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

DocSuf = [
    ".pdf",
    ".xps",
    ".epub",
]


class __MissionStructureClass(Mission):
    """
    文档结构化识别任务管理器
    
    处理表格识别、版式分析等需要结构化输出的OCR任务。
    支持多种输出格式：Markdown、JSON、HTML、Excel。
    """
    
    def __init__(self):
        super().__init__()
        self._apiKey = "pp_structure"
        self._api = None
        self._output_format = "markdown"
    
    # ========================= 【重载】 =========================
    
    def addMissionList(self, msnInfo, msnList):
        """添加任务列表"""
        # 获取输出格式
        argd = msnInfo.get("argd", {})
        self._output_format = argd.get("structure.output_format", "markdown")
        
        # 检查任务合法性
        for i in range(len(msnList) - 1, -1, -1):
            if "path" in msnList[i]:
                p = msnList[i]["path"]
                ext = os.path.splitext(p)[-1].lower()
                if ext not in ImageSuf and ext not in DocSuf:
                    logger.warning(f"添加结构化任务时，第{i}项的路径不是支持的文件类型：{p}")
                    del msnList[i]
            elif "bytes" not in msnList[i] and "base64" not in msnList[i]:
                logger.warning(f"添加结构化任务时，第{i}项不含 path、bytes、base64")
                del msnList[i]
        
        return super().addMissionList(msnInfo, msnList)
    
    def msnPreTask(self, msnInfo):
        """用于更新api和参数"""
        # 确保API已初始化
        if not self._api:
            _ensureInitialized()
            self._api = getApiOcr(self._apiKey, msnInfo.get("argd", {}))
            if not self._api or isinstance(self._api, str):
                logger.error(f"MissionStructure: 初始化结构化引擎失败: {self._api}")
                return "[Error] MissionStructure: Failed to initialize structure engine"
        
        # 更新配置
        argd = self._dictShortKey(msnInfo.get("argd", {}))
        msg = self._api.start(argd)
        if msg.startswith("[Error]"):
            logger.error(f"结构化引擎启动失败: {msg}")
            return msg
        
        return ""
    
    def msnTask(self, msnInfo, msn):
        """执行结构化识别任务"""
        argd = msnInfo.get("argd", {})
        output_format = argd.get("structure.output_format", self._output_format)
        
        # 执行识别
        if "path" in msn:
            res = self._api.recognize(msn["path"], output_format=output_format)
            res["path"] = msn["path"]
        elif "bytes" in msn:
            res = self._api.recognize(msn["bytes"], output_format=output_format)
        elif "base64" in msn:
            res = self._api.runBase64(msn["base64"])
        else:
            res = {
                "code": 901,
                "data": f"[Error] Unknown task type.\n【异常】未知的任务类型。\n{str(msn)[:100]}",
            }
        
        return res
    
    # ========================= 【qml接口】 =========================
    
    def getStatus(self):
        """返回当前状态"""
        return {
            "apiKey": self._apiKey,
            "outputFormat": self._output_format,
            "missionListsLength": self.getMissionListsLength(),
        }
    
    def setOutputFormat(self, format_type: str):
        """设置输出格式"""
        if format_type in ["markdown", "json", "html", "excel"]:
            self._output_format = format_type
            return "[Success]"
        return f"[Error] 不支持的输出格式: {format_type}"
    
    def convertResult(
        self,
        result: Dict[str, Any],
        output_format: str,
        output_path: Optional[str] = None
    ) -> Any:
        """
        转换识别结果为指定格式
        
        Args:
            result: 识别结果
            output_format: 目标格式
            output_path: 输出文件路径（Excel格式需要）
            
        Returns:
            转换后的结果
        """
        if result.get("code") != 100:
            return result
        
        data = result.get("data", {})
        
        # 如果数据中包含表格
        tables = []
        if isinstance(data, dict) and "tables" in data:
            tables = data["tables"]
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("type") == "table":
                    tables.append(item)
        
        if not tables:
            # 没有表格，返回原始结果
            return result
        
        try:
            converted = TableConverter.convert(
                tables,
                output_format,
                output_path=output_path
            )
            
            if output_format == "excel":
                return {
                    "code": 100,
                    "data": f"Excel已保存至: {output_path}",
                    "format": "excel",
                    "path": output_path,
                }
            else:
                return {
                    "code": 100,
                    "data": converted,
                    "format": output_format,
                }
        except Exception as e:
            logger.error(f"结果转换失败: {e}", exc_info=True)
            return {
                "code": 904,
                "data": f"[Error] 结果转换失败: {e}",
            }
    
    def exportToExcel(self, result: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """
        将表格结果导出为Excel
        
        Args:
            result: 识别结果
            output_path: 输出文件路径
            
        Returns:
            导出结果
        """
        return self.convertResult(result, "excel", output_path)
    
    def _dictShortKey(self, d):
        """将字典中配置项的长key转为短key"""
        newD = {}
        key1 = "structure."
        key2 = key1 + self._apiKey + "."
        for k in d:
            if k.startswith(key2):
                newD[k[len(key2):]] = d[k]
            elif k.startswith(key1):
                newD[k[len(key1):]] = d[k]
        return newD


# 全局 结构化任务管理器
MissionStructure = __MissionStructureClass()


# ========================= 【智能抽取任务管理器】 =========================

class __MissionChatClass(Mission):
    """
    智能信息抽取任务管理器
    
    使用PP-ChatOCRv4进行智能问答和关键信息抽取。
    """
    
    def __init__(self):
        super().__init__()
        self._apiKey = "pp_chat"
        self._api = None
        self._default_prompt = ""
    
    def addMissionList(self, msnInfo, msnList):
        """添加任务列表"""
        argd = msnInfo.get("argd", {})
        self._default_prompt = argd.get("chat.prompt", "")
        
        # 检查任务合法性
        for i in range(len(msnList) - 1, -1, -1):
            if "path" in msnList[i]:
                p = msnList[i]["path"]
                ext = os.path.splitext(p)[-1].lower()
                if ext not in ImageSuf and ext not in DocSuf:
                    logger.warning(f"添加智能抽取任务时，第{i}项不是支持的文件类型：{p}")
                    del msnList[i]
            elif "bytes" not in msnList[i] and "base64" not in msnList[i]:
                logger.warning(f"添加智能抽取任务时，第{i}项不含 path、bytes、base64")
                del msnList[i]
        
        return super().addMissionList(msnInfo, msnList)
    
    def msnPreTask(self, msnInfo):
        """用于更新api和参数"""
        if not self._api:
            _ensureInitialized()
            self._api = getApiOcr(self._apiKey, msnInfo.get("argd", {}))
            if not self._api or isinstance(self._api, str):
                logger.error(f"MissionChat: 初始化智能抽取引擎失败: {self._api}")
                return "[Error] MissionChat: Failed to initialize chat engine"
        
        argd = self._dictShortKey(msnInfo.get("argd", {}))
        msg = self._api.start(argd)
        if msg.startswith("[Error]"):
            logger.error(f"智能抽取引擎启动失败: {msg}")
            return msg
        
        return ""
    
    def msnTask(self, msnInfo, msn):
        """执行智能抽取任务"""
        argd = msnInfo.get("argd", {})
        prompt = msn.get("prompt", argd.get("chat.prompt", self._default_prompt))
        
        if "path" in msn:
            res = self._api.recognize(msn["path"], prompt=prompt)
            res["path"] = msn["path"]
        elif "bytes" in msn:
            res = self._api.recognize(msn["bytes"], prompt=prompt)
        elif "base64" in msn:
            import base64
            image_bytes = base64.b64decode(msn["base64"])
            res = self._api.recognize(image_bytes, prompt=prompt)
        else:
            res = {
                "code": 901,
                "data": "[Error] Unknown task type.",
            }
        
        return res
    
    def askQuestion(self, image_path: str, question: str) -> Dict[str, Any]:
        """
        对文档提问
        
        Args:
            image_path: 图片路径
            question: 问题
            
        Returns:
            回答结果
        """
        if not self._api:
            _ensureInitialized()
            self._api = getApiOcr(self._apiKey, {})
        
        return self._api.recognize(image_path, prompt=question)
    
    def extractKeyValues(
        self,
        image_path: str,
        keys: List[str]
    ) -> Dict[str, Any]:
        """
        提取指定的键值对信息
        
        Args:
            image_path: 图片路径
            keys: 要提取的字段名列表
            
        Returns:
            键值对结果
        """
        prompt = f"请从图片中提取以下信息：{', '.join(keys)}。以JSON格式返回结果。"
        return self.askQuestion(image_path, prompt)
    
    def getStatus(self):
        """返回当前状态"""
        return {
            "apiKey": self._apiKey,
            "defaultPrompt": self._default_prompt,
            "missionListsLength": self.getMissionListsLength(),
        }
    
    def setApiKey(self, api_key: str, secret_key: str = "") -> str:
        """
        设置API Key
        
        Args:
            api_key: 百度千帆 API Key
            secret_key: 百度千帆 Secret Key（可选）
            
        Returns:
            设置结果
        """
        if not api_key:
            return "[Error] API Key不能为空"
        
        # 重新初始化引擎
        config = {
            "api_key": api_key,
            "secret_key": secret_key,
        }
        
        self._api = getApiOcr(self._apiKey, config)
        if isinstance(self._api, str):
            return self._api
        
        return "[Success]"
    
    def _dictShortKey(self, d):
        """将字典中配置项的长key转为短key"""
        newD = {}
        key1 = "chat."
        key2 = key1 + self._apiKey + "."
        for k in d:
            if k.startswith(key2):
                newD[k[len(key2):]] = d[k]
            elif k.startswith(key1):
                newD[k[len(key1):]] = d[k]
        return newD


# 全局 智能抽取任务管理器
MissionChat = __MissionChatClass()
