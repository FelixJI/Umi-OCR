#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 依赖安装服务

后台安装OCR引擎依赖，支持多镜像源切换和进度通知。

主要功能：
- 支持CPU/GPU版本安装
- 智能镜像源切换（国内镜像优先）
- 安装进度实时通知（包含下载进度）
- 后台安装（QThread）
- 安装失败自动重试
- 用户可选择镜像源

Author: Umi-OCR Team
Date: 2026-01-27
"""

import sys
import subprocess
import threading
import logging
import re
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass, field
from enum import Enum

from PySide6.QtCore import QObject, Signal, QThread

from .check_dependencies import InstallOption

logger = logging.getLogger(__name__)


# =============================================================================
# 镜像源配置
# =============================================================================
# 镜像源配置
# =============================================================================

# 重要说明：DEFAULT_MIRRORS 是 pip 包安装镜像源，用于安装 paddlepaddle/ocr 包
# PaddleOCR 模型下载源由环境变量 PADDLE_PDX_MODEL_SOURCE 控制，只支持：
#   - "HuggingFace" (默认值，从 3.2.0+ 开始)
#   - "BOS" (百度对象存储，国内推荐)
# 更多信息请参考：paddle_doc/docs/update/update.en.md


@dataclass
class MirrorSource:
    """
    镜像源配置

    包含镜像源的URL和优先级。

    注意：这些是 pip 包安装镜像源，用于安装 paddlepaddle/ocr 包，
    不是 PaddleOCR 模型下载源。
    """

    name: str
    url: str
    priority: int
    is_official: bool = False

    def get_pip_command(self) -> List[str]:
        """
        获取 pip 安装命令

        Returns:
            List[str]: pip 命令列表
        """
        cmd = [sys.executable, "-m", "pip", "install"]

        if self.is_official:
            pass
        else:
            cmd.extend(["-i", self.url])

        if not self.is_official:
            cmd.extend(
                [
                    "--trusted-host",
                    self.url.replace("https://", "").replace("http://", ""),
                ]
            )

        return cmd


# 默认镜像源列表（用于 PaddleOCR 等普通包）
DEFAULT_MIRRORS = [
    MirrorSource(
        name="清华镜像",
        url="https://pypi.tuna.tsinghua.edu.cn/simple",
        priority=1,
        is_official=False,
    ),
    MirrorSource(
        name="阿里云镜像",
        url="https://mirrors.aliyun.com/pypi/simple/",
        priority=2,
        is_official=False,
    ),
    MirrorSource(
        name="豆瓣镜像",
        url="https://pypi.douban.com/simple",
        priority=3,
        is_official=False,
    ),
    MirrorSource(
        name="中科大镜像",
        url="https://pypi.mirrors.ustc.edu.cn/simple",
        priority=4,
        is_official=False,
    ),
    MirrorSource(
        name="pip官方源",
        url="https://pypi.org/simple",
        priority=100,
        is_official=True,
    ),
]

# PaddlePaddle官方源（必须使用官方源安装PaddlePaddle）
PADDLE_OFFICIAL_SOURCES = {
    "cpu": "https://www.paddlepaddle.org.cn/packages/stable/cpu/",
    "gpu_cu118": "https://www.paddlepaddle.org.cn/packages/stable/cu118/",
    "gpu_cu126": "https://www.paddlepaddle.org.cn/packages/stable/cu126/",
}

PADDLEPADDLE_VERSION = "3.3.0"
PADDLEOCR_VERSION = "3.3.0"


# =============================================================================
# 安装状态
# =============================================================================


class InstallStatus(Enum):
    """安装状态"""

    PREPARING = "preparing"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class InstallProgress:
    """
    安装进度信息

    用于通知UI安装进度。
    """

    status: InstallStatus
    message: str
    percentage: float = 0.0
    current_step: int = 1
    total_steps: int = 1
    mirror_name: str = ""
    error_message: Optional[str] = None
    download_speed: Optional[str] = None
    downloaded_size: Optional[str] = None
    total_size: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 0


# =============================================================================
# 安装配置
# =============================================================================


@dataclass
class InstallConfig:
    """
    安装配置

    包含安装选项和参数。
    """

    option: InstallOption
    mirrors: List[MirrorSource] = field(default_factory=lambda: DEFAULT_MIRRORS.copy())
    max_retries: int = 3
    timeout: int = 300
    user_agent: Optional[str] = None
    proxy: Optional[str] = None
    selected_mirror: Optional[MirrorSource] = None  # 用户选择的镜像源


# =============================================================================
# 安装工作线程
# =============================================================================


class InstallWorker(QThread):
    """
    安装工作线程

    在后台执行依赖安装，避免阻塞UI。
    """

    progress = Signal(object)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, config: InstallConfig):
        super().__init__()

        self.config = config
        self._is_cancelled = False
        self._lock = threading.Lock()

    def run(self):
        """
        执行安装任务

        在后台线程中执行，不阻塞UI。
        """
        try:
            self._emit_progress(InstallStatus.PREPARING, "准备安装...")
            self._check_cancelled()

            packages = self._get_packages_to_install()

            # 确定要使用的镜像源列表
            if self.config.selected_mirror:
                # 用户选择了特定镜像源，只使用该源
                mirrors_to_try = [self.config.selected_mirror]
            else:
                # 使用默认镜像源列表
                mirrors_to_try = self.config.mirrors

            total_steps = (
                len(packages) * len(mirrors_to_try) * (self.config.max_retries + 1)
            )

            # 遍历镜像源
            for mirror_idx, mirror in enumerate(mirrors_to_try):
                self._check_cancelled()

                # 遍历重试次数
                for retry in range(self.config.max_retries + 1):
                    self._check_cancelled()

                    if retry > 0:
                        self._emit_progress(
                            InstallStatus.RETRYING,
                            f"重试第 {retry} 次 ({mirror.name})...",
                            retry_count=retry,
                            max_retries=self.config.max_retries,
                        )

                    current_step = (
                        mirror_idx * len(packages) * (self.config.max_retries + 1)
                        + retry * len(packages)
                        + 1
                    )
                    progress = InstallProgress(
                        status=InstallStatus.DOWNLOADING,
                        message=f"正在使用 {mirror.name} 下载...",
                        percentage=(current_step / total_steps) * 100,
                        current_step=current_step,
                        total_steps=total_steps,
                        mirror_name=mirror.name,
                        retry_count=retry,
                        max_retries=self.config.max_retries,
                    )
                    self.progress.emit(progress)

                    success = self._install_from_mirror(
                        mirror, packages, retry, current_step, total_steps
                    )

                    if success:
                        self.finished.emit(True, "安装成功！")
                        return
                    elif retry < self.config.max_retries:
                        logger.warning(
                            f"镜像源 {mirror.name} 第 {retry + 1} 次尝试失败，准备重试"
                        )
                        continue
                    elif mirror_idx < len(mirrors_to_try) - 1:
                        logger.warning(f"镜像源 {mirror.name} 失败，尝试下一个镜像")
                        break
                    else:
                        error_msg = "所有镜像源都无法安装，请检查网络连接或手动安装"
                        self.error.emit(error_msg)
                        self.finished.emit(False, error_msg)
                        return

        except Exception as e:
            error_msg = f"安装异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            self.finished.emit(False, error_msg)

    def cancel(self):
        """取消安装"""
        with self._lock:
            self._is_cancelled = True

    def _check_cancelled(self):
        """检查是否已取消"""
        with self._lock:
            if self._is_cancelled:
                raise InterruptedError("安装已被用户取消")

    def _get_packages_to_install(self) -> List[Dict[str, any]]:
        """
        获取需要安装的包

        Returns:
            List[Dict]: 包列表（包含名称、版本、源地址等信息）
        """
        packages = []

        if self.config.option == InstallOption.GPU:
            packages.append(
                {
                    "name": "paddlepaddle-gpu",
                    "version": f"=={PADDLEPADDLE_VERSION}",
                    "source": PADDLE_OFFICIAL_SOURCES["gpu_cu118"],
                    "use_official_source": True,
                }
            )
        else:
            packages.append(
                {
                    "name": "paddlepaddle",
                    "version": f"=={PADDLEPADDLE_VERSION}",
                    "source": PADDLE_OFFICIAL_SOURCES["cpu"],
                    "use_official_source": True,
                }
            )

        packages.append(
            {
                "name": "paddleocr",
                "version": f">={PADDLEOCR_VERSION}",
                "use_official_source": False,
            }
        )

        return packages

    def _install_from_mirror(
        self,
        mirror: MirrorSource,
        packages: List[Dict[str, any]],
        retry: int,
        current_step: int,
        total_steps: int,
    ) -> bool:
        """
        从指定镜像安装包

        Args:
            mirror: 镜像源
            packages: 包列表
            retry: 当前重试次数
            current_step: 当前步骤
            total_steps: 总步骤

        Returns:
            bool: 是否安装成功
        """
        try:
            for i, package in enumerate(packages):
                self._check_cancelled()

                if package.get("use_official_source"):
                    cmd = [sys.executable, "-m", "pip", "install"]
                    cmd.extend(["-i", package["source"]])
                else:
                    cmd = mirror.get_pip_command()

                package_name = f"{package['name']}{package['version']}"
                cmd.append(package_name)
                cmd.extend(["--timeout", str(self.config.timeout)])

                if self.config.proxy:
                    cmd.extend(["--proxy", self.config.proxy])

                cmd.extend(["--upgrade"])

                source_name = (
                    "飞桨官方源" if package.get("use_official_source") else mirror.name
                )

                logger.info(f"安装命令: {' '.join(cmd)}")

                progress = InstallProgress(
                    status=InstallStatus.INSTALLING,
                    message=f"正在安装 {package['name']} ({source_name})...",
                    current_step=current_step,
                    total_steps=total_steps,
                    mirror_name=source_name,
                    retry_count=retry,
                    max_retries=self.config.max_retries,
                )
                self.progress.emit(progress)

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout,
                    encoding="utf-8",
                    errors="replace",
                )

                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "未知错误"
                    logger.error(f"安装 {package['name']} 失败: {error_msg}")
                    if package.get("use_official_source"):
                        return False
                    return False

                logger.info(f"安装 {package['name']} 成功")

            return True

        except subprocess.TimeoutExpired:
            logger.error(f"安装超时: {self.config.timeout}秒")
            return False
        except Exception as e:
            logger.error(f"安装异常: {e}", exc_info=True)
            return False

    def _emit_progress(
        self,
        status: InstallStatus,
        message: str,
        percentage: float = 0.0,
        **kwargs,
    ):
        """
        发射进度信号

        Args:
            status: 安装状态
            message: 状态消息
            percentage: 进度百分比
            **kwargs: 其他进度信息
        """
        progress = InstallProgress(
            status=status, message=message, percentage=percentage, **kwargs
        )
        self.progress.emit(progress)


# =============================================================================
# 安装管理器
# =============================================================================


class DependencyInstaller(QObject):
    """
    依赖安装管理器

    管理依赖安装的完整流程。
    """

    progress = Signal(object)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self):
        """初始化安装管理器"""
        super().__init__()

        self._worker: Optional[InstallWorker] = None
        self._config: Optional[InstallConfig] = None

    def start_install(self, config: InstallConfig):
        """
        开始安装

        Args:
            config: 安装配置
        """
        if self._worker and self._worker.isRunning():
            logger.warning("已有安装任务正在运行，先停止")
            self.cancel_install()

        self._config = config

        self._worker = InstallWorker(config)

        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        self._worker.start()

        logger.info(f"开始安装依赖，选项: {config.option.value}")

    def cancel_install(self):
        """取消安装"""
        if self._worker:
            self._worker.cancel()
            logger.info("安装已取消")

    def _on_progress(self, progress: InstallProgress):
        """
        安装进度回调

        Args:
            progress: 进度信息
        """
        self.progress.emit(progress)

    def _on_finished(self, success: bool, message: str):
        """
        安装完成回调

        Args:
            success: 是否成功
            message: 完成消息
        """
        self.finished.emit(success, message)
        self._worker = None

    def _on_error(self, error_message: str):
        """
        错误回调

        Args:
            error_message: 错误消息
        """
        self.error.emit(error_message)


# =============================================================================
# 全局安装管理器
# =============================================================================

_global_installer: Optional[DependencyInstaller] = None


def get_installer() -> DependencyInstaller:
    """
    获取全局安装管理器

    Returns:
        DependencyInstaller: 安装管理器实例
    """
    global _global_installer
    if _global_installer is None:
        _global_installer = DependencyInstaller()
    return _global_installer
