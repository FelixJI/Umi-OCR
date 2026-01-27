#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 依赖检测模块

检测OCR引擎依赖是否已安装，提供安装建议。

主要功能：
- 检测PaddlePaddle和PaddleOCR是否已安装
- 检测GPU可用性
- 提供依赖安装建议

Author: Umi-OCR Team
Date: 2026-01-27
"""

import sys
import logging
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

# 避免循环导入
if TYPE_CHECKING:
    from .gpu_detector import GPUDetector, GPUVendor, GPUInfo


logger = logging.getLogger(__name__)


# =============================================================================
# 枚举类型
# =============================================================================

class DependencyStatus(Enum):
    """依赖状态"""
    NOT_INSTALLED = "not_installed"    # 未安装
    INSTALLED = "installed"            # 已安装
    INCOMPATIBLE = "incompatible"      # 版本不兼容


class InstallOption(Enum):
    """安装选项"""
    SKIP = "skip"                      # 跳过（使用云OCR）
    CPU = "cpu"                        # CPU版本
    GPU = "gpu"                        # GPU版本


# =============================================================================
# 依赖信息
# =============================================================================

@dataclass
class DependencyInfo:
    """
    依赖信息

    包含依赖的安装状态、版本和推荐安装方案。
    """
    name: str                          # 依赖名称
    status: DependencyStatus            # 安装状态
    version: Optional[str] = None      # 已安装版本
    required_version: Optional[str] = None  # 要求的版本
    install_command: Optional[str] = None  # 安装命令
    description: str = ""              # 描述


@dataclass
class OCRDependencyInfo:
    """
    OCR引擎依赖信息

    包含所有OCR引擎依赖的完整信息。
    """
    paddlepaddle: DependencyInfo = field(default_factory=lambda: DependencyInfo(
        name="PaddlePaddle",
        status=DependencyStatus.NOT_INSTALLED,
        description="深度学习框架"
    ))
    paddleocr: DependencyInfo = field(default_factory=lambda: DependencyInfo(
        name="PaddleOCR",
        status=DependencyStatus.NOT_INSTALLED,
        description="OCR识别引擎"
    ))
    gpu_available: bool = False        # GPU是否可用
    gpu_count: int = 0               # GPU数量
    gpu_info_list: List = field(default_factory=list)  # GPU信息列表
    recommendation: Optional[InstallOption] = None  # 推荐选项


# =============================================================================
# 依赖检测器
# =============================================================================

class DependencyChecker:
    """
    依赖检测器

    检测OCR引擎依赖的安装状态和可用性。
    """

    # 要求的PaddlePaddle版本
    REQUIRED_PADDLE_VERSION = ">=3.2.0"
    # 要求的PaddleOCR版本
    REQUIRED_PADDLEOCR_VERSION = ">=3.3.0"

    def __init__(self):
        """初始化依赖检测器"""
        self._paddlepaddle_info: Optional[DependencyInfo] = DependencyInfo(
            name="PaddlePaddle",
            status=DependencyStatus.NOT_INSTALLED,
            description="深度学习框架"
        )
        self._paddleocr_info: Optional[DependencyInfo] = DependencyInfo(
            name="PaddleOCR",
            status=DependencyStatus.NOT_INSTALLED,
            description="OCR识别引擎"
        )
        self._gpu_available = False
        self._gpu_count = 0
        self._gpu_info_list: List = []
        self.recommendation: Optional[InstallOption] = None

    def check_all(self) -> OCRDependencyInfo:
        """
        检查所有OCR依赖

        Returns:
            OCRDependencyInfo: OCR依赖信息
        """
        # 检查PaddlePaddle
        self._check_paddlepaddle()

        # 检查PaddleOCR
        self._check_paddleocr()

        # 检查GPU（使用GPU检测器）
        self._check_gpu()

        # 生成推荐
        self._generate_recommendation()

        # 返回完整信息
        return OCRDependencyInfo(
            paddlepaddle=self._paddlepaddle_info,
            paddleocr=self._paddleocr_info,
            gpu_available=self._gpu_available,
            gpu_count=self._gpu_count,
            gpu_info_list=self._gpu_info_list,
            recommendation=self._get_recommendation()
        )

    def _check_paddlepaddle(self) -> None:
        """检查PaddlePaddle安装状态"""
        try:
            import paddle
            version = paddle.__version__

            # 检查版本
            if self._is_version_compatible(version, self.REQUIRED_PADDLE_VERSION):
                status = DependencyStatus.INSTALLED
                install_command = None
            else:
                status = DependencyStatus.INCOMPATIBLE
                install_command = f"pip install paddlepaddle=={self.REQUIRED_PADDLE_VERSION}"

            self._paddlepaddle_info = DependencyInfo(
                name="PaddlePaddle",
                status=status,
                version=version,
                required_version=self.REQUIRED_PADDLE_VERSION,
                install_command=install_command,
                description="深度学习框架，用于OCR推理"
            )

            logger.info(f"PaddlePaddle已安装: {version}")

        except ImportError:
            self._paddlepaddle_info = DependencyInfo(
                name="PaddlePaddle",
                status=DependencyStatus.NOT_INSTALLED,
                required_version=self.REQUIRED_PADDLE_VERSION,
                install_command=f"pip install paddlepaddle{self.REQUIRED_PADDLE_VERSION}",
                description="深度学习框架，用于OCR推理"
            )

            logger.warning("PaddlePaddle未安装")

    def _check_paddleocr(self) -> None:
        """检查PaddleOCR安装状态"""
        try:
            import paddleocr
            version = paddleocr.__version__

            # 检查版本
            if self._is_version_compatible(version, self.REQUIRED_PADDLEOCR_VERSION):
                status = DependencyStatus.INSTALLED
                install_command = None
            else:
                status = DependencyStatus.INCOMPATIBLE
                install_command = f"pip install paddleocr{self.REQUIRED_PADDLEOCR_VERSION}"

            self._paddleocr_info = DependencyInfo(
                name="PaddleOCR",
                status=status,
                version=version,
                required_version=self.REQUIRED_PADDLEOCR_VERSION,
                install_command=install_command,
                description="OCR识别引擎，支持多语言识别"
            )

            logger.info(f"PaddleOCR已安装: {version}")

        except ImportError:
            self._paddleocr_info = DependencyInfo(
                name="PaddleOCR",
                status=DependencyStatus.NOT_INSTALLED,
                required_version=self.REQUIRED_PADDLEOCR_VERSION,
                install_command=f"pip install paddleocr{self.REQUIRED_PADDLEOCR_VERSION}",
                description="OCR识别引擎，支持多语言识别"
            )

            logger.warning("PaddleOCR未安装")

    def _check_gpu(self) -> None:
        """检查GPU可用性"""
        # 方法1：使用GPU检测器（不依赖PaddlePaddle）
        try:
            gpu_detector = get_gpu_detector()
            self._gpu_info_list = gpu_detector.detect_all()

            if self._gpu_info_list:
                # 有GPU，检查是否有NVIDIA GPU
                nvidia_gpu = gpu_detector.detect_nvidia_gpu()
                if nvidia_gpu:
                    self._gpu_available = nvidia_gpu.cuda_support
                    self._gpu_count = len([g for g in self._gpu_info_list if g.vendor == GPUVendor.NVIDIA])
                    logger.info(f"检测到GPU: {self._gpu_count}个NVIDIA设备")

                    # 获取显存最大的GPU信息
                    best_gpu = gpu_detector.get_best_gpu()
                    if best_gpu:
                        logger.info(f"最佳GPU: {best_gpu.name}, {best_gpu.memory_mb}MB")
            else:
                logger.info("未检测到GPU")
                self._gpu_available = False
                self._gpu_info_list = []

        except Exception as e:
            logger.warning(f"GPU检测失败: {e}", exc_info=True)

        # 方法2：如果PaddlePaddle已安装，使用其检测GPU
        try:
            import paddle

            # 检查是否编译了CUDA支持
            if hasattr(paddle, 'device'):
                paddle_gpu_available = paddle.device.is_compiled_with_cuda()

                if paddle_gpu_available:
                    # 获取GPU数量
                    try:
                        paddle_gpu_count = paddle.device.cuda.device_count()
                        logger.info(f"Paddle检测到GPU: {paddle_gpu_count}个设备")
                    except Exception:
                        paddle_gpu_count = 0

                    # 更新GPU信息（如果GPU检测器没有检测到）
                    if not self._gpu_available and paddle_gpu_available:
                        self._gpu_available = True
                        self._gpu_count = paddle_gpu_count

        except ImportError:
            logger.info("PaddlePaddle未安装，无法通过Paddle检测GPU")
        except Exception as e:
            logger.warning(f"Paddle GPU检测失败: {e}", exc_info=True)

    def _is_version_compatible(self, version: str, required: str) -> bool:
        """
        检查版本兼容性

        Args:
            version: 已安装的版本
            required: 要求的版本（如 ">=3.2.0"）

        Returns:
            bool: 是否兼容
        """
        try:
            from packaging import version as pkg_version

            # 解析版本要求
            if required.startswith(">="):
                min_ver = required[2:]
                return pkg_version.parse(version) >= pkg_version.parse(min_ver)
            elif required.startswith("=="):
                req_ver = required[2:]
                return version == req_ver
            else:
                # 默认要求完全匹配
                return version == required

        except Exception as e:
            logger.warning(f"版本比较失败: {e}")
            return False

    def _generate_recommendation(self) -> None:
        """生成安装推荐"""
        # 如果都已安装，不需要推荐
        if (self._paddlepaddle_info.status == DependencyStatus.INSTALLED and
            self._paddleocr_info.status == DependencyStatus.INSTALLED):
            self.recommendation = None
            return

        # 根据GPU情况推荐
        if self._gpu_available and self._gpu_count > 0:
            # 有GPU，推荐GPU版本（但需要用户确认）
            self.recommendation = InstallOption.GPU
        else:
            # 无GPU，推荐CPU版本
            self.recommendation = InstallOption.CPU

    def _get_recommendation(self) -> Optional[InstallOption]:
        """获取推荐选项"""
        # 如果都已安装，不需要推荐
        if (self._paddlepaddle_info.status == DependencyStatus.INSTALLED and
            self._paddleocr_info.status == DependencyStatus.INSTALLED):
            return None

        # 根据GPU情况推荐
        if self._gpu_available and self._gpu_count > 0:
            return InstallOption.GPU
        else:
            return InstallOption.CPU

    def is_ocr_available(self) -> bool:
        """
        检查OCR引擎是否可用

        Returns:
            bool: OCR引擎是否可用
        """
        return (self._paddlepaddle_info and
                self._paddlepaddle_info.status == DependencyStatus.INSTALLED and
                self._paddleocr_info and
                self._paddleocr_info.status == DependencyStatus.INSTALLED)

    def get_missing_dependencies(self) -> List[str]:
        """
        获取缺失的依赖

        Returns:
            List[str]: 缺失的依赖名称列表
        """
        missing = []

        if self._paddlepaddle_info and self._paddlepaddle_info.status != DependencyStatus.INSTALLED:
            missing.append(self._paddlepaddle_info.name)

        if self._paddleocr_info and self._paddleocr_info.status != DependencyStatus.INSTALLED:
            missing.append(self._paddleocr_info.name)

        return missing


# =============================================================================
# 全局依赖检测器
# =============================================================================

_global_checker: Optional[DependencyChecker] = None


def get_dependency_checker() -> DependencyChecker:
    """
    获取全局依赖检测器

    Returns:
        DependencyChecker: 依赖检测器实例
    """
    global _global_checker
    if _global_checker is None:
        _global_checker = DependencyChecker()
    return _global_checker


def check_ocr_dependencies() -> OCRDependencyInfo:
    """
    检查OCR依赖（便捷函数）

    Returns:
        OCRDependencyInfo: OCR依赖信息
    """
    checker = get_dependency_checker()
    return checker.check_all()


def get_gpu_detector() -> 'GPUDetector':
    """
    获取GPU检测器（延迟导入）

    Returns:
        GPUDetector: GPU检测器实例
    """
    from .gpu_detector import GPUDetector
    return GPUDetector()
