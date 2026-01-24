# ===============================================
# =============== 内置 OCR 引擎管理 ===============
# ===============================================

from umi_log import logger
from typing import Dict, Any

# 内置 OCR API 字典
ApiDict = {}
AllDict = {}


def initBuiltInOcr():
    """
    初始化内置 OCR 引擎。
    替代动态插件系统，直接注册 PaddleOCR。
    """
    global ApiDict, AllDict

    # 导入内置 PaddleOCR 引擎
    try:
        from .paddleocr_direct import PaddleOCREngine
    except ImportError as e:
        logger.error(f"Failed to import PaddleOCR engine: {e}", exc_info=True)
        return False

    # 注册内置 OCR 引擎
    apiKey = "paddleocr_native"
    ApiDict[apiKey] = PaddleOCREngine

    # 配置信息
    AllDict[apiKey] = {
        "api_class": PaddleOCREngine,
        "group": "ocr",
        "global_options": {
            "lang": {
                "label": "语言/Language",
                "type": "str",
                "default": "ch",
                "options": [
                    {"value": "ch", "label": "简体中文"},
                    {"value": "chinese_cht", "label": "繁体中文"},
                    {"value": "en", "label": "English"},
                    {"value": "japan", "label": "日本語"},
                    {"value": "korean", "label": "한국어"},
                    {"value": "cyrillic", "label": "Cyrillic"},
                ],
            },
            "use_angle_cls": {
                "label": "文字方向检测/Orientation Detection",
                "type": "bool",
                "default": True,
            },
            "cpu_threads": {
                "label": "CPU 线程数/CPU Threads",
                "type": "int",
                "default": 4,
                "min": 1,
                "max": 8,
            },
            "ram_max": {
                "label": "最大内存限制/Max Memory (MB)",
                "type": "int",
                "default": -1,
                "min": -1,
            },
            "ram_time": {
                "label": "内存清理间隔/Ram Cleanup Time (s)",
                "type": "int",
                "default": 300,
                "min": 0,
            },
        },
        "local_options": {},
    }

    logger.info(f"Built-in PaddleOCR engine registered successfully")
    return True


def getApiOcr(apiKey: str, argd: Dict[str, Any]) -> Any:
    """
    生成一个 ocr api 实例。

    Args:
        apiKey: OCR 引擎标识符
        argd: 配置参数字典

    Returns:
        OCR API 实例，失败返回 [Error] 开头的字符串
    """
    if apiKey in ApiDict:
        try:
            return ApiDict[apiKey](argd)  # 实例化后返回
        except Exception as e:
            logger.error(f"生成api实例{apiKey}失败。", exc_info=True, stack_info=True)
            return f"[Error] Failed to generate API instance {apiKey}: {e}"
    return f'[Error] "{apiKey}" not in ApiDict.'


def getLocalOptions(apiKey: str) -> Dict[str, Any]:
    """
    返回一个 API 的局部配置字典。

    Args:
        apiKey: OCR 引擎标识符

    Returns:
        配置选项字典
    """
    if apiKey in AllDict:
        return AllDict[apiKey]["local_options"]
    return {}


# 向后兼容：初始化时自动调用
# 为了保持向后兼容，首次调用时自动初始化
_initialized = False


def _ensureInitialized():
    global _initialized
    if not _initialized:
        initBuiltInOcr()
        _initialized = True
