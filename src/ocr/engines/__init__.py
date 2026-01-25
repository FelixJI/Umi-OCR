# ===============================================
# =============== OCR 引擎模块 ===============
# ===============================================

"""
OCR引擎模块 - 提供多种OCR引擎的统一管理

支持的离线引擎：
- PP-OCRv5: 标准文字识别（多语言混合）
- PaddleOCR-VL: 视觉语言模型（109种语言）
- PP-StructureV3: 文档结构化（表格/版式）
- PP-ChatOCRv4: 智能信息抽取（需API Key）

支持的云API引擎：
- 百度智能云OCR: 高精度文字识别、发票识别
- 腾讯云OCR: 通用文字识别、证件识别
- 阿里云OCR: 多场景文字识别、印章识别
"""

from .base import BaseOCREngine
from .paddle_ocrv5 import PaddleOCRv5Engine
from .paddle_structure import PaddleStructureEngine
from .paddle_vl import PaddleVLEngine
from .paddle_chat import PaddleChatEngine
from .cloud_api_base import CloudAPIEngine
from .baidu_ocr import BaiduOCREngine
from .tencent_ocr import TencentOCREngine
from .alibaba_ocr import AlibabaOCREngine

__all__ = [
    # 基类
    "BaseOCREngine",
    "CloudAPIEngine",
    # PaddleOCR离线引擎
    "PaddleOCRv5Engine",
    "PaddleStructureEngine",
    "PaddleVLEngine",
    "PaddleChatEngine",
    # 云API引擎
    "BaiduOCREngine",
    "TencentOCREngine",
    "AlibabaOCREngine",
]

# 离线引擎注册表
OFFLINE_ENGINE_REGISTRY = {
    "pp_ocrv5": PaddleOCRv5Engine,
    "paddle_vl": PaddleVLEngine,
    "pp_structure": PaddleStructureEngine,
    "pp_chat": PaddleChatEngine,
}

# 云API引擎注册表
CLOUD_ENGINE_REGISTRY = {
    "baidu_ocr": BaiduOCREngine,
    "tencent_ocr": TencentOCREngine,
    "alibaba_ocr": AlibabaOCREngine,
}

# 统一引擎注册表
ENGINE_REGISTRY = {
    **OFFLINE_ENGINE_REGISTRY,
    **CLOUD_ENGINE_REGISTRY,
}


def get_engine_class(engine_type: str):
    """根据引擎类型获取引擎类"""
    return ENGINE_REGISTRY.get(engine_type)


def get_available_engines() -> list:
    """获取所有可用引擎列表"""
    return list(ENGINE_REGISTRY.keys())


def get_offline_engines() -> list:
    """获取离线引擎列表"""
    return list(OFFLINE_ENGINE_REGISTRY.keys())


def get_cloud_engines() -> list:
    """获取云API引擎列表"""
    return list(CLOUD_ENGINE_REGISTRY.keys())


def get_engine_info(engine_type: str) -> dict:
    """获取引擎信息"""
    engine_class = ENGINE_REGISTRY.get(engine_type)
    if not engine_class:
        return {}
    return {
        "type": engine_type,
        "name": engine_class.ENGINE_NAME,
        "requires_api_key": getattr(engine_class, "REQUIRES_API_KEY", False),
        "features": getattr(engine_class, "SUPPORTED_FEATURES", []),
    }
