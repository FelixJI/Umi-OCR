# ===============================================
# =============== 图像预处理工具 ===============
# ===============================================

"""
图像预处理模块 - 用于OCR识别前的图像增强处理
支持的预处理操作：
- 中值滤波（降噪）
- 锐化增强
- 对比度调整
- 亮度调整
- 灰度转换
- 自适应二值化
- PDF转图像
- 图像缩放和旋转
"""

from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
from io import BytesIO
from typing import Union, Optional, List, Tuple, Generator
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    图像预处理器 - 用于OCR任务前的图像增强

    配置项说明：
    - enabled: 是否启用预处理
    - denoise: 降噪强度 (0-9, 奇数, 0表示禁用)
    - sharpen: 锐化系数 (0.0-3.0, 1.0表示不变)
    - contrast: 对比度系数 (0.5-2.0, 1.0表示不变)
    - brightness: 亮度系数 (0.5-2.0, 1.0表示不变)
    - grayscale: 是否转为灰度图
    - threshold: 二值化阈值 (0-255, -1表示禁用, 0表示自适应)
    """

    def __init__(self, config: Optional[dict] = None):
        """
        初始化预处理器

        Args:
            config: 预处理配置字典
        """
        self.config = config or {}
        self._enabled = self.config.get("preprocessing.enabled", False)

    @property
    def enabled(self) -> bool:
        """是否启用预处理"""
        return self._enabled

    def process(self, image: Union[Image.Image, bytes, str]) -> Image.Image:
        """
        执行预处理流水线

        Args:
            image: PIL.Image对象、图片字节流或图片路径

        Returns:
            处理后的PIL.Image对象
        """
        # 统一转换为PIL.Image
        img = self._to_pil_image(image)

        if not self._enabled:
            return img

        try:
            # 检查是否启用自适应预处理
            enable_adaptive = self.config.get("preprocessing.enable_adaptive_preprocess", False)

            if enable_adaptive:
                # 使用自适应预处理（基于质量分析动态调整参数）
                img = self._apply_adaptive_preprocess(img)
            else:
                # 使用标准预处理流程
                img = self._apply_standard_preprocess(img)

        except Exception as e:
            logger.error(f"图像预处理失败: {e}", exc_info=True)
            # 预处理失败时返回原图
            return self._to_pil_image(image)

        return img

    def _apply_standard_preprocess(self, img: Image.Image) -> Image.Image:
        """
        应用标准预处理流程

        Args:
            img: PIL Image 对象

        Returns:
            处理后的图像
        """
        # 1. 中值滤波（降噪）
        img = self._apply_denoise(img)

        # 1.5. 双边滤波降噪（边缘保持）
        img = self._apply_bilateral_filter(img)

        # 2. 锐化增强
        img = self._apply_sharpen(img)

        # 3. CLAHE对比度增强（在对比度调整之前应用）
        img = self._apply_clahe(img)

        # 4. 对比度调整
        img = self._apply_contrast(img)

        # 5. 亮度调整
        img = self._apply_brightness(img)

        # 6. 灰度转换和二值化
        img = self._apply_grayscale_and_threshold(img)

        return img

    def _apply_adaptive_preprocess(self, img: Image.Image) -> Image.Image:
        """
        应用自适应预处理（基于文档质量分析动态调整参数）

        修复说明：
        - 新增功能，基于DocumentQualityAnalyzer分析图像质量
        - 根据质量分析结果动态调整预处理参数
        - 提高预处理效果，避免不必要的处理

        Args:
            img: PIL Image 对象

        Returns:
            处理后的图像
        """
        try:
            # 1. 分析文档质量
            quality = DocumentQualityAnalyzer.analyze(img)

            logger.debug(
                f"文档质量分析 - 清晰度: {quality['sharpness']:.2f}, "
                f"亮度: {quality['brightness']:.1f}, "
                f"对比度: {quality['contrast']:.1f}, "
                f"质量分数: {quality['quality_score']:.2f}"
            )

            # 2. 根据质量分析结果动态调整预处理
            processed = img

            # 2.1 清晰度低时启用锐化
            if quality['sharpness'] < 0.5:
                sharpen_factor = self.config.get("preprocessing.sharpen", 1.0)
                if sharpen_factor == 1.0:
                    # 如果用户没有设置锐化，自动设置
                    sharpen_factor = 1.5
                processed = self._apply_sharpen_with_factor(processed, sharpen_factor)
                logger.debug(f"自适应: 启用锐化（清晰度: {quality['sharpness']:.2f}）")

            # 2.2 对比度低时启用CLAHE或对比度增强
            if quality['contrast'] < 80:
                # 优先使用CLAHE
                enable_clahe = self.config.get("preprocessing.enable_clahe", False)
                if enable_clahe:
                    processed = self._apply_clahe(processed)
                else:
                    # 使用对比度调整
                    contrast_factor = self.config.get("preprocessing.contrast", 1.0)
                    if contrast_factor == 1.0:
                        # 如果用户没有设置对比度，自动设置
                        contrast_factor = 1.3
                    processed = self._apply_contrast_with_factor(processed, contrast_factor)
                logger.debug(f"自适应: 启用对比度增强（对比度: {quality['contrast']:.1f}）")

            # 2.3 亮度异常时调整亮度
            if quality['brightness'] < 100:
                # 图像太暗
                brightness_factor = 1.2
                processed = self._apply_brightness_with_factor(processed, brightness_factor)
                logger.debug(f"自适应: 调整亮度（亮度: {quality['brightness']:.1f} -> 太暗）")
            elif quality['brightness'] > 200:
                # 图像太亮
                brightness_factor = 0.8
                processed = self._apply_brightness_with_factor(processed, brightness_factor)
                logger.debug(f"自适应: 调整亮度（亮度: {quality['brightness']:.1f} -> 太亮）")

            # 2.4 质量分数低时应用降噪
            if quality['quality_score'] < 0.5:
                # 先尝试双边滤波
                enable_bilateral = self.config.get("preprocessing.enable_bilateral", False)
                if enable_bilateral:
                    processed = self._apply_bilateral_filter(processed)
                else:
                    # 使用中值滤波
                    processed = self._apply_denoise(processed)
                logger.debug(f"自适应: 启用降噪（质量分数: {quality['quality_score']:.2f}）")

            # 3. 应用其他用户配置的预处理
            processed = self._apply_grayscale_and_threshold(processed)

            return processed

        except Exception as e:
            logger.error(f"自适应预处理失败: {e}", exc_info=True)
            # 自适应预处理失败时，回退到标准预处理
            return self._apply_standard_preprocess(img)

    def _apply_sharpen_with_factor(self, img: Image.Image, factor: float) -> Image.Image:
        """使用指定锐度因子应用锐化"""
        if factor != 1.0 and factor > 0:
            factor = max(0.0, min(3.0, float(factor)))  # 限制范围0-3
            img = ImageEnhance.Sharpness(img).enhance(factor)
        return img

    def _apply_contrast_with_factor(self, img: Image.Image, factor: float) -> Image.Image:
        """使用指定对比度因子应用对比度调整"""
        if factor != 1.0 and factor > 0:
            factor = max(0.5, min(2.0, float(factor)))  # 限制范围0.5-2
            img = ImageEnhance.Contrast(img).enhance(factor)
        return img

    def _apply_brightness_with_factor(self, img: Image.Image, factor: float) -> Image.Image:
        """使用指定亮度因子应用亮度调整"""
        if factor != 1.0 and factor > 0:
            factor = max(0.5, min(2.0, float(factor)))  # 限制范围0.5-2
            img = ImageEnhance.Brightness(img).enhance(factor)
        return img

    def process_bytes(self, image_bytes: bytes) -> bytes:
        """
        处理图片字节流并返回字节流

        Args:
            image_bytes: 原始图片字节流

        Returns:
            处理后的图片字节流（PNG格式）
        """
        img = self.process(image_bytes)

        buffer = BytesIO()
        # 保持原格式或使用PNG
        img_format = getattr(img, "format", None) or "PNG"
        img.save(buffer, format=img_format)
        return buffer.getvalue()

    def _to_pil_image(self, image: Union[Image.Image, bytes, str]) -> Image.Image:
        """将输入转换为PIL.Image对象"""
        if isinstance(image, Image.Image):
            return image
        elif isinstance(image, bytes):
            return Image.open(BytesIO(image))
        elif isinstance(image, str):
            return Image.open(image)
        else:
            raise ValueError(f"不支持的图像类型: {type(image)}")

    def _apply_denoise(self, img: Image.Image) -> Image.Image:
        """应用中值滤波降噪"""
        size = self.config.get("preprocessing.denoise", 0)
        if size > 0:
            # 确保是奇数
            size = int(size)
            if size % 2 == 0:
                size += 1
            size = max(1, min(9, size))  # 限制范围1-9
            if size > 1:
                img = img.filter(ImageFilter.MedianFilter(size=size))
        return img

    def _apply_bilateral_filter(self, img: Image.Image) -> Image.Image:
        """
        应用双边滤波降噪

        双边滤波是一种边缘保持平滑滤波器，特别适合OCR降噪。
        它可以去除噪声同时保持边缘清晰，比高斯模糊效果更好。

        Args:
            img: PIL Image 对象

        Returns:
            降噪后的图像
        """
        enable_bilateral = self.config.get("preprocessing.enable_bilateral", False)

        if not enable_bilateral:
            return img

        try:
            import cv2
            import numpy as np

            # 获取双边滤波参数
            d = self.config.get("preprocessing.bilateral_d", 9)  # 邻域直径
            sigma_color = self.config.get(
                "preprocessing.bilateral_sigma_color", 75
            )  # 颜色空间的标准差
            sigma_space = self.config.get(
                "preprocessing.bilateral_sigma_space", 75
            )  # 坐标空间的标准差

            # 转换为OpenCV格式
            img_array = np.array(img)
            if len(img_array.shape) == 2:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)

            # 转换为BGR
            img_bgr = img_array[:, :, ::-1]

            # 应用双边滤波
            filtered = cv2.bilateralFilter(img_bgr, d, sigma_color, sigma_space)

            # 转换回RGB和PIL Image
            filtered_rgb = filtered[:, :, ::-1]
            return Image.fromarray(filtered_rgb, mode="RGB")

        except Exception as e:
            logger.error(f"双边滤波失败: {e}", exc_info=True)
            return img

    def _apply_sharpen(self, img: Image.Image) -> Image.Image:
        """应用锐化增强"""
        factor = self.config.get("preprocessing.sharpen", 1.0)
        if factor != 1.0 and factor > 0:
            factor = max(0.0, min(3.0, float(factor)))  # 限制范围0-3
            img = ImageEnhance.Sharpness(img).enhance(factor)
        return img

    def _apply_contrast(self, img: Image.Image) -> Image.Image:
        """应用对比度调整"""
        factor = self.config.get("preprocessing.contrast", 1.0)
        if factor != 1.0 and factor > 0:
            factor = max(0.5, min(2.0, float(factor)))  # 限制范围0.5-2
            img = ImageEnhance.Contrast(img).enhance(factor)
        return img

    def _apply_clahe(self, img: Image.Image) -> Image.Image:
        """
        应用CLAHE对比度受限自适应直方图均衡化

        CLAHE (Contrast Limited Adaptive Histogram Equalization) 比简单的
        对比度调整效果更好，特别适合OCR文档。

        Args:
            img: PIL Image 对象

        Returns:
            增强后的图像
        """
        enable_clahe = self.config.get("preprocessing.enable_clahe", False)

        if not enable_clahe:
            return img

        try:
            import cv2
            import numpy as np

            # 获取CLAHE参数
            clip_limit = self.config.get("preprocessing.clahe_clip_limit", 2.0)
            tile_size = self.config.get("preprocessing.clahe_tile_size", 8)

            # 转换为OpenCV格式
            img_array = np.array(img)

            # 判断图像类型
            if len(img_array.shape) == 2:
                # 灰度图
                clahe = cv2.createCLAHE(
                    clipLimit=clip_limit, tileGridSize=(tile_size, tile_size)
                )
                img_array = clahe.apply(img_array)
            elif len(img_array.shape) == 3:
                # 彩色图 - 转换到LAB颜色空间，只对L通道应用CLAHE
                lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
                l, a, b = cv2.split(lab)

                # 对L通道应用CLAHE
                clahe = cv2.createCLAHE(
                    clipLimit=clip_limit, tileGridSize=(tile_size, tile_size)
                )
                l = clahe.apply(l)

                # 合并通道并转换回RGB
                lab = cv2.merge([l, a, b])
                img_array = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

            return Image.fromarray(img_array)

        except Exception as e:
            logger.error(f"CLAHE处理失败: {e}", exc_info=True)
            return img

    def _apply_brightness(self, img: Image.Image) -> Image.Image:
        """应用亮度调整"""
        factor = self.config.get("preprocessing.brightness", 1.0)
        if factor != 1.0 and factor > 0:
            factor = max(0.5, min(2.0, float(factor)))  # 限制范围0.5-2
            img = ImageEnhance.Brightness(img).enhance(factor)
        return img

    def _apply_grayscale_and_threshold(self, img: Image.Image) -> Image.Image:
        """应用灰度转换和二值化"""
        grayscale = self.config.get("preprocessing.grayscale", False)
        threshold = self.config.get("preprocessing.threshold", -1)

        if grayscale:
            img = img.convert("L")

            # 二值化处理
            if threshold >= 0:
                if threshold == 0:
                    # 自适应二值化（使用Otsu算法）
                    img = self._otsu_threshold(img)
                else:
                    # 固定阈值二值化
                    threshold = max(0, min(255, int(threshold)))
                    img = img.point(lambda p: 255 if p > threshold else 0)

        return img

    def _otsu_threshold(self, img: Image.Image) -> Image.Image:
        """
        Otsu自适应二值化算法

        Args:
            img: 灰度图像

        Returns:
            二值化后的图像
        """
        # 转换为numpy数组
        img_array = np.array(img)

        # 计算直方图
        hist, _ = np.histogram(img_array.flatten(), bins=256, range=(0, 256))

        # 归一化直方图
        hist_norm = hist.astype(float) / hist.sum()

        # Otsu算法
        best_threshold = 0
        best_variance = 0

        for t in range(256):
            # 计算类概率
            w0 = hist_norm[:t].sum()
            w1 = hist_norm[t:].sum()

            if w0 == 0 or w1 == 0:
                continue

            # 计算类均值
            mu0 = (np.arange(t) * hist_norm[:t]).sum() / w0
            mu1 = (np.arange(t, 256) * hist_norm[t:]).sum() / w1

            # 计算类间方差
            variance = w0 * w1 * (mu0 - mu1) ** 2

            if variance > best_variance:
                best_variance = variance
                best_threshold = t

        # 应用阈值
        binary_array = (img_array > best_threshold).astype(np.uint8) * 255

        return Image.fromarray(binary_array, mode="L")

    @staticmethod
    def get_default_config() -> dict:
        """获取默认配置"""
        return {
            "preprocessing.enabled": False,
            "preprocessing.denoise": 0,
            "preprocessing.sharpen": 1.0,
            "preprocessing.contrast": 1.0,
            "preprocessing.brightness": 1.0,
            "preprocessing.grayscale": False,
            "preprocessing.threshold": -1,
        }

    @staticmethod
    def get_config_schema() -> dict:
        """获取配置项定义（用于UI生成）"""
        return {
            "preprocessing.enabled": {
                "label": "启用图像预处理/Enable Preprocessing",
                "type": "bool",
                "default": False,
            },
            "preprocessing.denoise": {
                "label": "降噪强度/Denoise Level",
                "type": "int",
                "default": 0,
                "min": 0,
                "max": 9,
                "tip": "0=禁用, 1-9奇数值 (Off=0, odd values 1-9)",
            },
            "preprocessing.sharpen": {
                "label": "锐化系数/Sharpen Factor",
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 3.0,
                "step": 0.1,
                "tip": "1.0=不变 (1.0=unchanged)",
            },
            "preprocessing.contrast": {
                "label": "对比度/Contrast",
                "type": "float",
                "default": 1.0,
                "min": 0.5,
                "max": 2.0,
                "step": 0.1,
                "tip": "1.0=不变 (1.0=unchanged)",
            },
            "preprocessing.brightness": {
                "label": "亮度/Brightness",
                "type": "float",
                "default": 1.0,
                "min": 0.5,
                "max": 2.0,
                "step": 0.1,
                "tip": "1.0=不变 (1.0=unchanged)",
            },
            "preprocessing.grayscale": {
                "label": "转灰度图/Convert to Grayscale",
                "type": "bool",
                "default": False,
            },
            "preprocessing.threshold": {
                "label": "二值化阈值/Binarization Threshold",
                "type": "int",
                "default": -1,
                "min": -1,
                "max": 255,
                "tip": "-1=禁用, 0=自适应, 1-255=固定阈值 (-1=off, 0=auto, 1-255=fixed)",
            },
            "preprocessing.enable_clahe": {
                "label": "启用CLAHE对比度增强/Enable CLAHE",
                "type": "bool",
                "default": False,
                "tip": "CLAHE对比度受限自适应直方图均衡化，效果优于简单对比度调整",
            },
            "preprocessing.clahe_clip_limit": {
                "label": "CLAHE裁剪限/CLAHE Clip Limit",
                "type": "float",
                "default": 2.0,
                "min": 0.5,
                "max": 10.0,
                "step": 0.5,
                "tip": "CLAHE裁剪限值，控制对比度增强强度 (0.5-10.0)",
            },
            "preprocessing.clahe_tile_size": {
                "label": "CLAHE网格大小/CLAHE Tile Size",
                "type": "int",
                "default": 8,
                "min": 4,
                "max": 16,
                "step": 2,
                "tip": "CLAHE网格大小，控制局部对比度范围 (4-16)",
            },
            "preprocessing.enable_bilateral": {
                "label": "启用双边滤波/Enable Bilateral Filter",
                "type": "bool",
                "default": False,
                "tip": "双边滤波降噪，边缘保持平滑，比高斯模糊效果更好",
            },
            "preprocessing.bilateral_d": {
                "label": "双边滤波直径/Bilateral Filter d",
                "type": "int",
                "default": 9,
                "min": 5,
                "max": 25,
                "step": 2,
                "tip": "邻域直径 (5-25)",
            },
            "preprocessing.bilateral_sigma_color": {
                "label": "双边滤波颜色sigma/Bilateral Sigma Color",
                "type": "int",
                "default": 75,
                "min": 50,
                "max": 150,
                "step": 5,
                "tip": "颜色空间标准差 (50-150)",
            },
            "preprocessing.bilateral_sigma_space": {
                "label": "双边滤波空间sigma/Bilateral Sigma Space",
                "type": "int",
                "default": 75,
                "min": 50,
                "max": 150,
                "step": 5,
                "tip": "坐标空间标准差 (50-150)",
            },
        }


class DocumentQualityAnalyzer:
    """
    文档质量分析器

    评估文档图像的质量指标，包括清晰度、光照、对比度等。
    可用于自动判断文档是否需要预处理。
    """

    @staticmethod
    def analyze(image: Image.Image) -> dict:
        """
        分析文档图像质量

        Args:
            image: PIL Image 对象

        Returns:
            dict: 包含各项质量指标的字典
                - sharpness: 清晰度 (0-1，越高越好)
                - brightness: 亮度 (0-255)
                - contrast: 对比度 (0-255)
                - saturation: 饱和度 (0-255)
                - quality_score: 综合质量分数 (0-1)
                - recommendations: 建议的预处理操作
        """
        try:
            import cv2
            import numpy as np

            # 转换为OpenCV格式
            img_array = np.array(image)
            if len(img_array.shape) == 2:
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
            else:
                img_bgr = img_array[:, :, ::-1]  # RGB -> BGR

            # 1. 计算清晰度（使用拉普拉斯方差）
            sharpness = DocumentQualityAnalyzer._calculate_sharpness(img_bgr)

            # 2. 计算亮度
            brightness = DocumentQualityAnalyzer._calculate_brightness(img_bgr)

            # 3. 计算对比度
            contrast = DocumentQualityAnalyzer._calculate_contrast(img_bgr)

            # 4. 计算饱和度（仅彩色图像）
            saturation = DocumentQualityAnalyzer._calculate_saturation(img_bgr)

            # 5. 计算综合质量分数
            quality_score = DocumentQualityAnalyzer._calculate_quality_score(
                sharpness, brightness, contrast, saturation
            )

            # 6. 生成预处理建议
            recommendations = DocumentQualityAnalyzer._generate_recommendations(
                sharpness, brightness, contrast, saturation
            )

            return {
                "sharpness": sharpness,
                "brightness": brightness,
                "contrast": contrast,
                "saturation": saturation,
                "quality_score": quality_score,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"文档质量分析失败: {e}", exc_info=True)
            return {
                "sharpness": 0.5,
                "brightness": 128,
                "contrast": 128,
                "saturation": 128,
                "quality_score": 0.5,
                "recommendations": [],
            }

    @staticmethod
    def _calculate_sharpness(image: np.ndarray) -> float:
        """
        使用拉普拉斯方差计算清晰度

        值越高表示图像越清晰。
        """
        try:
            import cv2
            import numpy as np

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            sharpness = float(laplacian.var())

            # 归一化到 0-1 范围（假设合理范围是 0-2000）
            normalized = min(1.0, sharpness / 2000.0)
            return max(0.0, normalized)

        except Exception:
            return 0.5

    @staticmethod
    def _calculate_brightness(image: np.ndarray) -> float:
        """
        计算图像平均亮度
        """
        try:
            import cv2
            import numpy as np

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            brightness = float(np.mean(gray))
            return brightness

        except Exception:
            return 128.0

    @staticmethod
    def _calculate_contrast(image: np.ndarray) -> float:
        """
        计算图像对比度（使用标准差）
        """
        try:
            import cv2
            import numpy as np

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            contrast = float(np.std(gray))

            # 归一化到 0-255 范围
            normalized = min(255.0, contrast * 2.0)
            return max(0.0, normalized)

        except Exception:
            return 128.0

    @staticmethod
    def _calculate_saturation(image: np.ndarray) -> float:
        """
        计算图像平均饱和度
        """
        try:
            import cv2
            import numpy as np

            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            saturation = float(np.mean(hsv[:, :, 1]))
            return saturation

        except Exception:
            return 128.0

    @staticmethod
    def _calculate_quality_score(
        sharpness: float, brightness: float, contrast: float, saturation: float
    ) -> float:
        """
        计算综合质量分数

        Args:
            sharpness: 清晰度 (0-1)
            brightness: 亮度 (0-255)
            contrast: 对比度 (0-255)
            saturation: 饱和度 (0-255)

        Returns:
            质量分数 (0-1)
        """
        import numpy as np

        # 理想值范围
        ideal_brightness = (100, 200)  # 理想亮度范围
        ideal_contrast = (50, 150)  # 理想对比度范围
        ideal_saturation = (80, 180)  # 理想饱和度范围

        # 计算各项得分
        brightness_score = 1.0 - abs(brightness - np.mean(ideal_brightness)) / 128.0
        brightness_score = max(0.0, min(1.0, brightness_score))

        contrast_score = 1.0 - abs(contrast - np.mean(ideal_contrast)) / 128.0
        contrast_score = max(0.0, min(1.0, contrast_score))

        saturation_score = 1.0 - abs(saturation - np.mean(ideal_saturation)) / 128.0
        saturation_score = max(0.0, min(1.0, saturation_score))

        # 加权平均（清晰度最重要）
        weights = {
            "sharpness": 0.4,
            "brightness": 0.2,
            "contrast": 0.2,
            "saturation": 0.2,
        }

        quality_score = (
            sharpness * weights["sharpness"]
            + brightness_score * weights["brightness"]
            + contrast_score * weights["contrast"]
            + saturation_score * weights["saturation"]
        )

        return float(quality_score)

    @staticmethod
    def _generate_recommendations(
        sharpness: float, brightness: float, contrast: float, saturation: float
    ) -> list:
        """
        根据质量指标生成预处理建议
        """
        recommendations = []

        # 清晰度建议
        if sharpness < 0.3:
            recommendations.append("锐化增强")
            recommendations.append("双边滤波降噪")
        elif sharpness < 0.5:
            recommendations.append("锐化增强")

        # 亮度建议
        if brightness < 80:
            recommendations.append("提高亮度")
        elif brightness > 220:
            recommendations.append("降低亮度")

        # 对比度建议
        if contrast < 50:
            recommendations.append("对比度增强")
            recommendations.append("CLAHE对比度增强")
        elif contrast < 80:
            recommendations.append("对比度增强")

        # 饱和度建议
        if saturation < 60:
            recommendations.append("饱和度调整")

        return recommendations


class ShadowRemover:
    """
    阴影去除器

    用于去除文档扫描时的阴影。
    使用形态学操作和自适应阈值。
    """

    @staticmethod
    def remove_shadow(image: Image.Image, method: str = "adaptive") -> Image.Image:
        """
        去除图像阴影

        Args:
            image: PIL Image 对象
            method: 去阴影方法 ('adaptive', 'morphology', 'inpaint')

        Returns:
            去除阴影后的图像
        """
        try:
            import cv2
            import numpy as np

            # 转换为OpenCV格式
            img_array = np.array(image)
            if len(img_array.shape) == 2:
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
            else:
                img_bgr = img_array[:, :, ::-1]  # RGB -> BGR

            if method == "adaptive":
                return ShadowRemover._remove_shadow_adaptive(img_bgr)
            elif method == "morphology":
                return ShadowRemover._remove_shadow_morphology(img_bgr)
            elif method == "inpaint":
                return ShadowRemover._remove_shadow_inpaint(img_bgr)
            else:
                return image

        except Exception as e:
            logger.error(f"去阴影失败: {e}", exc_info=True)
            return image

    @staticmethod
    def _remove_shadow_adaptive(image: np.ndarray) -> Image.Image:
        """
        使用自适应阈值去除阴影

        对每个小区域使用不同的阈值，适合不均匀光照。
        """
        try:
            import cv2
            import numpy as np

            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # 使用自适应阈值
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # 反转图像
            result = 255 - adaptive

            return Image.fromarray(result, mode="L")

        except Exception:
            return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), mode="L")

    @staticmethod
    def _remove_shadow_morphology(image: np.ndarray) -> Image.Image:
        """
        使用形态学操作去除阴影

        使用膨胀和腐蚀操作估计并去除阴影。
        """
        try:
            import cv2
            import numpy as np

            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # 使用Otsu阈值
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 形态学开运算（去除噪声）
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

            # 形态学闭运算（填充小洞）
            closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)

            return Image.fromarray(closed, mode="L")

        except Exception:
            return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), mode="L")

    @staticmethod
    def _remove_shadow_inpaint(image: np.ndarray) -> Image.Image:
        """
        使用修复技术去除阴影（简化版）

        检测暗色区域并使用邻域像素修复。
        """
        try:
            import cv2
            import numpy as np

            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # 计算亮度
            blur = cv2.GaussianBlur(gray, (21, 21), 0)
            normalized_gray = gray.astype("float32") / 255.0
            normalized_blur = blur.astype("float32") / 255.0

            # 检测阴影（比背景暗的区域）
            ratio = normalized_gray / normalized_blur
            shadow_mask = np.where(ratio < 0.8, 1, 0).astype("uint8")

            # 如果检测到阴影，使用原图
            if np.sum(shadow_mask) > 0:
                # 使用CLAHE增强
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                return Image.fromarray(enhanced, mode="L")
            else:
                return Image.fromarray(gray, mode="L")

        except Exception:
            return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), mode="L")


class PDFProcessor:
    """
    PDF处理器 - 将PDF文档转换为图像用于OCR

    支持使用 PyMuPDF (fitz) 进行PDF渲染
    """

    def __init__(self, dpi: int = 200, color_space: str = "rgb"):
        """
        初始化PDF处理器

        Args:
            dpi: 渲染分辨率（默认200）
            color_space: 颜色空间 (rgb/gray)
        """
        self.dpi = dpi
        self.color_space = color_space
        self._fitz = None

    def _ensure_fitz(self):
        """确保PyMuPDF已导入"""
        if self._fitz is None:
            try:
                import fitz

                self._fitz = fitz
            except ImportError:
                raise ImportError("PDF处理需要安装 PyMuPDF: pip install pymupdf")
        return self._fitz

    def pdf_to_images(
        self, pdf_path: str, page_numbers: Optional[List[int]] = None
    ) -> Generator[Tuple[int, Image.Image], None, None]:
        """
        将PDF文件转换为图像

        Args:
            pdf_path: PDF文件路径
            page_numbers: 指定页码列表（从0开始），None表示所有页

        Yields:
            (页码, PIL.Image) 元组
        """
        fitz = self._ensure_fitz()

        doc = fitz.open(pdf_path)
        try:
            total_pages = len(doc)

            if page_numbers is None:
                page_numbers = range(total_pages)
            else:
                # 过滤无效页码
                page_numbers = [p for p in page_numbers if 0 <= p < total_pages]

            # 计算缩放比例
            zoom = self.dpi / 72.0  # PDF默认72 DPI
            matrix = fitz.Matrix(zoom, zoom)

            for page_num in page_numbers:
                page = doc[page_num]

                # 渲染页面
                if self.color_space == "gray":
                    pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csGRAY)
                else:
                    pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)

                # 转换为PIL图像
                img = Image.frombytes(
                    "RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples
                )

                yield page_num, img

        finally:
            doc.close()

    def pdf_to_images_list(
        self, pdf_path: str, page_numbers: Optional[List[int]] = None
    ) -> List[Image.Image]:
        """
        将PDF文件转换为图像列表

        Args:
            pdf_path: PDF文件路径
            page_numbers: 指定页码列表

        Returns:
            PIL.Image列表
        """
        return [img for _, img in self.pdf_to_images(pdf_path, page_numbers)]

    def get_page_count(self, pdf_path: str) -> int:
        """获取PDF页数"""
        fitz = self._ensure_fitz()
        doc = fitz.open(pdf_path)
        try:
            return len(doc)
        finally:
            doc.close()

    def pdf_page_to_image(self, pdf_path: str, page_number: int = 0) -> Image.Image:
        """
        将PDF单页转换为图像

        Args:
            pdf_path: PDF文件路径
            page_number: 页码（从0开始）

        Returns:
            PIL.Image对象
        """
        for _, img in self.pdf_to_images(pdf_path, [page_number]):
            return img
        raise ValueError(f"PDF页码 {page_number} 无效")

    @staticmethod
    def is_pdf(file_path: str) -> bool:
        """检查文件是否为PDF"""
        return file_path.lower().endswith(".pdf")


class ImageResizer:
    """
    图像缩放器 - 用于调整图像尺寸
    """

    @staticmethod
    def resize_to_max(
        img: Image.Image, max_width: int = 4096, max_height: int = 4096
    ) -> Image.Image:
        """
        限制图像最大尺寸（保持宽高比）

        Args:
            img: 输入图像
            max_width: 最大宽度
            max_height: 最大高度

        Returns:
            缩放后的图像
        """
        width, height = img.size

        if width <= max_width and height <= max_height:
            return img

        # 计算缩放比例
        ratio = min(max_width / width, max_height / height)
        new_size = (int(width * ratio), int(height * ratio))

        return img.resize(new_size, Image.Resampling.LANCZOS)

    @staticmethod
    def resize_to_min(
        img: Image.Image, min_width: int = 640, min_height: int = 480
    ) -> Image.Image:
        """
        确保图像最小尺寸（保持宽高比）

        Args:
            img: 输入图像
            min_width: 最小宽度
            min_height: 最小高度

        Returns:
            缩放后的图像
        """
        width, height = img.size

        if width >= min_width and height >= min_height:
            return img

        # 计算缩放比例
        ratio = max(min_width / width, min_height / height)
        new_size = (int(width * ratio), int(height * ratio))

        return img.resize(new_size, Image.Resampling.LANCZOS)

    @staticmethod
    def resize_by_factor(img: Image.Image, factor: float) -> Image.Image:
        """
        按比例缩放图像

        Args:
            img: 输入图像
            factor: 缩放比例（1.0=原始大小）

        Returns:
            缩放后的图像
        """
        if factor == 1.0:
            return img

        width, height = img.size
        new_size = (int(width * factor), int(height * factor))

        return img.resize(new_size, Image.Resampling.LANCZOS)


class ImageRotator:
    """
    图像旋转器 - 用于校正图像方向
    """

    @staticmethod
    def auto_rotate(img: Image.Image) -> Image.Image:
        """
        根据EXIF信息自动旋转图像

        Args:
            img: 输入图像

        Returns:
            旋转后的图像
        """
        try:
            from PIL.ExifTags import TAGS

            exif = img.getexif()
            if not exif:
                return img

            # 获取方向标签
            orientation = None
            for tag, value in exif.items():
                if TAGS.get(tag) == "Orientation":
                    orientation = value
                    break

            if orientation is None:
                return img

            # 根据方向旋转
            if orientation == 3:
                return img.rotate(180, expand=True)
            elif orientation == 6:
                return img.rotate(270, expand=True)
            elif orientation == 8:
                return img.rotate(90, expand=True)

        except Exception as e:
            logger.warning(f"自动旋转失败: {e}")

        return img

    @staticmethod
    def rotate(
        img: Image.Image,
        angle: float,
        expand: bool = True,
        fill_color: Tuple[int, int, int] = (255, 255, 255),
    ) -> Image.Image:
        """
        旋转图像

        Args:
            img: 输入图像
            angle: 旋转角度（逆时针）
            expand: 是否扩展画布
            fill_color: 填充颜色

        Returns:
            旋转后的图像
        """
        if angle == 0:
            return img

        return img.rotate(angle, expand=expand, fillcolor=fill_color)

    @staticmethod
    def deskew(img: Image.Image) -> Image.Image:
        """
        简单的文档倾斜校正

        使用霍夫变换检测主要线条并校正倾斜
        注意：需要OpenCV支持

        Args:
            img: 输入图像

        Returns:
            校正后的图像
        """
        try:
            import cv2

            # 转换为OpenCV格式
            img_array = np.array(img)
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            # 边缘检测
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            # 霍夫变换检测直线
            lines = cv2.HoughLinesP(
                edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10
            )

            if lines is None:
                return img

            # 计算主要角度
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                # 只考虑接近水平的线条
                if abs(angle) < 45:
                    angles.append(angle)

            if not angles:
                return img

            # 计算中位数角度
            median_angle = np.median(angles)

            # 如果角度很小，不需要校正
            if abs(median_angle) < 0.5:
                return img

            # 旋转图像
            return ImageRotator.rotate(img, -median_angle)

        except ImportError:
            logger.warning("文档校正需要安装OpenCV: pip install opencv-python")
            return img
        except Exception as e:
            logger.warning(f"文档校正失败: {e}")
            return img


class DocumentPreprocessor:
    """
    文档预处理器 - 整合图像预处理、PDF处理、缩放和旋转功能
    """

    def __init__(self, config: Optional[dict] = None):
        """
        初始化文档预处理器

        Args:
            config: 预处理配置
        """
        self.config = config or {}
        self.image_preprocessor = ImagePreprocessor(config)
        self.pdf_processor = PDFProcessor(
            dpi=config.get("pdf.dpi", 200),
            color_space=config.get("pdf.color_space", "rgb"),
        )
        self.resizer = ImageResizer()
        self.rotator = ImageRotator()

    def process_file(
        self, file_path: str, page_numbers: Optional[List[int]] = None
    ) -> Generator[Image.Image, None, None]:
        """
        处理文件（支持图像和PDF）

        Args:
            file_path: 文件路径
            page_numbers: PDF页码列表（图像忽略此参数）

        Yields:
            处理后的PIL.Image对象
        """
        if PDFProcessor.is_pdf(file_path):
            # 处理PDF
            for page_num, img in self.pdf_processor.pdf_to_images(
                file_path, page_numbers
            ):
                yield self._process_single_image(img)
        else:
            # 处理图像
            img = Image.open(file_path)
            yield self._process_single_image(img)

    def _process_single_image(self, img: Image.Image) -> Image.Image:
        """处理单张图像"""
        # 1. 自动旋转（基于EXIF）
        if self.config.get("preprocessing.auto_rotate", True):
            img = self.rotator.auto_rotate(img)

        # 2. 文档校正
        if self.config.get("preprocessing.deskew", False):
            img = self.rotator.deskew(img)

        # 3. 尺寸调整
        max_size = self.config.get("preprocessing.max_size", 4096)
        if max_size > 0:
            img = self.resizer.resize_to_max(img, max_size, max_size)

        min_size = self.config.get("preprocessing.min_size", 0)
        if min_size > 0:
            img = self.resizer.resize_to_min(img, min_size, min_size)

        scale = self.config.get("preprocessing.scale", 1.0)
        if scale != 1.0:
            img = self.resizer.resize_by_factor(img, scale)

        # 4. 图像增强
        img = self.image_preprocessor.process(img)

        return img

    @staticmethod
    def get_config_schema() -> dict:
        """获取完整的配置项定义"""
        schema = ImagePreprocessor.get_config_schema()
        schema.update(
            {
                "preprocessing.auto_rotate": {
                    "label": "自动旋转/Auto Rotate",
                    "type": "bool",
                    "default": True,
                    "tip": "根据EXIF信息自动校正方向",
                },
                "preprocessing.deskew": {
                    "label": "文档校正/Deskew",
                    "type": "bool",
                    "default": False,
                    "tip": "校正文档倾斜（需要OpenCV）",
                },
                "preprocessing.max_size": {
                    "label": "最大尺寸/Max Size",
                    "type": "int",
                    "default": 4096,
                    "min": 0,
                    "max": 8192,
                    "tip": "0=不限制",
                },
                "preprocessing.min_size": {
                    "label": "最小尺寸/Min Size",
                    "type": "int",
                    "default": 0,
                    "min": 0,
                    "max": 2048,
                    "tip": "0=不限制",
                },
                "preprocessing.scale": {
                    "label": "缩放比例/Scale",
                    "type": "float",
                    "default": 1.0,
                    "min": 0.1,
                    "max": 4.0,
                    "step": 0.1,
                    "tip": "1.0=原始大小",
                },
                "pdf.dpi": {
                    "label": "PDF渲染DPI",
                    "type": "int",
                    "default": 200,
                    "min": 72,
                    "max": 600,
                    "tip": "越高越清晰，但处理越慢",
                },
                "pdf.color_space": {
                    "label": "PDF颜色空间/Color Space",
                    "type": "combobox",
                    "default": "rgb",
                    "options": [
                        {"value": "rgb", "label": "RGB彩色"},
                        {"value": "gray", "label": "灰度"},
                    ],
                },
            }
        )
        return schema
