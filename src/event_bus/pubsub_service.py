#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件总线服务 - 简化版

提供发布/订阅模式用于组件间通信。

Author: Umi-OCR Team
Date: 2026-01-28
"""

from typing import Dict, List, Callable, Any
from PySide6.QtCore import QObject, Signal


class PubSubService(QObject):
    """
    发布/订阅服务

    简化的事件总线，用于组件间解耦通信。
    """

    # 信号
    event_published = Signal(str, object)  # 事件名称, 数据

    # 类变量：订阅者字典
    _subscribers: Dict[str, List[Callable]] = {}

    def __init__(self, parent=None):
        super().__init__(parent)

    @classmethod
    def publish(cls, event_name: str, data: Any = None) -> None:
        """
        发布事件

        Args:
            event_name: 事件名称
            data: 事件数据
        """
        # 获取该事件的订阅者
        subscribers = cls._subscribers.get(event_name, [])

        # 通知所有订阅者
        for callback in subscribers:
            try:
                if data is None:
                    callback()
                else:
                    callback(data)
            except Exception as e:
                print(f"[PubSubService] 通知订阅者失败: {event_name}, {e}")

        # 发射 Qt 信号（用于 QML）
        cls.event_published.emit(event_name, data)

    @classmethod
    def subscribe(cls, event_name: str, callback: Callable) -> None:
        """
        订阅事件

        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name not in cls._subscribers:
            cls._subscribers[event_name] = []

        cls._subscribers[event_name].append(callback)

    @classmethod
    def unsubscribe(cls, event_name: str, callback: Callable) -> None:
        """
        取消订阅事件

        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name in cls._subscribers:
            if callback in cls._subscribers[event_name]:
                cls._subscribers[event_name].remove(callback)

    @classmethod
    def clear_all(cls) -> None:
        """清除所有订阅"""
        cls._subscribers.clear()


# 创建全局实例
_pubsub_instance = None


def get_pubsub_instance() -> PubSubService:
    """获取 PubSubService 单例"""
    global _pubsub_instance
    if _pubsub_instance is None:
        _pubsub_instance = PubSubService()
    return _pubsub_instance
