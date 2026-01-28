#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QRCodeScanner 性能基准测试

测试二维码扫描器的性能，包括：
- QPixmap 转换性能
- 不同尺寸图片的扫描性能
- 批量扫描性能
- 内存使用
- 与文件路径扫描的对比

Author: Umi-OCR Team
Date: 2026-01-28
"""

import unittest
import time
import tempfile
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QBuffer, QIODevice
from PySide6.QtGui import QImage, QPixmap, QPainter
from PIL import Image, ImageDraw, ImageFont

from src.services.qrcode.qrcode_scanner import QRCodeScanner


class TestQRCodeScannerPerformance(unittest.TestCase):
    """QRCodeScanner 性能测试"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

        cls.scanner = QRCodeScanner()

    def test_qimage_to_pil_conversion_performance(self):
        """测试 QImage 到 PIL 转换性能"""
        # 创建测试图像
        qimage = QImage(1920, 1080, QImage.Format.Format_RGB32)
        qimage.fill(0xFFFFFFFF)

        # 测试转换性能
        start_time = time.time()
        iterations = 100

        for _ in range(iterations):
            buffer = QBuffer()
            buffer.open(QIODevice.ReadWrite)
            qimage.save(buffer, "PNG")
            buffer_data = buffer.data()
            pil_image = Image.open(__import__('io').BytesIO(bytes(buffer_data)))

        end_time = time.time()
        avg_time = (end_time - start_time) / iterations * 1000  # 转换为毫秒

        print(f"\nQImage -> PIL 转换平均时间: {avg_time:.2f} ms")

        # 平均时间应该在 50ms 以内
        self.assertLess(avg_time, 50, "QImage 到 PIL 转换性能不够好")

    def test_scan_small_image_performance(self):
        """测试小图像扫描性能"""
        # 创建包含二维码的小图像 (640x480)
        qimage = QImage(640, 480, QImage.Format.Format_RGB32)
        qimage.fill(0xFFFFFFFF)

        # 绘制简单的二维码区域（白色背景上的黑色方块）
        painter = QPainter(qimage)
        painter.fillRect(100, 100, 200, 200, 0xFF000000)
        painter.end()

        pixmap = QPixmap.fromImage(qimage)

        # 测试扫描性能
        start_time = time.time()
        iterations = 10

        for _ in range(iterations):
            results = self.scanner.scan_from_pixmap(pixmap)

        end_time = time.time()
        avg_time = (end_time - start_time) / iterations * 1000

        print(f"\n小图像 (640x480) 扫描平均时间: {avg_time:.2f} ms")

        # 小图像扫描应该在 20ms 以内
        self.assertLess(avg_time, 20, "小图像扫描性能不够好")

    def test_scan_hd_image_performance(self):
        """测试 HD 图像扫描性能"""
        # 创建 HD 图像 (1920x1080)
        qimage = QImage(1920, 1080, QImage.Format.Format_RGB32)
        qimage.fill(0xFFFFFFFF)

        pixmap = QPixmap.fromImage(qimage)

        # 测试扫描性能
        start_time = time.time()
        iterations = 10

        for _ in range(iterations):
            results = self.scanner.scan_from_pixmap(pixmap)

        end_time = time.time()
        avg_time = (end_time - start_time) / iterations * 1000

        print(f"\nHD 图像 (1920x1080) 扫描平均时间: {avg_time:.2f} ms")

        # HD 图像扫描应该在 100ms 以内
        self.assertLess(avg_time, 100, "HD 图像扫描性能不够好")

    def test_scan_4k_image_performance(self):
        """测试 4K 图像扫描性能"""
        # 创建 4K 图像 (3840x2160)
        qimage = QImage(3840, 2160, QImage.Format.Format_RGB32)
        qimage.fill(0xFFFFFFFF)

        pixmap = QPixmap.fromImage(qimage)

        # 测试扫描性能
        start_time = time.time()
        iterations = 5

        for _ in range(iterations):
            results = self.scanner.scan_from_pixmap(pixmap)

        end_time = time.time()
        avg_time = (end_time - start_time) / iterations * 1000

        print(f"\n4K 图像 (3840x2160) 扫描平均时间: {avg_time:.2f} ms")

        # 4K 图像扫描应该在 300ms 以内
        self.assertLess(avg_time, 300, "4K 图像扫描性能不够好")

    def test_batch_scan_performance(self):
        """测试批量扫描性能"""
        # 创建多个测试图像
        pixmaps = []
        for _ in range(10):
            qimage = QImage(800, 600, QImage.Format.Format_RGB32)
            qimage.fill(0xFFFFFFFF)
            pixmaps.append(QPixmap.fromImage(qimage))

        # 测试批量扫描性能
        start_time = time.time()

        for pixmap in pixmaps:
            results = self.scanner.scan_from_pixmap(pixmap)

        end_time = time.time()
        total_time = end_time - start_time * 1000
        avg_time = total_time / len(pixmaps)

        print(f"\n批量扫描 10 张图像总时间: {total_time:.2f} ms")
        print(f"每张图像平均时间: {avg_time:.2f} ms")

        # 每张图像扫描应该在 30ms 以内
        self.assertLess(avg_time, 30, "批量扫描性能不够好")

    def test_file_vs_pixmap_performance(self):
        """测试文件路径扫描 vs QPixmap 扫描性能"""
        import io

        # 创建临时图像文件
        qimage = QImage(1920, 1080, QImage.Format.Format_RGB32)
        qimage.fill(0xFFFFFFFF)

        # 保存为文件
        buffer = QBuffer()
        buffer.open(QIODevice.ReadWrite)
        qimage.save(buffer, "PNG")
        buffer_data = bytes(buffer.data())

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(buffer_data)
            temp_file = f.name

        try:
            # 创建 QPixmap
            pixmap = QPixmap.fromImage(qimage)

            # 测试文件路径扫描
            start_time = time.time()
            iterations = 20

            for _ in range(iterations):
                results_file = self.scanner.scan_from_image(temp_file)

            file_time = time.time() - start_time

            # 测试 QPixmap 扫描
            start_time = time.time()

            for _ in range(iterations):
                results_pixmap = self.scanner.scan_from_pixmap(pixmap)

            pixmap_time = time.time() - start_time

            avg_file_time = (file_time / iterations) * 1000
            avg_pixmap_time = (pixmap_time / iterations) * 1000

            print(f"\n文件路径扫描平均时间: {avg_file_time:.2f} ms")
            print(f"QPixmap 扫描平均时间: {avg_pixmap_time:.2f} ms")

            # QPixmap 扫描应该比文件扫描快（减少了磁盘 I/O）
            # 或者至少不应该慢太多
            ratio = avg_pixmap_time / avg_file_time
            print(f"QPixmap 扫描 / 文件扫描比率: {ratio:.2f}")

            self.assertLess(ratio, 2.0, "QPixmap 扫描比文件路径扫描慢太多")

        finally:
            # 清理临时文件
            Path(temp_file).unlink()

    def test_memory_efficiency(self):
        """测试内存效率"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 执行多次扫描
        iterations = 50
        for i in range(iterations):
            qimage = QImage(1920, 1080, QImage.Format.Format_RGB32)
            qimage.fill(0xFFFFFFFF)
            pixmap = QPixmap.fromImage(qimage)
            results = self.scanner.scan_from_pixmap(pixmap)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"\n初始内存: {initial_memory:.2f} MB")
        print(f"最终内存: {final_memory:.2f} MB")
        print(f"内存增长: {memory_increase:.2f} MB ({iterations} 次扫描)")

        # 内存增长不应该超过 50MB（50 次扫描）
        self.assertLess(memory_increase, 50, "内存使用增长过大")

    def test_no_temp_files_created(self):
        """测试不创建临时文件"""
        import tempfile

        # 记录当前临时文件数量
        temp_dir = tempfile.gettempdir()
        before_files = set(Path(temp_dir).glob('*.png'))

        # 执行多次扫描
        for _ in range(20):
            qimage = QImage(1920, 1080, QImage.Format.Format_RGB32)
            qimage.fill(0xFFFFFFFF)
            pixmap = QPixmap.fromImage(qimage)
            results = self.scanner.scan_from_pixmap(pixmap)

        # 检查临时文件数量
        after_files = set(Path(temp_dir).glob('*.png'))
        new_files = after_files - before_files

        print(f"\n新创建的临时文件数量: {len(new_files)}")

        # 不应该创建新的临时文件
        self.assertEqual(len(new_files), 0, "扫描过程创建了临时文件")

    def test_conversion_accuracy(self):
        """测试转换准确性"""
        # 创建包含特定颜色模式的测试图像
        qimage = QImage(400, 400, QImage.Format.Format_RGBA8888)

        # 绘制不同颜色的区域
        painter = QPainter(qimage)
        painter.fillRect(0, 0, 200, 200, 0xFFFF0000)  # 红色
        painter.fillRect(200, 0, 200, 200, 0xFF00FF00)  # 绿色
        painter.fillRect(0, 200, 200, 200, 0xFF0000FF)  # 蓝色
        painter.fillRect(200, 200, 200, 200, 0xFFFFFF00)  # 黄色
        painter.end()

        pixmap = QPixmap.fromImage(qimage)

        # 扫描
        results = self.scanner.scan_from_pixmap(pixmap)

        # 验证扫描不会崩溃
        self.assertIsInstance(results, list)

        # 即使没有二维码，也应该返回空列表而不是报错
        self.assertEqual(len(results), 0)


def run_performance_benchmarks():
    """运行所有性能测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestQRCodeScannerPerformance))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*70)
    print("性能基准测试完成")
    print("="*70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_performance_benchmarks()
    import sys
    sys.exit(0 if success else 1)
