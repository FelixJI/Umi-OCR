#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 引擎实现

集成 PaddleOCR 作为本地识别引擎，采用组合模式支持多种功能模块。

主要功能：
- 文本识别（多语言）
- 方向分类
- 表格识别
- 文档结构分析
- GPU自动检测和回退
- 图像预处理
- 识别结果增强处理
- 文本后处理

Author: Umi-OCR Team
Date: 2026-01-26
"""

import os
import threading
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from PIL import Image, ImageOps, ImageEnhance

# 禁用PaddleOCR的模型源检查
os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

from PySide6.QtCore import QObject, Signal

from .base_engine import BaseOCREngine, BatchOCREngine, OCRErrorCode, ConfigSchema
from .ocr_result import OCRResult, TextBlock, TextBlockType, BoundingBox
from .model_manager import get_model_manager, ModelRepository

logger = logging.getLogger(__name__)


# =============================================================================
# PaddleOCR 配置
# =============================================================================

@dataclass
class PaddleConfig:
    """PaddleOCR 配置 - 对齐官方 PaddleOCR v5 API"""

    # ========== 语言配置 ==========
    lang: str = "ch"                      # 语言（支持100+语言）
    ocr_version: str = "PP-OCRv5"         # OCR版本 (PP-OCRv3, PP-OCRv4, PP-OCRv5)

    # ========== 模型路径 ==========
    text_detection_model_dir: Optional[str] = None   # 检测模型路径
    text_recognition_model_dir: Optional[str] = None # 识别模型路径
    textline_orientation_model_dir: Optional[str] = None  # 方向分类模型路径
    doc_orientation_classify_model_dir: Optional[str] = None  # 文档方向分类模型路径
    doc_unwarping_model_dir: Optional[str] = None    # 文档纠平模型路径

    # ========== 功能开关 ==========
    use_textline_orientation: bool = True     # 文本方向分类（替代 use_angle_cls）
    use_doc_orientation_classify: bool = False  # 文档方向分类
    use_doc_unwarping: bool = False           # 文档纠平
    use_table: bool = False                   # 表格识别
    use_structure: bool = False               # 结构分析

    # ========== 检测参数 ==========
    text_det_limit_side_len: int = 736        # 检测输入图片最大边长限制
    text_det_limit_type: str = "min"          # 限制类型 ('min' 或 'max')
    text_det_thresh: float = 0.3              # 检测置信度阈值
    text_det_box_thresh: float = 0.6          # 检测框置信度阈值
    text_det_unclip_ratio: float = 1.5        # 检测框扩展系数

    # ========== 识别参数 ==========
    text_rec_score_thresh: float = 0.5        # 识别置信度阈值
    return_word_box: bool = False             # 是否返回单词级别的坐标

    # ========== 性能配置 ==========
    device: str = "gpu"                       # 设备 (cpu, gpu, npu)
    precision: str = "fp32"                   # 精度 (fp32, fp16, bf16)
    enable_mkldnn: bool = True                # MKL-DNN 加速
    cpu_threads: int = 4                      # CPU 线程数
    use_tensorrt: bool = True                 # TensorRT 加速
    enable_hpi: bool = False                  # 高性能推理（需要额外安装插件）

    # ========== 预处理配置 ==========
    enable_denoise: bool = False              # 降噪
    enable_binarization: bool = False         # 二值化
    enable_deskew: bool = False               # 纠偏
    max_image_size: int = 0                   # 最大图片尺寸（0表示不限制）

    # ========== 结果处理 ==========
    confidence_threshold: float = 0.5         # 置信度阈值
    enable_text_type_inference: bool = True   # 启用文本块类型推断
    enable_low_confidence_marking: bool = True  # 启用低置信度标记
    low_confidence_threshold: float = 0.3     # 低置信度阈值
    low_confidence_color: str = "#FF0000"     # 低置信度标记颜色

    # ========== 文本后处理 ==========
    enable_merge_lines: bool = True           # 合并相邻行
    enable_remove_duplicates: bool = True     # 去除重复

    # ========== 内存管理 ==========
    ram_max_mb: int = -1                      # 最大内存使用（MB）
    ram_time_seconds: int = -1                # 内存重置时间（秒）


# =============================================================================
# 文本块类型推断器
# =============================================================================

class TextBlockInference:
    """
    文本块类型推断器

    基于文本内容和位置特征，自动推断文本块的类型。
    """

    # 关键词模式（用于推断类型）
    PATTERNS = {
        TextBlockType.HEADER: [
            r"第[一二三四五六七八九十百]+章",
            r"^\d+\.",
            r"^[一二三四五六七八九十]+、",
            r"^[A-Z][a-z]*\s*[a-z]*:",
        ],
        TextBlockType.FOOTER: [
            r"第\d+页",
            r"Page\s*\d+",
        ],
        TextBlockType.FORMULA: [
            r"[A-Za-z]+\s*[=≠<>≤≥]+\s*[\d.]+",
            r"[\d.]+\s*[+\-×÷]\s*[\d.]+",
        ]
    }

    @classmethod
    def infer_type(cls, text: str, bbox: Optional[BoundingBox] = None) -> TextBlockType:
        """
        推断文本块类型

        Args:
            text: 文本内容
            bbox: 边界框（用于位置推断）

        Returns:
            TextBlockType: 推断的类型
        """
        import re

        # 检查表格特征（多行对齐）
        if cls._is_table_like(text):
            return TextBlockType.TABLE

        # 检查公式特征
        if cls._matches_pattern(text, cls.PATTERNS[TextBlockType.FORMULA]):
            return TextBlockType.FORMULA

        # 检查标题特征
        if cls._matches_pattern(text, cls.PATTERNS[TextBlockType.HEADER]):
            return TextBlockType.HEADER

        # 检查页脚特征
        if cls._matches_pattern(text, cls.PATTERNS[TextBlockType.FOOTER]):
            return TextBlockType.FOOTER

        # 默认为段落
        return TextBlockType.PARAGRAPH

    @classmethod
    def _matches_pattern(cls, text: str, patterns: List[str]) -> bool:
        """
        检查文本是否匹配模式

        Args:
            text: 文本内容
            patterns: 正则表达式模式列表

        Returns:
            bool: 是否匹配
        """
        import re

        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False

    @classmethod
    def _is_table_like(cls, text: str) -> bool:
        """
        检查文本是否像表格

        Args:
            text: 文本内容

        Returns:
            bool: 是否像表格
        """
        # 检查是否有大量的制表符或管道符
        if text.count('\t') >= 3 or text.count('|') >= 3:
            return True

        # 检查是否有大量数字对齐
        lines = text.split('\n')
        if len(lines) > 2:
            # 检查每行的数字数量
            num_counts = [len([c for c in line if c.isdigit()]) for line in lines]
            avg_num_count = sum(num_counts) / len(num_counts)

            # 如果平均每行有多个数字，可能是表格
            if avg_num_count >= 2:
                return True

        return False


# =============================================================================
# 图像预处理器
# =============================================================================

class ImagePreprocessor:
    """
    图像预处理器

    提供图像预处理功能，包括降噪、二值化、纠偏等。
    """

    @staticmethod
    def denoise(image: Image.Image, strength: float = 1.0) -> Image.Image:
        """
        图像降噪

        Args:
            image: PIL Image 对象
            strength: 降噪强度（0.0 - 1.0）

        Returns:
            Image.Image: 降噪后的图像
        """
        # 简单实现：使用模糊
        if strength <= 0:
            return image

        import cv2
        import numpy as np

        # 转换为OpenCV格式
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # 应用高斯模糊
        kernel_size = int(3 + strength * 5)
        kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1

        cv_image = cv2.GaussianBlur(cv_image, (kernel_size, kernel_size), strength)

        # 转换回PIL Image
        return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))

    @staticmethod
    def binarize(image: Image.Image, threshold: int = 128) -> Image.Image:
        """
        图像二值化

        Args:
            image: PIL Image 对象
            threshold: 二值化阈值（0-255）

        Returns:
            Image.Image: 二值化后的图像
        """
        # 转换为灰度图
        gray_image = image.convert('L')

        # 应用阈值
        import cv2
        import numpy as np

        cv_image = np.array(gray_image)
        _, binary = cv2.threshold(cv_image, threshold, 255, cv2.THRESH_BINARY)

        return Image.fromarray(binary)

    @staticmethod
    def deskew(image: Image.Image) -> Tuple[Image.Image, float]:
        """
        图像纠偏

        Args:
            image: PIL Image 对象

        Returns:
            Tuple[Image.Image, float]: (纠偏后的图像, 偏转角度）
        """
        import cv2
        import numpy as np

        # 转换为灰度图
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)

        # 使用霍夫变换检测角度
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)

        if lines is not None:
            angles = [line[0][1] for line in lines]
            angle = np.median(angles) * 180 / np.pi

            # 限制角度在 -45 到 45 度之间
            if angle > 45:
                angle -= 90
            elif angle < -45:
                angle += 90

            # 旋转图像
            if abs(angle) > 1:  # 只在角度大于1度时才旋转
                return ImageOps.rotate(image, -angle), angle

        return image, 0.0

    @staticmethod
    def resize_if_needed(image: Image.Image, max_size: int) -> Image.Image:
        """
        如果需要，调整图像大小

        Args:
            image: PIL Image 对象
            max_size: 最大边长（0表示不限制）

        Returns:
            Image.Image: 调整后的图像
        """
        if max_size <= 0:
            return image

        width, height = image.size
        max_dim = max(width, height)

        if max_dim <= max_size:
            return image

        # 计算缩放比例
        scale = max_size / max_dim
        new_width = int(width * scale)
        new_height = int(height * scale)

        return image.resize((new_width, new_height), Image.LANCZOS)


# =============================================================================
# 文本后处理器
# =============================================================================

class TextPostprocessor:
    """
    文本后处理器

    提供文本后处理功能，包括合并相邻行、去除重复等。
    """

    @staticmethod
    def merge_adjacent_lines(
        text_blocks: List[TextBlock],
        vertical_threshold: int = 10,
        horizontal_threshold: int = 20
    ) -> List[TextBlock]:
        """
        合并相邻的文本行

        Args:
            text_blocks: 文本块列表
            vertical_threshold: 垂直间距阈值
            horizontal_threshold: 水平间距阈值

        Returns:
            List[TextBlock]: 合并后的文本块列表
        """
        if len(text_blocks) <= 1:
            return text_blocks

        # 按Y坐标排序
        sorted_blocks = sorted(text_blocks, key=lambda b: b.bbox.y if b.bbox else 0)

        merged = []
        current_block = sorted_blocks[0]

        for block in sorted_blocks[1:]:
            if not current_block.bbox or not block.bbox:
                merged.append(current_block)
                current_block = block
                continue

            # 检查是否在同一行（Y坐标接近）
            y_diff = abs(block.bbox.y - current_block.bbox.y)
            x_overlap = max(0, min(current_block.bbox.x + current_block.bbox.width, block.bbox.x + block.bbox.width) -
                          max(current_block.bbox.x, block.bbox.x))

            if y_diff < vertical_threshold and x_overlap > 0:
                # 合并到同一行
                current_block.text += " " + block.text
                # 更新边界框
                new_x = min(current_block.bbox.x, block.bbox.x)
                new_width = max(current_block.bbox.x + current_block.bbox.width, block.bbox.x + block.bbox.width) - new_x
                current_block.bbox.x = new_x
                current_block.bbox.width = new_width
            else:
                # 添加到结果，开始新的行
                merged.append(current_block)
                current_block = block

        merged.append(current_block)
        return merged

    @staticmethod
    def remove_duplicates(text_blocks: List[TextBlock]) -> List[TextBlock]:
        """
        去除重复的文本块

        Args:
            text_blocks: 文本块列表

        Returns:
            List[TextBlock]: 去重后的文本块列表
        """
        seen = set()
        unique_blocks = []

        for block in text_blocks:
            text = block.text.strip()
            if text and text not in seen:
                seen.add(text)
                unique_blocks.append(block)

        return unique_blocks


# =============================================================================
# PaddleOCR 引擎主类
# =============================================================================

class PaddleOCREngine(BaseOCREngine):
    """
    PaddleOCR 引擎

    基于 PaddleOCR Python API 的本地 OCR 引擎。
    采用组合模式，支持多种功能模块。
    """

    # 引擎信息
    ENGINE_TYPE = "paddle"
    ENGINE_NAME = "PaddleOCR"
    ENGINE_VERSION = "4.0"

    # 支持的功能
    SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff", "webp"]
    SUPPORTS_BATCH = True
    SUPPORTS_GPU = True

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 PaddleOCR 引擎

        Args:
            config: 引擎配置字典
        """
        super().__init__(config)

        # 转换配置
        self.paddle_config = PaddleConfig(**config)

        # 获取模型管理器
        self.model_manager = get_model_manager()

        # PaddleOCR 实例（组合不同的识别模块）
        self._paddle_ocr = None
        self._table_engine = None
        self._structure_engine = None

        # GPU 信息
        self._gpu_available = False
        self._gpu_count = 0

        # 内存管理计时器
        self._ram_timer = None

    # -------------------------------------------------------------------------
    # GPU 检测
    # -------------------------------------------------------------------------

    def _check_gpu(self) -> bool:
        """
        检测 GPU 是否可用

        Returns:
            bool: GPU 是否可用
        """
        try:
            import paddle

            # 检查 CUDA 编译和设备数量
            self._gpu_available = (
                paddle.device.is_compiled_with_cuda()
                and paddle.device.cuda.device_count() > 0
            )

            if self._gpu_available:
                self._gpu_count = paddle.device.cuda.device_count()
                logger.info(f"GPU 检测成功: {self._gpu_count} 个设备")
            else:
                logger.info("GPU 不可用，将使用 CPU")

            return self._gpu_available

        except ImportError:
            logger.warning("PaddlePaddle 未安装")
            return False
        except Exception as e:
            logger.error(f"GPU 检测失败: {e}", exc_info=True)
            return False

    # -------------------------------------------------------------------------
    # 抽象方法实现
    # -------------------------------------------------------------------------

    def _do_initialize(self) -> bool:
        """
        初始化 PaddleOCR 引擎 - 对齐官方 v5 API

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 检测 GPU
            self._check_gpu()

            # 根据配置决定设备类型
            if self.paddle_config.device == "gpu" and self._gpu_available:
                device = "gpu:0"
            elif self.paddle_config.device == "npu":
                device = "npu:0"
            else:
                device = "cpu"

            # 构建初始化参数
            init_params = self._build_init_params()

            # 导入 PaddleOCR
            from paddleocr import PaddleOCR

            # 初始化 PaddleOCR（性能参数通过 kwargs 传递）
            self._paddle_ocr = PaddleOCR(
                **init_params,
                device=device,
                enable_hpi=self.paddle_config.enable_hpi,
                use_tensorrt=self.paddle_config.use_tensorrt,
                precision=self.paddle_config.precision,
                enable_mkldnn=self.paddle_config.enable_mkldnn,
                cpu_threads=self.paddle_config.cpu_threads,
            )

            logger.info(
                f"PaddleOCR 初始化成功 - 语言: {self.paddle_config.lang}, "
                f"版本: {self.paddle_config.ocr_version}, "
                f"设备: {device}"
            )

            # 启动内存管理计时器
            if self.paddle_config.ram_time_seconds > 0:
                import threading
                self._ram_timer = threading.Timer(
                    self.paddle_config.ram_time_seconds,
                    self._reset_ram
                )
                self._ram_timer.start()

            return True

        except Exception as e:
            logger.error(f"PaddleOCR 初始化失败: {e}", exc_info=True)
            return False

    def _build_init_params(self) -> Dict[str, Any]:
        """
        构建 PaddleOCR 初始化参数 - 对齐官方 v5 API

        Returns:
            Dict[str, Any]: 初始化参数字典
        """
        # 语言映射（PP-OCRv5 支持的语言）
        lang_map = {
            "ch": "ch",
            "chinese": "ch",
            "chinese_cht": "ch",
            "en": "en",
            "english": "en",
            "japan": "japan",
            "japanese": "japan",
            "korean": "korean",
            "korean": "korean",
            "th": "th",
            "te": "te",
            "ta": "ta",
            "latin": "latin",
            "arabic": "arabic",
            "cyrillic": "cyrillic",
            "devanagari": "devanagari",
            # 拉丁语系
            "af": "af", "az": "az", "bs": "bs", "cs": "cs", "cy": "cy",
            "da": "da", "de": "de", "es": "es", "et": "et", "fr": "fr",
            "ga": "ga", "hr": "hr", "hu": "hu", "id": "id", "is": "is",
            "it": "it", "ku": "ku", "la": "la", "lt": "lt", "lv": "lv",
            "mi": "mi", "ms": "ms", "mt": "mt", "nl": "nl", "no": "no",
            "oc": "oc", "pi": "pi", "pl": "pl", "pt": "pt", "ro": "ro",
            "rs_latin": "rs_latin", "sk": "sk", "sl": "sl", "sq": "sq",
            "sv": "sv", "sw": "sw", "tl": "tl", "tr": "tr", "uz": "uz",
            "vi": "vi", "flemish": "flemish", "german": "german",
            "fi": "fi", "eu": "eu", "gl": "gl", "lb": "lb", "rm": "rm",
            "ca": "ca", "qu": "qu",
            # 阿拉伯语系
            "ar": "ar", "fa": "fa", "ug": "ug", "ur": "ur", "ps": "ps",
            # 斯拉夫语系
            "ru": "ru", "be": "be", "uk": "uk",
            # 印地语系
            "hi": "hi", "mr": "mr", "ne": "ne", "bh": "bh", "mai": "mai",
            "ang": "ang", "bho": "bho", "mah": "mah", "sck": "sck",
            "new": "new", "gom": "gom", "sa": "sa", "bgc": "bgc",
        }

        paddle_lang = lang_map.get(self.paddle_config.lang, "ch")

        # 基础参数
        params = {
            "lang": paddle_lang,
            "ocr_version": self.paddle_config.ocr_version,
            "use_textline_orientation": self.paddle_config.use_textline_orientation,
            "use_doc_orientation_classify": self.paddle_config.use_doc_orientation_classify,
            "use_doc_unwarping": self.paddle_config.use_doc_unwarping,
        }

        # 检测参数
        params.update({
            "text_det_limit_side_len": self.paddle_config.text_det_limit_side_len,
            "text_det_limit_type": self.paddle_config.text_det_limit_type,
            "text_det_thresh": self.paddle_config.text_det_thresh,
            "text_det_box_thresh": self.paddle_config.text_det_box_thresh,
            "text_det_unclip_ratio": self.paddle_config.text_det_unclip_ratio,
        })

        # 识别参数
        params.update({
            "text_rec_score_thresh": self.paddle_config.text_rec_score_thresh,
            "return_word_box": self.paddle_config.return_word_box,
        })

        # 自定义模型路径
        if self.paddle_config.text_detection_model_dir:
            params["text_detection_model_dir"] = self.paddle_config.text_detection_model_dir
        if self.paddle_config.text_recognition_model_dir:
            params["text_recognition_model_dir"] = self.paddle_config.text_recognition_model_dir
        if self.paddle_config.textline_orientation_model_dir:
            params["textline_orientation_model_dir"] = self.paddle_config.textline_orientation_model_dir
        if self.paddle_config.doc_orientation_classify_model_dir:
            params["doc_orientation_classify_model_dir"] = self.paddle_config.doc_orientation_classify_model_dir
        if self.paddle_config.doc_unwarping_model_dir:
            params["doc_unwarping_model_dir"] = self.paddle_config.doc_unwarping_model_dir

        # 性能参数（通过 kwargs 传递，由 paddlex 处理）
        self._common_init_args = {
            "device": self.paddle_config.device,
            "enable_hpi": self.paddle_config.enable_hpi,
            "use_tensorrt": self.paddle_config.use_tensorrt,
            "precision": self.paddle_config.precision,
            "enable_mkldnn": self.paddle_config.enable_mkldnn,
            "cpu_threads": self.paddle_config.cpu_threads,
        }

        return params

    def _do_recognize(self, image: Image.Image, **kwargs) -> OCRResult:
        """
        执行 OCR 识别

        Args:
            image: PIL Image 对象
            **kwargs: 额外的识别参数

        Returns:
            OCRResult: 识别结果
        """
        # 图像预处理
        processed_image = self._preprocess_image(image)

        # 转换为 OpenCV 格式
        import numpy as np
        cv_image = np.array(processed_image)

        # 执行识别
        if self.paddle_config.use_table:
            result = self._recognize_table(cv_image)
        elif self.paddle_config.use_structure:
            result = self._recognize_structure(cv_image)
        else:
            result = self._recognize_text(cv_image)

        # 增强处理
        result = self._enhance_result(result)

        return result

    def _do_cleanup(self) -> None:
        """
        清理资源
        """
        # 停止内存管理计时器
        if self._ram_timer:
            self._ram_timer.cancel()
            self._ram_timer = None

        # 清理 PaddleOCR 实例
        self._paddle_ocr = None
        self._table_engine = None
        self._structure_engine = None

    # -------------------------------------------------------------------------
    # 图像预处理
    # -------------------------------------------------------------------------

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        图像预处理

        Args:
            image: PIL Image 对象

        Returns:
            Image.Image: 预处理后的图像
        """
        processed = image

        # 调整大小
        if self.paddle_config.max_image_size > 0:
            processed = ImagePreprocessor.resize_if_needed(
                processed,
                self.paddle_config.max_image_size
            )

        # 纠偏
        if self.paddle_config.enable_deskew:
            processed, _ = ImagePreprocessor.deskew(processed)

        # 二值化
        if self.paddle_config.enable_binarization:
            processed = ImagePreprocessor.binarize(processed)

        # 降噪
        if self.paddle_config.enable_denoise:
            processed = ImagePreprocessor.denoise(processed)

        return processed

    # -------------------------------------------------------------------------
    # 文本识别
    # -------------------------------------------------------------------------

    def _recognize_text(self, cv_image: np.ndarray) -> OCRResult:
        """
        文本识别

        Args:
            cv_image: OpenCV 格式的图像

        Returns:
            OCRResult: 识别结果
        """
        # 新版本 PaddleOCR 使用 predict 方法
        result_list = self._paddle_ocr.predict(cv_image)

        # 创建结果对象
        result = OCRResult(
            engine_type=self.ENGINE_TYPE,
            engine_name=self.ENGINE_NAME,
            engine_version=self.ENGINE_VERSION,
            success=True
        )

        # 新版本返回 OCRResult 对象列表
        text_blocks = []
        for output in result_list:
            if hasattr(output, 'res') and output.res:
                res = output.res

                # 提取识别文本和置信度
                rec_texts = res.get('rec_texts', [])
                rec_scores = res.get('rec_scores', [])
                rec_polys = res.get('rec_polys', [])

                for i, text in enumerate(rec_texts):
                    confidence = rec_scores[i] if i < len(rec_scores) else 1.0

                    # 构建边界框
                    if i < len(rec_polys):
                        points = rec_polys[i].tolist() if hasattr(rec_polys[i], 'tolist') else list(rec_polys[i])
                        bbox = BoundingBox(points=points)
                    else:
                        bbox = None

                    # 创建文本块
                    text_block = TextBlock(
                        text=text,
                        confidence=confidence,
                        bbox=bbox,
                        block_type=TextBlockType.PARAGRAPH
                    )
                    text_blocks.append(text_block)

                # 提取检测框（用于未识别到文本的情况）
                if not text_blocks:
                    dt_polys = res.get('dt_polys', [])
                    for poly in dt_polys:
                        points = poly.tolist() if hasattr(poly, 'tolist') else list(poly)
                        bbox = BoundingBox(points=points)
                        text_block = TextBlock(
                            text="",
                            confidence=0.0,
                            bbox=bbox,
                            block_type=TextBlockType.UNKNOWN
                        )
                        text_blocks.append(text_block)

                break

        result.text_blocks = text_blocks
        result.full_text = result.get_text(separator="\n")

        return result

    # -------------------------------------------------------------------------
    # 表格识别
    # -------------------------------------------------------------------------

    def _recognize_table(self, cv_image: np.ndarray) -> OCRResult:
        """
        表格识别

        Args:
            cv_image: OpenCV 格式的图像

        Returns:
            OCRResult: 识别结果
        """
        # TODO: 实现表格识别
        # 暂时使用普通文本识别
        return self._recognize_text(cv_image)

    # -------------------------------------------------------------------------
    # 结构分析
    # -------------------------------------------------------------------------

    def _recognize_structure(self, cv_image: np.ndarray) -> OCRResult:
        """
        文档结构分析

        Args:
            cv_image: OpenCV 格式的图像

        Returns:
            OCRResult: 识别结果
        """
        # TODO: 实现结构分析
        # 暂时使用普通文本识别
        return self._recognize_text(cv_image)

    # -------------------------------------------------------------------------
    # 结果解析
    # -------------------------------------------------------------------------

    def _parse_ocr_result(self, ocr_result: List) -> OCRResult:
        """
        解析 PaddleOCR 识别结果

        Args:
            ocr_result: PaddleOCR 原始结果

        Returns:
            OCRResult: 解析后的结果
        """
        result = OCRResult(
            engine_type=self.ENGINE_TYPE,
            engine_name=self.ENGINE_NAME,
            engine_version=self.ENGINE_VERSION,
            success=True
        )

        text_blocks = []

        for item in ocr_result:
            # 格式: [[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], (text, confidence)]
            bbox_points = item[0]
            text_info = item[1]

            text = text_info[0]
            confidence = text_info[1] if len(text_info) > 1 else 0.0

            # 创建边界框
            bbox = BoundingBox(points=[[int(p[0]), int(p[1])] for p in bbox_points])

            # 推断文本块类型
            block_type = TextBlockType.PARAGRAPH
            if self.paddle_config.enable_text_type_inference:
                block_type = TextBlockInference.infer_type(text, bbox)

            # 创建文本块
            text_block = TextBlock(
                text=text,
                confidence=confidence,
                bbox=bbox,
                block_type=block_type
            )

            # 低置信度标记
            if self.paddle_config.enable_low_confidence_marking:
                if confidence < self.paddle_config.low_confidence_threshold:
                    # 将颜色信息存储在 extra 字段中
                    text_block.extra["low_confidence"] = True
                    text_block.extra["marker_color"] = self.paddle_config.low_confidence_color

            text_blocks.append(text_block)

        # 置信度过滤
        filtered_blocks = [
            block for block in text_blocks
            if block.confidence >= self.paddle_config.confidence_threshold
        ]

        result.text_blocks = filtered_blocks

        # 文本后处理
        result.text_blocks = self._postprocess_text_blocks(result.text_blocks)

        # 生成完整文本
        result.full_text = result.get_text(separator="\n")

        return result

    # -------------------------------------------------------------------------
    # 结果增强处理
    # -------------------------------------------------------------------------

    def _enhance_result(self, result: OCRResult) -> OCRResult:
        """
        增强识别结果

        Args:
            result: 原始识别结果

        Returns:
            OCRResult: 增强后的结果
        """
        # 检测语言
        if not result.text_blocks:
            return result

        # 语言检测（简单实现）
        languages = set()
        for block in result.text_blocks:
            # 简单判断：包含中文
            if any('\u4e00' <= c <= '\u9fff' for c in block.text):
                languages.add("zh")
            # 包含英文
            elif any('a' <= c.lower() <= 'z' for c in block.text):
                languages.add("en")

        if languages:
            result.extra["detected_languages"] = list(languages)

        return result

    # -------------------------------------------------------------------------
    # 文本后处理
    # -------------------------------------------------------------------------

    def _postprocess_text_blocks(self, text_blocks: List[TextBlock]) -> List[TextBlock]:
        """
        文本后处理

        Args:
            text_blocks: 文本块列表

        Returns:
            List[TextBlock]: 处理后的文本块列表
        """
        processed = text_blocks

        # 合并相邻行
        if self.paddle_config.enable_merge_lines:
            processed = TextPostprocessor.merge_adjacent_lines(processed)

        # 去除重复
        if self.paddle_config.enable_remove_duplicates:
            processed = TextPostprocessor.remove_duplicates(processed)

        return processed

    # -------------------------------------------------------------------------
    # 内存管理
    # -------------------------------------------------------------------------

    def _reset_ram(self) -> None:
        """
        重置内存（通过重新初始化 PaddleOCR）
        """
        logger.info("执行内存重置...")

        # 停止旧实例
        if self._paddle_ocr:
            del self._paddle_ocr
            self._paddle_ocr = None

        # 重新初始化
        self._do_initialize()

        # 重启计时器
        if self.paddle_config.ram_time_seconds > 0:
            import threading
            self._ram_timer = threading.Timer(
                self.paddle_config.ram_time_seconds,
                self._reset_ram
            )
            self._ram_timer.start()

    # -------------------------------------------------------------------------
    # 配置 Schema
    # -------------------------------------------------------------------------

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        获取配置 Schema - 对齐官方 v5 API

        Returns:
            Dict[str, Any]: JSON Schema 格式的配置定义
        """
        return {
            "type": "object",
            "title": "PaddleOCR 引擎配置",
            "properties": {
                # ========== 语言配置节 ==========
                "lang": {
                    "type": "string",
                    "title": "识别语言",
                    "description": "选择要识别的语言（支持100+语言）",
                    "default": "ch",
                    "enum": [
                        "ch", "en", "japan", "korean", "th",
                        "latin", "arabic", "cyrillic", "devanagari",
                        "af", "az", "bs", "cs", "cy", "da", "de", "es", "et",
                        "fr", "ga", "hr", "hu", "id", "is", "it", "ku", "la",
                        "lt", "lv", "mi", "ms", "mt", "nl", "no", "oc", "pi",
                        "pl", "pt", "ro", "rs_latin", "sk", "sl", "sq", "sv",
                        "sw", "tl", "tr", "uz", "vi", "ar", "fa", "ug", "ur",
                        "ps", "ru", "be", "uk", "hi", "mr", "ne", "bh", "mai",
                        "ang", "bho", "mah", "sck", "new", "gom", "sa", "bgc"
                    ],
                    "i18n_key": "paddle.lang"
                },
                "ocr_version": {
                    "type": "string",
                    "title": "OCR 版本",
                    "description": "选择 PP-OCR 版本",
                    "default": "PP-OCRv5",
                    "enum": ["PP-OCRv3", "PP-OCRv4", "PP-OCRv5"],
                    "i18n_key": "paddle.ocr_version"
                },

                # ========== 功能开关节 ==========
                "use_textline_orientation": {
                    "type": "boolean",
                    "title": "启用文本方向分类",
                    "description": "是否使用文本方向分类器（识别竖排文字）",
                    "default": True,
                    "i18n_key": "paddle.use_textline_orientation"
                },
                "use_doc_orientation_classify": {
                    "type": "boolean",
                    "title": "启用文档方向分类",
                    "description": "是否使用文档方向分类（适用于扫描文档）",
                    "default": False,
                    "i18n_key": "paddle.use_doc_orientation_classify"
                },
                "use_doc_unwarping": {
                    "type": "boolean",
                    "title": "启用文档纠平",
                    "description": "是否使用文档纠平（适用于弯曲页面）",
                    "default": False,
                    "i18n_key": "paddle.use_doc_unwarping"
                },
                "use_table": {
                    "type": "boolean",
                    "title": "启用表格识别",
                    "description": "是否启用表格识别功能",
                    "default": False,
                    "i18n_key": "paddle.use_table"
                },

                # ========== 检测参数节 ==========
                "text_det_limit_side_len": {
                    "type": "integer",
                    "title": "检测输入尺寸限制",
                    "description": "检测模型输入图片的最大边长限制",
                    "default": 736,
                    "minimum": 32,
                    "maximum": 4096,
                    "i18n_key": "paddle.text_det_limit_side_len"
                },
                "text_det_limit_type": {
                    "type": "string",
                    "title": "检测尺寸限制类型",
                    "description": "如何应用尺寸限制",
                    "default": "min",
                    "enum": ["min", "max"],
                    "i18n_key": "paddle.text_det_limit_type"
                },
                "text_det_thresh": {
                    "type": "number",
                    "title": "检测置信度阈值",
                    "description": "检测像素置信度阈值",
                    "default": 0.3,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "i18n_key": "paddle.text_det_thresh"
                },
                "text_det_box_thresh": {
                    "type": "number",
                    "title": "检测框置信度阈值",
                    "description": "检测框平均置信度阈值",
                    "default": 0.6,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "i18n_key": "paddle.text_det_box_thresh"
                },
                "text_det_unclip_ratio": {
                    "type": "number",
                    "title": "检测框扩展系数",
                    "description": "检测框扩展系数",
                    "default": 1.5,
                    "minimum": 1.0,
                    "maximum": 3.0,
                    "i18n_key": "paddle.text_det_unclip_ratio"
                },

                # ========== 识别参数节 ==========
                "text_rec_score_thresh": {
                    "type": "number",
                    "title": "识别置信度阈值",
                    "description": "识别结果置信度阈值",
                    "default": 0.5,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "i18n_key": "paddle.text_rec_score_thresh"
                },

                # ========== 性能配置节 ==========
                "device": {
                    "type": "string",
                    "title": "计算设备",
                    "description": "选择使用的计算设备",
                    "default": "gpu",
                    "enum": ["cpu", "gpu", "npu"],
                    "i18n_key": "paddle.device"
                },
                "precision": {
                    "type": "string",
                    "title": "推理精度",
                    "description": "选择推理精度（GPU 时有效）",
                    "default": "fp32",
                    "enum": ["fp32", "fp16", "bf16"],
                    "i18n_key": "paddle.precision"
                },
                "enable_mkldnn": {
                    "type": "boolean",
                    "title": "启用 MKL-DNN",
                    "description": "CPU 模式下是否启用 MKL-DNN 加速",
                    "default": True,
                    "i18n_key": "paddle.enable_mkldnn"
                },
                "cpu_threads": {
                    "type": "integer",
                    "title": "CPU 线程数",
                    "description": "CPU 模式下的线程数",
                    "default": 4,
                    "minimum": 1,
                    "maximum": 32,
                    "i18n_key": "paddle.cpu_threads"
                },
                "use_tensorrt": {
                    "type": "boolean",
                    "title": "启用 TensorRT",
                    "description": "GPU 模式下是否使用 TensorRT 加速",
                    "default": True,
                    "i18n_key": "paddle.use_tensorrt"
                },
                "enable_hpi": {
                    "type": "boolean",
                    "title": "启用高性能推理",
                    "description": "是否启用高性能推理模式（需要安装 paddlepaddle-gpu HPC 插件）",
                    "default": False,
                    "i18n_key": "paddle.enable_hpi"
                },

                # ========== 预处理节 ==========
                "enable_denoise": {
                    "type": "boolean",
                    "title": "启用降噪",
                    "default": False,
                    "i18n_key": "paddle.enable_denoise"
                },
                "enable_binarization": {
                    "type": "boolean",
                    "title": "启用二值化",
                    "default": False,
                    "i18n_key": "paddle.enable_binarization"
                },
                "enable_deskew": {
                    "type": "boolean",
                    "title": "启用纠偏",
                    "default": False,
                    "i18n_key": "paddle.enable_deskew"
                },
                "max_image_size": {
                    "type": "integer",
                    "title": "最大图片尺寸",
                    "description": "限制图片的最大边长（像素），0 表示不限制",
                    "default": 0,
                    "minimum": 0,
                    "maximum": 10000,
                    "i18n_key": "paddle.max_image_size"
                },

                # ========== 结果处理节 ==========
                "confidence_threshold": {
                    "type": "number",
                    "title": "置信度阈值",
                    "description": "过滤低于此置信度的文本块",
                    "default": 0.5,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "i18n_key": "paddle.confidence_threshold"
                },
                "enable_text_type_inference": {
                    "type": "boolean",
                    "title": "启用文本类型推断",
                    "default": True,
                    "i18n_key": "paddle.enable_text_type_inference"
                },
                "enable_low_confidence_marking": {
                    "type": "boolean",
                    "title": "启用低置信度标记",
                    "description": "标记低置信度的文本块",
                    "default": True,
                    "i18n_key": "paddle.enable_low_confidence_marking"
                },
                "low_confidence_threshold": {
                    "type": "number",
                    "title": "低置信度阈值",
                    "default": 0.3,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "i18n_key": "paddle.low_confidence_threshold"
                },
                "low_confidence_color": {
                    "type": "string",
                    "title": "低置信度标记颜色",
                    "default": "#FF0000",
                    "i18n_key": "paddle.low_confidence_color"
                },

                # ========== 文本后处理节 ==========
                "enable_merge_lines": {
                    "type": "boolean",
                    "title": "合并相邻行",
                    "default": True,
                    "i18n_key": "paddle.enable_merge_lines"
                },
                "enable_remove_duplicates": {
                    "type": "boolean",
                    "title": "去除重复",
                    "default": True,
                    "i18n_key": "paddle.enable_remove_duplicates"
                },

                # ========== 内存管理节 ==========
                "ram_max_mb": {
                    "type": "integer",
                    "title": "最大内存使用 (MB)",
                    "description": "达到此内存使用量时自动重启，-1 表示不限制",
                    "default": -1,
                    "minimum": -1,
                    "i18n_key": "paddle.ram_max_mb"
                },
                "ram_time_seconds": {
                    "type": "integer",
                    "title": "内存重置时间 (秒)",
                    "description": "每隔此时间自动重启以释放内存，-1 表示不重置",
                    "default": -1,
                    "minimum": -1,
                    "i18n_key": "paddle.ram_time_seconds"
                }
            },
            "required": ["lang"]
        }


# =============================================================================
# 批量识别引擎
# =============================================================================

class PaddleBatchOCREngine(BatchOCREngine):
    """
    PaddleOCR 批量识别引擎

    支持批量图片识别的 PaddleOCR 引擎。
    """

    ENGINE_TYPE = "paddle_batch"
    ENGINE_NAME = "PaddleOCR 批量识别"

    def __init__(self, config: Dict[str, Any]):
        """
        初始化批量识别引擎

        Args:
            config: 引擎配置字典
        """
        super().__init__(config)

        # 内部使用 PaddleOCREngine
        self._paddle_engine = PaddleOCREngine(config)

    def _do_initialize(self) -> bool:
        """初始化引擎"""
        return self._paddle_engine.initialize()

    def _do_recognize(self, image: Image.Image, **kwargs) -> OCRResult:
        """执行识别"""
        return self._paddle_engine.recognize(image, **kwargs)

    def _do_cleanup(self) -> None:
        """清理资源"""
        self._paddle_engine.stop()

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """获取配置 Schema"""
        return PaddleOCREngine.get_config_schema()
