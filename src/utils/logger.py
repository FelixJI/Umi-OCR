"""
Umi-OCR 日志系统

提供统一的日志记录功能，支持控制台和文件双输出、日志级别配置、日志文件自动轮转。

使用示例:
    from utils.logger import Logger

    # 获取全局日志记录器
    logger = Logger.get_instance()

    # 记录不同级别的日志
    logger.debug("调试信息")
    logger.info("普通信息")
    logger.warning("警告信息")
    logger.error("错误信息")
    logger.critical("严重错误信息")

    # 带异常信息的日志
    try:
        1 / 0
    except Exception:
        logger.error("发生错误", exc_info=True)
"""

import os
import sys
import json
import logging
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from logging import LogRecord
from typing import Optional, Dict, Any
from enum import Enum


class LogLevel(Enum):
    """日志级别枚举"""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    NONE = logging.CRITICAL + 10  # 表示不记录日志


class LogLevelFilter(logging.Filter):
    """
    日志级别过滤器

    根据配置的最低级别过滤日志消息，用于文件输出。
    """

    def __init__(self, min_level: int = logging.DEBUG):
        """
        初始化过滤器

        Args:
            min_level: 最低记录级别，低于此级别的日志将被过滤
        """
        super().__init__()
        self.min_level = min_level

    def filter(self, record: LogRecord) -> bool:
        """
        过滤日志记录

        Args:
            record: 日志记录对象

        Returns:
            bool: 是否记录该日志
        """
        return record.levelno >= self.min_level


class LevelFormatter(logging.Formatter):
    """
    自定义日志格式化器

    使用符号代替日志级别文字，使控制台输出更简洁。
    """

    # 日志级别符号映射
    LEVEL_SYMBOLS: Dict[str, str] = {
        "DEBUG": " ",
        "INFO": "√",
        "WARNING": "?",
        "ERROR": "×",
        "CRITICAL": "×××",
    }

    def format(self, record: LogRecord) -> str:
        """
        格式化日志记录

        Args:
            record: 日志记录对象

        Returns:
            str: 格式化后的日志字符串
        """
        level_name = record.levelname
        # 添加自定义的 level_symbol 属性
        record.level_symbol = self.LEVEL_SYMBOLS.get(level_name, level_name)
        return super().format(record)


class JsonRotatingFileHandler(RotatingFileHandler):
    """
    JSON 格式的轮转文件处理器

    将日志以 JSON 格式写入文件，每行一条日志记录。
    支持文件大小限制和备份轮转。
    """

    def __init__(self, filename: str, **kwargs):
        """
        初始化 JSON 文件处理器

        Args:
            filename: 日志文件路径
            **kwargs: 传递给 RotatingFileHandler 的其他参数
        """
        super().__init__(filename, **kwargs)

    def _record_to_dict(self, record: LogRecord) -> Dict[str, Any]:
        """
        将日志记录转换为字典

        Args:
            record: 日志记录对象

        Returns:
            Dict[str, Any]: 日志信息字典
        """
        dt_object = datetime.fromtimestamp(record.created)
        formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S.%f")

        return {
            "time": formatted_time,
            "level": record.levelname,
            "message": record.getMessage(),
            "filename": record.filename,
            "lineno": record.lineno,
            "module": record.module,
            "funcName": record.funcName,
            "exc_text": record.exc_text,
            "stack_info": record.stack_info,
            "thread": record.thread,
            "threadName": record.threadName,
            "process": record.process,
            "processName": record.processName,
            "name": record.name,
        }

    def emit(self, record: LogRecord) -> None:
        """
        发送日志记录到文件

        Args:
            record: 日志记录对象
        """
        try:
            # 检查是否需要轮转
            if self.shouldRollover(record):
                self.doRollover()

            # 转换为 JSON 并写入文件
            log_dict = self._record_to_dict(record)
            with open(self.baseFilename, "a", encoding=self.encoding) as f:
                json.dump(log_dict, f, ensure_ascii=False)
                f.write("\n")

            # 刷新缓冲区
            self.flush()

        except Exception:
            self.handleError(record)


class Logger:
    """
    日志管理器（单例模式）

    提供全局统一的日志记录功能，支持控制台和文件双输出。
    """

    _instance: Optional["Logger"] = None
    _lock = threading.Lock()

    # 日志目录
    LOGS_DIR = "./logs"

    # 单个日志文件最大大小 (10 MB)
    MAX_BYTES = 10 * 1024 * 1024

    # 保留的日志备份数量
    BACKUP_COUNT = 5

    # 控制台日志格式
    CONSOLE_FORMAT = (
        "%(asctime)s %(level_symbol)s %(name)s.%(funcName)s:%(lineno)d | %(message)s"
    )
    CONSOLE_DATE_FORMAT = "%H:%M:%S"

    def __new__(cls) -> "Logger":
        """
        实现单例模式

        Returns:
            Logger: 唯一的日志管理器实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        初始化日志管理器

        注意：由于单例模式，此方法只会被调用一次。
        """
        # 防止重复初始化
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._initialized = True

        # 日志目录（绝对路径）
        self.logs_dir = os.path.abspath(self.LOGS_DIR)

        # 确保日志目录存在
        os.makedirs(self.logs_dir, exist_ok=True)

        # 文件日志最低级别（可配置）
        self._file_log_level = logging.INFO

        # Qt 日志忽略列表
        self._qt_log_ignore_list = [
            "Retrying to obtain clipboard.",
            "Unable to obtain clipboard.",
        ]

        # 创建日志记录器
        self._logger = self._create_logger()

    def _create_logger(self) -> logging.Logger:
        """
        创建并配置日志记录器

        Returns:
            logging.Logger: 配置好的日志记录器
        """
        logger = logging.getLogger("Umi-OCR")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # 防止传递到父记录器

        # 清除已有的处理器（防止重复添加）
        logger.handlers.clear()

        # 添加控制台处理器
        console_handler = self._create_console_handler()
        logger.addHandler(console_handler)

        # 添加文件处理器
        file_handler = self._create_file_handler()
        logger.addHandler(file_handler)

        return logger

    def _create_console_handler(self) -> logging.StreamHandler:
        """
        创建控制台日志处理器

        Returns:
            logging.StreamHandler: 控制台处理器
        """
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)

        formatter = LevelFormatter(
            fmt=self.CONSOLE_FORMAT, datefmt=self.CONSOLE_DATE_FORMAT
        )
        console_handler.setFormatter(formatter)

        return console_handler

    def _create_file_handler(self) -> JsonRotatingFileHandler:
        """
        创建文件日志处理器

        Returns:
            JsonRotatingFileHandler: JSON 格式的文件处理器
        """
        # 获取当前日期作为日志文件名的一部分
        current_date = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.logs_dir, f"log_{current_date}.jsonl.txt")

        file_handler = JsonRotatingFileHandler(
            log_file,
            mode="a",
            maxBytes=self.MAX_BYTES,
            backupCount=self.BACKUP_COUNT,
            encoding="utf-8",
            delay=True,
        )

        # 添加级别过滤器
        file_handler.addFilter(LogLevelFilter(self._file_log_level))

        return file_handler

    def _refresh_file_handler(self) -> None:
        """重新创建文件处理器（用于更改配置后）"""
        # 移除旧的文件处理器
        for handler in self._logger.handlers[:]:
            if isinstance(handler, (JsonRotatingFileHandler, RotatingFileHandler)):
                self._logger.removeHandler(handler)

        # 添加新的文件处理器
        file_handler = self._create_file_handler()
        self._logger.addHandler(file_handler)

    # -------------------------------------------------------------------------
    # 公共 API
    # -------------------------------------------------------------------------

    def debug(self, message: str, *args, **kwargs) -> None:
        """记录 DEBUG 级别日志"""
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """记录 INFO 级别日志"""
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """记录 WARNING 级别日志"""
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """记录 ERROR 级别日志"""
        self._logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """记录 CRITICAL 级别日志"""
        self._logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        """记录异常信息（自动包含 exc_info）"""
        kwargs.setdefault("exc_info", True)
        self._logger.error(message, *args, **kwargs)

    # -------------------------------------------------------------------------
    # 配置方法
    # -------------------------------------------------------------------------

    def set_file_log_level(self, level_name: str) -> bool:
        """
        设置文件日志的最低记录级别

        Args:
            level_name: 日志级别名称 (DEBUG/INFO/WARNING/ERROR/CRITICAL/NONE)

        Returns:
            bool: 设置是否成功
        """
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
            "NONE": logging.CRITICAL + 10,
        }

        if level_name not in level_map:
            self.error(f"无效的日志级别: {level_name}")
            return False

        self._file_log_level = level_map[level_name]
        self._refresh_file_handler()

        self.info(f"文件日志级别已设置为: {level_name}")
        return True

    def get_file_log_level(self) -> str:
        """
        获取当前文件日志的最低记录级别

        Returns:
            str: 日志级别名称
        """
        level_map = {
            logging.DEBUG: "DEBUG",
            logging.INFO: "INFO",
            logging.WARNING: "WARNING",
            logging.ERROR: "ERROR",
            logging.CRITICAL: "CRITICAL",
            logging.CRITICAL + 10: "NONE",
        }
        return level_map.get(self._file_log_level, "INFO")

    # -------------------------------------------------------------------------
    # Qt 日志集成
    # -------------------------------------------------------------------------

    def get_qt_message_handler(self):
        """
        获取 Qt 消息处理器，用于将 Qt/QML 日志重定向到日志系统

        Returns:
            Callable: Qt 消息处理函数

        使用示例:
            from PySide6.QtCore import qInstallMessageHandler
            logger = Logger.get_instance()
            qInstallMessageHandler(logger.get_qt_message_handler())
        """
        from PySide6.QtCore import QtMsgType, QMessageLogContext

        def qt_message_handler(mode: QtMsgType, context: QMessageLogContext, msg: str):
            """处理 Qt 框架抛出的日志"""
            try:
                # 忽略指定的日志消息
                if msg in self._qt_log_ignore_list:
                    return

                # 提取上下文信息
                filepath = getattr(context, "file", "") or ""
                filename = os.path.basename(filepath) if filepath else "?"
                func_name = getattr(context, "function", "") or r"()=>{}"

                # 构建额外的日志属性
                extra = {
                    "cover": {
                        "filename": filename,
                        "funcName": func_name,
                        "lineno": getattr(context, "line", "?"),
                        "category": getattr(context, "category", "?"),
                        "module": "qml",
                    }
                }

                # 根据 Qt 消息类型记录对应级别的日志
                if mode == QtMsgType.QtDebugMsg:
                    self.debug(msg, extra=extra)
                elif mode == QtMsgType.QtInfoMsg:
                    self.info(msg, extra=extra)
                elif mode == QtMsgType.QtWarningMsg:
                    self.warning(msg, extra=extra)
                elif mode == QtMsgType.QtCriticalMsg:
                    self.error(msg, extra=extra)
                elif mode == QtMsgType.QtFatalMsg:
                    self.critical(msg, extra=extra)

            except Exception:
                self.error("Qt 消息处理器错误", exc_info=True, stack_info=True)

        return qt_message_handler

    # -------------------------------------------------------------------------
    # 工具方法
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "Logger":
        """
        获取日志管理器单例

        Returns:
            Logger: 日志管理器实例
        """
        return cls()

    def get_logs_dir(self) -> str:
        """
        获取日志目录路径

        Returns:
            str: 日志目录的绝对路径
        """
        return self.logs_dir

    def open_logs_dir(self) -> None:
        """打开日志目录（在文件管理器中显示）"""
        if os.name == "nt":  # Windows
            os.startfile(self.logs_dir)
        elif os.name == "posix":  # macOS / Linux
            import subprocess

            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.run([opener, self.logs_dir])


# 全局日志记录器实例，供模块直接导入使用
_global_logger: Optional[Logger] = None


def get_logger() -> Logger:
    """
    获取全局日志记录器

    Returns:
        Logger: 日志记录器单例

    使用示例:
        from utils.logger import get_logger
        logger = get_logger()
        logger.info("Hello, World!")
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger.get_instance()
    return _global_logger


# 默认导出的 logger 实例
logger = get_logger()
