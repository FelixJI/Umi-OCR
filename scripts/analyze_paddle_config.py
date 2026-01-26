#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR 模型配置分析报告

基于 model_download_config.py 直接分析模型定义和语言支持

Author: Umi-OCR Team
Date: 2026-01-26
"""

from pathlib import Path
import json
from collections import defaultdict

# 读取 model_download_config.py
config_file = (
    Path(__file__).parent.parent
    / "src"
    / "services"
    / "ocr"
    / "model_download_config.py"
)

# 执行配置文件以提取模型定义
exec(open(config_file, "r", encoding="utf-8").read())

print("\n" + "=" * 70)
print("Umi-OCR PaddleOCR 模型配置分析报告")
print("=" * 70)
print(f"配置文件: {config_file}")
print()

# 1. 模型覆盖统计
print("=" * 70)
print("1. 模型覆盖统计")
print("=" * 70)

model_counts = defaultdict(int)
total_size_mb = 0

# 统计所有模型
for model_id, model in ALL_MODELS.items():
    model_counts[model.category.value] += 1
    total_size_mb += model.size_mb

print(f"\n总模型数: {len(ALL_MODELS)}")
print(f"总大小: {total_size_mb:.1f} MB ({total_size_mb / 1024:.2f} GB)")

print("\n按类别统计：")
for category in sorted(model_counts.keys()):
    count = model_counts[category]
    size = sum(m.size_mb for m in ALL_MODELS.values() if m.category.value == category)
    print(f"  {category:25s} : {count:3d} 个模型 (总计 {size:7.1f} MB)")

# 2. 版本统计
print("\n" + "=" * 70)
print("2. 模型版本统计")
print("=" * 70)

version_counts = defaultdict(int)
for model_id, model in ALL_MODELS.items():
    if "PP-OCRv5" in model_id or "ppocrv5" in model_id:
        version_counts["v5"] += 1
    elif "PP-OCRv4" in model_id or "ppocrv4" in model_id:
        version_counts["v4"] += 1
    elif "PP-OCRv3" in model_id or "ppocrv3" in model_id:
        version_counts["v3"] += 1
    else:
        version_counts["other"] += 1

for version, count in sorted(version_counts.items()):
    print(f"  {version.upper():10s} : {count:3d} 个模型")

# 3. 语言支持统计
print("\n" + "=" * 70)
print("3. 语言支持统计")
print("=" * 70)

language_models = defaultdict(list)
for model_id, model in ALL_MODELS.items():
    language_models[model.language].append((model_id, model))

print(f"\n支持的语言数: {len(language_models)}")
print("\n主要语言模型数：")
for lang in sorted(
    ["ch", "en", "japan", "korean", "cyrillic", "latin", "arabic", "devanagari"]
):
    if lang in language_models:
        models = language_models[lang]
        size = sum(m.size_mb for m in models)
        print(f"  {lang:15s} : {len(models):3d} 个模型 (总计 {size:7.1f} MB)")

# 4. 语言专用模型
print("\n" + "=" * 70)
print("4. 语言专用优化模型")
print("=" * 70)

language_specific_models = [
    ("korean_PP-OCRv5_mobile_rec", "韩文优化 (+65% 精度)"),
    ("latin_PP-OCRv5_mobile_rec", "拉丁语系 37种语言 (+46.8% 精度)"),
    ("eslav_PP-OCRv5_mobile_rec", "东斯拉夫语族 (+31.4% 精度)"),
    ("th_PP-OCRv5_mobile_rec", "泰语 (82.68% 精度)"),
    ("el_PP-OCRv5_mobile_rec", "希腊语 (89.28% 精度)"),
    ("arabic_PP-OCRv5_mobile_rec", "阿拉伯语系 (+22.83% 精度)"),
    ("devanagari_PP-OCRv5_mobile_rec", "印度语系 (+68.26% 精度)"),
    ("ta_PP-OCRv5_mobile_rec", "泰米尔语 (94.2% 精度)"),
    ("te_PP-OCRv5_mobile_rec", "泰卢固语 (87.65% 精度)"),
]

for model_id, description in language_specific_models:
    model = ALL_MODELS.get(model_id)
    if model:
        print(f"  {model_id:35s} : {description} ({model.size_mb:.1f} MB)")

# 5. 模型预设组合
print("\n" + "=" * 70)
print("5. 模型预设组合（按功能渐进）")
print("=" * 70)

for preset in MODEL_PRESETS.values():
    print(f"\n[{preset.id}] {preset.name}")
    print(f"  描述: {preset.description}")
    print(f"  场景: {preset.recommended_for}")
    print(f"  总大小: {preset.total_size_mb:.1f} MB")
    print(f"  包含模型: {len(preset.models)} 个")

    # 列出前5个模型
    print("  模型列表:")
    for model_id in preset.models[:5]:
        model = ALL_MODELS.get(model_id)
        if model:
            print(f"    - {model_id:40s} ({model.display_name})")

    if len(preset.models) > 5:
        print(f"    ... 还有 {len(preset.models) - 5} 个模型")

# 6. 公式识别模型
print("\n" + "=" * 70)
print("6. 公式识别模型（多个版本）")
print("=" * 70)

formula_models = {
    "LaTeX_OCR_rec": "LaTeX-OCR",
    "PP-FormulaNet-S": "PP-FormulaNet S (轻量)",
    "PP-FormulaNet_plus-S": "PP-FormulaNet+ S (轻量增强, 中文 BLEU 53.32%)",
    "PP-FormulaNet_plus-M": "PP-FormulaNet+ M (中等, 中文 BLEU 89.76%)",
    "PP-FormulaNet_plus-L": "PP-FormulaNet+ L (高精度, 中文 BLEU 90.64%)",
    "PP-FormulaNet-L": "PP-FormulaNet L (高精度, 旧版)",
    "UniMERNet": "UniMERNet (超大规模, 英文 BLEU 85.91%)",
}

for model_id, description in formula_models.items():
    model = ALL_MODELS.get(model_id)
    if model:
        print(f"  {model_id:30s} : {description} ({model.size_mb:.1f} MB)")

# 7. 版面分析模型
print("\n" + "=" * 70)
print("7. 版面分析模型（多精度级别）")
print("=" * 70)

layout_models = [
    ("PP-DocLayout_plus-L", "高精度, 20类区域"),
    ("PP-DocLayout-L", "标准, 23类区域"),
    ("PP-DocLayout-M", "中等精度"),
    ("PP-DocLayout-S", "轻量, 快速"),
    ("PicoDet-S_layout_3cls", "轻量 3类 (表格/图像/印章)"),
    ("PicoDet-L_layout_3cls", "标准 3类"),
    ("RT-DETR-H_layout_3cls", "高精度 3类 (mAP 95.8%)"),
    ("PicoDet-S_layout_17cls", "轻量 17类 (mAP 98.3%)"),
    ("PicoDet-L_layout_17cls", "标准 17类"),
    ("RT-DETR-H_layout_17cls", "高精度 17类 (mAP 98.3%)"),
    ("PP-DocBlockLayout", "子区域检测（多栏文档）"),
    ("PicoDet_layout_1x_table", "表格区域检测"),
]

for model_id, description in layout_models:
    model = ALL_MODELS.get(model_id)
    if model:
        print(f"  {model_id:30s} : {description} ({model.size_mb:.1f} MB)")

# 8. 文档视觉语言模型
print("\n" + "=" * 70)
print("8. 文档视觉语言模型 (Doc VLM)")
print("=" * 70)

vlm_models = [
    ("PP-DocBee2-3B", "3B 参数, 7.6GB"),
    ("PP-DocBee-2B", "2B 参数, 4.2GB"),
    ("PP-DocBee-7B", "7B 参数, 15.8GB, 高精度"),
]

for model_id, description in vlm_models:
    model = ALL_MODELS.get(model_id)
    if model:
        print(f"  {model_id:30s} : {description} ({model.size_mb:.1f} MB)")

# 9. 语言代码说明
print("\n" + "=" * 70)
print("9. PaddleOCR 3.3.0 语言代码说明")
print("=" * 70)

print("""
官方 PaddleOCR 3.3.0 支持的语言代码（109种）：

【统一模型】
PP-OCRv5 统一模型支持 5 种文字类型：
  - "ch" : 简体中文（自动支持繁体、英文、日文、韩文、拼音）
  - "en" : 英文
  - "japan" : 日文
  - "korean" : 韩文

【语言组 - 专用优化模型】
以下语言有专门优化的模型，精度显著提升：

1. cyrillic (西里尔字母，20+种语言)
   - 包含：俄语、乌克兰语、白俄罗斯语、保加利亚语、塞尔维亚语等
   - 模型：cyrillic_PP-OCRv5_mobile_rec

2. latin (拉丁语系，37+种语言)
   - 包含：法文、德文、西班牙文、意大利文、葡萄牙文、荷兰文、波兰文等
   - 模型：latin_PP-OCRv5_mobile_rec

3. arabic (阿拉伯语系，20+种语言)
   - 包含：阿拉伯语、波斯语、乌尔都语、普什图语等
   - 模型：arabic_PP-OCRv5_mobile_rec

4. devanagari (印度语系，10+种语言)
   - 包含：印地语、马拉地语、尼泊尔语、孟加拉语等
   - 模型：devanagari_PP-OCRv5_mobile_rec

【语言专用模型】（更进一步提升特定语言精度）
以下语言有单独优化的模型：

1. th (泰语)
   - 模型：th_PP-OCRv5_mobile_rec
   - 精度：82.68%

2. el (希腊语)
   - 模型：el_PP-OCRv5_mobile_rec
   - 精度：89.28%

3. ta (泰米尔语)
   - 模型：ta_PP-OCRv5_mobile_rec
   - 精度：94.2%

4. te (泰卢固语)
   - 模型：te_PP-OCRv5_mobile_rec
   - 精度：87.65%

【单一语言列表】（PP-OCRv4/v4 时代，109种语言）
欧洲语言 (29种)：
  af, az, bs, cs, cy, da, de, es, et, fi, fr, ga, hr, hu, is, it,
  lt, lv, mi, ms, nl, no, oc, pi, pl, pt, ro, rs_latin, sk, sl, sq, sv, tr, vi

斯拉夫语言 (6种)：
  be, bg, mk, ru, uk, sr

亚洲语言 (4种)：
  id, ku, la, ms

阿拉伯语系 (4种)：
  ar, fa, ug, ur

印度语系 (10种)：
  hi, mr, ne, bh, mai, ang, bho, mah, sck, new, gom, sa, bgc

其他语言 (2种)：
  sw (斯瓦希里语), uz (乌兹别克语)

【已弃用的语言代码】
以下语言代码在旧文档中出现，但建议避免使用：
  - "flemish" (已弃用，使用 "nl" 代替)
  - "german" (已弃用，使用 "de" 代替)
  - "english" (别名，使用 "en" 代替)
  - "chinese" (别名，使用 "ch" 代替)
  - "japanese" (别名，使用 "japan" 代替)

【语言选择建议】
- 新项目：使用 PP-OCRv5 统一模型（"ch"）支持5种文字类型
- 多语言文档：使用统一模型 "ch"
- 单一语言批量：考虑使用语言组模型（如 "latin", "arabic"）
- 特定语言优化：使用专用语言模型（如 "th", "el", "ta"）
- 需要最高精度：使用语言专用模型而非统一模型
""")

# 10. 为什么保留 v4 模型？
print("\n" + "=" * 70)
print("10. 为什么保留 PP-OCRv4 模型？")
print("=" * 70)

print("""
PP-OCRv5 是 PaddleOCR 3.x 的最新版本（2025年发布），主要改进：
  - 精度提升 13%（中英文混合识别）
  - 手写文本错误率降低 26%
  - 支持更多语言（109种 vs 80+种）
  - 更大的字典（识别更多字符）

然而，保留 PP-OCRv4 模型有以下重要原因：

【1. 向后兼容性】
  - 现有用户配置可能使用 v4
  - v4 模型已经在生产环境验证过，更稳定
  - 允许用户平滑迁移到 v5，避免强制升级

【2. 特定场景优势】
  - 某些语言可能在 v4 上有更好的支持
  - 部分语种的模型可能只有 v4 版本
  - 某些硬件配置下 v4 的性能可能更优

【3. 性能考虑】
  - v4 模型在某些硬件上可能有更优的性能
  - 用户可以根据场景选择速度 vs 精度
  - 对于不需要多语言混合的场景，v4 可能更快

【4. 渐进式迁移策略】
  - 保留 v4 允许用户 A/B 测试两个版本的效果
  - 避免"一刀切"强制升级可能带来的问题
  - 用户可以验证 v5 在其场景下是否真的更好
  - 如果 v5 在特定场景下表现不佳，可以回退到 v4

【推荐使用策略】
  ✓ 新项目：默认使用 PP-OCRv5
  ✓ 生产环境：建议使用 v5（精度提升）
  ✓ 需要稳定：可以选择 v4（经验证）
  ✓ 特定场景：根据实际测试结果选择
  ✓ 语言优化场景：使用专用优化模型（v5 多语言扩展或语言专用模型）

【注意】
  PP-OCRv3 已标记为 deprecated，不建议使用
  v4 不会是永久保留的，随着 v5 稳定性和覆盖率提升，最终会淘汰
""")

# 11. 改进建议
print("\n" + "=" * 70)
print("11. 改进建议")
print("=" * 70)

print("""
【高优先级】
1. ✓ 统一模型定义
   - model_manager.py 已引用 model_download_config.py 的完整模型定义
   - 避免模型定义分散在多个文件中

2. ⚠️ 验证语言代码
   - 对照官方 PaddleOCR 3.3.0 文档验证所有语言代码
   - 移除已弃用的语言代码（flemish, german 等）
   - 添加语言代码验证逻辑

3. ⚠️ 完成功能实现
   - 实现 paddle_engine.py 中的 _recognize_structure 方法
   - 集成版面分析模型（PP-DocLayout）
   - 集成表格识别模型（SLANet/SLANeXt）
   - 集成公式识别模型（PP-FormulaNet）

【中优先级】
4. ⚠️ 添加移动端模型
   - 当前配置仅包含服务端模型（server）
   - 建议添加移动端模型（mobile）以支持 CPU/边缘设备
   - 示例：
     * ppocrv5_mobile_det (~30MB)
     * ppocrv5_mobile_rec (~4.5MB)

5. 考虑旧引擎整合
   - 当前有 6 个旧引擎文件与新的 paddle_engine.py 并存
   - 考虑弃用或整合旧引擎，避免代码冗余
   - 旧文件：
     * paddleocr_direct.py
     * paddle_ocrv5.py
     * paddle_vl.py
     * paddle_structure.py
     * paddle_chat.py

【低优先级】
6. 添加模型管理 UI
   - 利用 model_manager 的信号机制
   - 显示下载进度、速度、剩余时间
   - 提供模型查看、缓存管理界面

7. 实现模型预设加载
   - 支持按预设自动下载和加载所需模型
   - 提供预设选择的 UI 界面

【总体评价】
重构方向：✓ 正确 - 向统一管理、完整模型覆盖、企业级架构发展
当前状态：⚠️ 中间阶段 - 新旧代码并存，功能实现不完整
下一步：
  1. 验证并修复语言代码
  2. 完成高级功能的实现
  3. 添加移动端模型支持
  4. 整合或弃用旧引擎文件

风险：如果不尽快解决新旧代码冗余问题，技术债务会持续累积
""")

print("\n" + "=" * 70)
print("报告生成完成")
print("=" * 70)
print(
    f"生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
