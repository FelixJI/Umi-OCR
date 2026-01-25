# ===============================================
# =============== PP-OCRv5 引擎 ===============
# ===============================================

"""
PP-OCRv5 OCR引擎实现
- 支持多语言混合识别（简中、繁中、英文、日文、韩文）
- 支持文字方向检测
- 支持文档方向分类和矫正
- 支持图像预处理
"""

import os
import logging
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Dict, Any, Union, List

from .base import BaseOCREngine

# 禁用PaddleOCR的模型源检查
os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

logger = logging.getLogger(__name__)


class PaddleOCRv5Engine(BaseOCREngine):
    """
    PP-OCRv5 OCR引擎
    
    基于PaddleOCR 3.3.0+，支持多语言混合文字识别。
    特点：
    - 单模型支持5种文字类型（简中、繁中、英文、日文、韩文）
    - 精度较上一代提升13%
    - 支持文档方向分类和矫正
    """
    
    ENGINE_TYPE = "pp_ocrv5"
    ENGINE_NAME = "PP-OCRv5 标准识别"
    SUPPORTED_FEATURES = [
        "text_recognition",
        "multi_language",
        "orientation_detection",
        "doc_orientation_classify",
        "doc_unwarping",
    ]
    
    # 语言映射表
    LANG_MAP = {
        "ch": "ch",              # 简体中文
        "chinese": "ch",
        "chinese_cht": "ch",     # 繁体中文（PP-OCRv5统一使用ch）
        "en": "en",              # 英文
        "english": "en",
        "japan": "japan",        # 日文
        "japanese": "japan",
        "korean": "korean",      # 韩文
        "cyrillic": "cyrillic",  # 西里尔字母
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 内存管理参数
        self.ram_info = {
            "max": config.get("ram_max", -1),
            "time": config.get("ram_time", -1),
        }
        
        # 预处理器
        self._preprocessor = None
    
    def initialize(self) -> bool:
        """初始化PaddleOCR引擎"""
        try:
            from paddleocr import PaddleOCR
            
            # 获取配置参数
            lang = self.config.get("lang", "ch")
            paddle_lang = self.LANG_MAP.get(lang, "ch")
            
            use_angle_cls = self.config.get("use_angle_cls", True)
            use_doc_orientation = self.config.get("use_doc_orientation_classify", False)
            use_doc_unwarping = self.config.get("use_doc_unwarping", False)
            
            # 检测GPU
            gpu_available = self._check_gpu()
            
            # 构建初始化参数
            init_params = {
                "lang": paddle_lang,
                "use_textline_orientation": use_angle_cls,
            }
            
            # 添加高级预处理参数（如果PaddleOCR版本支持）
            if use_doc_orientation:
                init_params["use_doc_orientation_classify"] = True
            if use_doc_unwarping:
                init_params["use_doc_unwarping"] = True
            
            # 初始化PaddleOCR
            self._engine = PaddleOCR(**init_params)
            self._initialized = True
            
            logger.info(
                f"PP-OCRv5 初始化成功 - 语言: {paddle_lang}, "
                f"设备: {'GPU' if gpu_available else 'CPU'}, "
                f"方向检测: {use_angle_cls}"
            )
            
            return True
            
        except ImportError as e:
            logger.error(f"导入PaddleOCR失败: {e}")
            return False
        except Exception as e:
            logger.error(f"PP-OCRv5 初始化失败: {e}", exc_info=True)
            return False
    
    def _check_gpu(self) -> bool:
        """检测GPU是否可用"""
        try:
            import paddle
            gpu_available = (
                paddle.device.is_compiled_with_cuda()
                and paddle.device.cuda.device_count() > 0
            )
            if gpu_available:
                gpu_count = paddle.device.cuda.device_count()
                logger.info(f"检测到GPU: {gpu_count}个设备")
            return gpu_available
        except Exception:
            return False
    
    def _do_recognize(self, image: Union[str, bytes, Image.Image], **kwargs) -> Dict[str, Any]:
        """执行OCR识别"""
        # 内存管理
        self._ram_clear()
        
        # 图像预处理
        img_input = self._prepare_image(image)
        
        # 执行识别
        result = self._engine.ocr(img_input)
        
        # 解析结果
        return self._parse_result(result)
    
    def _prepare_image(self, image: Union[str, bytes, Image.Image]) -> Union[str, np.ndarray]:
        """准备图像输入"""
        # 如果是路径，直接返回
        if isinstance(image, str):
            return image
        
        # 转换为numpy数组
        if isinstance(image, bytes):
            pil_img = Image.open(BytesIO(image))
        elif isinstance(image, Image.Image):
            pil_img = image
        else:
            raise ValueError(f"不支持的图像类型: {type(image)}")
        
        # 应用预处理（如果启用）
        if self._preprocessor and self._preprocessor.enabled:
            pil_img = self._preprocessor.process(pil_img)
        
        # 确保是RGB模式
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        
        return np.array(pil_img)
    
    def _parse_result(self, raw_result: List) -> Dict[str, Any]:
        """
        解析PaddleOCR结果为Umi-OCR格式
        
        PaddleOCR输出格式:
        [
            [  # 每张图片
                [  # 每个文本块
                    [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],  # 边界框
                    ("text", confidence)  # 文本和置信度
                ]
            ]
        ]
        """
        if not raw_result or not raw_result[0]:
            return {"code": 101, "data": ""}
        
        parsed_data = []
        
        for block in raw_result[0]:
            if len(block) >= 2:
                bbox = block[0]
                text_info = block[1]
                
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
                
                parsed_data.append({
                    "text": text,
                    "score": float(confidence),
                    "box": box,
                    "end": "\n",
                    "from": "ocr",
                })
        
        if parsed_data:
            return {"code": 100, "data": parsed_data}
        else:
            return {"code": 101, "data": ""}
    
    def _ram_clear(self):
        """内存管理 - 检查并在需要时重启引擎"""
        if self.ram_info["max"] > 0:
            try:
                import psutil
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                if memory_mb > self.ram_info["max"]:
                    logger.warning(f"内存超限 {memory_mb:.1f}MB，正在重启引擎...")
                    self.initialize()
            except ImportError:
                pass  # psutil未安装，跳过内存检查
    
    def set_preprocessor(self, preprocessor):
        """设置图像预处理器"""
        self._preprocessor = preprocessor
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """获取配置项定义"""
        return {
            "lang": {
                "label": "识别语言/Language",
                "type": "combobox",
                "default": "ch",
                "options": [
                    {"value": "ch", "label": "简体中文/Chinese Simplified"},
                    {"value": "chinese_cht", "label": "繁体中文/Chinese Traditional"},
                    {"value": "en", "label": "English"},
                    {"value": "japan", "label": "日本語/Japanese"},
                    {"value": "korean", "label": "한국어/Korean"},
                    {"value": "cyrillic", "label": "Cyrillic/西里尔字母"},
                ],
            },
            "use_angle_cls": {
                "label": "文字方向检测/Text Orientation Detection",
                "type": "bool",
                "default": True,
                "tip": "检测并纠正倾斜或旋转的文字",
            },
            "use_doc_orientation_classify": {
                "label": "文档方向分类/Document Orientation Classification",
                "type": "bool",
                "default": False,
                "tip": "自动检测文档是否需要旋转90°/180°/270°",
            },
            "use_doc_unwarping": {
                "label": "文档矫正/Document Unwarping",
                "type": "bool",
                "default": False,
                "tip": "矫正弯曲或透视变形的文档",
            },
            "ram_max": {
                "label": "最大内存限制/Max Memory (MB)",
                "type": "int",
                "default": -1,
                "min": -1,
                "tip": "-1=不限制，超过限制时自动重启引擎",
            },
            "ram_time": {
                "label": "内存清理间隔/Memory Cleanup Interval (s)",
                "type": "int",
                "default": 300,
                "min": 0,
            },
        }
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "lang": "ch",
            "use_angle_cls": True,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "ram_max": -1,
            "ram_time": 300,
        }
