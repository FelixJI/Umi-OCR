#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 图像预处理器

提供图像预处理功能，包括降噪、二值化、纠偏等。

Author: Umi-OCR Team
Date: 2026-01-27
"""

from typing import Tuple
from PIL import Image, ImageOps


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
        import cv2
        import numpy as np

        # 转换为灰度图
        gray_image = image.convert('L')

        # 应用阈值
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

    @staticmethod
    def enhance_contrast(image: Image.Image, factor: float = 1.5) -> Image.Image:
        """
        增强对比度

        Args:
            image: PIL Image 对象
            factor: 对比度因子（1.0 为原始值）

        Returns:
            Image.Image: 增强后的图像
        """
        from PIL import ImageEnhance

        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)

    @staticmethod
    def enhance_sharpness(image: Image.Image, factor: float = 1.5) -> Image.Image:
        """
        增强锐度

        Args:
            image: PIL Image 对象
            factor: 锐度因子（1.0 为原始值）

        Returns:
            Image.Image: 增强后的图像
        """
        from PIL import ImageEnhance

        enhancer = ImageEnhance.Sharpness(image)
        return enhancer.enhance(factor)

    @staticmethod
    def enhance_document_quality(image: Image.Image, 
                               contrast_factor: float = 1.5, 
                               sharpness_factor: float = 1.5,
                               denoise_strength: float = 0.5) -> Image.Image:
        """
        综合增强文档质量
        
        对文档图像应用多种预处理操作以提高OCR识别准确率。
        
        Args:
            image: PIL Image 对象
            contrast_factor: 对比度增强因子
            sharpness_factor: 锐度增强因子
            denoise_strength: 降噪强度
        
        Returns:
            Image.Image: 增强后的图像
        """
        processed = image
        
        # 1. 增强对比度
        if contrast_factor != 1.0:
            processed = ImagePreprocessor.enhance_contrast(processed, contrast_factor)
        
        # 2. 增强锐度
        if sharpness_factor != 1.0:
            processed = ImagePreprocessor.enhance_sharpness(processed, sharpness_factor)
        
        # 3. 适度降噪
        if denoise_strength > 0:
            processed = ImagePreprocessor.denoise(processed, denoise_strength)
        
        return processed
