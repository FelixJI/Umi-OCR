#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的设置页面
"""

import sys
import os
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def test_settings_import():
    """测试能否正确导入设置模块"""
    try:
        from src.ui.settings.settings import SettingsWindow
        print("✓ 设置窗口模块导入成功")
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        return False

def test_settings_creation():
    """测试设置窗口实例化"""
    try:
        from src.ui.settings.settings import SettingsWindow
        from src.app import UmiApplication
        
        # 创建应用实例
        app = UmiApplication(sys.argv)
        
        # 创建设置窗口
        settings_window = SettingsWindow()
        print("✓ 设置窗口实例化成功")
        
        return True
    except Exception as e:
        print(f"✗ 实例化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("开始测试修复后的设置窗口...")
    
    print("\n1. 测试设置模块导入:")
    if not test_settings_import():
        return False
    
    print("\n2. 测试设置窗口创建:")
    if not test_settings_creation():
        return False
    
    print("\n✓ 所有测试通过！设置页面修复应该生效。")
    print("\n修复说明：")
    print("- 修复了CredentialManager调用问题")
    print("- 创建了全局CredentialManager实例")
    print("- 修改了SettingsController中对CredentialManager的调用方式")
    return True

if __name__ == "__main__":
    main()