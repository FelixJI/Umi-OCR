# ========================================
# =============== 表格识别页 ===============
# ========================================

"""
表格识别页面连接器
使用PP-StructureV3进行表格识别和文档结构化
支持输出格式：Markdown、JSON、HTML、Excel
"""

import os
import time
from typing import Dict, Any, List, Optional

from umi_log import logger
from .page import Page
from ..mission.mission_structure import MissionStructure
from ..ocr.output.table_converter import TableConverter
from ..utils.utils import allowedFileName


class TableOCR(Page):
    """表格识别页面类"""
    
    def __init__(self, *args):
        super().__init__(*args)
        self.argd = None
        self.msnID = ""
        self.results = []  # 存储识别结果
        self._output_format = "markdown"
    
    # ========================= 【qml调用python】 =========================
    
    def msnPaths(self, paths: List[str], argd: Dict[str, Any]) -> str:
        """
        接收路径列表和配置参数字典，开始表格识别任务
        
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
        
        # 获取输出格式
        self._output_format = argd.get("structure.output_format", "markdown")
        
        # 清空之前的结果
        self.results = []
        
        # 路径转为任务列表格式
        msnList = [{"path": x} for x in paths]
        self.msnID = MissionStructure.addMissionList(msnInfo, msnList)
        
        if self.msnID.startswith("[Error]"):
            self._onEnd(None, f"{self.msnID}\n添加任务失败。")
        else:
            logger.debug(f"添加表格识别任务成功 {self.msnID}")
        
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
                    logger.warning(f"表格识别无法创建目录： {d}", exc_info=True)
                    self._onEnd(
                        None,
                        f'[Error] Failed to create directory: "{d}"\n【异常】无法创建目录。',
                    )
                    return False
            argd["mission.dir"] = d
        
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
        logger.debug("表格识别任务开始")
        self.callQml("onStart", len(msnInfo.get("msnList", [])))
    
    def _onReady(self, msnInfo: Dict, msn: Dict) -> None:
        """单个任务准备完成回调"""
        path = msn.get("path", "")
        logger.debug(f"表格识别准备: {path}")
        self.callQml("onReady", path)
    
    def _onGet(self, msnInfo: Dict, msn: Dict, result: Dict) -> None:
        """单个任务完成回调"""
        path = msn.get("path", "")
        
        if result.get("code") == 100:
            # 保存结果
            self.results.append({
                "path": path,
                "data": result.get("data"),
                "format": result.get("format", self._output_format),
            })
            logger.debug(f"表格识别成功: {path}")
        else:
            logger.warning(f"表格识别失败: {path}, {result.get('data')}")
        
        # 通知前端
        self.callQml("onGet", path, result)
    
    def _onEnd(self, msnInfo: Optional[Dict], msg: str) -> None:
        """任务结束回调"""
        if msg:
            logger.info(f"表格识别任务结束: {msg}")
        else:
            logger.info(f"表格识别任务完成，共处理 {len(self.results)} 个文件")
        
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
    
    def exportResult(
        self,
        result: Dict,
        output_format: str,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        导出识别结果
        
        Args:
            result: 识别结果
            output_format: 输出格式 (markdown/json/html/excel)
            output_path: 输出文件路径（excel格式必需）
            
        Returns:
            导出结果
        """
        try:
            data = result.get("data")
            if not data:
                return {"code": 101, "data": "无数据可导出"}
            
            # 提取表格数据
            tables = []
            if isinstance(data, dict) and "tables" in data:
                tables = data["tables"]
            elif isinstance(data, list):
                tables = data
            elif isinstance(data, str):
                # 如果是字符串（如Markdown），直接返回
                return {"code": 100, "data": data, "format": output_format}
            
            if not tables:
                return {"code": 101, "data": "未检测到表格"}
            
            # 转换格式
            converted = TableConverter.convert(
                tables,
                output_format,
                output_path=output_path
            )
            
            if output_format == "excel":
                return {
                    "code": 100,
                    "data": f"Excel已保存至: {output_path}",
                    "path": output_path,
                }
            else:
                return {"code": 100, "data": converted, "format": output_format}
                
        except Exception as e:
            logger.error(f"导出失败: {e}", exc_info=True)
            return {"code": 904, "data": f"[Error] 导出失败: {e}"}
    
    def exportAllToExcel(self, output_dir: str) -> Dict[str, Any]:
        """
        将所有结果导出为Excel文件
        
        Args:
            output_dir: 输出目录
            
        Returns:
            导出结果
        """
        if not self.results:
            return {"code": 101, "data": "无结果可导出"}
        
        exported = []
        errors = []
        
        for result in self.results:
            path = result.get("path", "")
            filename = os.path.splitext(os.path.basename(path))[0]
            output_path = os.path.join(output_dir, f"{filename}_table.xlsx")
            
            export_result = self.exportResult(result, "excel", output_path)
            if export_result.get("code") == 100:
                exported.append(output_path)
            else:
                errors.append(f"{path}: {export_result.get('data')}")
        
        if exported:
            msg = f"成功导出 {len(exported)} 个文件"
            if errors:
                msg += f"，{len(errors)} 个失败"
            return {"code": 100, "data": msg, "files": exported, "errors": errors}
        else:
            return {"code": 904, "data": "导出失败", "errors": errors}
    
    def getAvailableFormats(self) -> List[Dict[str, str]]:
        """获取可用的输出格式列表"""
        return [
            {"value": "markdown", "label": "Markdown"},
            {"value": "json", "label": "JSON"},
            {"value": "html", "label": "HTML"},
            {"value": "excel", "label": "Excel (.xlsx)"},
        ]
    
    def setOutputFormat(self, format_type: str) -> str:
        """设置默认输出格式"""
        if format_type in ["markdown", "json", "html", "excel"]:
            self._output_format = format_type
            return "[Success]"
        return f"[Error] 不支持的格式: {format_type}"
    
    def cancelMsn(self) -> None:
        """取消当前任务"""
        if self.msnID:
            MissionStructure.cancelMissionList(self.msnID)
            logger.info(f"取消表格识别任务: {self.msnID}")
            self.msnID = ""
    
    def getMsnStatus(self) -> Dict[str, Any]:
        """获取任务状态"""
        return MissionStructure.getStatus()
