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
            # 方法1: 优先使用nvidia-smi检测NVIDIA GPU（更准确）
            nvidia_detected = self._detect_nvidia_cuda_primary()

            # 方法2: 使用wmic命令检测所有GPU（包括非NVIDIA）
            self._detect_windows_wmic()

            # 方法3: 如果wmic没有检测到NVIDIA GPU但nvidia-smi成功了，补充nvidia-smi的信息
            if not any(g.vendor == GPUVendor.NVIDIA for g in self._gpu_info_list):
                if nvidia_detected:
                    logger.info("wmic未检测到NVIDIA GPU，但nvidia-smi检测到了，使用nvidia-smi数据")

        except Exception as e:
            logger.error(f"Windows GPU检测失败: {e}", exc_info=True)

    def _detect_nvidia_cuda_primary(self) -> bool:
        """
        使用nvidia-smi作为主要检测方法（优先于wmic）

        Returns:
            bool: 是否检测到NVIDIA GPU
        """
        try:
            # 修复：cuda_version不是有效的查询字段，已移除
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,memory.total",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10,
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                nvidia_count = 0

                for line in lines:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 3:
                        name = parts[0]
                        driver_version = parts[1]
                        memory_str = parts[2]

                        # 解析显存
                        try:
                            memory_mb = int(memory_str.split()[0])
                        except (ValueError, IndexError):
                            memory_mb = 0

                        # 创建GPU信息
                        gpu_info = GPUInfo(
                            vendor=GPUVendor.NVIDIA,
                            name=name,
                            memory_mb=memory_mb,
                            cuda_support=True,
                            cuda_version=None,  # 无法直接从nvidia-smi获取
                            driver_version=driver_version,
                            is_available=True,
                        )
                        gpu_info.recommendation = self._generate_recommendation(gpu_info)

                        self._gpu_info_list.append(gpu_info)
                        nvidia_count += 1

                        logger.info(
                            f"nvidia-smi检测到: {name}, 驱动: {driver_version}, 显存: {memory_mb}MB"
                        )

                return nvidia_count > 0

        except subprocess.TimeoutExpired:
            logger.warning("nvidia-smi命令超时")
        except FileNotFoundError:
            logger.info("未找到nvidia-smi命令")
        except Exception as e:
            logger.warning(f"nvidia-smi检测失败: {e}")

        return False

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

            # 记录原始输出用于调试
            logger.debug(f"wmic输出:\n{result.stdout}")

            # 解析输出
            lines = result.stdout.strip().split("\n")

            # 识别列顺序（第一行是表头）
            header_line = lines[0] if lines else ""
            headers = [h.strip() for h in header_line.split("  ") if h.strip()]

            # 确定列索引
            name_idx = headers.index("Name") if "Name" in headers else -1
            memory_idx = headers.index("AdapterRAM") if "AdapterRAM" in headers else -1

            # 如果无法从表头识别，使用默认顺序
            if name_idx == -1 or memory_idx == -1:
                name_idx, memory_idx = 1, 0  # 默认：name在第2列，memory在第1列

            logger.debug(f"检测到列顺序: name_idx={name_idx}, memory_idx={memory_idx}")

            # 解析数据行
            for line in lines[1:]:  # 跳过表头
                parts = [p.strip() for p in line.split("  ") if p.strip()]

                if len(parts) >= 2:
                    # 修复：根据实际列索引获取数据
                    if name_idx < len(parts) and memory_idx < len(parts):
                        name = parts[name_idx]
                        memory_str = parts[memory_idx]

                        logger.debug(f"解析GPU: name='{name}', memory='{memory_str}'")

                        try:
                            # 内存值是字节数，需要转换为MB
                            memory_bytes = int(memory_str)
                            memory_mb = memory_bytes // (1024 * 1024)
                        except (ValueError, IndexError):
                            logger.warning(f"无法解析显存值: {memory_str}")
                            memory_mb = 0

                        # 识别厂商
                        vendor = self._identify_vendor(name)

                        # 修复：检查是否已经存在相同名称的GPU（避免重复）
                        gpu_exists = any(
                            g.name.lower() == name.lower() for g in self._gpu_info_list
                        )

                        if gpu_exists:
                            logger.debug(f"GPU '{name}' 已存在，跳过wmic数据")
                            continue

                        logger.info(
                            f"检测到GPU: {name}, 厂商: {vendor.value}, 显存: {memory_mb}MB"
                        )

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
            logger.warning(f"wmic GPU检测失败: {e}", exc_info=True)

    def _detect_nvidia_cuda(self) -> None:
        """检测NVIDIA CUDA支持（已废弃，保留用于兼容）"""
        # 这个方法已被_detect_nvidia_cuda_primary替代
        # 保留空实现以避免破坏现有调用
        pass

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
                    # 检测到CUDA，明确推荐
                    return "推荐安装GPU版本（已检测到CUDA支持）"
                else:
                    # 有NVIDIA GPU但未检测到CUDA
                    # 不应该直接判定为不可用，而是建议用户尝试
                    return "推荐安装GPU版本（检测到NVIDIA GPU，支持CUDA加速）"
            else:
                # 显存不足2GB
                return "建议使用CPU版本（显存不足，需要至少2GB显存）"

        # AMD GPU
        elif gpu_info.vendor == GPUVendor.AMD:
            if gpu_info.memory_mb >= 4096:  # 至少4GB显存
                return "AMD GPU暂不支持，建议使用CPU版本或NVIDIA GPU"
            else:
                return "建议使用CPU版本（显存不足）"

        # Intel GPU
        elif gpu_info.vendor == GPUVendor.INTEL:
            return "Intel集成显卡暂不支持，建议使用CPU版本"

        # 未知厂商
        else:
            return "建议使用CPU版本（未识别的GPU厂商）"

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
