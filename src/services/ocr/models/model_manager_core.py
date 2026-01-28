#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 模型管理器核心

负责模型的下载、缓存、加载和管理。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import json
import shutil
import threading
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from .model_types import ModelType, ModelStatus, ModelInfo
from .model_repository import ModelRepository

logger = logging.getLogger(__name__)


class PaddleModelManager(QObject):
    """
    PaddleOCR 模型管理器

    负责模型的下载、缓存、加载和管理。
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    download_progress = Signal(str, int, int, float)
    download_completed = Signal(str, bool, str)
    model_loaded = Signal(str, bool)
    cache_cleaned = Signal(int, int)

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, cache_dir: Optional[Path] = None):
        """初始化模型管理器"""
        super().__init__()

        if cache_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            self.cache_dir = project_root / "models"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._models: Dict[str, ModelInfo] = {}
        self._load_model_cache()

        self._lock = threading.RLock()
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
                self._models[name] = ModelInfo.from_dict(model_data)

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
        """更新单个模型的缓存信息"""
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
        """下载模型"""
        with self._lock:
            model_info = ModelRepository.get_model_info(model_name)
            if not model_info:
                logger.error(f"未找到模型: {model_name}")
                self.download_completed.emit(
                    model_name, False, f"未找到模型: {model_name}"
                )
                return False

            if model_name in self._models:
                cached_model = self._models[model_name]
                if cached_model.status == ModelStatus.DOWNLOADED and not force:
                    logger.info(f"模型 {model_name} 已存在，跳过下载")
                    self.download_completed.emit(model_name, True, "模型已存在")
                    return True

            if model_name in self._active_downloads:
                logger.info(f"模型 {model_name} 正在下载中")
                return False

            self._active_downloads.add(model_name)

        thread = threading.Thread(
            target=self._download_model_thread, args=(model_name, model_info, force)
        )
        thread.daemon = True
        thread.start()

        return True

    def _download_model_thread(
        self, model_name: str, model_info: Dict, force: bool
    ) -> None:
        """下载模型（线程函数）"""
        try:
            with self._lock:
                if model_name not in self._models:
                    self._models[model_name] = ModelInfo(
                        name=model_name,
                        type=ModelType(model_info["type"]),
                        version=model_info["version"],
                        language=model_info["language"],
                        url=model_info["url"],
                        required=model_info.get("required", True),
                        status=ModelStatus.DOWNLOADING,
                    )
                else:
                    self._models[model_name].status = ModelStatus.DOWNLOADING

                self._save_model_cache()

            url = model_info.get("download_url", model_info["url"])
            target_path = self.cache_dir / f"{model_name}.tar"

            logger.info(f"开始下载模型: {model_name} from {url}")

            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))

            with open(target_path, "wb") as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percentage = (downloaded / total_size) * 100
                            self.download_progress.emit(
                                model_name, downloaded, total_size, percentage
                            )

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
        """取消下载"""
        return False

    # -------------------------------------------------------------------------
    # 模型加载
    # -------------------------------------------------------------------------

    def load_model(self, model_name: str) -> Optional[Path]:
        """加载模型"""
        with self._lock:
            if model_name not in self._models:
                logger.error(f"模型未找到: {model_name}")
                self.model_loaded.emit(model_name, False)
                return None

            model = self._models[model_name]

            if model.status == ModelStatus.LOADED:
                logger.info(f"模型 {model_name} 已加载")
                self.model_loaded.emit(model_name, True)
                return model.local_path

            if model.status == ModelStatus.NOT_DOWNLOADED:
                logger.warning(f"模型 {model_name} 未下载")
                self.model_loaded.emit(model_name, False)
                return None

            if model.status == ModelStatus.DOWNLOADED:
                model.status = ModelStatus.LOADED
                model.last_used = datetime.now()
                self._save_model_cache()

                logger.info(f"模型 {model_name} 加载成功")
                self.model_loaded.emit(model_name, True)
                return model.local_path

            return None

    def unload_model(self, model_name: str) -> None:
        """卸载模型"""
        with self._lock:
            if model_name in self._models:
                self._models[model_name].status = ModelStatus.DOWNLOADED
                self._save_model_cache()

    # -------------------------------------------------------------------------
    # 缓存清理
    # -------------------------------------------------------------------------

    def clean_cache(
        self, max_age_days: int = 30, max_size_gb: float = 10.0
    ) -> Tuple[int, int]:
        """清理模型缓存"""
        with self._lock:
            cleaned_count = 0
            freed_space = 0

            total_size = sum(model.size for model in self._models.values())
            total_size_gb = total_size / (1024**3)

            now = datetime.now()

            for name, model in list(self._models.items()):
                if model.required:
                    continue

                if model.last_used:
                    age_days = (now - model.last_used).days
                elif model.download_time:
                    age_days = (now - model.download_time).days
                else:
                    age_days = 0

                should_clean = False

                if age_days > max_age_days:
                    should_clean = True
                    logger.info(f"清理过期模型: {name} (未使用 {age_days} 天)")

                elif total_size_gb > max_size_gb:
                    should_clean = True
                    logger.info(f"清理模型以释放空间: {name}")

                if should_clean:
                    if model.local_path and model.local_path.exists():
                        freed_space += model.size
                        shutil.rmtree(model.local_path.parent, ignore_errors=True)

                    del self._models[name]
                    cleaned_count += 1

                    total_size = sum(model.size for model in self._models.values())
                    total_size_gb = total_size / (1024**3)

            self._save_model_cache()
            self.cache_cleaned.emit(cleaned_count, freed_space // (1024 * 1024))

            logger.info(
                f"缓存清理完成: 清理了 {cleaned_count} 个模型，"
                f"释放了 {freed_space // (1024 * 1024)} MB"
            )

            return cleaned_count, freed_space // (1024 * 1024)

    # -------------------------------------------------------------------------
    # 模型查询
    # -------------------------------------------------------------------------

    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        return self._models.get(model_name)

    def list_models(self, status: Optional[ModelStatus] = None) -> List[ModelInfo]:
        """列出模型"""
        models = list(self._models.values())

        if status:
            models = [m for m in models if m.status == status]

        return models

    def get_cache_size(self) -> int:
        """获取缓存大小（字节）"""
        return sum(model.size for model in self._models.values())


# =============================================================================
# 全局模型管理器实例
# =============================================================================

_global_model_manager: Optional[PaddleModelManager] = None


def get_model_manager(cache_dir: Optional[Path] = None) -> PaddleModelManager:
    """获取全局模型管理器"""
    global _global_model_manager
    if _global_model_manager is None:
        _global_model_manager = PaddleModelManager(cache_dir)
    return _global_model_manager
