#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 云 OCR 模块

提供百度云、腾讯云、阿里云 OCR 引擎。

模块结构:
- base_cloud: 云引擎基类
- request_queue: 请求队列（QPS控制）
- baidu_ocr: 百度云 OCR
- tencent_ocr: 腾讯云 OCR
- aliyun_ocr: 阿里云 OCR

Author: Umi-OCR Team
Date: 2026-01-27
"""

from .base_cloud import BaseCloudEngine, CloudOCRType, CloudOCRResult
from .request_queue import RequestQueue
from .baidu_ocr import BaiduOCREngine
from .tencent_ocr import TencentOCREngine
from .aliyun_ocr import AliyunOCREngine


__all__ = [
    'BaseCloudEngine',
    'CloudOCRType',
    'CloudOCRResult',
    'RequestQueue',
    'BaiduOCREngine',
    'TencentOCREngine',
    'AliyunOCREngine',
]
