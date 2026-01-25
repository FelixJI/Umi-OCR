# ===============================================
# =============== OCR 引擎基类 ===============
# ===============================================

"""
OCR引擎基类定义 - 所有OCR引擎的抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union, Optional
from PIL import Image
import threading
import logging

logger = logging.getLogger(__name__)


class BaseOCREngine(ABC):
    """
    OCR引擎基类
    
    所有OCR引擎实现必须继承此类并实现抽象方法。
    提供统一的接口规范，支持多种输入格式和输出格式。
    """
    
    # 子类需要重写的类属性
    ENGINE_TYPE: str = "base"
    ENGINE_NAME: str = "Base OCR Engine"
    SUPPORTED_FEATURES: List[str] = []
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化引擎
        
        Args:
            config: 引擎配置字典
        """
        self.config = config
        self.lock = threading.Lock()
        self._initialized = False
        self._engine = None
    
    @property
    def engine_type(self) -> str:
        """引擎类型标识"""
        return self.ENGINE_TYPE
    
    @property
    def engine_name(self) -> str:
        """引擎显示名称"""
        return self.ENGINE_NAME
    
    @property
    def supported_features(self) -> List[str]:
        """支持的功能列表"""
        return self.SUPPORTED_FEATURES
    
    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._initialized
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化引擎
        
        Returns:
            初始化是否成功
        """
        pass
    
    @abstractmethod
    def _do_recognize(self, image: Any) -> Dict[str, Any]:
        """
        执行实际的识别操作（子类实现）
        
        Args:
            image: 图像数据（格式由子类定义）
            
        Returns:
            识别结果字典
        """
        pass
    
    def recognize(self, image: Union[str, bytes, Image.Image], **kwargs) -> Dict[str, Any]:
        """
        执行OCR识别
        
        Args:
            image: 图像路径、字节流或PIL.Image对象
            **kwargs: 额外的识别参数
            
        Returns:
            识别结果，格式为:
            {
                "code": int,  # 状态码: 100=成功, 101=无内容, 其他=错误
                "data": list/str,  # 识别结果或错误信息
            }
        """
        with self.lock:
            if not self._initialized:
                try:
                    if not self.initialize():
                        return {"code": 901, "data": "[Error] 引擎初始化失败"}
                except Exception as e:
                    logger.error(f"引擎初始化异常: {e}", exc_info=True)
                    return {"code": 901, "data": f"[Error] 引擎初始化异常: {e}"}
            
            try:
                return self._do_recognize(image, **kwargs)
            except Exception as e:
                logger.error(f"识别执行异常: {e}", exc_info=True)
                return {"code": 902, "data": f"[Error] 识别执行异常: {e}"}
    
    def runPath(self, img_path: str) -> Dict[str, Any]:
        """
        识别图片路径（兼容旧接口）
        
        Args:
            img_path: 图片文件路径
            
        Returns:
            识别结果字典
        """
        return self.recognize(img_path)
    
    def runBytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        识别图片字节流（兼容旧接口）
        
        Args:
            image_bytes: 图片字节流
            
        Returns:
            识别结果字典
        """
        return self.recognize(image_bytes)
    
    def runBase64(self, image_base64: str) -> Dict[str, Any]:
        """
        识别Base64编码的图片（兼容旧接口）
        
        Args:
            image_base64: Base64编码的图片字符串
            
        Returns:
            识别结果字典
        """
        import base64
        try:
            image_bytes = base64.b64decode(image_base64)
            return self.recognize(image_bytes)
        except Exception as e:
            return {"code": 903, "data": f"[Error] Base64解码失败: {e}"}
    
    def start(self, argd: Dict[str, Any]) -> str:
        """
        启动/重启引擎（兼容旧接口）
        
        Args:
            argd: 配置参数
            
        Returns:
            "" 表示成功，"[Error]..." 表示失败
        """
        try:
            # 检查是否需要重启
            if self._needs_restart(argd):
                self.stop()
                self.config.update(argd)
                if not self.initialize():
                    return "[Error] 引擎重启失败"
            return ""
        except Exception as e:
            logger.error(f"引擎启动失败: {e}", exc_info=True)
            return f"[Error] 引擎启动失败: {e}"
    
    def stop(self):
        """停止引擎"""
        with self.lock:
            self._engine = None
            self._initialized = False
            logger.info(f"{self.ENGINE_NAME} 已停止")
    
    def _needs_restart(self, new_config: Dict[str, Any]) -> bool:
        """
        检查是否需要重启引擎
        
        Args:
            new_config: 新的配置参数
            
        Returns:
            是否需要重启
        """
        # 默认实现：检查关键参数是否变化
        key_params = ["lang", "use_angle_cls", "use_doc_orientation_classify"]
        for key in key_params:
            if key in new_config and self.config.get(key) != new_config.get(key):
                return True
        return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        获取配置项定义（用于UI生成）
        
        Returns:
            配置项定义字典
        """
        return {}
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            默认配置字典
        """
        return {}
    
    @staticmethod
    def parse_result_to_umi_format(raw_data: List, source: str = "ocr") -> List[Dict]:
        """
        将原始识别结果转换为Umi-OCR标准格式
        
        Args:
            raw_data: 原始识别数据
            source: 数据来源标识
            
        Returns:
            Umi-OCR格式的结果列表
        """
        parsed = []
        for item in raw_data:
            if len(item) >= 2:
                bbox = item[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text_info = item[1]  # (text, confidence)
                
                text = text_info[0] if text_info else ""
                confidence = text_info[1] if len(text_info) > 1 else 0
                
                # 转换坐标格式
                if len(bbox) == 4:
                    box = [
                        [int(bbox[0][0]), int(bbox[0][1])],
                        [int(bbox[1][0]), int(bbox[1][1])],
                        [int(bbox[2][0]), int(bbox[2][1])],
                        [int(bbox[3][0]), int(bbox[3][1])],
                    ]
                else:
                    box = []
                
                parsed.append({
                    "text": text,
                    "score": float(confidence),
                    "box": box,
                    "end": "\n",
                    "from": source,
                })
        
        return parsed


class StructuredOCREngine(BaseOCREngine):
    """
    结构化OCR引擎基类
    
    用于支持文档结构化识别的引擎（如表格、版式分析）
    """
    
    SUPPORTED_OUTPUT_FORMATS: List[str] = ["markdown", "json", "html"]
    
    @abstractmethod
    def recognize_structured(
        self, 
        image: Union[str, bytes, Image.Image],
        output_format: str = "markdown",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行结构化识别
        
        Args:
            image: 图像数据
            output_format: 输出格式 (markdown/json/html/excel)
            **kwargs: 额外参数
            
        Returns:
            结构化识别结果
        """
        pass


class LLMOCREngine(BaseOCREngine):
    """
    LLM增强OCR引擎基类
    
    用于支持大语言模型增强的OCR引擎（如智能信息抽取）
    """
    
    REQUIRES_API_KEY: bool = True
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.llm_name = config.get("llm_name", "ernie-4.5")
    
    @abstractmethod
    def extract_info(
        self,
        image: Union[str, bytes, Image.Image],
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行智能信息抽取
        
        Args:
            image: 图像数据
            prompt: 提取指令/问题
            **kwargs: 额外参数
            
        Returns:
            抽取结果
        """
        pass
    
    def validate_api_key(self) -> bool:
        """验证API Key是否有效"""
        return bool(self.api_key and len(self.api_key) > 10)
