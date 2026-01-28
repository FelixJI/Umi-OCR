#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖安装流程测试脚本

测试依赖检测、GPU检测、安装服务等核心功能。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_gpu_detection():
    """测试GPU检测"""
    print("\n" + "=" * 60)
    print("测试1: GPU检测")
    print("=" * 60)

    try:
        from utils.gpu_detector import get_gpu_detector

        # 创建检测器
        detector = get_gpu_detector()

        # 检测GPU
        gpu_list = detector.detect_all()

        print(f"\n检测到 {len(gpu_list)} 个GPU:")
        for i, gpu in enumerate(gpu_list, 1):
            print(f"\nGPU {i}:")
            print(f"  名称: {gpu.name}")
            print(f"  厂商: {gpu.vendor.value}")
            print(f"  显存: {gpu.memory_mb} MB ({gpu.memory_mb / 1024:.1f} GB)")
            print(f"  CUDA支持: {gpu.cuda_support}")
            print(f"  CUDA版本: {gpu.cuda_version or 'N/A'}")
            print(f"  建议: {gpu.recommendation}")

        # 获取最佳GPU
        best_gpu = detector.get_best_gpu()
        if best_gpu:
            print(f"\n最佳GPU: {best_gpu.name}")
            print(f"建议: {best_gpu.recommendation}")

        # 获取摘要
        summary = detector.get_summary()
        print("\n摘要:")
        print(f"  GPU总数: {summary['gpu_count']}")
        print(f"  NVIDIA GPU: {summary['nvidia_gpu_available']}")
        print(f"  推荐选项: {summary['recommend_gpu']}")

        print("\n[OK] GPU检测测试通过")
        return True

    except Exception as e:
        print(f"\n[ERROR] GPU检测测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_dependency_check():
    """测试依赖检测"""
    print("\n" + "=" * 60)
    print("测试2: 依赖检测")
    print("=" * 60)

    try:
        from utils.check_dependencies import check_ocr_dependencies

        # 检查依赖
        dep_info = check_ocr_dependencies()

        print("\nPaddlePaddle:")
        print(f"  状态: {dep_info.paddlepaddle.status.value}")
        print(f"  描述: {dep_info.paddlepaddle.description}")
        if dep_info.paddlepaddle.version:
            print(f"  版本: {dep_info.paddlepaddle.version}")
        if dep_info.paddlepaddle.install_command:
            print(f"  安装命令: {dep_info.paddlepaddle.install_command}")

        print("\nPaddleOCR:")
        print(f"  状态: {dep_info.paddleocr.status.value}")
        print(f"  描述: {dep_info.paddleocr.description}")
        if dep_info.paddleocr.version:
            print(f"  版本: {dep_info.paddleocr.version}")
        if dep_info.paddleocr.install_command:
            print(f"  安装命令: {dep_info.paddleocr.install_command}")

        print("\nGPU:")
        print(f"  可用: {dep_info.gpu_available}")
        print(f"  数量: {dep_info.gpu_count}")

        if dep_info.gpu_info_list:
            print("\n检测到的GPU:")
            for i, gpu in enumerate(dep_info.gpu_info_list, 1):
                print(f"  {i}. {gpu.name} ({gpu.vendor.value})")
                print(f"     显存: {gpu.memory_mb // 1024}GB")
                print(f"     建议: {gpu.recommendation}")

        print(
            f"\n推荐安装选项: {dep_info.recommendation.value if dep_info.recommendation else 'N/A'}"
        )

        print("\n[OK] 依赖检测测试通过")
        return True

    except Exception as e:
        print(f"\n[ERROR] 依赖检测测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_mirror_sources():
    """测试镜像源配置"""
    print("\n" + "=" * 60)
    print("测试3: 镜像源配置")
    print("=" * 60)

    try:
        from utils.dependency_installer import DEFAULT_MIRRORS

        print(f"\n配置了 {len(DEFAULT_MIRRORS)} 个镜像源:")

        for i, mirror in enumerate(DEFAULT_MIRRORS, 1):
            print(f"\n{i}. {mirror.name}")
            print(f"   URL: {mirror.url}")
            print(f"   优先级: {mirror.priority}")
            print(f"   官方源: {'是' if mirror.is_official else '否'}")

            # 获取pip命令
            cmd = mirror.get_pip_command()
            print(f"   安装命令: {' '.join(cmd[:5])}...")

        print("\n[OK] 镜像源配置测试通过")
        return True

    except Exception as e:
        print(f"\n[ERROR] 镜像源配置测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_install_config():
    """测试安装配置"""
    print("\n" + "=" * 60)
    print("测试4: 安装配置")
    print("=" * 60)

    try:
        from utils.dependency_installer import InstallConfig, InstallOption

        # 测试CPU配置
        cpu_config = InstallConfig(option=InstallOption.CPU)
        print("\nCPU配置:")
        print(f"  选项: {cpu_config.option.value}")
        print(f"  镜像源数量: {len(cpu_config.mirrors)}")
        print(f"  最大重试: {cpu_config.max_retries}")
        print(f"  超时: {cpu_config.timeout}秒")

        # 测试GPU配置
        gpu_config = InstallConfig(option=InstallOption.GPU)
        print("\nGPU配置:")
        print(f"  选项: {gpu_config.option.value}")

        # 测试SKIP配置
        skip_config = InstallConfig(option=InstallOption.SKIP)
        print("\nSKIP配置:")
        print(f"  选项: {skip_config.option.value}")

        print("\n[OK] 安装配置测试通过")
        return True

    except Exception as e:
        print(f"\n[ERROR] 安装配置测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Umi-OCR 依赖安装流程测试")
    print("=" * 60)

    # 运行所有测试
    results = []
    results.append(("GPU检测", test_gpu_detection()))
    results.append(("依赖检测", test_dependency_check()))
    results.append(("镜像源配置", test_mirror_sources()))
    results.append(("安装配置", test_install_config()))

    # 打印测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{name:20s} {status}")

    print(f"\n总计: {passed}/{total} 个测试通过")

    if passed == total:
        print("\n所有测试通过！依赖安装流程准备就绪。")
        return 0
    else:
        print(f"\n警告: {total - passed} 个测试失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
