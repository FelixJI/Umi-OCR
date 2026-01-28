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
            # 1. 中值滤波（降噪）
            img = self._apply_denoise(img)

            # 2. 锐化增强
            img = self._apply_sharpen(img)

            # 3. 对比度调整
            img = self._apply_contrast(img)

            # 4. 亮度调整
            img = self._apply_brightness(img)

            # 5. 灰度转换和二值化
            img = self._apply_grayscale_and_threshold(img)

        except Exception as e:
            logger.error(f"图像预处理失败: {e}", exc_info=True)
            # 预处理失败时返回原图
            return self._to_pil_image(image)

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
        }


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
