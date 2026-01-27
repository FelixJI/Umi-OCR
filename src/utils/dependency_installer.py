#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 依赖安装服务

后台安装OCR引擎依赖，支持多镜像源切换和进度通知。

主要功能：
- 支持CPU/GPU版本安装
- 智能镜像源切换（国内镜像优先）
- 安装进度实时通知
- 后台安装（QThread）
- 安装失败自动重试

Author: Umi-OCR Team
Date: 2026-01-27
"""

import sys
import subprocess
import threading
import logging
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThread

from .check_dependencies import (
    InstallOption,
    DependencyInfo,
    DependencyStatus
)


logger = logging.getLogger(__name__)


# =============================================================================
# 镜像源配置
# =============================================================================

@dataclass
class MirrorSource:
    """
    镜像源配置

    包含镜像源的URL和优先级。
    """
    name: str                          # 镜像源名称
    url: str                           # 镜像源URL
    priority: int                      # 优先级（数字越小优先级越高）
    is_official: bool = False          # 是否为官方源

    def get_pip_command(self) -> List[str]:
        """
        获取pip安装命令

        Returns:
            List[str]: pip命令列表
        """
        cmd = [sys.executable, "-m", "pip", "install"]

        # 添加镜像源
        if self.is_official:
            # 官方源，不指定-i参数
            pass
        else:
            # 国内镜像源
            cmd.extend(["-i", self.url])

        # 添加信任源（针对国内镜像）
        if not self.is_official:
            cmd.extend(["--trusted-host", self.url.replace("https://", "").replace("http://", "")])

        return cmd


# 默认镜像源列表（用于PaddleOCR等普通包）
DEFAULT_MIRRORS = [
    # 清华大学镜像（国内首选）
    MirrorSource(
        name="清华镜像",
        url="https://pypi.tuna.tsinghua.edu.cn/simple",
        priority=1,
        is_official=False
    ),
    # 阿里云镜像
    MirrorSource(
        name="阿里云镜像",
        url="https://mirrors.aliyun.com/pypi/simple/",
        priority=2,
        is_official=False
    ),
    # 豆瓣镜像
    MirrorSource(
        name="豆瓣镜像",
        url="https://pypi.douban.com/simple",
        priority=3,
        is_official=False
    ),
    # 中国科学技术大学镜像
    MirrorSource(
        name="中科大镜像",
        url="https://pypi.mirrors.ustc.edu.cn/simple",
        priority=4,
        is_official=False
    ),
    # pip官方源（作为后备）
    MirrorSource(
        name="pip官方源",
        url="https://pypi.org/simple",
        priority=100,
        is_official=True
    ),
]

# PaddlePaddle官方源（必须使用官方源安装PaddlePaddle）
# 参考: https://www.paddlepaddle.org.cn/install/quick
PADDLE_OFFICIAL_SOURCES = {
    "cpu": "https://www.paddlepaddle.org.cn/packages/stable/cpu/",
    "gpu_cu118": "https://www.paddlepaddle.org.cn/packages/stable/cu118/",
    "gpu_cu126": "https://www.paddlepaddle.org.cn/packages/stable/cu126/",
}

# PaddlePaddle版本号
PADDLEPADDLE_VERSION = "3.3.0"
PADDLEOCR_VERSION = "3.3.0"


# =============================================================================
# 安装状态
# =============================================================================

class InstallStatus(Enum):
    """安装状态"""
    PREPARING = "preparing"              # 准备中
    DOWNLOADING = "downloading"          # 下载中
    INSTALLING = "installing"            # 安装中
    COMPLETED = "completed"              # 已完成
    FAILED = "failed"                    # 失败
    CANCELLED = "cancelled"              # 已取消


@dataclass
class InstallProgress:
    """
    安装进度信息

    用于通知UI安装进度。
    """
    status: InstallStatus                # 安装状态
    message: str                        # 状态消息
    percentage: float = 0.0             # 进度百分比
    current_step: int = 1               # 当前步骤
    total_steps: int = 1                # 总步骤
    mirror_name: str = ""               # 当前使用的镜像源
    error_message: Optional[str] = None   # 错误信息


# =============================================================================
# 安装配置
# =============================================================================

@dataclass
class InstallConfig:
    """
    安装配置

    包含安装选项和参数。
    """
    option: InstallOption                # 安装选项（CPU/GPU）
    mirrors: List[MirrorSource] = field(default_factory=lambda: DEFAULT_MIRRORS.copy())  # 镜像源列表
    max_retries: int = 3                # 最大重试次数
    timeout: int = 300                  # 超时时间（秒）
    user_agent: Optional[str] = None     # 自定义User-Agent
    proxy: Optional[str] = None         # 代理设置


# =============================================================================
# 安装工作线程
# =============================================================================

class InstallWorker(QThread):
    """
    安装工作线程

    在后台执行依赖安装，避免阻塞UI。
    """

    # 信号定义
    progress = Signal(object)              # 安装进度 (InstallProgress)
    finished = Signal(bool, str)          # 安装完成 (成功, 消息)
    error = Signal(str)                   # 错误 (错误消息)

    def __init__(self, config: InstallConfig):
        """
        初始化安装工作线程

        Args:
            config: 安装配置
        """
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
            # 准备阶段
            self._emit_progress(InstallStatus.PREPARING, "准备安装...")
            self._check_cancelled()

            # 根据安装选项获取依赖列表
            packages = self._get_packages_to_install()
            total_steps = len(packages) * len(self.config.mirrors)

            # 遍历镜像源
            for mirror_idx, mirror in enumerate(self.config.mirrors):
                # 检查是否取消
                self._check_cancelled()

                # 发射进度（当前镜像）
                current_step = mirror_idx * len(packages) + 1
                progress = InstallProgress(
                    status=InstallStatus.DOWNLOADING,
                    message=f"正在使用 {mirror.name} 下载...",
                    percentage=(mirror_idx / len(self.config.mirrors)) * 100,
                    current_step=current_step,
                    total_steps=total_steps,
                    mirror_name=mirror.name
                )
                self.progress.emit(progress)

                # 尝试从当前镜像安装
                success = self._install_from_mirror(mirror, packages)

                if success:
                    # 安装成功
                    self.finished.emit(True, "安装成功！")
                    return
                elif mirror_idx < len(self.config.mirrors) - 1:
                    # 当前镜像失败，尝试下一个镜像
                    logger.warning(f"镜像源 {mirror.name} 失败，尝试下一个镜像")
                    continue
                else:
                    # 所有镜像都失败
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

        # PaddlePaddle - 必须使用官方源安装
        if self.config.option == InstallOption.GPU:
            # GPU版本 - 使用paddlepaddle-gpu包名和飞桨官方GPU源
            # 默认使用CUDA 11.8源（兼容性更好），后续可根据检测到的CUDA版本选择
            packages.append({
                "name": "paddlepaddle-gpu",
                "version": f"=={PADDLEPADDLE_VERSION}",
                "source": PADDLE_OFFICIAL_SOURCES["gpu_cu118"],
                "use_official_source": True,  # 标记使用官方源
            })
        else:
            # CPU版本 - 使用paddlepaddle包名和飞桨官方CPU源
            packages.append({
                "name": "paddlepaddle",
                "version": f"=={PADDLEPADDLE_VERSION}",
                "source": PADDLE_OFFICIAL_SOURCES["cpu"],
                "use_official_source": True,
            })

        # PaddleOCR - 可使用国内镜像源
        packages.append({
            "name": "paddleocr",
            "version": f">={PADDLEOCR_VERSION}",
            "use_official_source": False,
        })

        return packages

    def _install_from_mirror(self, mirror: MirrorSource, packages: List[Dict[str, any]]) -> bool:
        """
        从指定镜像安装包

        Args:
            mirror: 镜像源
            packages: 包列表

        Returns:
            bool: 是否安装成功
        """
        try:
            for i, package in enumerate(packages):
                # 检查是否取消
                self._check_cancelled()

                # 构建安装命令
                if package.get("use_official_source"):
                    # 使用PaddlePaddle官方源
                    cmd = [sys.executable, "-m", "pip", "install"]
                    cmd.extend(["-i", package["source"]])
                else:
                    # 使用普通镜像源
                    cmd = mirror.get_pip_command()

                # 添加包名和版本
                package_name = f"{package['name']}{package['version']}"
                cmd.append(package_name)

                # 添加超时
                cmd.extend(["--timeout", str(self.config.timeout)])

                # 添加代理（如果有）
                if self.config.proxy:
                    cmd.extend(["--proxy", self.config.proxy])

                # 添加其他选项
                cmd.extend([
                    "--upgrade",          # 升级已安装的包
                ])

                # 获取源名称用于显示
                source_name = "飞桨官方源" if package.get("use_official_source") else mirror.name

                logger.info(f"安装命令: {' '.join(cmd)}")

                # 发射进度
                progress = InstallProgress(
                    status=InstallStatus.INSTALLING,
                    message=f"正在安装 {package['name']} ({source_name})...",
                    current_step=i + 1,
                    total_steps=len(packages),
                    mirror_name=source_name
                )
                self.progress.emit(progress)

                # 执行安装
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout,
                    encoding='utf-8',
                    errors='replace'
                )

                # 检查是否成功
                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "未知错误"
                    logger.error(f"安装 {package['name']} 失败: {error_msg}")
                    # 如果是官方源安装失败，直接返回失败（不切换镜像）
                    if package.get("use_official_source"):
                        return False
                    return False

                # 安装成功
                logger.info(f"安装 {package['name']} 成功")

            return True

        except subprocess.TimeoutExpired:
            logger.error(f"安装超时: {self.config.timeout}秒")
            return False
        except Exception as e:
            logger.error(f"安装异常: {e}", exc_info=True)
            return False

    def _emit_progress(self, status: InstallStatus, message: str, percentage: float = 0.0):
        """
        发射进度信号

        Args:
            status: 安装状态
            message: 状态消息
            percentage: 进度百分比
        """
        progress = InstallProgress(
            status=status,
            message=message,
            percentage=percentage
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

    # 信号定义
    progress = Signal(object)              # 安装进度 (InstallProgress)
    finished = Signal(bool, str)          # 安装完成 (成功, 消息)
    error = Signal(str)                   # 错误 (错误消息)

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
        # 停止之前的安装任务
        if self._worker and self._worker.isRunning():
            logger.warning("已有安装任务正在运行，先停止")
            self.cancel_install()

        # 保存配置
        self._config = config

        # 创建工作线程
        self._worker = InstallWorker(config)

        # 连接信号
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        # 开始安装
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
        # 转发信号
        self.progress.emit(progress)

    def _on_finished(self, success: bool, message: str):
        """
        安装完成回调

        Args:
            success: 是否成功
            message: 完成消息
        """
        # 转发信号
        self.finished.emit(success, message)

        # 清理工作线程
        self._worker = None

    def _on_error(self, error_message: str):
        """
        错误回调

        Args:
            error_message: 错误消息
        """
        # 转发信号
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
