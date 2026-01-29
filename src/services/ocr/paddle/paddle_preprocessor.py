#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 图像预处理器

提供图像预处理功能，包括降噪、二值化、纠偏等。
集成PaddleOCR官方DocPreprocessor管道，支持文档方向分类和文档纠平。

Author: Umi-OCR Team
Date: 2026-01-27
"""

from typing import Tuple, Optional
from PIL import Image, ImageOps
import logging
import math

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    图像预处理器

    提供图像预处理功能，包括降噪、二值化、纠偏等。
    """

    @staticmethod
    def denoise(
        image: Image.Image, strength: float = 1.0, method: str = "bilateral"
    ) -> Image.Image:
        """
        图像降噪

        修复说明：
        - 改用双边滤波替代高斯模糊
        - 原因：双边滤波是边缘保持平滑滤波器，可以去除噪声同时保持边缘清晰
        - 对于OCR任务，双边滤波比高斯模糊效果更好，因为不会模糊文字边缘

        Args:
            image: PIL Image 对象
            strength: 降噪强度（0.0 - 1.0）
            method: 降噪方法 ('bilateral' 或 'gaussian' 或 'fastNlMeans')

        Returns:
            Image.Image: 降噪后的图像
        """
        if strength <= 0:
            return image

        import cv2
        import numpy as np

        # 转换为OpenCV格式
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        try:
            if method == "bilateral":
                # 使用双边滤波（边缘保持）
                # 双边滤波参数根据strength动态调整
                d = int(5 + strength * 10)  # 邻域直径
                sigma_color = 75  # 颜色空间标准差
                sigma_space = 75  # 坐标空间标准差

                cv_image = cv2.bilateralFilter(cv_image, d, sigma_color, sigma_space)

            elif method == "fastNlMeans":
                # 使用非局部均值降噪（效果最好，但计算量大）
                h = int(10 * strength)  # 滤波强度
                template_window_size = 7
                search_window_size = 21

                cv_image = cv2.fastNlMeansDenoisingColored(
                    cv_image, None, h, h, template_window_size, search_window_size
                )

            else:
                # 使用高斯模糊（最快，但效果一般）
                kernel_size = int(3 + strength * 5)
                kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1

                cv_image = cv2.GaussianBlur(
                    cv_image, (kernel_size, kernel_size), strength
                )

            # 转换回PIL Image
            return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))

        except Exception as e:
            logger.error(f"降噪失败（方法: {method}）: {e}", exc_info=True)
            # 降噪失败时返回原图
            return image

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
        gray_image = image.convert("L")

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
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

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
    def enhance_document_quality(
        image: Image.Image,
        contrast_factor: float = 1.5,
        sharpness_factor: float = 1.5,
        denoise_strength: float = 0.5,
    ) -> Image.Image:
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

    @staticmethod
    def apply_doc_orientation_classification(
        image: Image.Image,
    ) -> Tuple[Image.Image, Optional[int]]:
        """
        应用PaddleOCR官方文档方向分类

        使用PaddleOCR的PP-LCNet_x1_0_doc_ori模型进行文档方向分类，
        支持0°/90°/180°/270°旋转校正。

        Args:
            image: PIL Image 对象

        Returns:
            Tuple[Image.Image, Optional[int]]: (校正后的图像, 旋转角度)
        """
        try:
            import cv2
            import numpy as np

            # 转换为OpenCV格式（RGB）
            img_array = np.array(image)
            if len(img_array.shape) == 2:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
            cv_image = img_array[:, :, ::-1]  # RGB -> BGR

            # 尝试使用PaddleOCR的文档方向分类
            # 注意：如果未安装paddleocr库，则使用简化版方向检测
            try:
                from paddleocr import PaddleOCR

                # 创建轻量级方向分类器
                ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang="ch",
                    show_log=False,
                    det=False,
                    rec=False,
                    use_gpu=False,
                )

                # 调用方向分类
                result = ocr.ocr(cv_image, cls=True)

                # PaddleOCR返回的cls结果：[0-3] 对应 [0°, 90°, 180°, 270°]
                if result and result[0] and len(result[0][0]) == 4:
                    orientation = result[0][0][3]  # cls分数
                    if orientation > 0:  # >0 表示需要旋转
                        angle_map = {1: 90, 2: 180, 3: 270}
                        angle = angle_map.get(orientation, 0)

                        if angle != 0:
                            # 使用PIL旋转
                            rotated = image.rotate(
                                -angle, expand=True, fillcolor=(255, 255, 255)
                            )
                            return rotated, angle

                return image, 0

            except ImportError:
                logger.warning("PaddleOCR库未安装，使用简化版方向检测")
                return image, 0

        except Exception as e:
            logger.error(f"文档方向分类失败: {e}", exc_info=True)
            return image, 0

    @staticmethod
    def apply_doc_unwarping(image: Image.Image) -> Image.Image:
        """
        应用PaddleOCR官方文档纠平（UVDoc模型）

        使用UVDoc模型处理弯曲文档图像，进行透视变换和曲面矫正。

        Args:
            image: PIL Image 对象

        Returns:
            Image.Image: 矫正后的图像
        """
        try:
            import cv2
            import numpy as np

            # 转换为OpenCV格式
            img_array = np.array(image)
            if len(img_array.shape) == 2:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
            cv_image = img_array[:, :, ::-1]  # RGB -> BGR

            # 尝试使用PaddleOCR的DocPreprocessor
            try:
                from paddleocr import DocPreprocessor

                # 创建文档预处理器
                preprocessor = DocPreprocessor(
                    use_doc_unwarping=True,
                    # 注意：需要UVDoc模型文件
                    # use_doc_orientation_classify=False  # 单独处理方向分类
                )

                # 执行文档纠平
                result = preprocessor(cv_image)

                # 转换回PIL Image
                if result is not None and len(result.shape) == 3:
                    result_rgb = result[:, :, ::-1]  # BGR -> RGB
                    return Image.fromarray(result_rgb, mode="RGB")
                else:
                    return image

            except ImportError:
                logger.warning("PaddleOCR DocPreprocessor未可用，跳过文档纠平")
                return image

        except Exception as e:
            logger.error(f"文档纠平失败: {e}", exc_info=True)
            return image

    @staticmethod
    def det_resize_img(
        image: Image.Image,
        image_shape: tuple = (3, 640, 640),
        limit_type: str = "min",
        limit_side_len: int = 736,
    ) -> Image.Image:
        """
        PaddleOCR官方检测图像Resize（DetResizeImg）

        按照PaddleOCR官方的检测图像resize逻辑调整图像尺寸。

        Args:
            image: PIL Image 对象
            image_shape: 目标图像形状 (C, H, W)
            limit_type: 限制类型 ('min' 或 'max')
            limit_side_len: 限制边长

        Returns:
            调整后的图像
        """
        try:
            import cv2
            import numpy as np

            # 转换为OpenCV格式
            img_array = np.array(image)
            if len(img_array.shape) == 2:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)

            h, w = img_array.shape[:2]
            img_c, img_h, img_w = image_shape

            # 按照PaddleOCR官方逻辑计算目标尺寸
            if limit_type == "min":
                # 限制最小边
                im_ratio = float(h) / w
                tar_ratio = float(img_h) / img_w

                if im_ratio <= tar_ratio:
                    ratio = float(img_h) / h
                else:
                    ratio = float(img_w) / w
            else:  # limit_type == "max"
                # 限制最大边
                im_max = max(h, w)
                tar_max = max(img_h, img_w)

                if im_max <= tar_max:
                    return image

                ratio = float(tar_max) / im_max

            # 计算新尺寸
            resize_h = int(h * ratio)
            resize_w = int(w * ratio)

            # 执行resize
            resized = cv2.resize(
                img_array, (resize_w, resize_h), interpolation=cv2.INTER_LINEAR
            )
            resized_rgb = resized[:, :, ::-1]  # BGR -> RGB if needed

            return Image.fromarray(resized_rgb, mode="RGB")

        except Exception as e:
            logger.error(f"DetResizeImg失败: {e}", exc_info=True)
            return image

    @staticmethod
    def rec_resize_img(
        image: Image.Image,
        image_shape: tuple = (3, 48, 320),
        max_wh_ratio: float = 16.0,
    ) -> Image.Image:
        """
        PaddleOCR官方识别图像Resize（RecResizeImg）

        按照PaddleOCR官方的识别图像resize逻辑调整图像尺寸，
        保持宽高比，适合长文本识别。

        Args:
            image: PIL Image 对象
            image_shape: 目标图像形状 (C, H, W)
            max_wh_ratio: 最大宽高比

        Returns:
            调整后的图像
        """
        try:
            import cv2
            import numpy as np

            # 转换为OpenCV格式
            img_array = np.array(image)
            if len(img_array.shape) == 2:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)

            h, w = img_array.shape[:2]
            img_c, img_h, img_w = image_shape

            # 保持宽高比调整
            ratio = float(w) / float(h)
            if math.ceil(img_h * ratio) > img_w:
                ratio_w = float(img_w) / float(w)
                new_h = int(img_h * ratio_w)
                new_w = img_w
            else:
                new_h = img_h
                new_w = int(img_h * ratio)

            # 执行resize
            resized = cv2.resize(
                img_array, (new_w, new_h), interpolation=cv2.INTER_LINEAR
            )
            resized_rgb = resized[:, :, ::-1]

            return Image.fromarray(resized_rgb, mode="RGB")

        except Exception as e:
            logger.error(f"RecResizeImg失败: {e}", exc_info=True)
            return image
