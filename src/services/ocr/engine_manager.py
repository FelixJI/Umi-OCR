#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 引擎管理器

管理多个 OCR 引擎的注册、加载、切换和销毁。
采用策略模式，支持引擎热切换和失败自动回退。

主要功能：
- 引擎注册和发现
- 引擎热切换（任务间切换）
- 延迟加载引擎实例
- 延迟销毁旧引擎（5分钟）
- 失败自动回退（本地优先，云引擎备用）
- 配置状态保存（每个引擎独立配置）
- 统一识别接口

Author: Umi-OCR Team
Date: 2026-01-27
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, List, Type, Callable
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal

from .base_engine import BaseOCREngine, OCRErrorCode
from .ocr_result import OCRResult
from .paddle_engine import PaddleOCREngine

logger = logging.getLogger(__name__)


# =============================================================================
# 配置管理器集成
# =============================================================================

_config_manager = None


def set_config_manager(config_manager) -> None:
    """
    设置配置管理器（用于引擎配置管理）

    Args:
        config_manager: 配置管理器实例
    """
    global _config_manager
    _config_manager = config_manager


# =============================================================================
# 引擎注册信息
# =============================================================================


@dataclass
class EngineInfo:
    """
    引擎注册信息

    包含引擎的元数据和工厂方法。
    """

    engine_type: str  # 引擎类型标识
    engine_class: Type[BaseOCREngine]  # 引擎类
    factory: Callable  # 工厂方法
    is_local: bool = False  # 是否为本地引擎
    priority: int = 0  # 优先级（数字越小优先级越高）


@dataclass
class EngineState:
    """
    引擎状态信息

    跟踪引擎实例的运行时状态。
    """

    engine_type: str  # 引擎类型
    engine_instance: Optional[BaseOCREngine] = None  # 引擎实例（延迟加载）
    config: Dict[str, Any] = field(default_factory=dict)  # 当前配置
    config_path: str = ""  # 配置路径（如 "ocr.paddle"）
    is_initialized: bool = False  # 是否已初始化
    last_used_time: float = 0.0  # 最后使用时间（Unix timestamp）
    destroy_timer: Optional[threading.Timer] = None  # 销毁计时器


# =============================================================================
# 引擎管理器
# =============================================================================


class EngineManager(QObject):
    """
    引擎管理器（单例模式）

    管理 OCR 引擎的注册、加载、切换和销毁。
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    # 引擎切换信号
    # 参数: old_engine_type (str), new_engine_type (str)
    engine_switched = Signal(str, str)

    # 引擎初始化失败信号
    # 参数: engine_type (str), error_code (str), error_message (str)
    engine_failed = Signal(str, str, str)

    # 引擎状态变更信号
    # 参数: engine_type (str), is_ready (bool)
    engine_ready = Signal(str, bool)

    # -------------------------------------------------------------------------
    # 单例模式
    # -------------------------------------------------------------------------

    _instance: Optional["EngineManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "EngineManager":
        """
        实现单例模式

        Returns:
            EngineManager: 唯一的引擎管理器实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self):
        """
        初始化引擎管理器

        注意：由于单例模式，此方法只会被调用一次。
        """
        # 防止重复初始化
        if hasattr(self, "_initialized") and self._initialized:
            return

        super().__init__()

        self._initialized: bool = True

        # 引擎注册表 {engine_type: EngineInfo}
        self._engine_registry: Dict[str, EngineInfo] = {}

        # 引擎状态表 {engine_type: EngineState}
        self._engine_states: Dict[str, EngineState] = {}

        # 当前活跃的引擎
        self._current_engine_type: Optional[str] = None

        # 读写锁（保护引擎状态）
        self._state_lock = threading.RLock()

        # 延迟销毁时间（秒）
        self._destroy_delay = 300  # 5分钟

        # 是否启用自动回退
        self._auto_fallback = True

        # 配置变更监听器引用
        self._config_listener = None

    # -------------------------------------------------------------------------
    # 引擎注册
    # -------------------------------------------------------------------------

    def register_engine(
        self,
        engine_type: str,
        engine_class: Type[BaseOCREngine],
        factory: Optional[Callable] = None,
        is_local: bool = False,
        priority: int = 0,
    ) -> None:
        """
        注册 OCR 引擎

        Args:
            engine_type: 引擎类型标识（如 "paddle", "baidu"）
            engine_class: 引擎类（必须继承 BaseOCREngine）
            factory: 工厂方法（可选，默认使用 engine_class 构造函数）
            is_local: 是否为本地引擎（本地引擎优先级更高）
            priority: 优先级（数字越小优先级越高）

        Raises:
            ValueError: 引擎已注册或引擎类不合法
        """
        with self._state_lock:
            # 检查是否已注册
            if engine_type in self._engine_registry:
                logger.warning(f"引擎 {engine_type} 已注册，覆盖之前的注册")

            # 验证引擎类
            if not issubclass(engine_class, BaseOCREngine):
                raise ValueError(f"{engine_class} 必须继承 BaseOCREngine")

            # 创建工厂方法（如果未提供）
            if factory is None:
                factory = engine_class

            # 注册引擎
            self._engine_registry[engine_type] = EngineInfo(
                engine_type=engine_type,
                engine_class=engine_class,
                factory=factory,
                is_local=is_local,
                priority=priority,
            )

            # 初始化引擎状态
            self._engine_states[engine_type] = EngineState(
                engine_type=engine_type, config_path=f"ocr.{engine_type}"
            )

            logger.info(
                f"注册引擎: {engine_type} (local={is_local}, priority={priority})"
            )

    def unregister_engine(self, engine_type: str) -> bool:
        """
        注销 OCR 引擎

        Args:
            engine_type: 引擎类型标识

        Returns:
            bool: 是否注销成功
        """
        with self._state_lock:
            if engine_type not in self._engine_registry:
                return False

            # 如果是当前引擎，先停止
            if self._current_engine_type == engine_type:
                self._stop_engine(engine_type)
                self._current_engine_type = None

            # 移除注册
            del self._engine_registry[engine_type]
            del self._engine_states[engine_type]

            logger.info(f"注销引擎: {engine_type}")
            return True

    # -------------------------------------------------------------------------
    # 引擎查询
    # -------------------------------------------------------------------------

    def get_available_engines(self) -> List[str]:
        """
        获取所有已注册的引擎类型列表

        Returns:
            List[str]: 引擎类型列表（按优先级排序）
        """
        with self._state_lock:
            # 按优先级排序（本地引擎优先）
            engines = list(self._engine_registry.keys())
            engines.sort(
                key=lambda e: (
                    0 if self._engine_registry[e].is_local else 1,
                    self._engine_registry[e].priority,
                )
            )
            return engines

    def get_engine_info(self, engine_type: str) -> Optional[EngineInfo]:
        """
        获取引擎注册信息

        Args:
            engine_type: 引擎类型

        Returns:
            Optional[EngineInfo]: 引擎信息（未注册返回 None）
        """
        with self._state_lock:
            return self._engine_registry.get(engine_type)

    def get_current_engine(self) -> Optional[BaseOCREngine]:
        """
        获取当前活跃的引擎实例

        Returns:
            Optional[BaseOCREngine]: 当前引擎实例（未设置返回 None）
        """
        with self._state_lock:
            if self._current_engine_type is None:
                return None

            state = self._engine_states.get(self._current_engine_type)
            return state.engine_instance if state else None

    def get_current_engine_type(self) -> Optional[str]:
        """
        获取当前活跃的引擎类型

        Returns:
            Optional[str]: 当前引擎类型（未设置返回 None）
        """
        return self._current_engine_type

    # -------------------------------------------------------------------------
    # 引擎生命周期
    # -------------------------------------------------------------------------

    def _load_engine_instance(self, engine_type: str) -> Optional[BaseOCREngine]:
        """
        加载引擎实例（延迟加载）

        Args:
            engine_type: 引擎类型

        Returns:
            Optional[BaseOCREngine]: 引擎实例（失败返回 None）
        """
        with self._state_lock:
            engine_info = self._engine_registry.get(engine_type)
            if not engine_info:
                logger.error(f"引擎未注册: {engine_type}")
                return None

            state = self._engine_states.get(engine_type)
            if not state:
                logger.error(f"引擎状态不存在: {engine_type}")
                return None

            # 如果已加载，直接返回
            if state.engine_instance is not None:
                return state.engine_instance

            try:
                # 使用工厂方法创建实例
                engine = engine_info.factory(state.config)

                # 检查引擎可用性
                if not engine.is_available():
                    logger.error(f"引擎不可用: {engine_type}")
                    return None

                # 初始化引擎
                if not engine.initialize():
                    logger.error(f"引擎初始化失败: {engine_type}")
                    return None

                # 保存实例
                state.engine_instance = engine
                state.is_initialized = True
                state.last_used_time = time.time()

                # 发送就绪信号
                self.engine_ready.emit(engine_type, True)

                logger.info(f"引擎加载成功: {engine_type}")
                return engine

            except Exception as e:
                logger.error(f"引擎加载异常: {engine_type}, {e}", exc_info=True)
                return None

    def _stop_engine(self, engine_type: str) -> None:
        """
        停止引擎实例

        Args:
            engine_type: 引擎类型
        """
        with self._state_lock:
            state = self._engine_states.get(engine_type)
            if not state:
                return

            # 取消销毁计时器
            if state.destroy_timer:
                state.destroy_timer.cancel()
                state.destroy_timer = None

            # 停止引擎
            if state.engine_instance:
                try:
                    state.engine_instance.stop()
                except Exception as e:
                    logger.error(f"引擎停止异常: {engine_type}, {e}", exc_info=True)
                finally:
                    state.engine_instance = None
                    state.is_initialized = False

                    # 发送未就绪信号
                    self.engine_ready.emit(engine_type, False)

            logger.info(f"引擎已停止: {engine_type}")

    def _schedule_destroy(self, engine_type: str, delay: float = 300.0) -> None:
        """
        调度引擎销毁（延迟销毁）

        Args:
            engine_type: 引擎类型
            delay: 延迟时间（秒），默认5分钟
        """
        with self._state_lock:
            state = self._engine_states.get(engine_type)
            if not state or not state.engine_instance:
                return

            # 取消之前的计时器
            if state.destroy_timer:
                state.destroy_timer.cancel()

            # 创建新的销毁计时器
            def destroy_callback():
                self._stop_engine(engine_type)

            state.destroy_timer = threading.Timer(delay, destroy_callback)
            state.destroy_timer.start()

            logger.info(f"引擎销毁已调度: {engine_type}, {delay}秒后销毁")

    def _cancel_destroy(self, engine_type: str) -> None:
        """
        取消引擎销毁

        Args:
            engine_type: 引擎类型
        """
        with self._state_lock:
            state = self._engine_states.get(engine_type)
            if not state:
                return

            if state.destroy_timer:
                state.destroy_timer.cancel()
                state.destroy_timer = None
                logger.info(f"已取消引擎销毁: {engine_type}")

    # -------------------------------------------------------------------------
    # 引擎切换
    # -------------------------------------------------------------------------

    def switch_engine(self, engine_type: str) -> bool:
        """
        切换到指定引擎

        Args:
            engine_type: 目标引擎类型

        Returns:
            bool: 是否切换成功
        """
        with self._state_lock:
            # 检查引擎是否已注册
            if engine_type not in self._engine_registry:
                logger.error(f"引擎未注册: {engine_type}")
                return False

            # 如果已经是当前引擎，直接返回
            if self._current_engine_type == engine_type:
                logger.info(f"已经是当前引擎: {engine_type}")
                return True

            # 保存旧引擎类型
            old_engine_type = self._current_engine_type

            # 调度旧引擎销毁（5分钟后）
            if old_engine_type:
                self._schedule_destroy(old_engine_type)

            # 加载新引擎
            new_engine = self._load_engine_instance(engine_type)
            if not new_engine:
                logger.error(f"引擎加载失败: {engine_type}")

                # 尝试回退到旧引擎
                if old_engine_type:
                    logger.warning(f"回退到原引擎: {old_engine_type}")
                    self._cancel_destroy(old_engine_type)
                    return False
                else:
                    # 尝试回退到默认引擎
                    return self._fallback_to_default_engine()

            # 更新当前引擎
            self._current_engine_type = engine_type

            # 发送切换信号
            self.engine_switched.emit(old_engine_type or "", engine_type)

            logger.info(f"引擎切换成功: {old_engine_type or 'None'} -> {engine_type}")
            return True

    # -------------------------------------------------------------------------
    # 失败回退
    # -------------------------------------------------------------------------

    def _fallback_to_default_engine(self) -> bool:
        """
        回退到默认引擎（本地引擎优先）

        Returns:
            bool: 是否回退成功
        """
        available_engines = self.get_available_engines()

        if not available_engines:
            logger.error("没有可用的引擎")
            return False

        # 尝试加载第一个可用的引擎
        for engine_type in available_engines:
            engine = self._load_engine_instance(engine_type)
            if engine:
                self._current_engine_type = engine_type
                logger.warning(f"回退到引擎: {engine_type}")
                return True

        logger.error("所有引擎都无法加载")
        return False

    # -------------------------------------------------------------------------
    # 配置管理
    # -------------------------------------------------------------------------

    def get_engine_config(self, engine_type: str) -> Dict[str, Any]:
        """
        获取引擎配置

        Args:
            engine_type: 引擎类型

        Returns:
            Dict[str, Any]: 引擎配置字典
        """
        with self._state_lock:
            state = self._engine_states.get(engine_type)
            return state.config.copy() if state else {}

    def set_engine_config(self, engine_type: str, config: Dict[str, Any]) -> None:
        """
        设置引擎配置

        Args:
            engine_type: 引擎类型
            config: 配置字典
        """
        with self._state_lock:
            state = self._engine_states.get(engine_type)
            if state:
                state.config = config.copy()
                logger.info(f"引擎配置已更新: {engine_type}")

                # 如果引擎已加载，需要重新初始化
                if state.engine_instance:
                    state.engine_instance.set_config_value("config", config)
                    logger.info(f"已重新应用配置: {engine_type}")

    # -------------------------------------------------------------------------
    # 统一识别接口
    # -------------------------------------------------------------------------

    def recognize(
        self, image: Any, task_id: Optional[str] = None, **kwargs
    ) -> OCRResult:
        """
        执行 OCR 识别（统一接口）

        Args:
            image: 图像数据
            task_id: 任务 ID
            **kwargs: 额外的识别参数

        Returns:
            OCRResult: 识别结果
        """
        # 获取当前引擎
        engine = self.get_current_engine()
        if not engine:
            # 尝试加载默认引擎
            if not self._fallback_to_default_engine():
                # 所有本地引擎都不可用
                logger.warning("没有可用的本地OCR引擎")
                return OCRResult(
                    success=False,
                    error_code=OCRErrorCode.NOT_INITIALIZED.value,
                    error_message="没有可用的本地OCR引擎。\n\n"
                    "请安装OCR引擎：\n"
                    "1. 重新启动程序，按照安装向导的提示安装OCR引擎\n"
                    '2. 或运行: pip install -e ".[cpu]" (CPU版本)\n'
                    "3. 重新启动程序后使用\n\n"
                    "提示：第18-19阶段将支持在线OCR服务（需要网络）",
                    engine_type="none",
                    engine_name="Unknown",
                )
            engine = self.get_current_engine()

            # 再次检查，防止回退也失败
            if not engine:
                return OCRResult(
                    success=False,
                    error_code=OCRErrorCode.NOT_INITIALIZED.value,
                    error_message="没有可用的 OCR 引擎（回退失败）\n\n"
                    "请尝试重新安装OCR引擎，或联系技术支持。",
                    engine_type="none",
                    engine_name="Unknown",
                )

        # 更新最后使用时间（取消销毁计时器）
        if self._current_engine_type:
            state = self._engine_states.get(self._current_engine_type)
            if state:
                state.last_used_time = time.time()
                self._cancel_destroy(self._current_engine_type)

        # 委托给引擎执行识别
        return engine.recognize(image, task_id, **kwargs)

    # -------------------------------------------------------------------------
    # 初始化和配置集成
    # -------------------------------------------------------------------------

    def initialize(self) -> bool:
        """
        初始化引擎管理器

        从配置管理器加载配置，注册引擎，并设置默认引擎。

        Returns:
            bool: 是否初始化成功
        """
        try:
            # 1. 注册所有可用的引擎
            self._register_builtin_engines()

            # 2. 从配置管理器加载引擎配置
            self._load_engine_configs()

            # 3. 监听配置变更
            self._setup_config_listener()

            # 4. 初始化默认引擎
            self._initialize_default_engine()

            logger.info("引擎管理器初始化成功")
            return True

        except Exception as e:
            logger.error(f"引擎管理器初始化失败: {e}", exc_info=True)
            return False

    def _register_builtin_engines(self) -> None:
        """注册内置的 OCR 引擎"""
        # 注册 PaddleOCR（本地引擎）
        self.register_engine(
            engine_type="paddle",
            engine_class=PaddleOCREngine,
            factory=lambda config: PaddleOCREngine(config),
            is_local=True,
            priority=1,
        )

        # 注册云引擎（第18-19阶段实现）
        # 百度云 OCR
        from .cloud import BaiduOCREngine

        self.register_engine(
            engine_type="baidu_cloud",
            engine_class=BaiduOCREngine,
            factory=lambda config: BaiduOCREngine(config, qps_limit=10),
            is_local=False,
            priority=10,
        )

        # 腾讯云 OCR
        from .cloud import TencentOCREngine

        self.register_engine(
            engine_type="tencent_cloud",
            engine_class=TencentOCREngine,
            factory=lambda config: TencentOCREngine(config, qps_limit=10),
            is_local=False,
            priority=11,
        )

        # 阿里云 OCR
        from .cloud import AliyunOCREngine

        self.register_engine(
            engine_type="aliyun_cloud",
            engine_class=AliyunOCREngine,
            factory=lambda config: AliyunOCREngine(config, qps_limit=10),
            is_local=False,
            priority=12,
        )

        logger.info(f"已注册 {len(self._engine_registry)} 个引擎")

    def _load_engine_configs(self) -> None:
        """从配置管理器加载引擎配置"""
        global _config_manager
        if not _config_manager:
            logger.warning("配置管理器未设置，使用默认配置")
            return

        with self._state_lock:
            for engine_type, state in self._engine_states.items():
                # 从配置管理器读取引擎配置
                config = _config_manager.get(f"ocr.{engine_type}", {})
                if config:
                    state.config = config
                    logger.info(f"加载引擎配置: {engine_type}")

    def _setup_config_listener(self) -> None:
        """设置配置变更监听"""
        global _config_manager
        if not _config_manager:
            return

        # 创建监听器函数
        def on_config_changed(event):
            """配置变更回调"""

            key_path = event.key_path

            # 监听 OCR 引擎类型变更
            if key_path == "ocr.engine_type":
                new_engine_type = event.new_value
                logger.info(
                    f"检测到引擎配置变更: {event.old_value} -> {new_engine_type}"
                )

                # 尝试切换引擎
                if new_engine_type and new_engine_type in self._engine_registry:
                    success = self.switch_engine(new_engine_type)
                    if not success:
                        logger.error(f"引擎切换失败: {new_engine_type}")
                        # 发送失败信号
                        self.engine_failed.emit(
                            new_engine_type,
                            OCRErrorCode.ENGINE_INIT_FAILED.value,
                            f"无法切换到引擎: {new_engine_type}",
                        )

            # 监听引擎配置变更
            elif key_path.startswith("ocr."):
                parts = key_path.split(".")
                if len(parts) >= 2:
                    engine_type = parts[1]
                    if engine_type in self._engine_states:
                        # 更新引擎配置
                        config = _config_manager.get(f"ocr.{engine_type}", {})
                        state = self._engine_states[engine_type]
                        state.config = config

                        logger.info(f"引擎配置已更新: {engine_type}")

                        # 如果引擎已加载，应用新配置
                        if state.engine_instance:
                            for key, value in config.items():
                                state.engine_instance.set_config_value(key, value)

        # 添加监听器
        _config_manager.add_listener(on_config_changed)
        self._config_listener = on_config_changed

        logger.info("配置变更监听器已设置")

    def _initialize_default_engine(self) -> bool:
        """
        初始化默认引擎

        Returns:
            bool: 是否初始化成功
        """
        global _config_manager
        default_engine_type = "paddle"  # 默认使用 PaddleOCR

        # 从配置管理器读取默认引擎类型
        if _config_manager:
            default_engine_type = _config_manager.get("ocr.engine_type", "paddle")

        # 尝试切换到默认引擎
        if default_engine_type in self._engine_registry:
            success = self.switch_engine(default_engine_type)
            if success:
                logger.info(f"默认引擎初始化成功: {default_engine_type}")
                return True
            else:
                logger.warning(f"默认引擎初始化失败: {default_engine_type}，尝试回退")
                # 尝试回退到其他引擎
                return self._fallback_to_default_engine()
        else:
            logger.error(f"默认引擎未注册: {default_engine_type}")
            # 尝试回退到其他引擎
            return self._fallback_to_default_engine()

    # -------------------------------------------------------------------------
    # 工具方法
    # -------------------------------------------------------------------------

    def get_engine_state(self, engine_type: str) -> Optional[EngineState]:
        """
        获取引擎状态

        Args:
            engine_type: 引擎类型

        Returns:
            Optional[EngineState]: 引擎状态（不存在返回 None）
        """
        with self._state_lock:
            return self._engine_states.get(engine_type)

    @classmethod
    def get_instance(cls) -> "EngineManager":
        """
        获取引擎管理器单例

        Returns:
            EngineManager: 引擎管理器实例
        """
        return cls()


# =============================================================================
# 全局引擎管理器实例
# =============================================================================

_global_engine_manager: Optional[EngineManager] = None


def get_engine_manager() -> EngineManager:
    """
    获取全局引擎管理器

    Returns:
        EngineManager: 引擎管理器单例
    """
    global _global_engine_manager
    if _global_engine_manager is None:
        _global_engine_manager = EngineManager.get_instance()
    return _global_engine_manager
