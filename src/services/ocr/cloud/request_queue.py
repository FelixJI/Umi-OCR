#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 云 OCR 请求队列

实现 QPS 控制的请求队列，避免触发云端限流。

主要功能:
- 滑动窗口限流算法
- 异步请求队列
- 并发控制
- 请求统计和监控

Author: Umi-OCR Team
Date: 2026-01-27
"""

import asyncio
import time
from typing import Callable, Any, Dict, List, Optional
from collections import deque
import threading

from PySide6.QtCore import QObject, Signal


# =============================================================================
# 请求队列异常
# =============================================================================

class RequestQueueError(Exception):
    """请求队列异常"""
    pass

class RateLimitExceeded(RequestQueueError):
    """请求频率超限异常"""
    pass

class QueueShutdown(RequestQueueError):
    """队列已关闭异常"""
    pass


# =============================================================================
# 请求队列实现
# =============================================================================

class RequestQueue(QObject):
    """
    请求队列（QPS 控制）

    使用滑动窗口算法实现 QPS 限制：
    - 维护最近 N 秒内的请求时间戳
    - 新请求前检查窗口内请求数是否超过 QPS 限制
    - 超限时等待或拒绝

    特性：
    - 线程安全
    - 异步支持
    - 请求统计
    - 动态 QPS 调整
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    # 请求完成信号
    # 参数: duration (float), success (bool)
    request_completed = Signal(float, bool)

    # 队列状态变更信号
    # 参数: queue_size (int), rate_limited (bool)
    queue_status_changed = Signal(int, bool)

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self, qps_limit: int = 10, window_size: float = 1.0):
        """
        初始化请求队列

        Args:
            qps_limit: 每秒最大请求数（QPS限制）
            window_size: 滑动窗口大小（秒），默认1秒
        """
        super().__init__()

        # 配置
        self._qps_limit = qps_limit
        self._window_size = window_size

        # 滑动窗口（存储最近请求时间戳）
        self._request_window: deque = deque()

        # 异步队列和事件循环
        self._queue: asyncio.Queue = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._running: bool = False

        # 线程安全锁
        self._lock = threading.RLock()

        # 统计信息
        self._total_requests: int = 0
        self._successful_requests: int = 0
        self._failed_requests: int = 0
        self._total_duration: float = 0.0

    # -------------------------------------------------------------------------
    # 生命周期管理
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """
        启动请求队列

        创建异步事件循环和队列处理线程
        """
        with self._lock:
            if self._running:
                return

            self._running = True

            # 创建异步队列
            self._queue = asyncio.Queue()

            # 创建并启动事件循环线程
            self._event_loop = asyncio.new_event_loop()

            def run_loop():
                """运行事件循环"""
                asyncio.set_event_loop(self._event_loop)
                self._event_loop.run_forever()

            self._loop_thread = threading.Thread(target=run_loop, daemon=True)
            self._loop_thread.start()

    def stop(self) -> None:
        """
        停止请求队列

        关闭事件循环，清理资源
        """
        with self._lock:
            if not self._running:
                return

            self._running = False

            # 停止事件循环
            if self._event_loop and self._event_loop.is_running():
                self._event_loop.call_soon_threadsafe(self._event_loop.stop)

            # 等待线程结束
            if self._loop_thread and self._loop_thread.is_alive():
                self._loop_thread.join(timeout=5.0)

            self._event_loop = None

    # -------------------------------------------------------------------------
    # 请求提交
    # -------------------------------------------------------------------------

    async def enqueue(self, request_func: Callable) -> Any:
        """
        请求入队，按 QPS 限制依次执行

        Args:
            request_func: 请求函数（协程或普通函数）

        Returns:
            Any: 请求函数的返回值

        Raises:
            QueueShutdown: 队列已关闭
            Exception: 请求函数抛出的异常
        """
        if not self._running:
            raise QueueShutdown("请求队列已关闭，无法接受新请求")

        # 等待 QPS 限制
        await self._wait_for_rate_limit()

        # 提交到队列
        try:
            # 记录开始时间
            start_time = time.time()

            # 执行请求
            if asyncio.iscoroutinefunction(request_func):
                result = await request_func()
            else:
                result = request_func()

            # 记录完成时间
            duration = time.time() - start_time

            # 更新滑动窗口
            self._add_request_to_window()

            # 更新统计
            with self._lock:
                self._total_requests += 1
                self._successful_requests += 1
                self._total_duration += duration

            # 发送信号
            self.request_completed.emit(duration, True)

            return result

        except Exception as e:
            # 记录失败
            with self._lock:
                self._total_requests += 1
                self._failed_requests += 1

            # 发送信号
            self.request_completed.emit(0.0, False)

            raise e

    # -------------------------------------------------------------------------
    # QPS 控制（滑动窗口算法）
    # -------------------------------------------------------------------------

    async def _wait_for_rate_limit(self) -> None:
        """
        等待 QPS 限制

        检查滑动窗口内的请求数，如果超过 QPS 限制则等待
        """
        while True:
            # 获取当前窗口内的请求数
            request_count = self._get_window_request_count()

            # 检查是否超过限制
            if request_count < self._qps_limit:
                break

            # 超过限制，计算等待时间
            with self._lock:
                if not self._request_window:
                    break

                # 获取最旧的请求时间戳
                oldest_time = self._request_window[0]

                # 计算需要等待的时间（最旧请求过期时间 - 当前时间）
                wait_time = oldest_time + self._window_size - time.time()

                if wait_time <= 0:
                    # 窗口已刷新，重试
                    break

            # 发送状态信号
            self.queue_status_changed.emit(self._queue.qsize(), True)

            # 等待
            await asyncio.sleep(wait_time)

        # 发送状态信号
        self.queue_status_changed.emit(self._queue.qsize(), False)

    def _add_request_to_window(self) -> None:
        """
        添加请求到滑动窗口

        清理过期的请求，添加新请求时间戳
        """
        current_time = time.time()

        with self._lock:
            # 清理过期请求（超出窗口大小）
            while self._request_window:
                oldest = self._request_window[0]
                if current_time - oldest > self._window_size:
                    self._request_window.popleft()
                else:
                    break

            # 添加新请求
            self._request_window.append(current_time)

    def _get_window_request_count(self) -> int:
        """
        获取当前窗口内的请求数

        Returns:
            int: 当前请求数
        """
        with self._lock:
            return len(self._request_window)

    # -------------------------------------------------------------------------
    # 配置管理
    # -------------------------------------------------------------------------

    def set_qps_limit(self, qps: int) -> None:
        """
        设置 QPS 限制

        Args:
            qps: 新的 QPS 限制值
        """
        with self._lock:
            self._qps_limit = qps

    def set_window_size(self, size: float) -> None:
        """
        设置滑动窗口大小

        Args:
            size: 窗口大小（秒）
        """
        with self._lock:
            self._window_size = size

            # 清理超出新窗口的请求
            current_time = time.time()
            while self._request_window:
                oldest = self._request_window[0]
                if current_time - oldest > size:
                    self._request_window.popleft()
                else:
                    break

    def get_qps_limit(self) -> int:
        """获取当前 QPS 限制"""
        with self._lock:
            return self._qps_limit

    # -------------------------------------------------------------------------
    # 统计信息
    # -------------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取请求统计信息

        Returns:
            Dict: 统计信息字典
        """
        with self._lock:
            success_rate = 0.0
            if self._total_requests > 0:
                success_rate = self._successful_requests / self._total_requests

            avg_duration = 0.0
            if self._successful_requests > 0:
                avg_duration = self._total_duration / self._successful_requests

            return {
                "total_requests": self._total_requests,
                "successful_requests": self._successful_requests,
                "failed_requests": self._failed_requests,
                "success_rate": success_rate,
                "total_duration": self._total_duration,
                "average_duration": avg_duration,
                "qps_limit": self._qps_limit,
                "window_size": self._window_size,
                "current_requests_in_window": len(self._request_window)
            }

    def reset_statistics(self) -> None:
        """重置统计信息"""
        with self._lock:
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._total_duration = 0.0


# =============================================================================
# 日志记录器
# =============================================================================

import logging
logger = logging.getLogger(__name__)
