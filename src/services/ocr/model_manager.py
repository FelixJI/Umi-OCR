#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 模型管理器

负责 PaddleOCR 模型的自动下载、缓存管理和按需加载。

主要功能：
- 自动下载 PaddleOCR 模型
- 模型缓存管理（清理旧模型、更新检查）
- 按需加载模型（必需模型 + 可选模型）
- 模型版本管理
- 下载进度通知

Author: Umi-OCR Team
Date: 2026-01-26
"""

import os
import json
import shutil
import threading
import hashlib
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from PySide6.QtCore import QObject, Signal


logger = logging.getLogger(__name__)


# =============================================================================
# 模型类型枚举
# =============================================================================

class ModelType(Enum):
    """模型类型"""
    DETECTION = "detection"      # 检测模型
    RECOGNITION = "recognition"  # 识别模型
    CLASSIFICATION = "classification"  # 分类模型（方向）
    TABLE = "table"              # 表格模型
    STRUCTURE = "structure"      # 结构分析模型
    LAYOUT = "layout"            # 版面分析模型


class ModelStatus(Enum):
    """模型状态"""
    NOT_DOWNLOADED = "not_downloaded"  # 未下载
    DOWNLOADING = "downloading"        # 下载中
    DOWNLOADED = "downloaded"          # 已下载
    LOADED = "loaded"                  # 已加载
    ERROR = "error"                    # 错误


# =============================================================================
# 模型信息数据类
# =============================================================================

@dataclass
class ModelInfo:
    """
    模型信息

    包含模型的基本信息和状态。
    """

    # 基本信息
    name: str                          # 模型名称
    type: ModelType                    # 模型类型
    version: str                       # 模型版本
    language: str                      # 语言（如 "ch", "en"）

    # 下载信息
    url: Optional[str] = None           # 下载URL（自动填充）
    size: int = 0                      # 文件大小（字节）
    md5: Optional[str] = None          # MD5校验值

    # 本地信息
    local_path: Optional[Path] = None   # 本地路径
    status: ModelStatus = ModelStatus.NOT_DOWNLOADED
    last_used: Optional[datetime] = None  # 最后使用时间
    download_time: Optional[datetime] = None  # 下载时间

    # 配置
    required: bool = True               # 是否为必需模型
    enabled: bool = True                # 是否启用

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.type.value,
            "version": self.version,
            "language": self.language,
            "url": self.url,
            "size": self.size,
            "md5": self.md5,
            "local_path": str(self.local_path) if self.local_path else None,
            "status": self.status.value,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "download_time": self.download_time.isoformat() if self.download_time else None,
            "required": self.required,
            "enabled": self.enabled
        }


# =============================================================================
# 模型仓库配置
# =============================================================================

class ModelRepository:
    """
    模型仓库

    定义 PaddleOCR 官方模型的仓库信息。
    """

    # PaddleOCR 官方模型仓库
    BASE_URL = "https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese"

    # 模型列表
    MODELS = {
        # 检测模型
        "ch_PP-OCRv4_det": {
            "type": ModelType.DETECTION,
            "version": "v4",
            "language": "ch",
            "required": True,
            "url": f"{BASE_URL}/ch_PP-OCRv4_det_infer.tar",
            "md5": "..."
        },
        "en_PP-OCRv4_det": {
            "type": ModelType.DETECTION,
            "version": "v4",
            "language": "en",
            "required": False,
            "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/english/en_PP-OCRv4_det_infer.tar",
            "md5": "..."
        },

        # 识别模型
        "ch_PP-OCRv4_rec": {
            "type": ModelType.RECOGNITION,
            "version": "v4",
            "language": "ch",
            "required": True,
            "url": f"{BASE_URL}/ch_PP-OCRv4_rec_infer.tar",
            "md5": "..."
        },
        "en_PP-OCRv4_rec": {
            "type": ModelType.RECOGNITION,
            "version": "v4",
            "language": "en",
            "required": False,
            "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/english/en_PP-OCRv4_rec_infer.tar",
            "md5": "..."
        },

        # 分类模型（方向检测）
        "ch_ppocr_mobile_v2.0_cls": {
            "type": ModelType.CLASSIFICATION,
            "version": "v2.0",
            "language": "ch",
            "required": True,
            "url": f"{BASE_URL}/ch_ppocr_mobile_v2.0_cls_infer.tar",
            "md5": "..."
        },

        # 表格模型
        "ch_ppstructure_mobile_v2.0_SLANet": {
            "type": ModelType.TABLE,
            "version": "v2.0",
            "language": "ch",
            "required": False,
            "url": "https://paddleocr.bj.bcebos.com/ppstructure/models/slanet/ch_ppstructure_mobile_v2.0_SLANet_infer.tar",
            "md5": "..."
        },

        # 结构分析模型
        "ch_ppstructure_mobile_v2.0_ppstructure": {
            "type": ModelType.STRUCTURE,
            "version": "v2.0",
            "language": "ch",
            "required": False,
            "url": "https://paddleocr.bj.bcebos.com/ppstructure/models/ch_ppstructure_mobile_v2.0_infer.tar",
            "md5": "..."
        }
    }

    @classmethod
    def get_model_info(cls, model_name: str) -> Optional[Dict]:
        """
        获取模型信息

        Args:
            model_name: 模型名称

        Returns:
            Optional[Dict]: 模型信息字典
        """
        return cls.MODELS.get(model_name)

    @classmethod
    def get_models_by_language(cls, language: str) -> List[str]:
        """
        按语言获取模型列表

        Args:
            language: 语言代码（如 "ch", "en"）

        Returns:
            List[str]: 模型名称列表
        """
        return [
            name for name, info in cls.MODELS.items()
            if info.get("language") == language
        ]

    @classmethod
    def get_required_models(cls, language: str = "ch") -> List[str]:
        """
        获取必需模型列表

        Args:
            language: 语言代码

        Returns:
            List[str]: 必需模型名称列表
        """
        return [
            name for name, info in cls.MODELS.items()
            if info.get("language") == language and info.get("required", False)
        ]


# =============================================================================
# 模型管理器
# =============================================================================

class PaddleModelManager(QObject):
    """
    PaddleOCR 模型管理器

    负责模型的下载、缓存、加载和管理。
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    # 下载进度信号
    # 参数: model_name (str), downloaded (int), total (int), percentage (float)
    download_progress = Signal(str, int, int, float)

    # 下载完成信号
    # 参数: model_name (str), success (bool), message (str)
    download_completed = Signal(str, bool, str)

    # 模型加载完成信号
    # 参数: model_name (str), success (bool)
    model_loaded = Signal(str, bool)

    # 缓存清理完成信号
    # 参数: cleaned_count (int), freed_space (int)
    cache_cleaned = Signal(int, int)

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        初始化模型管理器

        Args:
            cache_dir: 模型缓存目录（默认为项目根目录下的 models/）
        """
        super().__init__()

        # 缓存目录
        if cache_dir is None:
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent.parent
            self.cache_dir = project_root / "models"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 模型信息缓存
        self._models: Dict[str, ModelInfo] = {}
        self._load_model_cache()

        # 线程安全锁
        self._lock = threading.RLock()

        # 下载会话管理
        self._active_downloads: Set[str] = set()

    # -------------------------------------------------------------------------
    # 模型缓存管理
    # -------------------------------------------------------------------------

    def _load_model_cache(self) -> None:
        """加载模型信息缓存"""
        cache_file = self.cache_dir / "model_cache.json"

        if not cache_file.exists():
            return

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for name, model_data in data.items():
                self._models[name] = ModelInfo(
                    name=model_data["name"],
                    type=ModelType(model_data["type"]),
                    version=model_data["version"],
                    language=model_data["language"],
                    url=model_data.get("url"),
                    size=model_data.get("size", 0),
                    md5=model_data.get("md5"),
                    local_path=Path(model_data["local_path"]) if model_data.get("local_path") else None,
                    status=ModelStatus(model_data.get("status", ModelStatus.NOT_DOWNLOADED)),
                    last_used=datetime.fromisoformat(model_data["last_used"]) if model_data.get("last_used") else None,
                    download_time=datetime.fromisoformat(model_data["download_time"]) if model_data.get("download_time") else None,
                    required=model_data.get("required", True),
                    enabled=model_data.get("enabled", True)
                )

            logger.info(f"加载了 {len(self._models)} 个模型的缓存信息")

        except Exception as e:
            logger.error(f"加载模型缓存失败: {e}", exc_info=True)

    def _save_model_cache(self) -> None:
        """保存模型信息缓存"""
        cache_file = self.cache_dir / "model_cache.json"

        try:
            data = {name: model.to_dict() for name, model in self._models.items()}

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存模型缓存失败: {e}", exc_info=True)

    def _update_model_cache(self, model_name: str, **kwargs) -> None:
        """
        更新单个模型的缓存信息

        Args:
            model_name: 模型名称
            **kwargs: 要更新的字段
        """
        if model_name not in self._models:
            return

        for key, value in kwargs.items():
            if hasattr(self._models[model_name], key):
                setattr(self._models[model_name], key, value)

        self._save_model_cache()

    # -------------------------------------------------------------------------
    # 模型下载
    # -------------------------------------------------------------------------

    def download_model(self, model_name: str, force: bool = False) -> bool:
        """
        下载模型

        Args:
            model_name: 模型名称
            force: 是否强制重新下载

        Returns:
            bool: 是否下载成功
        """
        with self._lock:
            # 检查模型是否存在
            model_info = ModelRepository.get_model_info(model_name)
            if not model_info:
                logger.error(f"未找到模型: {model_name}")
                self.download_completed.emit(model_name, False, f"未找到模型: {model_name}")
                return False

            # 检查是否已下载
            if model_name in self._models:
                cached_model = self._models[model_name]
                if cached_model.status == ModelStatus.DOWNLOADED and not force:
                    logger.info(f"模型 {model_name} 已存在，跳过下载")
                    self.download_completed.emit(model_name, True, "模型已存在")
                    return True

            # 检查是否正在下载
            if model_name in self._active_downloads:
                logger.info(f"模型 {model_name} 正在下载中")
                return False

            # 添加到下载列表
            self._active_downloads.add(model_name)

        # 执行下载（异步）
        import threading
        thread = threading.Thread(
            target=self._download_model_thread,
            args=(model_name, model_info, force)
        )
        thread.daemon = True
        thread.start()

        return True

    def _download_model_thread(self, model_name: str, model_info: Dict, force: bool) -> None:
        """
        下载模型（线程函数）

        Args:
            model_name: 模型名称
            model_info: 模型信息
            force: 是否强制重新下载
        """
        try:
            # 更新状态为下载中
            with self._lock:
                if model_name not in self._models:
                    self._models[model_name] = ModelInfo(
                        name=model_name,
                        type=model_info["type"],
                        version=model_info["version"],
                        language=model_info["language"],
                        url=model_info["url"],
                        required=model_info.get("required", True),
                        status=ModelStatus.DOWNLOADING
                    )
                else:
                    self._models[model_name].status = ModelStatus.DOWNLOADING

                self._save_model_cache()

            # 下载文件
            url = model_info["url"]
            target_path = self.cache_dir / f"{model_name}.tar"

            logger.info(f"开始下载模型: {model_name} from {url}")

            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))

            # 写入文件
            with open(target_path, "wb") as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # 发送进度信号
                        if total_size > 0:
                            percentage = (downloaded / total_size) * 100
                            self.download_progress.emit(model_name, downloaded, total_size, percentage)

            # 更新模型信息
            with self._lock:
                self._models[model_name].status = ModelStatus.DOWNLOADED
                self._models[model_name].local_path = target_path
                self._models[model_name].size = downloaded
                self._models[model_name].download_time = datetime.now()
                self._save_model_cache()

            logger.info(f"模型 {model_name} 下载完成")
            self.download_completed.emit(model_name, True, "下载成功")

        except Exception as e:
            logger.error(f"下载模型 {model_name} 失败: {e}", exc_info=True)

            with self._lock:
                if model_name in self._models:
                    self._models[model_name].status = ModelStatus.ERROR
                    self._save_model_cache()

            self.download_completed.emit(model_name, False, str(e))

        finally:
            with self._lock:
                self._active_downloads.discard(model_name)

    def cancel_download(self, model_name: str) -> bool:
        """
        取消下载

        Args:
            model_name: 模型名称

        Returns:
            bool: 是否成功取消
        """
        # TODO: 实现下载取消
        return False

    # -------------------------------------------------------------------------
    # 模型加载
    # -------------------------------------------------------------------------

    def load_model(self, model_name: str) -> Optional[Path]:
        """
        加载模型

        Args:
            model_name: 模型名称

        Returns:
            Optional[Path]: 模型路径（如果加载成功）
        """
        with self._lock:
            # 检查模型是否存在
            if model_name not in self._models:
                logger.error(f"模型未找到: {model_name}")
                self.model_loaded.emit(model_name, False)
                return None

            model = self._models[model_name]

            # 检查模型状态
            if model.status == ModelStatus.LOADED:
                logger.info(f"模型 {model_name} 已加载")
                self.model_loaded.emit(model_name, True)
                return model.local_path

            if model.status == ModelStatus.NOT_DOWNLOADED:
                logger.warning(f"模型 {model_name} 未下载")
                self.model_loaded.emit(model_name, False)
                return None

            # 模型已下载，标记为已加载
            if model.status == ModelStatus.DOWNLOADED:
                model.status = ModelStatus.LOADED
                model.last_used = datetime.now()
                self._save_model_cache()

                logger.info(f"模型 {model_name} 加载成功")
                self.model_loaded.emit(model_name, True)
                return model.local_path

            return None

    def unload_model(self, model_name: str) -> None:
        """
        卸载模型

        Args:
            model_name: 模型名称
        """
        with self._lock:
            if model_name in self._models:
                self._models[model_name].status = ModelStatus.DOWNLOADED
                self._save_model_cache()

    # -------------------------------------------------------------------------
    # 缓存清理
    # -------------------------------------------------------------------------

    def clean_cache(self, max_age_days: int = 30, max_size_gb: float = 10.0) -> Tuple[int, int]:
        """
        清理模型缓存

        Args:
            max_age_days: 最大保留天数
            max_size_gb: 最大缓存大小（GB）

        Returns:
            Tuple[int, int]: (清理的模型数, 释放的空间MB）
        """
        import time

        with self._lock:
            cleaned_count = 0
            freed_space = 0

            # 计算总大小
            total_size = sum(model.size for model in self._models.values())
            total_size_gb = total_size / (1024 ** 3)

            # 检查时间
            now = datetime.now()

            for name, model in list(self._models.items()):
                # 跳过必需模型
                if model.required:
                    continue

                # 检查年龄
                if model.last_used:
                    age_days = (now - model.last_used).days
                elif model.download_time:
                    age_days = (now - model.download_time).days
                else:
                    age_days = 0

                # 决定是否清理
                should_clean = False

                # 超过最大天数
                if age_days > max_age_days:
                    should_clean = True
                    logger.info(f"清理过期模型: {name} (未使用 {age_days} 天)")

                # 超过最大大小
                elif total_size_gb > max_size_gb:
                    # 清理最久未使用的模型
                    should_clean = True
                    logger.info(f"清理模型以释放空间: {name}")

                if should_clean:
                    # 删除文件
                    if model.local_path and model.local_path.exists():
                        freed_space += model.size
                        shutil.rmtree(model.local_path.parent, ignore_errors=True)

                    # 从缓存中移除
                    del self._models[name]
                    cleaned_count += 1

                    # 重新计算总大小
                    total_size = sum(model.size for model in self._models.values())
                    total_size_gb = total_size / (1024 ** 3)

            # 保存缓存
            self._save_model_cache()

            # 发送信号
            self.cache_cleaned.emit(cleaned_count, freed_space // (1024 * 1024))

            logger.info(f"缓存清理完成: 清理了 {cleaned_count} 个模型，释放了 {freed_space // (1024 * 1024)} MB")

            return cleaned_count, freed_space // (1024 * 1024)

    # -------------------------------------------------------------------------
    # 模型查询
    # -------------------------------------------------------------------------

    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """
        获取模型信息

        Args:
            model_name: 模型名称

        Returns:
            Optional[ModelInfo]: 模型信息
        """
        return self._models.get(model_name)

    def list_models(self, status: Optional[ModelStatus] = None) -> List[ModelInfo]:
        """
        列出模型

        Args:
            status: 状态过滤器（None 表示不过滤）

        Returns:
            List[ModelInfo]: 模型列表
        """
        models = list(self._models.values())

        if status:
            models = [m for m in models if m.status == status]

        return models

    def get_cache_size(self) -> int:
        """
        获取缓存大小（字节）

        Returns:
            int: 缓存大小（字节）
        """
        return sum(model.size for model in self._models.values())


# =============================================================================
# 全局模型管理器实例
# =============================================================================

_global_model_manager: Optional[PaddleModelManager] = None


def get_model_manager(cache_dir: Optional[Path] = None) -> PaddleModelManager:
    """
    获取全局模型管理器

    Args:
        cache_dir: 模型缓存目录

    Returns:
        PaddleModelManager: 模型管理器单例
    """
    global _global_model_manager
    if _global_model_manager is None:
        _global_model_manager = PaddleModelManager(cache_dir)
    return _global_model_manager
