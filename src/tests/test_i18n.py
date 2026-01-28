#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 多语言系统单元测试

测试多语言管理器的所有核心功能：
- 单例模式
- 语言包加载
- 语言切换
- 翻译查询
- 嵌套键路径
- 占位符替换
- 默认语言回退
- 线程安全

Author: Umi-OCR Team
Date: 2025-01-26
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import unittest
import tempfile
import json
import shutil

# 需要先导入 PySide6，否则会报错
from PySide6.QtWidgets import QApplication


class TestI18nManager(unittest.TestCase):
    """多语言管理器测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化（只执行一次）"""
        # 创建 QApplication 实例（Qt 测试必须）
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        # 清理 QApplication
        if hasattr(cls, "app"):
            cls.app.quit()

    def setUp(self):
        """每个测试用例前的初始化"""
        from src.utils.i18n import I18nManager

        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试语言包文件
        self._create_test_language_files()

        # 重置单例，确保每个测试用例使用新实例
        I18nManager._instance = None

        # 创建新实例
        self.i18n = I18nManager.get_instance()

        # 设置语言包目录
        self.i18n.set_i18n_dir(Path(self.temp_dir))

        # 创建语言管理器实例（用于测试，不使用单例）
        # 先重置单例标志
        if hasattr(I18nManager, "_instance"):
            old_instance = I18nManager._instance
            I18nManager._instance = None

        # 创建新实例
        self.i18n = I18nManager.get_instance()
        self.i18n.set_i18n_dir(Path(self.temp_dir))

        # 恢复旧的单例（用于其他测试）
        if "old_instance" in locals():
            I18nManager._instance = old_instance

    def tearDown(self):
        """每个测试用例后的清理"""
        # 清理临时目录
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # 清除语言管理器的缓存
        self.i18n.clear_cache()

    def _create_test_language_files(self):
        """创建测试语言包文件"""
        # 中文语言包
        zh_cn = {
            "language": "简体中文",
            "locale": "zh_CN",
            "app": {"name": "Umi-OCR", "description": "测试描述"},
            "test": {"key1": "测试值1", "key2": "测试值2"},
            "messages": {"welcome": "欢迎来到{name}", "goodbye": "再见{name}"},
        }

        # 英文语言包
        en_us = {
            "language": "English",
            "locale": "en_US",
            "app": {"name": "Umi-OCR", "description": "Test description"},
            "test": {"key1": "Test value 1", "key2": "Test value 2"},
            "messages": {"welcome": "Welcome to {name}", "goodbye": "Goodbye {name}"},
        }

        # 写入文件
        with open(Path(self.temp_dir) / "zh_CN.json", "w", encoding="utf-8") as f:
            json.dump(zh_cn, f, ensure_ascii=False, indent=2)

        with open(Path(self.temp_dir) / "en_US.json", "w", encoding="utf-8") as f:
            json.dump(en_us, f, ensure_ascii=False, indent=2)

    def test_singleton_pattern(self):
        """测试单例模式"""
        from src.utils.i18n import I18nManager

        # 重置单例
        I18nManager._instance = None

        # 使用 get_instance() 获取实例
        instance1 = I18nManager.get_instance()

        # 再次调用应该返回同一个实例
        instance2 = I18nManager.get_instance()

        # 验证是否是同一个实例
        self.assertIs(instance1, instance2, "get_instance() 应该返回单例")

        # 验证是 I18nManager 类型
        self.assertIsInstance(instance1, I18nManager, "实例应该是 I18nManager 类型")

    def test_language_loading(self):
        """测试语言包加载"""
        # 加载中文
        result = self.i18n.load_language("zh_CN")
        self.assertTrue(result, "应该成功加载中文语言包")

        # 检查是否已加载
        self.assertTrue(self.i18n.is_loaded("zh_CN"), "zh_CN 应该标记为已加载")

        # 加载英文
        result = self.i18n.load_language("en_US")
        self.assertTrue(result, "应该成功加载英文语言包")

        # 加载不存在的语言
        result = self.i18n.load_language("fr_FR")
        self.assertFalse(result, "不应该加载不存在的语言包")

    def test_get_available_languages(self):
        """测试获取可用语言列表"""
        # 先加载语言包
        self.i18n.load_all_languages()

        languages = self.i18n.get_available_languages()

        self.assertIn("zh_CN", languages, "应该包含 zh_CN")
        self.assertIn("en_US", languages, "应该包含 en_US")
        self.assertEqual(len(languages), 2, "应该有2个语言")

    def test_language_switching(self):
        """测试语言切换"""
        # 先加载语言包
        self.i18n.load_language("zh_CN")
        self.i18n.load_language("en_US")

        # 模拟语言变更信号
        self.language_changed_calls = []
        self.i18n.language_changed.connect(
            lambda lang: self.language_changed_calls.append(lang)
        )

        # 切换到中文
        result = self.i18n.set_language("zh_CN")
        self.assertTrue(result, "应该成功切换到中文")
        self.assertEqual(self.i18n.get_language(), "zh_CN", "当前语言应该是 zh_CN")
        self.assertIn("zh_CN", self.language_changed_calls, "应该触发语言变更信号")

        # 切换到英文
        result = self.i18n.set_language("en_US")
        self.assertTrue(result, "应该成功切换到英文")
        self.assertEqual(self.i18n.get_language(), "en_US", "当前语言应该是 en_US")

    def test_translate_simple_key(self):
        """测试简单键的翻译"""
        # 加载中文
        self.i18n.load_language("zh_CN")
        self.i18n.set_language("zh_CN")

        # 简单键
        result = self.i18n.translate("test.key1")
        self.assertEqual(result, "测试值1", "应该返回正确的中文翻译")

        # 切换到英文
        self.i18n.set_language("en_US")
        result = self.i18n.translate("test.key1")
        self.assertEqual(result, "Test value 1", "应该返回正确的英文翻译")

    def test_translate_nested_key(self):
        """测试嵌套键路径的翻译"""
        # 加载中文
        self.i18n.load_language("zh_CN")
        self.i18n.set_language("zh_CN")

        # 嵌套键路径
        result = self.i18n.translate("app.name")
        self.assertEqual(result, "Umi-OCR", "应该返回嵌套键的值")

        result = self.i18n.translate("app.description")
        self.assertEqual(result, "测试描述", "应该返回嵌套键的值")

    def test_translate_with_placeholder(self):
        """测试占位符替换"""
        # 加载中文
        self.i18n.load_language("zh_CN")
        self.i18n.set_language("zh_CN")

        # 带占位符的翻译
        result = self.i18n.translate("messages.welcome", name="Umi-OCR")
        self.assertEqual(result, "欢迎来到Umi-OCR", "应该正确替换占位符")

        result = self.i18n.translate("messages.goodbye", name="用户")
        self.assertEqual(result, "再见用户", "应该正确替换占位符")

    def test_translate_fallback_to_default(self):
        """测试默认语言回退"""
        # 加载中文和英文
        self.i18n.load_language("zh_CN")
        self.i18n.load_language("en_US")

        # 设置默认语言为中文
        self.i18n._default_language = "zh_CN"

        # 加载一个只有部分翻译的语言包
        partial_lang = {
            "language": "Partial",
            "locale": "partial",
            "app": {"name": "Partial App"},
            # 没有 test.key1
        }

        with open(Path(self.temp_dir) / "partial.json", "w", encoding="utf-8") as f:
            json.dump(partial_lang, f, ensure_ascii=False)

        self.i18n.load_language("partial")
        self.i18n.set_language("partial")

        # 查询存在的键
        result = self.i18n.translate("app.name")
        self.assertEqual(result, "Partial App", "应该返回 partial 语言的翻译")

        # 查询不存在的键，应该回退到默认语言
        result = self.i18n.translate("test.key1")
        self.assertEqual(result, "测试值1", "应该回退到默认语言的翻译")

    def test_translate_missing_key(self):
        """测试翻译键不存在的情况"""
        # 加载中文
        self.i18n.load_language("zh_CN")
        self.i18n.set_language("zh_CN")

        # 查询不存在的键
        result = self.i18n.translate("nonexistent.key")
        self.assertEqual(result, "nonexistent.key", "应该返回键路径本身")

    def test_translate_method_alias(self):
        """测试翻译方法别名 t()"""
        # 加载中文
        self.i18n.load_language("zh_CN")
        self.i18n.set_language("zh_CN")

        # 使用 t() 方法
        result = self.i18n.t("test.key1")
        self.assertEqual(result, "测试值1", "t() 方法应该与 translate() 相同")

    def test_get_language_info(self):
        """测试获取语言信息"""
        # 加载中文
        self.i18n.load_language("zh_CN")
        self.i18n.set_language("zh_CN")

        # 获取语言名称
        lang_name = self.i18n.get_language_name()
        self.assertEqual(lang_name, "简体中文", "应该返回正确的语言名称")

        # 获取区域设置
        locale = self.i18n.get_locale()
        self.assertEqual(locale, "zh_CN", "应该返回正确的区域设置")

        # 指定语言代码
        self.i18n.load_language("en_US")
        lang_name = self.i18n.get_language_name("en_US")
        self.assertEqual(lang_name, "English", "应该返回英文的语言名称")

    def test_reload_language(self):
        """测试重新加载语言包"""
        # 加载中文
        self.i18n.load_language("zh_CN")
        self.assertTrue(self.i18n.is_loaded("zh_CN"))

        # 修改语言包文件
        zh_cn_file = Path(self.temp_dir) / "zh_CN.json"
        with open(zh_cn_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["test"]["key1"] = "修改后的值"

        with open(zh_cn_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 重新加载
        result = self.i18n.reload_language("zh_CN")
        self.assertTrue(result, "应该成功重新加载")

        self.i18n.set_language("zh_CN")
        result = self.i18n.translate("test.key1")
        self.assertEqual(result, "修改后的值", "应该返回修改后的值")

    def test_clear_cache(self):
        """测试清除缓存"""
        # 加载语言包
        self.i18n.load_language("zh_CN")
        self.i18n.load_language("en_US")

        self.assertTrue(self.i18n.is_loaded("zh_CN"))
        self.assertTrue(self.i18n.is_loaded("en_US"))

        # 清除缓存
        self.i18n.clear_cache()

        self.assertFalse(self.i18n.is_loaded("zh_CN"))
        self.assertFalse(self.i18n.is_loaded("en_US"))

    def test_thread_safety(self):
        """测试线程安全"""
        from src.utils.i18n import I18nManager
        import threading

        # 重置单例并重新初始化
        I18nManager._instance = None
        i18n = I18nManager.get_instance()

        # 设置语言包目录
        i18n.set_i18n_dir(Path(self.temp_dir))

        # 加载语言包
        i18n.load_language("zh_CN")
        i18n.load_language("en_US")

        results = []
        errors = []

        def worker(lang_code):
            try:
                # 切换语言并翻译
                i18n.set_language(lang_code)
                result = i18n.translate("test.key1")
                results.append((lang_code, result))
            except Exception as e:
                errors.append(e)

        # 创建多个线程并发访问
        threads = []
        for _ in range(100):
            lang = "zh_CN" if _ % 2 == 0 else "en_US"
            t = threading.Thread(target=worker, args=(lang,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证没有错误
        self.assertEqual(len(errors), 0, "不应该有线程错误")

        # 验证结果正确
        self.assertEqual(len(results), 100, "应该有100个结果")

    def test_global_i18n_functions(self):
        """测试全局便捷函数"""
        from src.utils.i18n import get_i18n_manager, t

        # 设置语言包目录
        get_i18n_manager().set_i18n_dir(Path(self.temp_dir))
        get_i18n_manager().load_language("zh_CN")
        get_i18n_manager().set_language("zh_CN")

        # 使用全局函数 t()
        result = t("test.key1")
        self.assertEqual(result, "测试值1", "全局 t() 函数应该正常工作")

    def test_invalid_placeholder(self):
        """测试无效的占位符"""
        # 确保重新加载中文语言包
        self.i18n.load_language("zh_CN")
        self.i18n.set_language("zh_CN")

        # 使用不存在的占位符
        result = self.i18n.translate("messages.welcome", nonexistent="value")
        # 应该返回原始文本（占位符替换失败）
        self.assertIn("欢迎", result, "应该包含欢迎文字")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestI18nManager)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
