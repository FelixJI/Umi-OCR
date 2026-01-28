#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR GPU检测模块

检测用户的显卡硬件和CUDA支持情况。

主要功能：
- 检测显卡型号和显存大小
- 检测CUDA支持情况
- 检测计算能力（Compute Capability）
- 评估GPU是否适合OCR
- 提供安装建议

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
import platform
import subprocess
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# GPU厂商枚举
# =============================================================================


class GPUVendor(Enum):
    """GPU厂商"""

    NVIDIA = "nvidia"  # NVIDIA
    AMD = "amd"  # AMD
    INTEL = "intel"  # Intel
    UNKNOWN = "unknown"  # 未知


# =============================================================================
# GPU信息数据类
# =============================================================================


@dataclass
class GPUInfo:
    """
    GPU信息

    包含显卡的硬件信息和CUDA支持情况。
    """

    vendor: GPUVendor  # 厂商
    name: str  # 显卡型号
    memory_mb: int  # 显存大小（MB）
    compute_capability: Optional[Tuple[int, int]] = None  # 计算能力 (major, minor)
    cuda_support: bool = False  # 是否支持CUDA
    cuda_version: Optional[str] = None  # CUDA版本
    driver_version: Optional[str] = None  # 驱动版本
    is_available: bool = False  # 是否可用
    recommendation: str = ""  # 安装建议

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "vendor": self.vendor.value,
            "name": self.name,
            "memory_mb": self.memory_mb,
            "memory_gb": round(self.memory_mb / 1024, 1),
            "compute_capability": (
                f"{self.compute_capability[0]}.{self.compute_capability[1]}"
                if self.compute_capability
                else None
            ),
            "cuda_support": self.cuda_support,
            "cuda_version": self.cuda_version,
            "driver_version": self.driver_version,
            "is_available": self.is_available,
            "recommendation": self.recommendation,
        }


# =============================================================================
# GPU检测器
# =============================================================================


class GPUDetector:
    """
    GPU检测器

    检测用户的GPU硬件和CUDA支持情况。
    """

    def __init__(self):
        """初始化GPU检测器"""
        self._gpu_info_list: List[GPUInfo] = []
        self._platform = platform.system()

    def detect_all(self) -> List[GPUInfo]:
        """
        检测所有GPU

        Returns:
            List[GPUInfo]: GPU信息列表
        """
        self._gpu_info_list = []

        # 根据平台选择检测方法
        if self._platform == "Windows":
            self._detect_windows()
        elif self._platform == "Linux":
            self._detect_linux()
        elif self._platform == "Darwin":
            self._detect_macos()
        else:
            logger.warning(f"不支持的系统: {self._platform}")

        return self._gpu_info_list

    def detect_nvidia_gpu(self) -> Optional[GPUInfo]:
        """
        检测NVIDIA GPU

        Returns:
            Optional[GPUInfo]: NVIDIA GPU信息（无则返回None）
        """
        # 查找NVIDIA GPU
        for gpu_info in self._gpu_info_list:
            if gpu_info.vendor == GPUVendor.NVIDIA:
                return gpu_info
        return None

    def get_best_gpu(self) -> Optional[GPUInfo]:
        """
        获取最适合OCR的GPU

        Returns:
            Optional[GPUInfo]: 最佳GPU信息（无则返回None）
        """
        # 优先级：NVIDIA > AMD > Intel
        for vendor in [GPUVendor.NVIDIA, GPUVendor.AMD, GPUVendor.INTEL]:
            for gpu_info in self._gpu_info_list:
                if gpu_info.vendor == vendor and gpu_info.is_available:
                    return gpu_info
        return None

    def _detect_windows(self) -> None:
        """检测Windows平台的GPU"""
        try:
            # 方法1: 使用wmic命令检测GPU
            self._detect_windows_wmic()

            # 方法2: 如果检测到NVIDIA GPU，尝试获取CUDA信息
            nvidia_gpu = self.detect_nvidia_gpu()
            if nvidia_gpu:
                self._detect_nvidia_cuda()

        except Exception as e:
            logger.error(f"Windows GPU检测失败: {e}", exc_info=True)

    def _detect_windows_wmic(self) -> None:
        """使用wmic命令检测Windows GPU"""
        try:
            # 执行wmic命令
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name,AdapterRAM"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10,
            )

            if result.returncode != 0:
                logger.warning("wmic命令执行失败")
                return

            # 解析输出
            lines = result.stdout.strip().split("\n")
            for line in lines[1:]:  # 跳过表头
                parts = [p.strip() for p in line.split("  ") if p.strip()]
                if len(parts) >= 2:
                    name = parts[0]
                    try:
                        # 内存值可能是"xxxx bytes"
                        memory_str = parts[1].replace(" bytes", "").replace(",", "")
                        memory_mb = int(int(memory_str) / (1024 * 1024))
                    except (ValueError, IndexError):
                        memory_mb = 0

                    # 识别厂商
                    vendor = self._identify_vendor(name)

                    # 创建GPU信息
                    gpu_info = GPUInfo(
                        vendor=vendor, name=name, memory_mb=memory_mb, is_available=True
                    )

                    # 生成建议
                    gpu_info.recommendation = self._generate_recommendation(gpu_info)

                    self._gpu_info_list.append(gpu_info)

        except subprocess.TimeoutExpired:
            logger.warning("wmic命令超时")
        except Exception as e:
            logger.warning(f"wmic GPU检测失败: {e}")

    def _detect_nvidia_cuda(self) -> None:
        """检测NVIDIA CUDA支持"""
        try:
            # 方法1: 使用nvidia-smi命令
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,cuda_version,memory.total",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10,
            )

            if result.returncode == 0:
                # 解析nvidia-smi输出
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 4:
                        name = parts[0]
                        driver_version = parts[1]
                        cuda_version = parts[2]
                        memory_str = parts[3]

                        # 解析显存（如 "4096 MiB"）
                        try:
                            memory_mb = int(memory_str.split()[0])
                        except (ValueError, IndexError):
                            memory_mb = 0

                        # 查找对应的GPU并更新信息
                        for gpu_info in self._gpu_info_list:
                            if gpu_info.vendor == GPUVendor.NVIDIA:
                                gpu_info.cuda_support = True
                                gpu_info.cuda_version = cuda_version
                                gpu_info.driver_version = driver_version
                                if memory_mb > gpu_info.memory_mb:
                                    gpu_info.memory_mb = memory_mb

                                # 更新建议
                                gpu_info.recommendation = self._generate_recommendation(
                                    gpu_info
                                )

                        logger.info(
                            f"检测到NVIDIA GPU: {name}, CUDA {cuda_version}, {memory_mb}MB"
                        )
                        return

        except subprocess.TimeoutExpired:
            logger.warning("nvidia-smi命令超时")
        except FileNotFoundError:
            logger.info("未安装nvidia-smi，无法检测CUDA信息")
        except Exception as e:
            logger.warning(f"nvidia-smi CUDA检测失败: {e}")

    def _detect_linux(self) -> None:
        """检测Linux平台的GPU"""
        try:
            # 方法1: 使用lspci命令
            result = subprocess.run(
                ["lspci", "-nn", "-d", "::0300"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10,
            )

            if result.returncode == 0:
                # 解析lspci输出
                self._parse_lspci_output(result.stdout)

            # 方法2: 如果检测到NVIDIA GPU，尝试获取CUDA信息
            nvidia_gpu = self.detect_nvidia_gpu()
            if nvidia_gpu:
                self._detect_nvidia_cuda()

        except subprocess.TimeoutExpired:
            logger.warning("lspci命令超时")
        except FileNotFoundError:
            logger.info("未安装lspci，无法检测GPU")
        except Exception as e:
            logger.warning(f"Linux GPU检测失败: {e}", exc_info=True)

    def _parse_lspci_output(self, output: str) -> None:
        """解析lspci输出"""
        try:
            import re

            # 正则表达式匹配GPU信息
            # 示例: "VGA compatible controller: NVIDIA Corporation GP107M"
            # "[GeForce GTX 1050 Mobile]"
            pattern = r"(\w+(?:\s+\w+)*)\s*:\s*([\w\s]+)\s+\[([^\]]+)\]"

            for line in output.split("\n"):
                match = re.search(pattern, line)
                if match:
                    vendor_name = match.group(1)
                    name = match.group(2)

                    # 识别厂商
                    vendor = self._identify_vendor(vendor_name)

                    # 创建GPU信息
                    gpu_info = GPUInfo(
                        vendor=vendor,
                        name=name,
                        memory_mb=0,  # lspci无法直接获取显存
                        is_available=True,
                    )

                    # 尝试从dmesg获取显存信息
                    memory_mb = self._get_gpu_memory_from_dmesg(vendor, name)
                    if memory_mb > 0:
                        gpu_info.memory_mb = memory_mb

                    # 生成建议
                    gpu_info.recommendation = self._generate_recommendation(gpu_info)

                    self._gpu_info_list.append(gpu_info)

        except Exception as e:
            logger.warning(f"解析lspci输出失败: {e}")

    def _get_gpu_memory_from_dmesg(self, vendor: GPUVendor, name: str) -> int:
        """从dmesg获取GPU显存信息"""
        try:
            # 根据厂商和名称搜索dmesg
            keywords = []
            if vendor == GPUVendor.NVIDIA:
                keywords.append("NVRM")
                keywords.append("nvidia")
            elif vendor == GPUVendor.AMD:
                keywords.append("amdgpu")
                keywords.append("radeon")
            elif vendor == GPUVendor.INTEL:
                keywords.append("i915")

            # 搜索显存信息
            for keyword in keywords:
                result = subprocess.run(
                    ["dmesg", "|", "grep", "-i", keyword, "|", "grep", "-i", "memory"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    # 解析显存大小
                    import re

                    memory_match = re.search(
                        r"(\d+)\s*[MG]B", result.stdout, re.IGNORECASE
                    )
                    if memory_match:
                        memory_mb = int(memory_match.group(1))
                        if memory_mb < 1000:  # 可能是MB
                            return memory_mb
                        else:  # 可能是GB
                            return memory_mb * 1024

        except Exception as e:
            logger.warning(f"从dmesg获取显存失败: {e}")

        return 0

    def _detect_macos(self) -> None:
        """检测macOS平台的GPU"""
        try:
            # 使用system_profiler命令
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10,
            )

            if result.returncode == 0:
                import json

                data = json.loads(result.stdout)

                # 解析GPU信息
                if "SPDisplaysDataType" in data:
                    for display in data["SPDisplaysDataType"]:
                        name = display.get("sppci_model", "Unknown GPU")
                        vendor_str = display.get("sppci_vendor", "Unknown")

                        # 识别厂商
                        vendor = self._identify_vendor(vendor_str)

                        # 显存信息
                        vram_str = display.get("sppci_vram", "0 MB")
                        try:
                            memory_mb = int(vram_str.split()[0])
                        except (ValueError, IndexError):
                            memory_mb = 0

                        # 创建GPU信息
                        gpu_info = GPUInfo(
                            vendor=vendor,
                            name=name,
                            memory_mb=memory_mb,
                            is_available=True,
                        )

                        # 生成建议
                        gpu_info.recommendation = self._generate_recommendation(
                            gpu_info
                        )

                        self._gpu_info_list.append(gpu_info)

        except subprocess.TimeoutExpired:
            logger.warning("system_profiler命令超时")
        except FileNotFoundError:
            logger.info("未找到system_profiler，无法检测GPU")
        except Exception as e:
            logger.warning(f"macOS GPU检测失败: {e}", exc_info=True)

    def _identify_vendor(self, name: str) -> GPUVendor:
        """
        识别GPU厂商

        Args:
            name: GPU名称

        Returns:
            GPUVendor: 厂商枚举
        """
        name_lower = name.lower()

        if "nvidia" in name_lower:
            return GPUVendor.NVIDIA
        elif "amd" in name_lower or "radeon" in name_lower or "ati" in name_lower:
            return GPUVendor.AMD
        elif "intel" in name_lower:
            return GPUVendor.INTEL
        else:
            return GPUVendor.UNKNOWN

    def _generate_recommendation(self, gpu_info: GPUInfo) -> str:
        """
        生成安装建议

        Args:
            gpu_info: GPU信息

        Returns:
            str: 安装建议
        """
        # NVIDIA GPU
        if gpu_info.vendor == GPUVendor.NVIDIA:
            if gpu_info.memory_mb >= 2048:  # 至少2GB显存
                if gpu_info.cuda_support:
                    return "推荐安装GPU版本（支持CUDA加速）"
                else:
                    return "建议安装CUDA驱动后再使用GPU版本"
            else:
                return "建议使用CPU版本（显存不足）"

        # AMD GPU
        elif gpu_info.vendor == GPUVendor.AMD:
            if gpu_info.memory_mb >= 4096:  # 至少4GB显存
                return "AMD GPU暂不支持（NVIDIA GPU推荐）"
            else:
                return "建议使用CPU版本（显存不足）"

        # Intel GPU
        elif gpu_info.vendor == GPUVendor.INTEL:
            return "Intel GPU暂不支持（NVIDIA GPU推荐）"

        # 未知厂商
        else:
            return "建议使用CPU版本（不支持的GPU）"

    def get_summary(self) -> Dict:
        """
        获取GPU检测摘要

        Returns:
            Dict: 摘要信息
        """
        nvidia_gpu = self.detect_nvidia_gpu()
        best_gpu = self.get_best_gpu()

        return {
            "gpu_count": len(self._gpu_info_list),
            "nvidia_gpu_available": nvidia_gpu is not None,
            "best_gpu": best_gpu.to_dict() if best_gpu else None,
            "recommend_gpu": best_gpu.recommendation if best_gpu else "建议使用CPU版本",
        }


# =============================================================================
# 全局GPU检测器
# =============================================================================

_global_detector: Optional[GPUDetector] = None


def get_gpu_detector() -> GPUDetector:
    """
    获取全局GPU检测器

    Returns:
        GPUDetector: GPU检测器实例
    """
    global _global_detector
    if _global_detector is None:
        _global_detector = GPUDetector()
    return _global_detector


def detect_gpu() -> List[GPUInfo]:
    """
    检测GPU（便捷函数）

    Returns:
        List[GPUInfo]: GPU信息列表
    """
    detector = get_gpu_detector()
    return detector.detect_all()
