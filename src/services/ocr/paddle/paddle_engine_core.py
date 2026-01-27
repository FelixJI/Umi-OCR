#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 核心引擎

基于 PaddleOCR Python API 的本地 OCR 引擎实现。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import os
import logging
import threading
from typing import Dict, Any, List, Optional
from PIL import Image
import numpy as np

# 禁用PaddleOCR的模型源检查
os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

from ..base_engine import BaseOCREngine, BatchOCREngine
from ..ocr_result import OCRResult, TextBlock, TextBlockType, BoundingBox
from ..model_manager import get_model_manager

from .paddle_config import PaddleConfig
from .paddle_preprocessor import ImagePreprocessor
from .paddle_postprocessor import TextPostprocessor, TextBlockInference

logger = logging.getLogger(__name__)


# =============================================================================
# 语言映射
# =============================================================================

LANGUAGE_MAP = {
    "ch": "ch", "chinese": "ch", "chinese_cht": "ch",
    "en": "en", "english": "en",
    "japan": "japan", "japanese": "japan",
    "korean": "korean",
    "th": "th", "te": "te", "ta": "ta",
    "latin": "latin", "arabic": "arabic",
    "cyrillic": "cyrillic", "devanagari": "devanagari",
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


# =============================================================================
# PaddleOCR 引擎主类
# =============================================================================

class PaddleOCREngine(BaseOCREngine):
    """
    PaddleOCR 引擎

    基于 PaddleOCR Python API 的本地 OCR 引擎。
    """

    ENGINE_TYPE = "paddle"
    ENGINE_NAME = "PaddleOCR"
    ENGINE_VERSION = "4.0"

    SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff", "webp"]
    SUPPORTS_BATCH = True
    SUPPORTS_GPU = True

    def __init__(self, config: Dict[str, Any]):
        """初始化 PaddleOCR 引擎"""
        super().__init__(config)

        self.paddle_config = PaddleConfig(**config)
        self.model_manager = get_model_manager()

        self._paddle_ocr = None
        self._gpu_available = False
        self._gpu_count = 0
        self._ram_timer = None

    # -------------------------------------------------------------------------
    # GPU 检测
    # -------------------------------------------------------------------------

    def _check_gpu(self) -> bool:
        """检测 GPU 是否可用"""
        try:
            import paddle

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
    # 可用性检查
    # -------------------------------------------------------------------------

    def is_available(self) -> bool:
        """检查 PaddleOCR 引擎是否可用"""
        try:
            import paddle
            from paddleocr import PaddleOCR

            model_manager = get_model_manager()
            model_info = model_manager.get_model_info(self.paddle_config.lang)
            if not model_info:
                logger.warning(f"PaddleOCR 模型不可用: {self.paddle_config.lang}")
                return False

            if self.paddle_config.device == "gpu":
                if not paddle.device.is_compiled_with_cuda():
                    logger.warning("PaddlePaddle 未编译 CUDA 支持")
                    return False
                if paddle.device.cuda.device_count() == 0:
                    logger.warning("未检测到 GPU 设备")
                    return False

            return True

        except ImportError as e:
            logger.error(f"PaddleOCR 依赖未安装: {e}")
            return False
        except Exception as e:
            logger.error(f"检查可用性失败: {e}", exc_info=True)
            return False

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def _do_initialize(self) -> bool:
        """初始化 PaddleOCR 引擎"""
        try:
            self._check_gpu()

            if self.paddle_config.device == "gpu" and self._gpu_available:
                device = "gpu:0"
            elif self.paddle_config.device == "npu":
                device = "npu:0"
            else:
                device = "cpu"

            init_params = self._build_init_params()

            from paddleocr import PaddleOCR

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
                f"版本: {self.paddle_config.ocr_version}, 设备: {device}"
            )

            if self.paddle_config.ram_time_seconds > 0:
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
        """构建 PaddleOCR 初始化参数"""
        paddle_lang = LANGUAGE_MAP.get(self.paddle_config.lang, "ch")

        params = {
            "lang": paddle_lang,
            "ocr_version": self.paddle_config.ocr_version,
            "use_textline_orientation": self.paddle_config.use_textline_orientation,
            "use_doc_orientation_classify": self.paddle_config.use_doc_orientation_classify,
            "use_doc_unwarping": self.paddle_config.use_doc_unwarping,
        }

        params.update({
            "text_det_limit_side_len": self.paddle_config.text_det_limit_side_len,
            "text_det_limit_type": self.paddle_config.text_det_limit_type,
            "text_det_thresh": self.paddle_config.text_det_thresh,
            "text_det_box_thresh": self.paddle_config.text_det_box_thresh,
            "text_det_unclip_ratio": self.paddle_config.text_det_unclip_ratio,
        })

        params.update({
            "text_rec_score_thresh": self.paddle_config.text_rec_score_thresh,
            "return_word_box": self.paddle_config.return_word_box,
        })

        if self.paddle_config.text_detection_model_dir:
            params["text_detection_model_dir"] = self.paddle_config.text_detection_model_dir
        if self.paddle_config.text_recognition_model_dir:
            params["text_recognition_model_dir"] = self.paddle_config.text_recognition_model_dir
        if self.paddle_config.textline_orientation_model_dir:
            params["textline_orientation_model_dir"] = self.paddle_config.textline_orientation_model_dir

        return params

    # -------------------------------------------------------------------------
    # 识别
    # -------------------------------------------------------------------------

    def _do_recognize(self, image: Image.Image, **kwargs) -> OCRResult:
        """执行 OCR 识别"""
        processed_image = self._preprocess_image(image)
        cv_image = np.array(processed_image)

        if self.paddle_config.use_table:
            result = self._recognize_table(cv_image)
        elif self.paddle_config.use_structure:
            result = self._recognize_structure(cv_image)
        else:
            result = self._recognize_text(cv_image)

        result = self._enhance_result(result)
        return result

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """图像预处理流程
        
        预处理顺序（按最佳实践）:
        1. 调整大小 - 限制内存占用
        2. 纠偏 - 校正文档旋转
        3. 对比度增强 - 提升文字清晰度
        4. 锐度增强 - 提升边缘清晰度
        5. 二值化 - 去除背景干扰
        6. 降噪 - 去除器件噪声
        """
        processed = image

        # 1. 调整大小
        if self.paddle_config.max_image_size > 0:
            processed = ImagePreprocessor.resize_if_needed(
                processed, self.paddle_config.max_image_size
            )

        # 2. 纠偏
        if self.paddle_config.enable_deskew:
            processed, angle = ImagePreprocessor.deskew(processed)
            if abs(angle) > 1:
                logger.debug(f"图像纠偏: {angle:.1f}°")

        # 3. 对比度增强
        if self.paddle_config.enable_contrast_enhance:
            processed = ImagePreprocessor.enhance_contrast(
                processed, self.paddle_config.contrast_factor
            )

        # 4. 锐度增强
        if self.paddle_config.enable_sharpness_enhance:
            processed = ImagePreprocessor.enhance_sharpness(
                processed, self.paddle_config.sharpness_factor
            )

        # 5. 二值化
        if self.paddle_config.enable_binarization:
            processed = ImagePreprocessor.binarize(processed)

        # 6. 降噪
        if self.paddle_config.enable_denoise:
            processed = ImagePreprocessor.denoise(processed)

        # 7. 综合文档质量增强（可选，当启用了多项增强时）
        if (self.paddle_config.enable_contrast_enhance and 
            self.paddle_config.enable_sharpness_enhance and 
            self.paddle_config.enable_denoise and
            self.paddle_config.denoise_strength > 0):
            processed = ImagePreprocessor.enhance_document_quality(
                processed,
                self.paddle_config.contrast_factor,
                self.paddle_config.sharpness_factor,
                self.paddle_config.denoise_strength
            )

        return processed

    def _recognize_text(self, cv_image: np.ndarray) -> OCRResult:
        """文本识别"""
        result_list = self._paddle_ocr.predict(cv_image)

        result = OCRResult(
            engine_type=self.ENGINE_TYPE,
            engine_name=self.ENGINE_NAME,
            engine_version=self.ENGINE_VERSION,
            success=True
        )

        text_blocks = []
        for output in result_list:
            if hasattr(output, 'res') and output.res:
                res = output.res

                rec_texts = res.get('rec_texts', [])
                rec_scores = res.get('rec_scores', [])
                rec_polys = res.get('rec_polys', [])

                for i, text in enumerate(rec_texts):
                    confidence = rec_scores[i] if i < len(rec_scores) else 1.0

                    if i < len(rec_polys):
                        points = rec_polys[i].tolist() if hasattr(rec_polys[i], 'tolist') else list(rec_polys[i])
                        bbox = BoundingBox(points=points)
                    else:
                        bbox = None

                    text_block = TextBlock(
                        text=text,
                        confidence=confidence,
                        bbox=bbox,
                        block_type=TextBlockType.PARAGRAPH
                    )
                    text_blocks.append(text_block)

                break

        result.text_blocks = text_blocks
        result.full_text = result.get_text(separator="\n")

        return result

    def _recognize_table(self, cv_image: np.ndarray) -> OCRResult:
        """
        表格识别 (PP-TableMagic v2 产线)
        
        流程:
        1. 表格分类 - 判断有线表/无线表
        2. 表格结构识别 - 获取表格结构HTML
        3. 单元格检测 - 检测单元格位置
        4. OCR识别 - 识别单元格内文字
        5. 结果合并 - 生成完整表格
        """
        result = OCRResult(
            engine_type=self.ENGINE_TYPE,
            engine_name=self.ENGINE_NAME,
            engine_version=self.ENGINE_VERSION,
            success=True
        )
        
        try:
            # 尝试使用 PaddleOCR 的表格识别功能
            # PaddleOCR 3.3.0+ 支持 table_rec 产线
            from paddleocr import TableRecognition
            
            table_rec = TableRecognition(
                device=self.paddle_config.device,
                use_tensorrt=self.paddle_config.use_tensorrt,
                precision=self.paddle_config.precision,
            )
            
            # 执行表格识别
            table_result = table_rec.predict(cv_image)
            
            # 解析结果
            if table_result:
                for output in table_result:
                    if hasattr(output, 'res') and output.res:
                        res = output.res
                        
                        # 提取HTML表格
                        html_content = res.get('html', '')
                        if html_content:
                            table_block = TextBlock(
                                text=html_content,
                                confidence=1.0,
                                block_type=TextBlockType.TABLE
                            )
                            result.text_blocks.append(table_block)
                            result.extra['table_html'] = html_content
                        
                        # 提取单元格文本
                        cell_texts = res.get('cell_texts', [])
                        for cell_text in cell_texts:
                            if cell_text.strip():
                                cell_block = TextBlock(
                                    text=cell_text,
                                    confidence=0.9,
                                    block_type=TextBlockType.PARAGRAPH
                                )
                                result.text_blocks.append(cell_block)
                        
                        break
            
            # 生成纯文本
            result.full_text = result.get_text(separator="\n")
            
        except ImportError:
            # TableRecognition 未安装，回退到普通文本识别
            logger.warning("表格识别模块未安装，使用普通OCR识别")
            return self._recognize_text(cv_image)
        except Exception as e:
            logger.error(f"表格识别失败: {e}", exc_info=True)
            # 回退到普通文本识别
            return self._recognize_text(cv_image)
        
        return result

    def _recognize_structure(self, cv_image: np.ndarray) -> OCRResult:
        """
        文档版面结构分析 (PP-DocLayout)
        
        检测文档中的各类区域:
        - 文本区域
        - 表格区域
        - 图片区域
        - 公式区域
        - 标题/页眉/页脚等
        """
        result = OCRResult(
            engine_type=self.ENGINE_TYPE,
            engine_name=self.ENGINE_NAME,
            engine_version=self.ENGINE_VERSION,
            success=True
        )
        
        try:
            # 尝试使用 PaddleOCR 的版面分析功能
            from paddleocr import PPStructure
            
            structure = PPStructure(
                lang=self.paddle_config.lang,
                device=self.paddle_config.device,
                use_tensorrt=self.paddle_config.use_tensorrt,
            )
            
            # 执行版面分析
            structure_result = structure.predict(cv_image)
            
            # 解析结果
            if structure_result:
                for output in structure_result:
                    if hasattr(output, 'res') and output.res:
                        res = output.res
                        
                        # 提取各区域
                        regions = res.get('regions', [])
                        for region in regions:
                            region_type = region.get('type', 'text')
                            region_text = region.get('text', '')
                            region_bbox = region.get('bbox', [])
                            
                            # 映射区域类型
                            block_type = self._map_region_type(region_type)
                            
                            if region_text.strip():
                                block = TextBlock(
                                    text=region_text,
                                    confidence=region.get('score', 0.9),
                                    bbox=BoundingBox(points=region_bbox) if region_bbox else None,
                                    block_type=block_type
                                )
                                result.text_blocks.append(block)
                        
                        break
            
            result.full_text = result.get_text(separator="\n")
            
        except ImportError:
            logger.warning("版面分析模块未安装，使用普通OCR识别")
            return self._recognize_text(cv_image)
        except Exception as e:
            logger.error(f"版面分析失败: {e}", exc_info=True)
            return self._recognize_text(cv_image)
        
        return result
    
    def _map_region_type(self, region_type: str) -> TextBlockType:
        """映射版面区域类型到TextBlockType"""
        type_map = {
            'text': TextBlockType.PARAGRAPH,
            'title': TextBlockType.HEADER,
            'table': TextBlockType.TABLE,
            'figure': TextBlockType.UNKNOWN,
            'formula': TextBlockType.FORMULA,
            'header': TextBlockType.HEADER,
            'footer': TextBlockType.FOOTER,
        }
        return type_map.get(region_type.lower(), TextBlockType.PARAGRAPH)

    def _enhance_result(self, result: OCRResult) -> OCRResult:
        """增强识别结果"""
        if not result.text_blocks:
            return result

        languages = set()
        for block in result.text_blocks:
            if any('\u4e00' <= c <= '\u9fff' for c in block.text):
                languages.add("zh")
            elif any('a' <= c.lower() <= 'z' for c in block.text):
                languages.add("en")

        if languages:
            result.extra["detected_languages"] = list(languages)

        return result

    def _postprocess_text_blocks(self, text_blocks: List[TextBlock]) -> List[TextBlock]:
        """文本后处理"""
        processed = text_blocks

        if self.paddle_config.enable_merge_lines:
            processed = TextPostprocessor.merge_adjacent_lines(processed)

        if self.paddle_config.enable_remove_duplicates:
            processed = TextPostprocessor.remove_duplicates(processed)

        return processed

    # -------------------------------------------------------------------------
    # 清理
    # -------------------------------------------------------------------------

    def _do_cleanup(self) -> None:
        """清理资源"""
        if self._ram_timer:
            self._ram_timer.cancel()
            self._ram_timer = None

        self._paddle_ocr = None

    def _reset_ram(self) -> None:
        """重置内存"""
        logger.info("执行内存重置...")

        if self._paddle_ocr:
            del self._paddle_ocr
            self._paddle_ocr = None

        self._do_initialize()

        if self.paddle_config.ram_time_seconds > 0:
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
        """获取配置 Schema"""
        return {
            "type": "object",
            "title": "PaddleOCR 引擎配置",
            "properties": {
                "lang": {
                    "type": "string",
                    "title": "识别语言",
                    "default": "ch",
                    "enum": list(LANGUAGE_MAP.keys())[:30],
                },
                "ocr_version": {
                    "type": "string",
                    "title": "OCR 版本",
                    "default": "PP-OCRv5",
                    "enum": ["PP-OCRv5"],
                    "description": "PP-OCRv5 支持109种语言，精度86.38%",
                },
                "use_textline_orientation": {
                    "type": "boolean",
                    "title": "启用文本方向分类",
                    "default": True,
                },
                "use_table": {
                    "type": "boolean",
                    "title": "启用表格识别",
                    "default": False,
                    "description": "使用PP-TableMagic v2产线进行表格识别，需要安装表格相关模型",
                },
                "use_structure": {
                    "type": "boolean",
                    "title": "启用版面分析",
                    "default": False,
                    "description": "使用PP-DocLayout进行版面结构分析，需要安装版面相关模型",
                },
                "table_structure_model": {
                    "type": "string",
                    "title": "表格结构模型",
                    "default": "slanet_plus",
                    "enum": ["slanet", "slanet_plus", "slanext_wired", "slanext_wireless"],
                    "description": "表格结构识别模型",
                },
                "table_output_format": {
                    "type": "string",
                    "title": "表格输出格式",
                    "default": "html",
                    "enum": ["html", "markdown", "csv"],
                    "description": "表格识别结果输出格式",
                },
                "device": {
                    "type": "string",
                    "title": "计算设备",
                    "default": "gpu",
                    "enum": ["cpu", "gpu", "npu"],
                },
                "precision": {
                    "type": "string",
                    "title": "推理精度",
                    "default": "fp32",
                    "enum": ["fp32", "fp16", "bf16"],
                },
                "confidence_threshold": {
                    "type": "number",
                    "title": "置信度阈值",
                    "default": 0.5,
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "enable_denoise": {
                    "type": "boolean",
                    "title": "启用降噪",
                    "default": False,
                },
                "enable_binarization": {
                    "type": "boolean",
                    "title": "启用二值化",
                    "default": False,
                },
                "enable_deskew": {
                    "type": "boolean",
                    "title": "启用纠偏",
                    "default": False,
                },
                "max_image_size": {
                    "type": "integer",
                    "title": "最大图片尺寸",
                    "default": 0,
                    "minimum": 0,
                },
            },
            "required": ["lang"]
        }


# =============================================================================
# 批量识别引擎
# =============================================================================

class PaddleBatchOCREngine(BatchOCREngine):
    """PaddleOCR 批量识别引擎"""

    ENGINE_TYPE = "paddle_batch"
    ENGINE_NAME = "PaddleOCR 批量识别"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._paddle_engine = PaddleOCREngine(config)

    def _do_initialize(self) -> bool:
        return self._paddle_engine.initialize()

    def _do_recognize(self, image: Image.Image, **kwargs) -> OCRResult:
        return self._paddle_engine.recognize(image, **kwargs)

    def _do_cleanup(self) -> None:
        self._paddle_engine.stop()

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return PaddleOCREngine.get_config_schema()
