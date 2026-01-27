#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 配置数据类

定义 PaddleOCR 引擎的配置参数。

Author: Umi-OCR Team
Date: 2026-01-27
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PaddleConfig:
    """PaddleOCR 配置 - 对齐官方 PaddleOCR v5 API"""

    # ========== 语言配置 ==========
    lang: str = "ch"                      # 语言（支持109种语言）
    ocr_version: str = "PP-OCRv5"         # OCR版本 (仅支持PP-OCRv5)

    # ========== 模型路径 ==========
    text_detection_model_dir: Optional[str] = None   # 检测模型路径
    text_recognition_model_dir: Optional[str] = None # 识别模型路径
    textline_orientation_model_dir: Optional[str] = None  # 方向分类模型路径
    doc_orientation_classify_model_dir: Optional[str] = None  # 文档方向分类模型路径
    doc_unwarping_model_dir: Optional[str] = None    # 文档纠平模型路径

    # ========== 功能开关 ==========
    use_textline_orientation: bool = True     # 文本方向分类
    use_doc_orientation_classify: bool = False  # 文档方向分类
    use_doc_unwarping: bool = False           # 文档纠平
    use_table: bool = False                   # 表格识别 (PP-TableMagic)
    use_structure: bool = False               # 版面结构分析

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
    enable_contrast_enhance: bool = False     # 对比度增强
    enable_sharpness_enhance: bool = False    # 锐度增强
    contrast_factor: float = 1.5              # 对比度因子
    sharpness_factor: float = 1.5             # 锐度因子
    denoise_strength: float = 0.5             # 降噪强度
    max_image_size: int = 0                   # 最大图片尺寸（0 表示不限制)

    # ========== 表格识别配置 ==========
    table_structure_model: str = "slanet_plus"  # 表格结构模型: slanet, slanet_plus, slanext_wired, slanext_wireless
    table_cell_model: str = "auto"            # 单元格检测模型: auto, wired, wireless
    table_output_format: str = "html"         # 输出格式: html, markdown, csv

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
