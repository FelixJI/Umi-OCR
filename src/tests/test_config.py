#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置系统单元测试

测试配置模型和配置管理器的功能。

Author: Umi-OCR Team
Date: 2025-01-25
"""

import unittest
import json
import tempfile
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QObject, Signal

from src.models.config_model import (
    AppConfig,
    OcrConfig,
    PaddleEngineConfig,
    BaiduOcrConfig,
    OcrEngineType,
    OutputFormat,
    LogLevel,
    ConfigChangeEvent,
)
from src.utils.config_manager import ConfigManager, get_config_manager


class TestConfigModel(unittest.TestCase):
    """测试配置数据模型"""

    def test_default_config(self):
        """测试默认配置"""
        config = AppConfig()

        self.assertEqual(config.version, "2.0.0")
        self.assertEqual(config.ocr.engine_type, OcrEngineType.PADDLE.value)
        self.assertEqual(config.ui.language, "zh_CN")
        self.assertEqual(config.system.log_level, LogLevel.INFO.value)
        self.assertEqual(config.hotkeys.screenshot, "Ctrl+Shift+A")

    def test_config_to_dict(self):
        """测试配置转字典"""
        config = AppConfig()
        data = config.to_dict()

        self.assertIsInstance(data, dict)
        self.assertIn("version", data)
        self.assertIn("ocr", data)
        self.assertIn("ui", data)
        self.assertIn("hotkeys", data)
        self.assertIn("export", data)
        self.assertIn("task", data)
        self.assertIn("system", data)

    def test_config_from_dict(self):
        """测试从字典创建配置"""
        data = {
            "version": "2.0.0",
            "ocr": {
                "engine_type": "baidu",
                "paddle": {"use_gpu": True},
                "baidu": {"api_key": "test_key"},
                "tencent": {},
                "aliyun": {},
                "preprocessing": {}
            },
            "ui": {
                "language": "en_US",
                "main_window": {"width": 1200},
                "theme": {"mode": "dark"}
            },
            "hotkeys": {},
            "export": {},
            "task": {},
            "system": {},
            "extra": {}
        }

        config = AppConfig.from_dict(data)

        self.assertEqual(config.ocr.engine_type, "baidu")
        self.assertEqual(config.ocr.paddle.use_gpu, True)
        self.assertEqual(config.ocr.baidu.api_key, "test_key")
        self.assertEqual(config.ui.language, "en_US")
        self.assertEqual(config.ui.main_window.width, 1200)
        self.assertEqual(config.ui.theme.mode, "dark")

    def test_config_get(self):
        """测试获取配置值"""
        config = AppConfig()

        # 获取简单值
        self.assertEqual(config.get("ocr.engine_type"), "paddle")

        # 获取嵌套值
        self.assertEqual(config.get("ui.main_window.width"), 1000)
        self.assertEqual(config.get("ui.theme.mode"), "light")

        # 使用默认值
        self.assertIsNone(config.get("nonexistent.key"))
        self.assertEqual(config.get("nonexistent.key", "default"), "default")

    def test_config_set(self):
        """测试设置配置值"""
        config = AppConfig()

        # 设置简单值
        self.assertTrue(config.set("ocr.engine_type", "baidu"))
        self.assertEqual(config.ocr.engine_type, "baidu")

        # 设置嵌套值
        self.assertTrue(config.set("ui.main_window.width", 1200))
        self.assertEqual(config.ui.main_window.width, 1200)

        # 设置不存在的键
        self.assertFalse(config.set("nonexistent.key", "value"))

    def test_config_validate(self):
        """测试配置验证"""
        config = AppConfig()

        # 默认配置应该有效
        errors = config.validate()
        self.assertEqual(len(errors), 0)

        # 无效的引擎类型
        config.ocr.engine_type = "invalid"
        errors = config.validate()
        self.assertGreater(len(errors), 0)
        self.assertIn("引擎类型", errors[0])

        # 恢复有效值
        config.ocr.engine_type = OcrEngineType.PADDLE.value

        # 无效的端口号
        config.system.http_server_port = 99999
        errors = config.validate()
        self.assertGreater(len(errors), 0)

        # 无效的并发数
        config.system.http_server_port = 1224
        config.task.max_workers = -1
        errors = config.validate()
        self.assertGreater(len(errors), 0)

    def test_paddle_config(self):
        """测试 PaddleOCR 配置"""
        config = PaddleEngineConfig()

        self.assertEqual(config.det_model_name, "ch_PP-OCRv4_det")
        self.assertEqual(config.rec_model_name, "ch_PP-OCRv4_rec")
        self.assertTrue(config.use_angle_cls)
        self.assertFalse(config.use_gpu)
        self.assertEqual(config.cpu_threads, 4)

    def test_cloud_config(self):
        """测试云 OCR 配置"""
        config = BaiduOcrConfig()

        self.assertEqual(config.api_key, "")
        self.assertEqual(config.secret_key, "")
        self.assertEqual(config.timeout, 30)
        self.assertEqual(config.max_retry, 3)
        self.assertEqual(config.token_cache_duration, 2592000)


class TestConfigManager(unittest.TestCase):
    """测试配置管理器"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 创建 QApplication 实例（PySide6 需要）
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])
        else:
            cls.app = QCoreApplication.instance()

    def setUp(self):
        """每个测试前的设置"""
        # 创建临时配置文件
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8"
        )
        self.temp_path = Path(self.temp_file.name)
        self.temp_file.close()

        # 创建新的配置管理器实例
        self.manager = ConfigManager.get_instance()
        self.manager.set_config_path(self.temp_path)

    def tearDown(self):
        """每个测试后的清理"""
        # 删除临时文件
        if self.temp_path.exists():
            self.temp_path.unlink()

        # 重置配置管理器状态
        self.manager.reset()

    def test_singleton(self):
        """测试单例模式"""
        manager1 = ConfigManager.get_instance()
        manager2 = ConfigManager()

        self.assertIs(manager1, manager2)

    def test_load_default_config(self):
        """测试加载默认配置（文件不存在）"""
        # 确保文件不存在
        if self.temp_path.exists():
            self.temp_path.unlink()

        # 加载配置（应该创建默认配置文件）
        self.assertTrue(self.manager.load())

        # 检查配置值
        self.assertEqual(self.manager.get("ocr.engine_type"), "paddle")
        self.assertEqual(self.manager.get("ui.language"), "zh_CN")

        # 检查文件是否被创建
        self.assertTrue(self.temp_path.exists())

    def test_load_from_file(self):
        """测试从文件加载配置"""
        # 写入测试配置
        test_config = {
            "version": "2.0.0",
            "ocr": {
                "engine_type": "baidu",
                "paddle": {},
                "baidu": {},
                "tencent": {},
                "aliyun": {},
                "preprocessing": {}
            },
            "ui": {"language": "en_US", "main_window": {}, "theme": {}},
            "hotkeys": {},
            "export": {},
            "task": {},
            "system": {},
            "extra": {}
        }

        with open(self.temp_path, "w", encoding="utf-8") as f:
            json.dump(test_config, f)

        # 加载配置
        self.assertTrue(self.manager.load())

        # 验证加载的值
        self.assertEqual(self.manager.get("ocr.engine_type"), "baidu")
        self.assertEqual(self.manager.get("ui.language"), "en_US")

    def test_save_config(self):
        """测试保存配置"""
        # 修改配置
        self.manager.set("ocr.engine_type", "baidu")
        self.manager.set("ui.language", "en_US")

        # 保存配置
        self.assertTrue(self.manager.save())

        # 读取文件验证
        with open(self.temp_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["ocr"]["engine_type"], "baidu")
        self.assertEqual(data["ui"]["language"], "en_US")

    def test_get_config(self):
        """测试获取配置值"""
        # 获取存在的值
        self.assertEqual(self.manager.get("ocr.engine_type"), "paddle")

        # 获取嵌套值
        self.assertEqual(self.manager.get("ui.main_window.width"), 1000)

        # 获取不存在的值
        self.assertIsNone(self.manager.get("nonexistent.key"))

        # 使用默认值
        self.assertEqual(self.manager.get("nonexistent.key", "default"), "default")

    def test_set_config(self):
        """测试设置配置值"""
        # 设置值
        self.assertTrue(self.manager.set("ocr.engine_type", "baidu"))

        # 验证值已改变
        self.assertEqual(self.manager.get("ocr.engine_type"), "baidu")

        # 设置相同值（应该不触发变更）
        self.assertTrue(self.manager.set("ocr.engine_type", "baidu"))

    def test_config_signal(self):
        """测试配置变更信号"""
        # 创建信号收集器
        changes = []

        class SignalCollector(QObject):
            def __init__(self):
                super().__init__()
                self.changes = []

            def on_config_changed(self, key, old, new):
                self.changes.append((key, old, new))

        collector = SignalCollector()
        collector.on_config_changed = lambda k, o, n: changes.append((k, o, n))

        # 连接信号
        self.manager.config_changed.connect(collector.on_config_changed)

        # 修改配置
        self.manager.set("ocr.engine_type", "baidu")

        # 验证信号
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0][0], "ocr.engine_type")
        self.assertEqual(changes[0][1], "paddle")
        self.assertEqual(changes[0][2], "baidu")

    def test_config_listener(self):
        """测试配置变更监听器"""
        events = []

        def listener(event):
            events.append(event)

        # 添加监听器
        self.manager.add_listener(listener)

        # 修改配置
        self.manager.set("ocr.engine_type", "baidu")

        # 验证监听器被调用
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], ConfigChangeEvent)
        self.assertEqual(events[0].key_path, "ocr.engine_type")
        self.assertEqual(events[0].source, "user")

        # 移除监听器
        self.manager.remove_listener(listener)
        events.clear()

        # 再次修改
        self.manager.set("ocr.engine_type", "tencent")

        # 验证监听器不再被调用
        self.assertEqual(len(events), 0)

    def test_reset_config(self):
        """测试重置配置"""
        # 修改配置
        self.manager.set("ocr.engine_type", "baidu")
        self.manager.set("ui.language", "en_US")

        # 重置配置
        self.manager.reset()

        # 验证恢复默认值
        self.assertEqual(self.manager.get("ocr.engine_type"), "paddle")
        self.assertEqual(self.manager.get("ui.language"), "zh_CN")

    def test_reset_section(self):
        """测试重置配置节"""
        # 修改多个配置
        self.manager.set("ocr.engine_type", "baidu")
        self.manager.set("ui.language", "en_US")

        # 只重置 ocr 配置
        self.assertTrue(self.manager.reset_section("ocr"))

        # 验证只有 ocr 配置被重置
        self.assertEqual(self.manager.get("ocr.engine_type"), "paddle")
        self.assertEqual(self.manager.get("ui.language"), "en_US")

    def test_auto_save(self):
        """测试自动保存"""
        # 禁用自动保存
        self.manager.set_auto_save(False)

        # 修改配置
        self.manager.set("ocr.engine_type", "baidu")

        # 删除配置文件
        if self.temp_path.exists():
            self.temp_path.unlink()

        # 手动保存
        self.assertTrue(self.manager.save())

        # 验证文件被创建
        self.assertTrue(self.temp_path.exists())

    def test_export_import(self):
        """测试配置导入导出"""
        # 修改配置
        self.manager.set("ocr.engine_type", "baidu")
        self.manager.set("ui.language", "en_US")

        # 创建导出文件
        export_path = self.temp_path.parent / "export_config.json"

        # 导出配置
        self.assertTrue(self.manager.export_to_file(export_path))
        self.assertTrue(export_path.exists())

        # 重置配置
        self.manager.reset()
        self.assertEqual(self.manager.get("ocr.engine_type"), "paddle")

        # 导入配置
        self.assertTrue(self.manager.import_from_file(export_path))
        self.assertEqual(self.manager.get("ocr.engine_type"), "baidu")
        self.assertEqual(self.manager.get("ui.language"), "en_US")

        # 清理
        if export_path.exists():
            export_path.unlink()

    def test_get_config_object(self):
        """测试获取完整配置对象"""
        config = self.manager.get_config()

        self.assertIsInstance(config, AppConfig)
        self.assertEqual(config.ocr.engine_type, "paddle")
        self.assertEqual(config.ui.language, "zh_CN")

    def test_set_config_object(self):
        """测试设置完整配置对象"""
        new_config = AppConfig()
        new_config.ocr.engine_type = "baidu"
        new_config.ui.language = "en_US"

        self.manager.set_config(new_config)

        # 验证
        self.assertEqual(self.manager.get("ocr.engine_type"), "baidu")
        self.assertEqual(self.manager.get("ui.language"), "en_US")


class TestGetConfigManager(unittest.TestCase):
    """测试全局配置管理器获取函数"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def test_get_config_manager_singleton(self):
        """测试 get_config_manager 返回单例"""
        manager1 = get_config_manager()
        manager2 = get_config_manager()

        self.assertIs(manager1, manager2)
        self.assertIsInstance(manager1, ConfigManager)


if __name__ == "__main__":
    unittest.main()
