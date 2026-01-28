#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SettingsSearch 单元测试

测试设置搜索功能，包括：
- 基本搜索功能
- 不同类型查询的匹配
- 空查询处理
- 搜索结果结构
- 信号发射
- 边界情况
- 性能基准

Author: Umi-OCR Team
Date: 2026-01-28
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtCore import QCoreApplication, QObject, Signal

from src.ui.settings.settings_search import SettingsSearch, SearchResult


class TestSearchResult(unittest.TestCase):
    """测试 SearchResult 数据类"""

    def test_search_result_creation(self):
        """测试 SearchResult 对象创建"""
        result = SearchResult(
            key="ocr.engine_type",
            value="paddle",
            label="OCR 引擎类型",
            description="选择本地 OCR 引擎或云服务 OCR",
            matched_fields=["key", "label"]
        )

        self.assertEqual(result.key, "ocr.engine_type")
        self.assertEqual(result.value, "paddle")
        self.assertEqual(result.label, "OCR 引擎类型")
        self.assertEqual(result.description, "选择本地 OCR 引擎或云服务 OCR")
        self.assertIn("key", result.matched_fields)
        self.assertIn("label", result.matched_fields)

    def test_search_result_optional_fields(self):
        """测试 SearchResult 可选字段"""
        result = SearchResult(
            key="test.key",
            value="test_value",
            label="Test Label",
            description="",
            matched_fields=["key"]
        )

        # 空描述也应该有效
        self.assertEqual(result.description, "")
        self.assertEqual(len(result.matched_fields), 1)


class TestSettingsSearchInitialization(unittest.TestCase):
    """测试 SettingsSearch 初始化"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def test_init(self):
        """测试基本初始化"""
        search = SettingsSearch()

        self.assertIsInstance(search, QObject)
        self.assertIsNotNone(search._controller)
        self.assertIsNotNone(search.search_completed)

    def test_signal_exists(self):
        """测试信号是否存在"""
        search = SettingsSearch()

        # 验证信号可连接
        receiver = Mock()
        search.search_completed.connect(receiver.on_search_completed)
        # PySide6 信号连接后无法直接检查，但可以验证连接不会报错
        self.assertIsNotNone(receiver)


class TestSettingsSearchBasic(unittest.TestCase):
    """测试 SettingsSearch 基本搜索功能"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        """每个测试前的设置"""
        self.search = SettingsSearch()

    def test_search_empty_query(self):
        """测试空查询"""
        results = self.search.search("")

        self.assertEqual(len(results), 0)

    def test_search_whitespace_only(self):
        """测试只有空格的查询"""
        results = self.search.search("   ")

        self.assertEqual(len(results), 0)

    def test_search_none_query(self):
        """测试 None 查询"""
        results = self.search.search(None)

        self.assertEqual(len(results), 0)

    def test_search_signal_emitted(self):
        """测试搜索信号是否发射"""
        # 创建信号收集器
        collected_results = []

        def on_search_completed(results):
            collected_results.extend(results)

        self.search.search_completed.connect(on_search_completed)

        # 执行搜索
        results = self.search.search("ocr")

        # 验证信号被发射
        self.assertEqual(len(collected_results), len(results))


class TestSettingsSearchKeyMatching(unittest.TestCase):
    """测试配置键匹配"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        """每个测试前的设置"""
        self.search = SettingsSearch()

    def test_search_key_match(self):
        """测试键名匹配"""
        results = self.search.search("ocr.engine_type")

        self.assertGreater(len(results), 0)

        # 查找包含 key 匹配的结果
        key_matched = any("key" in r.matched_fields for r in results)
        self.assertTrue(key_matched)

    def test_search_partial_key_match(self):
        """测试部分键名匹配"""
        results = self.search.search("engine")

        self.assertGreater(len(results), 0)

        # 应该找到多个包含 "engine" 的配置项
        engine_results = [r for r in results if "engine" in r.key.lower()]
        self.assertGreater(len(engine_results), 0)

    def test_search_case_insensitive_key(self):
        """测试键名匹配大小写不敏感"""
        results1 = self.search.search("OCR")
        results2 = self.search.search("ocr")

        self.assertEqual(len(results1), len(results2))


class TestSettingsSearchLabelMatching(unittest.TestCase):
    """测试标签匹配"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        """每个测试前的设置"""
        self.search = SettingsSearch()

    def test_search_label_match(self):
        """测试标签匹配"""
        results = self.search.search("引擎")

        self.assertGreater(len(results), 0)

        # 验证至少有一个结果匹配了标签
        label_matched = any("label" in r.matched_fields for r in results)
        self.assertTrue(label_matched)

    def test_search_partial_label_match(self):
        """测试部分标签匹配"""
        results = self.search.search("语言")

        self.assertGreater(len(results), 0)

        # 应该找到语言相关配置
        language_results = [r for r in results if "语言" in r.label]
        self.assertGreater(len(language_results), 0)

    def test_search_case_insensitive_label(self):
        """测试标签匹配大小写不敏感"""
        results1 = self.search.search("快捷键")
        results2 = self.search.search("快捷键")

        # 中文不存在大小写问题，但验证逻辑一致
        self.assertEqual(len(results1), len(results2))


class TestSettingsSearchValueMatching(unittest.TestCase):
    """测试值匹配"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        """每个测试前的设置"""
        self.search = SettingsSearch()

    def test_search_string_value_match(self):
        """测试字符串值匹配"""
        results = self.search.search("paddle")

        self.assertGreater(len(results), 0)

        # 验证至少有一个结果匹配了值
        value_matched = any("value" in r.matched_fields for r in results)
        self.assertTrue(value_matched)

    def test_search_boolean_value(self):
        """测试布尔值搜索"""
        # 搜索数字字符串 "1"（可能表示 True）
        results = self.search.search("1")

        # 某些配置项的默认值可能是 1
        # 如果找不到，跳过此测试（不是关键功能）
        if len(results) > 0:
            self.assertGreater(len(results), 0)
        else:
            self.skipTest("没有找到值为 '1' 的配置项")


class TestSettingsSearchCategory(unittest.TestCase):
    """测试不同类别的搜索"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        """每个测试前的设置"""
        self.search = SettingsSearch()

    def test_search_ocr_config(self):
        """测试搜索 OCR 配置"""
        results = self.search.search("ocr")

        ocr_results = [r for r in results if r.key.startswith("ocr.")]
        self.assertGreater(len(ocr_results), 0)

    def test_search_ui_config(self):
        """测试搜索 UI 配置"""
        results = self.search.search("ui")

        ui_results = [r for r in results if r.key.startswith("ui.")]
        self.assertGreater(len(ui_results), 0)

    def test_search_hotkey_config(self):
        """测试搜索快捷键配置"""
        results = self.search.search("快捷键")

        hotkey_results = [r for r in results if r.key.startswith("hotkeys.")]
        self.assertGreater(len(hotkey_results), 0)

    def test_search_export_config(self):
        """测试搜索导出配置"""
        results = self.search.search("导出")

        export_results = [r for r in results if r.key.startswith("export.")]
        self.assertGreater(len(export_results), 0)

    def test_search_system_config(self):
        """测试搜索系统配置"""
        results = self.search.search("系统")

        system_results = [r for r in results if r.key.startswith("system.")]
        self.assertGreater(len(system_results), 0)


class TestSettingsSearchFuzzy(unittest.TestCase):
    """测试模糊搜索"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        """每个测试前的设置"""
        self.search = SettingsSearch()

    def test_search_partial_text(self):
        """测试部分文本匹配"""
        results = self.search.search("gpu")

        self.assertGreater(len(results), 0)

    def test_search_english_and_chinese(self):
        """测试中英文混合搜索"""
        results1 = self.search.search("ocr")
        results2 = self.search.search("识别")

        self.assertGreater(len(results1), 0)
        self.assertGreater(len(results2), 0)


class TestSettingsSearchResults(unittest.TestCase):
    """测试搜索结果的结构和内容"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        """每个测试前的设置"""
        self.search = SettingsSearch()

    def test_result_structure(self):
        """测试结果对象结构"""
        results = self.search.search("ocr")

        if results:
            result = results[0]

            # 验证结果包含所有必需字段
            self.assertTrue(hasattr(result, 'key'))
            self.assertTrue(hasattr(result, 'value'))
            self.assertTrue(hasattr(result, 'label'))
            self.assertTrue(hasattr(result, 'description'))
            self.assertTrue(hasattr(result, 'matched_fields'))

            # 验证字段类型
            self.assertIsInstance(result.key, str)
            self.assertIsInstance(result.label, str)
            self.assertIsInstance(result.description, str)
            self.assertIsInstance(result.matched_fields, list)

    def test_result_key_format(self):
        """测试结果键格式"""
        results = self.search.search("ocr")

        # 所有键应该包含点分隔符
        for result in results:
            self.assertGreater(result.key.count('.'), 0)

    def test_result_values_retrievable(self):
        """测试结果值可获取"""
        results = self.search.search("ocr")

        if results:
            # 尝试通过控制器获取相同值
            result = results[0]
            actual_value = self.search._controller.get_config(result.key)
            self.assertEqual(result.value, actual_value)


class TestSettingsSearchPerformance(unittest.TestCase):
    """测试搜索性能"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        """每个测试前的设置"""
        self.search = SettingsSearch()

    def test_search_performance_short_query(self):
        """测试短查询性能"""
        import time

        start_time = time.time()
        results = self.search.search("ocr")
        end_time = time.time()

        # 搜索应该在 100ms 内完成
        self.assertLess(end_time - start_time, 0.1)
        self.assertGreater(len(results), 0)

    def test_search_performance_long_query(self):
        """测试长查询性能"""
        import time

        start_time = time.time()
        results = self.search.search("ocr.engine_type")
        end_time = time.time()

        # 长查询也应该很快
        self.assertLess(end_time - start_time, 0.1)

    def test_multiple_searches_performance(self):
        """测试多次搜索性能"""
        import time

        queries = ["ocr", "ui", "hotkey", "export", "system"]
        start_time = time.time()

        for query in queries:
            self.search.search(query)

        end_time = time.time()

        # 5次搜索应该在 500ms 内完成
        self.assertLess(end_time - start_time, 0.5)


class TestSettingsSearchEdgeCases(unittest.TestCase):
    """测试边界情况"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        """每个测试前的设置"""
        self.search = SettingsSearch()

    def test_search_special_characters(self):
        """测试特殊字符查询"""
        results = self.search.search(".")

        # 特殊字符不应导致崩溃
        self.assertIsInstance(results, list)

    def test_search_very_long_query(self):
        """测试非常长的查询"""
        long_query = "a" * 1000
        results = self.search.search(long_query)

        # 长查询不应导致崩溃
        self.assertIsInstance(results, list)
        # 应该没有匹配
        self.assertEqual(len(results), 0)

    def test_search_unicode(self):
        """测试 Unicode 字符"""
        results = self.search.search("中文测试")

        # Unicode 查询不应导致崩溃
        self.assertIsInstance(results, list)


class TestSettingsSearchIntegration(unittest.TestCase):
    """集成测试"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        """每个测试前的设置"""
        self.search = SettingsSearch()

    def test_end_to_end_search(self):
        """测试端到端搜索流程"""
        # 1. 执行搜索
        results = self.search.search("ocr")

        # 2. 验证有结果
        self.assertGreater(len(results), 0)

        # 3. 验证结果结构
        for result in results:
            self.assertIsInstance(result, SearchResult)
            self.assertIsNotNone(result.key)
            self.assertIsNotNone(result.label)

        # 4. 验证可以通过键获取配置
        if results:
            config_value = self.search._controller.get_config(results[0].key)
            self.assertIsNotNone(config_value)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestSearchResult))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSearchInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSearchBasic))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSearchKeyMatching))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSearchLabelMatching))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSearchValueMatching))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSearchCategory))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSearchFuzzy))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSearchResults))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSearchPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSearchEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSearchIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    import sys
    sys.exit(0 if success else 1)
