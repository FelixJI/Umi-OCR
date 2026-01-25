# ===============================================
# =============== 内置 OCR 引擎管理 ===============
# ===============================================

"""
OCR引擎注册和管理模块
支持多种PaddleOCR引擎：
- PP-OCRv5: 标准文字识别
- PaddleOCR-VL: 视觉语言模型（109语言）
- PP-StructureV3: 文档结构化
- PP-ChatOCRv4: 智能信息抽取

支持多种云API引擎：
- 百度智能云OCR: 通用/高精度/表格/发票识别
- 腾讯云OCR: 通用/高精度/表格/发票识别
- 阿里云OCR: 通用/高精度/表格/发票识别
"""

from umi_log import logger
from typing import Dict, Any, List, Optional

# 内置 OCR API 字典
ApiDict = {}
AllDict = {}

# 默认引擎
DEFAULT_ENGINE = "pp_ocrv5"


def initBuiltInOcr():
    """
    初始化所有内置 OCR 引擎。
    注册 PP-OCRv5、PaddleOCR-VL、PP-StructureV3、PP-ChatOCRv4。
    注册百度、腾讯、阿里云OCR引擎。
    """
    global ApiDict, AllDict

    # 注册所有引擎
    engines_registered = []

    # 1. PP-OCRv5 - 标准识别
    if _register_ocrv5():
        engines_registered.append("pp_ocrv5")

    # 2. PaddleOCR-VL - 视觉语言模型
    if _register_vl():
        engines_registered.append("paddle_vl")

    # 3. PP-StructureV3 - 文档结构化
    if _register_structure():
        engines_registered.append("pp_structure")

    # 4. PP-ChatOCRv4 - 智能抽取
    if _register_chat():
        engines_registered.append("pp_chat")

    # 5. 百度智能云OCR
    if _register_baidu_ocr():
        engines_registered.append("baidu_ocr")

    # 6. 腾讯云OCR
    if _register_tencent_ocr():
        engines_registered.append("tencent_ocr")

    # 7. 阿里云OCR
    if _register_alibaba_ocr():
        engines_registered.append("alibaba_ocr")

    # 保持向后兼容：注册paddleocr_native别名
    if "pp_ocrv5" in ApiDict:
        ApiDict["paddleocr_native"] = ApiDict["pp_ocrv5"]
        AllDict["paddleocr_native"] = AllDict["pp_ocrv5"]

    if engines_registered:
        logger.info(f"已注册 OCR 引擎: {', '.join(engines_registered)}")
        return True
    else:
        logger.error("没有任何 OCR 引擎注册成功")
        return False


def _register_ocrv5() -> bool:
    """注册 PP-OCRv5 引擎"""
    try:
        from ..engines.paddle_ocrv5 import PaddleOCRv5Engine
        
        apiKey = "pp_ocrv5"
        ApiDict[apiKey] = PaddleOCRv5Engine
        
        AllDict[apiKey] = {
            "api_class": PaddleOCRv5Engine,
            "group": "ocr",
            "label": "PP-OCRv5 标准识别",
            "description": "多语言混合文字识别，支持简中/繁中/英文/日文/韩文",
            "global_options": PaddleOCRv5Engine.get_config_schema(),
            "local_options": {},
        }
        
        logger.debug("PP-OCRv5 引擎注册成功")
        return True
        
    except ImportError as e:
        logger.warning(f"PP-OCRv5 引擎注册失败: {e}")
        return False


def _register_vl() -> bool:
    """注册 PaddleOCR-VL 引擎"""
    try:
        from ..engines.paddle_vl import PaddleVLEngine
        
        apiKey = "paddle_vl"
        ApiDict[apiKey] = PaddleVLEngine
        
        AllDict[apiKey] = {
            "api_class": PaddleVLEngine,
            "group": "ocr",
            "label": "PaddleOCR-VL 多语言视觉",
            "description": "0.9B视觉语言模型，支持109种语言，复杂元素识别",
            "global_options": PaddleVLEngine.get_config_schema(),
            "local_options": {},
        }
        
        logger.debug("PaddleOCR-VL 引擎注册成功")
        return True
        
    except ImportError as e:
        logger.warning(f"PaddleOCR-VL 引擎注册失败: {e}")
        return False


def _register_structure() -> bool:
    """注册 PP-StructureV3 引擎"""
    try:
        from ..engines.paddle_structure import PaddleStructureEngine
        
        apiKey = "pp_structure"
        ApiDict[apiKey] = PaddleStructureEngine
        
        AllDict[apiKey] = {
            "api_class": PaddleStructureEngine,
            "group": "structure",
            "label": "PP-StructureV3 文档结构化",
            "description": "表格识别、版式分析，输出Markdown/JSON/Excel/HTML",
            "global_options": PaddleStructureEngine.get_config_schema(),
            "local_options": {},
        }
        
        logger.debug("PP-StructureV3 引擎注册成功")
        return True
        
    except ImportError as e:
        logger.warning(f"PP-StructureV3 引擎注册失败: {e}")
        return False


def _register_chat() -> bool:
    """注册 PP-ChatOCRv4 引擎"""
    try:
        from ..engines.paddle_chat import PaddleChatEngine

        apiKey = "pp_chat"
        ApiDict[apiKey] = PaddleChatEngine

        AllDict[apiKey] = {
            "api_class": PaddleChatEngine,
            "group": "chat",
            "label": "PP-ChatOCRv4 智能抽取",
            "description": "集成ERNIE 4.5，智能问答和关键信息抽取（需API Key）",
            "requires_api_key": True,
            "global_options": PaddleChatEngine.get_config_schema(),
            "local_options": {},
        }

        logger.debug("PP-ChatOCRv4 引擎注册成功")
        return True

    except ImportError as e:
        logger.warning(f"PP-ChatOCRv4 引擎注册失败: {e}")
        return False


def _register_baidu_ocr() -> bool:
    """注册百度智能云OCR引擎"""
    try:
        from ..engines.baidu_ocr import BaiduOCREngine

        apiKey = "baidu_ocr"
        ApiDict[apiKey] = BaiduOCREngine

        AllDict[apiKey] = {
            "api_class": BaiduOCREngine,
            "group": "ocr",
            "label": "百度智能云OCR",
            "description": "通用/高精度文字识别、表格/发票识别（需API Key）",
            "requires_api_key": True,
            "global_options": BaiduOCREngine.get_config_schema(),
            "local_options": {},
        }

        logger.debug("百度智能云OCR 引擎注册成功")
        return True

    except ImportError as e:
        logger.warning(f"百度智能云OCR 引擎注册失败: {e}")
        return False


def _register_tencent_ocr() -> bool:
    """注册腾讯云OCR引擎"""
    try:
        from ..engines.tencent_ocr import TencentOCREngine

        apiKey = "tencent_ocr"
        ApiDict[apiKey] = TencentOCREngine

        AllDict[apiKey] = {
            "api_class": TencentOCREngine,
            "group": "ocr",
            "label": "腾讯云OCR",
            "description": "通用/高精度文字识别、表格/发票识别（需API Key）",
            "requires_api_key": True,
            "global_options": TencentOCREngine.get_config_schema(),
            "local_options": {},
        }

        logger.debug("腾讯云OCR 引擎注册成功")
        return True

    except ImportError as e:
        logger.warning(f"腾讯云OCR 引擎注册失败: {e}")
        return False


def _register_alibaba_ocr() -> bool:
    """注册阿里云OCR引擎"""
    try:
        from ..engines.alibaba_ocr import AlibabaOCREngine

        apiKey = "alibaba_ocr"
        ApiDict[apiKey] = AlibabaOCREngine

        AllDict[apiKey] = {
            "api_class": AlibabaOCREngine,
            "group": "ocr",
            "label": "阿里云OCR",
            "description": "通用/高精度文字识别、表格/发票识别（需API Key）",
            "requires_api_key": True,
            "global_options": AlibabaOCREngine.get_config_schema(),
            "local_options": {},
        }

        logger.debug("阿里云OCR 引擎注册成功")
        return True

    except ImportError as e:
        logger.warning(f"阿里云OCR 引擎注册失败: {e}")
        return False


def getApiOcr(apiKey: str, argd: Dict[str, Any]) -> Any:
    """
    生成一个 OCR API 实例。

    Args:
        apiKey: OCR 引擎标识符
        argd: 配置参数字典

    Returns:
        OCR API 实例，失败返回 [Error] 开头的字符串
    """
    _ensureInitialized()
    
    if apiKey in ApiDict:
        try:
            return ApiDict[apiKey](argd)
        except Exception as e:
            logger.error(f"生成API实例 {apiKey} 失败", exc_info=True)
            return f"[Error] Failed to generate API instance {apiKey}: {e}"
    return f'[Error] "{apiKey}" not in ApiDict. 可用引擎: {list(ApiDict.keys())}'


def getLocalOptions(apiKey: str) -> Dict[str, Any]:
    """
    返回一个 API 的局部配置字典。

    Args:
        apiKey: OCR 引擎标识符

    Returns:
        配置选项字典
    """
    _ensureInitialized()
    
    if apiKey in AllDict:
        return AllDict[apiKey].get("local_options", {})
    return {}


def getGlobalOptions(apiKey: str) -> Dict[str, Any]:
    """
    返回一个 API 的全局配置字典。

    Args:
        apiKey: OCR 引擎标识符

    Returns:
        配置选项字典
    """
    _ensureInitialized()
    
    if apiKey in AllDict:
        return AllDict[apiKey].get("global_options", {})
    return {}


def getEngineInfo(apiKey: str) -> Optional[Dict[str, Any]]:
    """
    获取引擎的完整信息。

    Args:
        apiKey: OCR 引擎标识符

    Returns:
        引擎信息字典，包含 label, description, group 等
    """
    _ensureInitialized()
    
    if apiKey in AllDict:
        return AllDict[apiKey]
    return None


def getAllEngineOptions() -> Dict[str, Any]:
    """
    获取所有引擎的配置选项，用于初始化OcrManager。
    
    Returns:
        字典，key为引擎标识符，value为引擎信息
    """
    _ensureInitialized()
    
    options = {}
    for apiKey, info in AllDict.items():
        # 跳过别名
        if apiKey == "paddleocr_native":
            continue
        
        options[apiKey] = {
            "global_options": info.get("global_options", {}),
            "local_options": info.get("local_options", {}),
            "label": info.get("label", apiKey),
            "description": info.get("description", ""),
            "group": info.get("group", "ocr"),
            "requires_api_key": info.get("requires_api_key", False),
        }
    
    return options


def getAvailableEngines() -> List[Dict[str, Any]]:
    """
    获取所有可用引擎列表。

    Returns:
        引擎信息列表
    """
    _ensureInitialized()
    
    engines = []
    for apiKey, info in AllDict.items():
        # 跳过别名
        if apiKey == "paddleocr_native":
            continue
        engines.append({
            "key": apiKey,
            "label": info.get("label", apiKey),
            "description": info.get("description", ""),
            "group": info.get("group", "ocr"),
            "requires_api_key": info.get("requires_api_key", False),
        })
    return engines


def getEnginesByGroup(group: str) -> List[Dict[str, Any]]:
    """
    获取指定分组的引擎列表。

    Args:
        group: 引擎分组 (ocr/structure/chat)

    Returns:
        引擎信息列表
    """
    _ensureInitialized()
    
    engines = []
    for apiKey, info in AllDict.items():
        if apiKey == "paddleocr_native":
            continue
        if info.get("group") == group:
            engines.append({
                "key": apiKey,
                "label": info.get("label", apiKey),
                "description": info.get("description", ""),
            })
    return engines


def isEngineAvailable(apiKey: str) -> bool:
    """
    检查引擎是否可用。

    Args:
        apiKey: OCR 引擎标识符

    Returns:
        是否可用
    """
    _ensureInitialized()
    return apiKey in ApiDict


def getDefaultEngine() -> str:
    """
    获取默认引擎标识符。

    Returns:
        默认引擎的 apiKey
    """
    _ensureInitialized()
    
    if DEFAULT_ENGINE in ApiDict:
        return DEFAULT_ENGINE
    # 回退到第一个可用引擎
    for key in ApiDict:
        if key != "paddleocr_native":
            return key
    return ""


# 向后兼容：初始化标志
_initialized = False


def _ensureInitialized():
    """确保引擎已初始化"""
    global _initialized
    if not _initialized:
        initBuiltInOcr()
        _initialized = True
