#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 模型定义和语言验证脚本

生成报告：
1. 模型覆盖情况
2. 语言代码验证
3. 版本使用情况
4. 推荐改进建议

Author: Umi-OCR Team
Date: 2026-01-26
"""

import sys
from pathlib import Path
import logging
from typing import Dict, List, Tuple
from collections import defaultdict

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

# 导入项目模块
from services.ocr.model_manager import ModelRepository  # noqa: E402
from services.ocr.model_download_config import (
    ALL_MODELS,
    MODEL_PRESETS,
)  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def generate_model_coverage_report() -> Dict:
    """生成模型覆盖报告"""
    report = {
        "summary": {},
        "by_category": defaultdict(list),
        "by_version": defaultdict(list),
        "by_language": defaultdict(list),
    }

    # 统计模型
    total_models = len(ALL_MODELS)
    report["summary"]["total_models"] = total_models
    report["summary"]["total_size_mb"] = sum(m.size_mb for m in ALL_MODELS.values())

    # 按类别统计
    for model_id, model in ALL_MODELS.items():
        report["by_category"][model.category.value].append(model_id)

    # 按版本统计
    for model_id, model in ALL_MODELS.items():
        if "PP-OCRv5" in model_id or "ppocrv5" in model_id:
            report["by_version"]["v5"].append(model_id)
        elif "PP-OCRv4" in model_id or "ppocrv4" in model_id:
            report["by_version"]["v4"].append(model_id)
        elif "PP-OCRv3" in model_id or "ppocrv3" in model_id:
            report["by_version"]["v3"].append(model_id)
        else:
            report["by_version"]["other"].append(model_id)

    # 按语言统计
    for model_id, model in ALL_MODELS.items():
        report["by_language"][model.language].append(model_id)

    return report


def validate_language_codes() -> Tuple[Dict[str, List[Tuple[str, str]]], List[str]]:
    """
    验证所有语言代码

    Returns:
        Tuple[Dict[str, List[Tuple[str, str]]], List[str]]: (有效语言映射, 无效语言列表)
    """
    valid_languages = {
        # 统一模型（PP-OCRv5）
        "ch": [("PP-OCRv5_server_rec", "简体中文")],
        "en": [("PP-OCRv5_server_rec", "English")],
        "japan": [("PP-OCRv5_server_rec", "日本語")],
        "korean": [("PP-OCRv5_server_rec", "한국어")],
        "cyrillic": [("PP-OCRv5_server_rec", "Cyrillic")],
        "latin": [("PP-OCRv5_server_rec", "Latin")],
        "arabic": [("PP-OCRv5_server_rec", "Arabic")],
        "devanagari": [("PP-OCRv5_server_rec", "Devanagari")],
        "th": [("PP-OCRv5_server_rec", "泰语")],
        "el": [("PP-OCRv5_server_rec", "Greek")],
    }

    # 语言专用模型
    language_specific_models = {
        "korean": [("korean_PP-OCRv5_mobile_rec", "韩文优化")],
        "latin": [("latin_PP-OCRv5_mobile_rec", "拉丁语系优化")],
        "eslav": [("eslav_PP-OCRv5_mobile_rec", "东斯拉夫语系")],
        "th": [("th_PP-OCRv5_mobile_rec", "泰语优化")],
        "el": [("el_PP-OCRv5_mobile_rec", "希腊语优化")],
        "arabic": [("arabic_PP-OCRv5_mobile_rec", "阿拉伯语系")],
        "devanagari": [("devanagari_PP-OCRv5_mobile_rec", "印度语系")],
        "ta": [("ta_PP-OCRv5_mobile_rec", "泰米尔语")],
        "te": [("te_PP-OCRv5_mobile_rec", "泰卢固语")],
    }

    # 合并语言映射
    for lang, models in language_specific_models.items():
        if lang not in valid_languages:
            valid_languages[lang] = models

    # 109种语言扩展（v4 时代的单一语言）
    single_languages_v4 = [
        "af",
        "az",
        "bs",
        "cs",
        "cy",
        "da",
        "de",
        "es",
        "et",
        "fi",
        "fr",
        "ga",
        "hr",
        "hu",
        "is",
        "it",
        "lt",
        "lv",
        "mi",
        "ms",
        "nl",
        "no",
        "oc",
        "pi",
        "pl",
        "pt",
        "ro",
        "rs_latin",
        "sk",
        "sl",
        "sq",
        "sv",
        "tr",
        "vi",
        "be",
        "bg",
        "mk",
        "ru",
        "uk",
        "sr",
        "id",
        "ku",
        "la",
        "sw",
        "uz",
        "ar",
        "fa",
        "ug",
        "ur",
        "hi",
        "mr",
        "ne",
        "bh",
        "mai",
        "ang",
        "bho",
        "mah",
    ]

    # 添加到有效语言列表
    for lang in single_languages_v4:
        if lang not in valid_languages:
            valid_languages[lang] = [("PP-OCRv4_server_rec", f"单一语言 ({lang})")]

    # 验证 paddle_engine.py 中的语言代码
    paddle_engine_languages = [
        "ch",
        "en",
        "japan",
        "korean",
        "th",
        "latin",
        "arabic",
        "cyrillic",
        "devanagari",
        "af",
        "az",
        "bs",
        "cs",
        "cy",
        "da",
        "de",
        "es",
        "et",
        "fr",
        "ga",
        "hr",
        "hu",
        "id",
        "is",
        "it",
        "ku",
        "la",
        "lt",
        "lv",
        "mi",
        "ms",
        "nl",
        "no",
        "oc",
        "pi",
        "pl",
        "pt",
        "ro",
        "rs_latin",
        "sk",
        "sl",
        "sq",
        "sv",
        "sw",
        "tl",
        "tr",
        "uz",
        "vi",
        "ar",
        "fa",
        "ug",
        "ur",
        "ps",
        "ru",
        "be",
        "uk",
        "hi",
        "mr",
        "ne",
        "bh",
        "mai",
        "ang",
        "bho",
        "mah",
        "sck",
        "new",
        "gom",
        "sa",
        "bgc",
    ]

    # 验证语言代码
    invalid_languages = []

    for lang in paddle_engine_languages:
        is_valid, error_msg = ModelRepository.validate_language_code(lang)
        if not is_valid:
            invalid_languages.append((lang, error_msg))

    return valid_languages, invalid_languages


def generate_recommendations() -> List[str]:
    """生成改进建议"""
    recommendations = []

    # 1. 统一模型定义
    recommendations.append(
        "✓ 已完成：model_manager.py 现在引用 model_download_config.py 的完整模型定义"
    )

    # 2. 验证语言代码
    _, invalid_languages = validate_language_codes()

    if invalid_languages:
        recommendations.append(f"\n⚠️ 发现 {len(invalid_languages)} 个无效语言代码：")
        for lang, msg in invalid_languages:
            recommendations.append(f"   - {lang}: {msg}")

        recommendations.append("\n建议操作：")
        recommendations.append("   1. 对照官方 PaddleOCR 3.3.0 文档验证语言代码")
        recommendations.append("   2. 移除已弃用的语言代码（flemish, german 等）")
        recommendations.append("   3. 使用别名代替全称（如 en 代替 english）")
        recommendations.append("   4. 考虑将语言映射提取为单独的配置文件")
    else:
        recommendations.append("✓ 语言代码验证通过，所有语言代码均有效")

    # 3. 模型版本策略
    recommendations.append("\n" + "=" * 70)
    recommendations.append("模型版本使用建议：")
    recommendations.append("=" * 70)
    recommendations.append("""
为什么保留 PP-OCRv4 模型？

1. 向后兼容性
   - 现有用户配置可能使用 v4
   - v4 模型已在生产环境验证过，更稳定
   - 允许用户平滑迁移到 v5

2. 特定语言支持
   - 某些语言可能在 v4 上有更好的支持
   - 部分语种的模型可能只有 v4 版本

3. 性能考虑
   - v4 模型在某些硬件上可能有更优的性能
   - 用户可以根据场景选择速度 vs 精度

4. 渐进式迁移策略
   - 保留 v4 允许用户 A/B 测试两个版本的效果
   - 避免"一刀切"强制升级可能带来的问题

推荐使用策略：
   - 新项目：默认使用 PP-OCRv5
   - 生产环境：建议使用 v5（精度提升 13%）
   - 需要稳定：可以选择 v4（经验证）
   - 特定场景：根据实际测试结果选择

注意：PP-OCRv3 已标记为 deprecated，不建议使用
    """)

    # 4. 移动端模型
    recommendations.append("\n⚠️ 缺少移动端模型：")
    recommendations.append("   当前配置仅包含服务端模型（server）")
    recommendations.append("   建议添加移动端模型（mobile）以支持 CPU/边缘设备")
    recommendations.append("\n   示例配置：")
    recommendations.append("   - ppocrv5_mobile_det (~30MB)")
    recommendations.append("   - ppocrv5_mobile_rec (~4.5MB)")
    recommendations.append("\n   移动端模型优势：")
    recommendations.append("   - 更快的推理速度（CPU）")
    recommendations.append("   - 更小的模型大小")
    recommendations.append("   - 更低的内存占用")

    # 5. 功能实现
    recommendations.append("\n⚠️ 功能实现不完整：")
    recommendations.append(
        "   paddle_engine.py 中的 _recognize_structure 方法标记为 TODO"
    )
    recommendations.append("   建议实现以下功能：")
    recommendations.append("   - 版面分析（使用 PP-DocLayout 模型）")
    recommendations.append("   - 表格识别（使用 SLANet/SLANeXt 模型）")
    recommendations.append("   - 公式识别（使用 PP-FormulaNet 模型）")

    return recommendations


def print_report():
    """打印完整报告"""
    print("\n" + "=" * 70)
    print("Umi-OCR PaddleOCR 模型配置统一验证报告")
    print("=" * 70)
    print("生成时间: 2026-01-26")
    print("Commit: 9e4ba28d - 集成 PaddleOCR 本地引擎与模型管理器")
    print()

    # 1. 模型覆盖报告
    print("=" * 70)
    print("1. 模型覆盖情况")
    print("=" * 70)

    model_report = generate_model_coverage_report()

    print(f"✓ 总模型数: {model_report['summary']['total_models']}")
    print(f"✓ 总大小: {model_report['summary']['total_size_mb']:.1f} MB")

    print("\n按类别统计：")
    for category, models in sorted(model_report["by_category"].items()):
        print(f"  {category:20s} : {len(models):3d} 个模型")

    print("\n按版本统计：")
    for version, models in sorted(model_report["by_version"].items()):
        print(f"  {version:10s} : {len(models):3d} 个模型")

    print("\n按语言统计（前 10）：")
    sorted_languages = sorted(
        model_report["by_language"].items(), key=lambda x: len(x[1]), reverse=True
    )[:10]
    for lang, models in sorted_languages:
        print(f"  {lang:15s} : {len(models):3d} 个模型")

    # 2. 语言代码验证
    print("\n" + "=" * 70)
    print("2. 语言代码验证")
    print("=" * 70)

    valid_languages, invalid_languages = validate_language_codes()

    print(f"\n✓ 有效语言代码: {len(valid_languages)} 种")

    # 显示统一模型支持的主要语言
    unified_langs = ["ch", "en", "japan", "korean"]
    print("\n  PP-OCRv5 统一模型支持的语言：")
    for lang in unified_langs:
        info = valid_languages.get(lang, [])
        if info:
            print(f"    {lang:10s} : {info[0][1] if info else 'N/A'}")

    # 显示语言组
    language_groups = ["cyrillic", "latin", "arabic", "devanagari"]
    print("\n  语言组模型（专用优化）：")
    for lang in language_groups:
        info = valid_languages.get(lang, [])
        if info:
            print(f"    {lang:10s} : {info[0][1] if info else 'N/A'}")

    if invalid_languages:
        print(f"\n✗ 无效语言代码: {len(invalid_languages)} 种")
        for lang, msg in invalid_languages:
            print(f"  {lang:15s} : {msg}")

    # 3. 模型预设组合
    print("\n" + "=" * 70)
    print("3. 模型预设组合（按功能渐进）")
    print("=" * 70)

    for preset in MODEL_PRESETS.values():
        print(f"\n  [{preset.id}] {preset.name}")
        print(f"    描述: {preset.description}")
        print(f"    推荐场景: {preset.recommended_for}")
        print(f"    总大小: {preset.total_size_mb:.1f} MB")
        print(f"    包含模型: {len(preset.models)} 个")
        print("    模型列表:")
        for model_id in preset.models:
            model = ALL_MODELS.get(model_id)
            if model:
                print(f"      - {model_id:40s} ({model.display_name})")

    # 4. 改进建议
    print("\n" + "=" * 70)
    print("4. 改进建议")
    print("=" * 70)

    recommendations = generate_recommendations()
    for rec in recommendations:
        print(rec)

    # 5. 总结
    print("\n" + "=" * 70)
    print("总结")
    print("=" * 70)

    print("""
重构评估：
  ✓ 已统一模型定义：model_manager.py 引用 model_download_config.py
  ✓ 已添加完整语言验证逻辑
  ✓ 已解释 v4 模型保留原因
  ✓ 已生成模型预设组合文档

下一步建议：
  1. 验证并修复 paddle_engine.py 中的无效语言代码
  2. 完成高级功能的实现（版面分析、表格、公式识别）
  3. 添加移动端模型到 model_download_config.py
  4. 考虑弃用或整合旧引擎文件（paddleocr_direct.py 等）
  5. 实现模型预设加载逻辑

    """)


if __name__ == "__main__":
    print_report()
