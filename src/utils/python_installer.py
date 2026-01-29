#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python 嵌入式环境安装器

负责下载、解压和配置 Python Embeddable Package。
"""

import os
import sys
import shutil
import logging
import zipfile
import urllib.request
import ssl
import subprocess
from pathlib import Path
from typing import Optional, Callable, List, Tuple

# 只有在主程序中引用时才会有 logger 配置，独立运行时使用默认配置
logger = logging.getLogger(__name__)

# Python 版本配置 (3.10.11 是目前兼容性较好的版本)
PYTHON_VERSION = "3.10.11"
PYTHON_DIR_NAME = "python_runtime"

# 下载源配置
PYTHON_URLS = {
    "official": f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip",
    "taobao": f"https://npmmirror.com/mirrors/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip",
}

GET_PIP_URLS = {
    "official": "https://bootstrap.pypa.io/get-pip.py",
    "aliyun": "https://mirrors.aliyun.com/pypi/get-pip.py",  # 阿里云有时会有
}


class PythonInstaller:
    """Python 环境安装器"""

    def __init__(self, install_dir: str):
        self.install_dir = Path(install_dir)
        self.python_dir = self.install_dir / PYTHON_DIR_NAME
        self.python_exe = self.python_dir / "python.exe"
        self._cancel_flag = False

    def is_installed(self) -> bool:
        """检查 Python 环境是否已安装且可用"""
        if not self.python_exe.exists():
            return False
        
        # 简单检查是否能运行
        try:
            subprocess.run(
                [str(self.python_exe), "--version"], 
                capture_output=True, 
                check=True
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def install(self, progress_callback: Optional[Callable[[str, float], None]] = None) -> bool:
        """
        执行安装流程
        
        Args:
            progress_callback: 进度回调 (message, percentage)
        """
        self._cancel_flag = False
        
        try:
            # 1. 准备目录
            if self.python_dir.exists():
                # 如果已存在但损坏，或者强制重新安装，先清理
                if not self.is_installed():
                    shutil.rmtree(self.python_dir)
                else:
                    if progress_callback:
                        progress_callback("Python 环境已存在", 100)
                    return True
            
            self.python_dir.mkdir(parents=True, exist_ok=True)

            # 2. 下载 Python Embed 包
            zip_path = self.install_dir / f"python-{PYTHON_VERSION}.zip"
            if not self._download_file(
                PYTHON_URLS["taobao"],  # 优先使用国内源
                zip_path, 
                "Python 运行环境",
                progress_callback,
                start_pct=0,
                end_pct=40
            ):
                # 尝试官方源
                if not self._download_file(
                    PYTHON_URLS["official"],
                    zip_path,
                    "Python 运行环境 (官方源)",
                    progress_callback,
                    start_pct=0,
                    end_pct=40
                ):
                    raise RuntimeError("无法下载 Python 环境")

            # 3. 解压
            if progress_callback:
                progress_callback("正在解压 Python 环境...", 45)
            
            self._extract_zip(zip_path, self.python_dir)
            zip_path.unlink() # 删除压缩包

            # 4. 配置 _pth 文件 (允许 import site)
            if progress_callback:
                progress_callback("正在配置环境...", 50)
            self._configure_pth_file()

            # 5. 下载 get-pip.py
            get_pip_path = self.python_dir / "get-pip.py"
            if not self._download_file(
                GET_PIP_URLS["official"], # get-pip 通常比较小，官方源也可，或者找稳定镜像
                get_pip_path,
                "pip 安装工具",
                progress_callback,
                start_pct=50,
                end_pct=60
            ):
                raise RuntimeError("无法下载 get-pip.py")

            # 6. 安装 pip
            if progress_callback:
                progress_callback("正在安装 pip...", 65)
            
            self._install_pip(get_pip_path)
            get_pip_path.unlink() # 删除脚本

            if progress_callback:
                progress_callback("Python 环境准备完成", 100)
            
            return True

        except Exception as e:
            logger.error(f"Python 环境安装失败: {e}", exc_info=True)
            # 清理可能损坏的安装
            if self.python_dir.exists():
                shutil.rmtree(self.python_dir, ignore_errors=True)
            raise e

    def cancel(self):
        """取消安装"""
        self._cancel_flag = True

    def _download_file(
        self, 
        url: str, 
        save_path: Path, 
        desc: str,
        callback: Optional[Callable[[str, float], None]],
        start_pct: float,
        end_pct: float
    ) -> bool:
        """下载文件带进度"""
        try:
            if callback:
                callback(f"正在下载 {desc}...", start_pct)

            # 忽略 SSL 错误 (针对某些环境)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(url, context=ctx, timeout=30) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                block_size = 8192

                with open(save_path, 'wb') as f:
                    while True:
                        if self._cancel_flag:
                            return False
                        
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        
                        downloaded += len(buffer)
                        f.write(buffer)

                        if total_size > 0 and callback:
                            pct = start_pct + (downloaded / total_size) * (end_pct - start_pct)
                            callback(f"正在下载 {desc}...", pct)
            return True
        except Exception as e:
            logger.warning(f"下载失败 {url}: {e}")
            if save_path.exists():
                save_path.unlink()
            return False

    def _extract_zip(self, zip_path: Path, extract_to: Path):
        """解压 ZIP"""
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

    def _configure_pth_file(self):
        """修改 ._pth 文件以支持 site-packages"""
        # 查找 python3xx._pth
        pth_files = list(self.python_dir.glob("python*._pth"))
        if not pth_files:
            logger.warning("未找到 ._pth 文件，可能无法正确加载 pip")
            return
        
        pth_file = pth_files[0]
        content = pth_file.read_text(encoding='utf-8')
        
        # 取消 'import site' 的注释
        # 原文通常是 "#import site"
        new_content = content.replace("#import site", "import site")
        
        if new_content == content:
            # 如果没找到带#的，可能已经开启，或者格式不同，尝试强制添加
            if "import site" not in content:
                new_content += "\nimport site"
        
        pth_file.write_text(new_content, encoding='utf-8')

    def _install_pip(self, get_pip_path: Path):
        """运行 get-pip.py"""
        # 使用国内源安装 pip 自身，避免连接 pypi.org 超时
        cmd = [
            str(self.python_exe), 
            str(get_pip_path), 
            "--no-warn-script-location",
            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple" 
        ]
        
        # 隐藏控制台窗口 (Windows)
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=startupinfo
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"pip 安装失败: {stderr}")

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    installer = PythonInstaller(".")
    installer.install(lambda msg, pct: print(f"{pct:.1f}%: {msg}"))
