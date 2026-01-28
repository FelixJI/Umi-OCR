"""
日志系统单元测试

测试 Logger 类的各项功能，包括：
- 基本日志记录
- 日志级别配置
- 文件日志输出
- 日志文件轮转
- 单例模式
"""

import os
import sys
import json
import unittest
import logging
import tempfile
import time
import gc
from unittest.mock import patch, MagicMock

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.logger import (
    Logger,
    get_logger,
    LogLevel,
    LogLevelFilter,
    JsonRotatingFileHandler,
    LevelFormatter,
)


class TestLogLevelEnum(unittest.TestCase):
    """测试日志级别枚举"""

    def test_log_level_values(self):
        """测试日志级别值对应正确"""
        self.assertEqual(LogLevel.DEBUG.value, logging.DEBUG)
        self.assertEqual(LogLevel.INFO.value, logging.INFO)
        self.assertEqual(LogLevel.WARNING.value, logging.WARNING)
        self.assertEqual(LogLevel.ERROR.value, logging.ERROR)
        self.assertEqual(LogLevel.CRITICAL.value, logging.CRITICAL)
        self.assertEqual(LogLevel.NONE.value, logging.CRITICAL + 10)


class TestLogLevelFilter(unittest.TestCase):
    """测试日志级别过滤器"""

    def test_filter_pass(self):
        """测试允许通过的日志级别"""
        filter_obj = LogLevelFilter(min_level=logging.WARNING)

        # 创建 mock 日志记录
        debug_record = MagicMock()
        debug_record.levelno = logging.DEBUG

        info_record = MagicMock()
        info_record.levelno = logging.INFO

        warning_record = MagicMock()
        warning_record.levelno = logging.WARNING

        error_record = MagicMock()
        error_record.levelno = logging.ERROR

        # 测试过滤
        self.assertFalse(filter_obj.filter(debug_record))
        self.assertFalse(filter_obj.filter(info_record))
        self.assertTrue(filter_obj.filter(warning_record))
        self.assertTrue(filter_obj.filter(error_record))


class TestLevelFormatter(unittest.TestCase):
    """测试自定义日志格式化器"""

    def test_format(self):
        """测试格式化输出"""
        formatter = LevelFormatter("%(level_symbol)s %(message)s")

        # 使用真实 logger 创建日志记录
        logger = logging.getLogger("test_formatter")
        record = logger.makeRecord(
            name="test_formatter",
            level=logging.INFO,
            fn="test.py",
            lno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        self.assertIn("√", formatted)
        self.assertIn("Test message", formatted)

    def test_level_symbols(self):
        """测试各级别符号映射"""
        expected_symbols = {
            "DEBUG": " ",
            "INFO": "√",
            "WARNING": "?",
            "ERROR": "×",
            "CRITICAL": "×××",
        }

        self.assertEqual(LevelFormatter.LEVEL_SYMBOLS, expected_symbols)


class TestJsonRotatingFileHandler(unittest.TestCase):
    """测试 JSON 文件处理器"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.handlers = []

    def tearDown(self):
        """清理测试环境"""
        # 关闭所有处理器
        for handler in self.handlers:
            try:
                handler.close()
            except Exception:
                pass

        # 强制垃圾回收
        gc.collect()

        # 等待一小段时间确保文件释放
        time.sleep(0.1)

        # 删除临时目录
        if os.path.exists(self.temp_dir):
            try:
                shutil = __import__("shutil")
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

    def test_record_to_dict(self):
        """测试日志记录转字典"""
        handler = JsonRotatingFileHandler(self.log_file)
        self.handlers.append(handler)

        # 创建测试日志记录
        logger = logging.getLogger("test_record_dict")
        logger.setLevel(logging.DEBUG)

        record = logger.makeRecord(
            name="test",
            level=logging.INFO,
            fn="test_file.py",
            lno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        log_dict = handler._record_to_dict(record)

        # 验证字典内容
        self.assertEqual(log_dict["level"], "INFO")
        self.assertEqual(log_dict["message"], "Test message")
        self.assertEqual(log_dict["filename"], "test_file.py")
        self.assertEqual(log_dict["lineno"], 42)
        self.assertIn("time", log_dict)

    def test_emit_creates_file(self):
        """测试 emit 方法创建日志文件"""
        handler = JsonRotatingFileHandler(self.log_file)
        self.handlers.append(handler)

        logger = logging.getLogger("test_emit_create")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # 记录一条日志
        logger.info("Test message")

        # 验证文件创建
        self.assertTrue(os.path.exists(self.log_file))

        # 读取并验证内容
        with open(self.log_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            log_dict = json.loads(content)
            self.assertEqual(log_dict["message"], "Test message")
            self.assertEqual(log_dict["level"], "INFO")

        # 清理 logger
        logger.removeHandler(handler)

    def test_emit_multiple_records(self):
        """测试写入多条日志"""
        handler = JsonRotatingFileHandler(self.log_file)
        self.handlers.append(handler)

        logger = logging.getLogger("test_multi")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # 记录多条日志
        messages = ["Message 1", "Message 2", "Message 3"]
        for msg in messages:
            logger.info(msg)

        # 读取并验证
        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 3)

        for i, line in enumerate(lines):
            log_dict = json.loads(line.strip())
            self.assertEqual(log_dict["message"], messages[i])

        # 清理 logger
        logger.removeHandler(handler)


class TestLoggerSingleton(unittest.TestCase):
    """测试 Logger 单例模式"""

    def test_singleton(self):
        """测试多次获取返回同一实例"""
        logger1 = Logger()
        logger2 = Logger.get_instance()
        logger3 = get_logger()

        self.assertIs(logger1, logger2)
        self.assertIs(logger2, logger3)

    def test_double_init_prevention(self):
        """测试防止重复初始化"""
        logger1 = Logger()
        logger2 = Logger()

        # 确保是同一个实例
        self.assertIs(logger1, logger2)

        # 确保只初始化一次
        self.assertTrue(hasattr(logger1, "_initialized"))
        self.assertTrue(logger1._initialized)


class TestLoggerBasicLogging(unittest.TestCase):
    """测试 Logger 基本日志功能"""

    def setUp(self):
        """设置测试环境"""
        # 使用临时目录
        self.temp_dir = tempfile.mkdtemp()

        # 修改日志目录
        Logger.LOGS_DIR = self.temp_dir

        # 重置单例以便重新初始化
        Logger._instance = None

    def tearDown(self):
        """清理测试环境"""
        # 关闭所有 handlers
        if Logger._instance is not None:
            for handler in Logger._instance._logger.handlers[:]:
                try:
                    handler.close()
                except Exception:
                    pass
            Logger._instance._logger.handlers.clear()

        # 强制垃圾回收
        gc.collect()
        time.sleep(0.1)

        # 删除临时目录
        if os.path.exists(self.temp_dir):
            try:
                shutil = __import__("shutil")
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

        # 恢复默认值
        Logger.LOGS_DIR = "./logs"
        Logger._instance = None

    def test_log_methods(self):
        """测试各级别日志方法"""
        logger = Logger()

        # 这些方法不应抛出异常
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

    def test_log_with_exception(self):
        """测试带异常信息的日志"""
        logger = Logger()

        try:
            1 / 0
        except ZeroDivisionError:
            # 不应抛出异常
            logger.exception("Division by zero occurred")

    def test_log_dir_created(self):
        """测试日志目录自动创建"""
        logger = Logger()

        self.assertTrue(os.path.exists(logger.get_logs_dir()))


class TestLoggerConfiguration(unittest.TestCase):
    """测试 Logger 配置功能"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        Logger.LOGS_DIR = self.temp_dir
        Logger._instance = None

    def tearDown(self):
        """清理测试环境"""
        # 关闭所有 handlers
        if Logger._instance is not None:
            for handler in Logger._instance._logger.handlers[:]:
                try:
                    handler.close()
                except Exception:
                    pass
            Logger._instance._logger.handlers.clear()

        gc.collect()
        time.sleep(0.1)

        # 删除临时目录
        if os.path.exists(self.temp_dir):
            try:
                shutil = __import__("shutil")
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

        Logger.LOGS_DIR = "./logs"
        Logger._instance = None

    def test_set_file_log_level(self):
        """测试设置文件日志级别"""
        logger = Logger()

        # 测试设置各个级别
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NONE"]
        for level in levels:
            result = logger.set_file_log_level(level)
            self.assertTrue(result, f"设置 {level} 级别失败")
            self.assertEqual(logger.get_file_log_level(), level)

    def test_set_invalid_file_log_level(self):
        """测试设置无效的日志级别"""
        logger = Logger()

        result = logger.set_file_log_level("INVALID")
        self.assertFalse(result)

    def test_get_file_log_level(self):
        """测试获取文件日志级别"""
        logger = Logger()

        # 默认应该是 INFO
        self.assertEqual(logger.get_file_log_level(), "INFO")

        logger.set_file_log_level("ERROR")
        self.assertEqual(logger.get_file_log_level(), "ERROR")


class TestLoggerUtilities(unittest.TestCase):
    """测试 Logger 工具方法"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        Logger.LOGS_DIR = self.temp_dir
        Logger._instance = None

    def tearDown(self):
        """清理测试环境"""
        # 关闭所有 handlers
        if Logger._instance is not None:
            for handler in Logger._instance._logger.handlers[:]:
                try:
                    handler.close()
                except Exception:
                    pass
            Logger._instance._logger.handlers.clear()

        gc.collect()
        time.sleep(0.1)

        # 删除临时目录
        if os.path.exists(self.temp_dir):
            try:
                shutil = __import__("shutil")
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

        Logger.LOGS_DIR = "./logs"
        Logger._instance = None

    def test_get_logs_dir(self):
        """测试获取日志目录"""
        logger = Logger()

        logs_dir = logger.get_logs_dir()

        self.assertTrue(os.path.isabs(logs_dir))
        # 检查日志目录路径正确
        self.assertIn(self.temp_dir.replace("\\", "/").replace("/", os.sep), logs_dir)

    @patch("os.startfile")
    def test_open_logs_dir_windows(self, mock_startfile):
        """测试打开日志目录（Windows）"""
        logger = Logger()

        with patch.object(os, "name", "nt"):
            logger.open_logs_dir()
            mock_startfile.assert_called_once()


class TestGetLoggerFunction(unittest.TestCase):
    """测试 get_logger 函数"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        Logger.LOGS_DIR = self.temp_dir
        Logger._instance = None

    def tearDown(self):
        """清理测试环境"""
        # 关闭所有 handlers
        if Logger._instance is not None:
            for handler in Logger._instance._logger.handlers[:]:
                try:
                    handler.close()
                except Exception:
                    pass
            Logger._instance._logger.handlers.clear()

        gc.collect()
        time.sleep(0.1)

        # 删除临时目录
        if os.path.exists(self.temp_dir):
            try:
                shutil = __import__("shutil")
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

        Logger.LOGS_DIR = "./logs"
        Logger._instance = None

    def test_get_logger_returns_singleton(self):
        """测试 get_logger 返回单例"""
        logger1 = get_logger()
        logger2 = get_logger()

        self.assertIs(logger1, logger2)
        self.assertIsInstance(logger1, Logger)


class TestQtMessageHandler(unittest.TestCase):
    """测试 Qt 消息处理器"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        Logger.LOGS_DIR = self.temp_dir
        Logger._instance = None

    def tearDown(self):
        """清理测试环境"""
        # 关闭所有 handlers
        if Logger._instance is not None:
            for handler in Logger._instance._logger.handlers[:]:
                try:
                    handler.close()
                except Exception:
                    pass
            Logger._instance._logger.handlers.clear()

        gc.collect()
        time.sleep(0.1)

        # 删除临时目录
        if os.path.exists(self.temp_dir):
            try:
                shutil = __import__("shutil")
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

        Logger.LOGS_DIR = "./logs"
        Logger._instance = None

    @unittest.skip("需要 PySide6 环境")
    def test_qt_message_handler_filters_ignored(self):
        """测试 Qt 消息处理器过滤忽略列表"""
        # 此测试需要 PySide6 环境，在实际运行环境中执行
        pass


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestLogLevelEnum))
    suite.addTests(loader.loadTestsFromTestCase(TestLogLevelFilter))
    suite.addTests(loader.loadTestsFromTestCase(TestLevelFormatter))
    suite.addTests(loader.loadTestsFromTestCase(TestJsonRotatingFileHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestLoggerSingleton))
    suite.addTests(loader.loadTestsFromTestCase(TestLoggerBasicLogging))
    suite.addTests(loader.loadTestsFromTestCase(TestLoggerConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestLoggerUtilities))
    suite.addTests(loader.loadTestsFromTestCase(TestGetLoggerFunction))
    suite.addTests(loader.loadTestsFromTestCase(TestQtMessageHandler))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回测试是否全部通过
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
