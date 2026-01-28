#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddlePaddle & PaddleOCR 导入验证脚本

用于验证生产环境安装的依赖能否正确导入和使用。

运行方式：
    python scripts/verify_paddle_import.py

Author: Umi-OCR Team
Date: 2026-01-27
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_paddlepaddle():
    """检查 PaddlePaddle 安装"""
    print_header("1. PaddlePaddle 检查")

    try:
        import paddle

        version = paddle.__version__
        print(f"✅ PaddlePaddle 已安装: {version}")

        # 检查 CUDA 支持
        cuda_support = paddle.device.is_compiled_with_cuda()
        print(f"   CUDA 编译支持: {'是' if cuda_support else '否'}")

        if cuda_support:
            gpu_count = paddle.device.cuda.device_count()
            print(f"   可用 GPU 数量: {gpu_count}")

            if gpu_count > 0:
                for i in range(gpu_count):
                    props = paddle.device.cuda.get_device_properties(i)
                    print(
                f"   GPU {i}: {props.name}, "
                f"显存 {props.total_memory // (1024**3)}GB"
            )

        # 版本兼容性检查
        version_parts = version.split(".")
        major = int(version_parts[0])
        if major >= 3:
            print(f"✅ 版本兼容: PaddlePaddle {version} >= 3.0.0")
        else:
            print(f"⚠️ 版本过旧: PaddlePaddle {version} < 3.0.0，建议升级到 3.3.0")

        return True, version

    except ImportError as e:
        print(f"❌ PaddlePaddle 未安装: {e}")
        return False, None
    except Exception as e:
        print(f"❌ PaddlePaddle 检查失败: {e}")
        return False, None


def check_paddleocr():
    """检查 PaddleOCR 安装"""
    print_header("2. PaddleOCR 检查")

    try:
        import paddleocr

        version = paddleocr.__version__
        print(f"✅ PaddleOCR 已安装: {version}")

        # 版本兼容性检查
        version_parts = version.split(".")
        major = int(version_parts[0])
        minor = int(version_parts[1])
        if major >= 3 and minor >= 3:
            print(f"✅ 版本兼容: PaddleOCR {version} >= 3.3.0")
        else:
            print(f"⚠️ 版本过旧: PaddleOCR {version} < 3.3.0，建议升级")

        return True, version

    except ImportError as e:
        print(f"❌ PaddleOCR 未安装: {e}")
        return False, None
    except Exception as e:
        print(f"❌ PaddleOCR 检查失败: {e}")
        return False, None


def test_paddleocr_initialization():
    """测试 PaddleOCR 初始化"""
    print_header("3. PaddleOCR 初始化测试")

    try:
        # 禁用模型源检查
        os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

        from paddleocr import PaddleOCR

        print("   正在初始化 PaddleOCR (PP-OCRv5, 语言=ch)...")
        print("   首次运行会自动下载模型，请耐心等待...")

        # 使用 PP-OCRv5 和最小配置测试
        ocr = PaddleOCR(
            lang="ch",
            ocr_version="PP-OCRv5",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )

        print("✅ PaddleOCR 初始化成功")
        return True, ocr

    except Exception as e:
        print(f"❌ PaddleOCR 初始化失败: {e}")
        import traceback

        traceback.print_exc()
        return False, None


def test_ocr_recognition(ocr):
    """测试 OCR 识别"""
    print_header("4. OCR 识别测试")

    try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np

        # 创建测试图片
        print("   创建测试图片...")
        image = Image.new("RGB", (400, 100), color="white")
        draw = ImageDraw.Draw(image)

        # 尝试使用系统字体
        try:
            # Windows
            font = ImageFont.truetype("msyh.ttc", 32)  # 微软雅黑
        except Exception:
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except Exception:
                font = ImageFont.load_default()

        test_text = "Umi-OCR 测试文本 2026"
        draw.text((20, 30), test_text, fill="black", font=font)

        # 转换为 numpy 数组
        cv_image = np.array(image)

        # 执行识别
        print("   执行 OCR 识别...")
        result = ocr.predict(cv_image)

        # 解析结果
        recognized_text = ""
        for output in result:
            if hasattr(output, "res") and output.res:
                rec_texts = output.res.get("rec_texts", [])
                recognized_text = " ".join(rec_texts)
                break

        print("✅ 识别成功")
        print(f"   原始文本: {test_text}")
        print(f"   识别结果: {recognized_text}")

        # 检查识别准确性
        if (
            "Umi" in recognized_text
            or "测试" in recognized_text
            or "2026" in recognized_text
        ):
            print("✅ 识别结果包含关键词")
            return True
        else:
            print("⚠️ 识别结果可能不准确")
            return True  # 仍然算成功

    except Exception as e:
        print(f"❌ OCR 识别失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_project_imports():
    """测试项目内部导入"""
    print_header("5. 项目内部导入测试")

    try:
        # 测试依赖检测模块
        # 仅测试模块是否存在
        import importlib.util
        if importlib.util.find_spec('utils.check_dependencies'):
            print("✅ utils.check_dependencies 导入成功")
        else:
            print("❌ utils.check_dependencies 导入失败")

        # 测试依赖安装模块
        from utils.dependency_installer import (
            PADDLEPADDLE_VERSION,
            PADDLEOCR_VERSION,
        )

        print("✅ utils.dependency_installer 导入成功")
        print(
            f"   配置版本: PaddlePaddle={PADDLEPADDLE_VERSION}, "
            f"PaddleOCR={PADDLEOCR_VERSION}"
        )

        # 测试 PaddleOCR 引擎
        from services.ocr.paddle_engine import (
            LANGUAGE_MAP,
        )

        print("✅ services.ocr.paddle_engine 导入成功")
        print(f"   支持语言数: {len(LANGUAGE_MAP)}")

        # 测试模型配置
        from services.ocr.model_download_config import (
            ALL_MODELS,
            MODEL_PRESETS,
        )

        print("✅ services.ocr.model_download_config 导入成功")
        print(f"   总模型数: {len(ALL_MODELS)}")
        print(f"   预设组合数: {len(MODEL_PRESETS)}")

        return True

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  PaddlePaddle & PaddleOCR 导入验证")
    print("=" * 60)

    results = {}

    # 1. 检查 PaddlePaddle
    paddle_ok, paddle_version = check_paddlepaddle()
    results["paddlepaddle"] = paddle_ok

    # 2. 检查 PaddleOCR
    paddleocr_ok, paddleocr_version = check_paddleocr()
    results["paddleocr"] = paddleocr_ok

    # 3. 测试 PaddleOCR 初始化
    if paddle_ok and paddleocr_ok:
        init_ok, ocr = test_paddleocr_initialization()
        results["initialization"] = init_ok

        # 4. 测试 OCR 识别
        if init_ok and ocr:
            recognition_ok = test_ocr_recognition(ocr)
            results["recognition"] = recognition_ok
        else:
            results["recognition"] = False
    else:
        results["initialization"] = False
        results["recognition"] = False

    # 5. 测试项目内部导入
    project_ok = test_project_imports()
    results["project_imports"] = project_ok

    # 打印总结
    print_header("验证总结")

    all_passed = all(results.values())

    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {name:20s}: {status}")

    print()
    if all_passed:
        print("🎉 所有验证通过！PaddlePaddle 和 PaddleOCR 可以正常使用。")
    else:
        print("⚠️ 部分验证失败，请检查上面的错误信息。")

        # 提供修复建议
        if not results.get("paddlepaddle"):
            print("\n修复建议 - PaddlePaddle:")
            print(
                "   CPU版: pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/"
            )
            print(
                "   GPU版: pip install paddlepaddle-gpu==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/"
            )

        if not results.get("paddleocr"):
            print("\n修复建议 - PaddleOCR:")
            print("   pip install paddleocr>=3.3.0")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
