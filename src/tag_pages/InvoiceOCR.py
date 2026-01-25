# ========================================
# =============== 发票识别页 ===============
# ========================================

"""
发票识别页面连接器
使用云端OCR服务（百度/腾讯/阿里云）进行发票识别
支持类型：增值税发票、火车票、出租车发票、机票行程单等
"""

import os
import time
from typing import Dict, Any, List, Optional

from umi_log import logger
from .page import Page
from ..mission.mission_invoice import MissionInvoice, INVOICE_TYPES


class InvoiceOCR(Page):
    """发票识别页面类"""
    
    def __init__(self, *args):
        super().__init__(*args)
        self.argd = None
        self.msnID = ""
        self.results = []
        self._engine_type = "baidu_ocr"
        self._invoice_type = "vat_invoice"
    
    # ========================= 【qml调用python】 =========================
    
    def msnPaths(self, paths: List[str], argd: Dict[str, Any]) -> str:
        """
        接收路径列表和配置参数字典，开始发票识别任务
        
        Args:
            paths: 图片/文档路径列表
            argd: 配置参数字典
            
        Returns:
            任务ID或错误信息
        """
        # 任务信息
        msnInfo = {
            "onStart": self._onStart,
            "onReady": self._onReady,
            "onGet": self._onGet,
            "onEnd": self._onEnd,
            "argd": argd,
        }
        
        # 预处理参数
        if not self._preprocessArgd(argd, paths[0]):
            return ""
        
        # 获取配置
        self._engine_type = argd.get("invoice.engine", "baidu_ocr")
        self._invoice_type = argd.get("invoice.type", "vat_invoice")
        
        # 将API配置传递给任务
        argd["invoice.api_key"] = argd.get("api.api_key", "")
        argd["invoice.secret_key"] = argd.get("api.secret_key", "")
        argd["invoice.region"] = argd.get("api.region", "")
        
        # 清空之前的结果
        self.results = []
        MissionInvoice.clearResults()
        
        # 路径转为任务列表格式
        msnList = [{"path": x} for x in paths]
        self.msnID = MissionInvoice.addMissionList(msnInfo, msnList)
        
        if self.msnID.startswith("[Error]"):
            self._onEnd(None, f"{self.msnID}\n添加任务失败。")
        else:
            logger.debug(f"添加发票识别任务成功 {self.msnID}")
        
        return self.msnID
    
    def _preprocessArgd(self, argd: Dict, path0: str) -> bool:
        """预处理参数字典"""
        self.argd = None
        
        # 处理保存路径
        if argd.get("mission.dirType") == "source":
            argd["mission.dir"] = os.path.dirname(path0)
        else:
            d = os.path.abspath(argd.get("mission.dir", "."))
            if not os.path.exists(d):
                try:
                    os.makedirs(d)
                except OSError:
                    logger.warning(f"发票识别无法创建目录： {d}", exc_info=True)
                    self._onEnd(
                        None,
                        f'[Error] Failed to create directory: "{d}"\n【异常】无法创建目录。',
                    )
                    return False
            argd["mission.dir"] = d
        
        # 验证API配置
        api_key = argd.get("api.api_key", "")
        if not api_key:
            self._onEnd(
                None,
                "[Error] API Key未配置。请在设置中配置云服务商的API密钥。"
            )
            return False
        
        # 时间戳
        startTimestamp = time.time()
        argd["startTimestamp"] = startTimestamp
        argd["startDatetime"] = time.strftime(
            r"%Y-%m-%d %H:%M:%S", time.localtime(startTimestamp)
        )
        
        self.argd = argd
        return True
    
    def _onStart(self, msnInfo: Dict) -> None:
        """任务开始回调"""
        logger.debug("发票识别任务开始")
        self.callQml("onStart", len(msnInfo.get("msnList", [])))
    
    def _onReady(self, msnInfo: Dict, msn: Dict) -> None:
        """单个任务准备完成回调"""
        path = msn.get("path", "")
        logger.debug(f"发票识别准备: {path}")
        self.callQml("onReady", path)
    
    def _onGet(self, msnInfo: Dict, msn: Dict, result: Dict) -> None:
        """单个任务完成回调"""
        path = msn.get("path", "")
        
        if result.get("code") == 100:
            # 保存结果
            self.results.append({
                "path": path,
                "data": result.get("data"),
                "invoice_type": result.get("invoice_type", self._invoice_type),
                "invoice_name": result.get("invoice_name", ""),
            })
            logger.debug(f"发票识别成功: {path}")
        else:
            logger.warning(f"发票识别失败: {path}, {result.get('data')}")
        
        # 通知前端
        self.callQml("onGet", path, result)
    
    def _onEnd(self, msnInfo: Optional[Dict], msg: str) -> None:
        """任务结束回调"""
        if msg:
            logger.info(f"发票识别任务结束: {msg}")
        else:
            logger.info(f"发票识别任务完成，共处理 {len(self.results)} 个文件")
        
        self.callQml("onEnd", msg)
    
    def getResults(self) -> List[Dict]:
        """获取所有识别结果"""
        return self.results
    
    def getResultByPath(self, path: str) -> Optional[Dict]:
        """根据路径获取识别结果"""
        for r in self.results:
            if r.get("path") == path:
                return r
        return None
    
    def exportResults(self, output_path: str, format_type: str = "excel") -> Dict[str, Any]:
        """
        导出识别结果
        
        Args:
            output_path: 输出文件路径
            format_type: 输出格式 (json/csv/excel)
            
        Returns:
            导出结果
        """
        if not self.results:
            return {"code": 101, "data": "无结果可导出"}
        
        # 同步结果到MissionInvoice
        MissionInvoice._results = self.results
        
        return MissionInvoice.exportResults(output_path, format_type)
    
    def getInvoiceTypes(self) -> Dict[str, Any]:
        """获取支持的发票类型"""
        return INVOICE_TYPES
    
    def getCloudEngines(self) -> List[Dict[str, str]]:
        """获取可用的云OCR引擎"""
        return MissionInvoice.getCloudEngines()
    
    def setEngine(self, engine_type: str) -> str:
        """设置识别引擎"""
        self._engine_type = engine_type
        return MissionInvoice.setEngine(engine_type)
    
    def setInvoiceType(self, invoice_type: str) -> str:
        """设置发票类型"""
        self._invoice_type = invoice_type
        return MissionInvoice.setInvoiceType(invoice_type)
    
    def recognizeSingle(
        self,
        image_path: str,
        invoice_type: str = None,
        engine_type: str = None,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        识别单张发票（直接调用，不通过任务队列）
        
        Args:
            image_path: 图片路径
            invoice_type: 发票类型
            engine_type: 引擎类型
            config: API配置
            
        Returns:
            识别结果
        """
        return MissionInvoice.recognizeSingle(
            image_path,
            invoice_type or self._invoice_type,
            engine_type or self._engine_type,
            config
        )
    
    def cancelMsn(self) -> None:
        """取消当前任务"""
        if self.msnID:
            MissionInvoice.cancelMissionList(self.msnID)
            logger.info(f"取消发票识别任务: {self.msnID}")
            self.msnID = ""
    
    def getMsnStatus(self) -> Dict[str, Any]:
        """获取任务状态"""
        return MissionInvoice.getStatus()
    
    def clearResults(self) -> None:
        """清空识别结果"""
        self.results = []
        MissionInvoice.clearResults()
