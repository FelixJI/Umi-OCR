#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 重构阶段13-17集成测试

测试服务层、控制器和UI层的集成。

Author: Umi-OCR Team
Date: 2026-01-27
"""

import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication

from services.screenshot.screen_capture import ScreenCaptureService
from services.screenshot.region_selector import RegionSelector
from services.pdf.pdf_parser import PDFParser
from services.qrcode.qrcode_scanner import QRCodeScanner
from services.qrcode.qrcode_generator import QRCodeGenerator
from services.export.text_exporter import TextExporter
from services.export.json_exporter import JsonExporter
from services.export.excel_exporter import ExcelExporter
from services.export.pdf_exporter import PdfExporter

from controllers.screenshot_controller import ScreenshotController
from controllers.batch_ocr_controller import BatchOcrController
from controllers.batch_doc_controller import BatchDocController
from controllers.qrcode_controller import QRCodeController

from ui.screenshot_ocr.screenshot_ocr import ScreenshotOCRView
from ui.batch_ocr.batch_ocr import BatchOCRView
from ui.batch_doc.batch_doc import BatchDocView
from ui.qrcode.qrcode import QRCodeView


class IntegrationTest:
    """集成测试"""

    def __init__(self):
        """初始化测试"""
        self.app = QApplication(sys.argv)
        self.test_results = []

    def test_service_layer(self):
        """测试服务层"""
        print("测试服务层...")

        try:
            # 测试截图服务
            screen_capture = ScreenCaptureService()
            assert screen_capture is not None
            print("  ✅ ScreenCaptureService 初始化成功")

            region_selector = RegionSelector()
            assert region_selector is not None
            print("  ✅ RegionSelector 初始化成功")

            # 测试PDF服务
            pdf_parser = PDFParser()
            assert pdf_parser is not None
            print("  ✅ PDFParser 初始化成功")

            # 测试二维码服务
            qr_scanner = QRCodeScanner()
            assert qr_scanner is not None
            print("  ✅ QRCodeScanner 初始化成功")

            qr_generator = QRCodeGenerator()
            assert qr_generator is not None
            print("  ✅ QRCodeGenerator 初始化成功")

            # 测试导出服务
            text_exporter = TextExporter()
            assert text_exporter is not None
            print("  ✅ TextExporter 初始化成功")

            json_exporter = JsonExporter()
            assert json_exporter is not None
            print("  ✅ JsonExporter 初始化成功")

            excel_exporter = ExcelExporter()
            assert excel_exporter is not None
            print("  ✅ ExcelExporter 初始化成功")

            pdf_exporter = PdfExporter()
            assert pdf_exporter is not None
            print("  ✅ PdfExporter 初始化成功")

            self.test_results.append(("服务层", True))

        except Exception as e:
            print(f"  ❌ 服务层测试失败: {e}")
            self.test_results.append(("服务层", False))

    def test_controller_layer(self):
        """测试控制器层"""
        print("\n测试控制器层...")

        try:
            # 测试截图控制器
            screenshot_controller = ScreenshotController()
            assert screenshot_controller is not None
            print("  ✅ ScreenshotController 初始化成功")

            # 测试批量OCR控制器
            batch_ocr_controller = BatchOcrController()
            assert batch_ocr_controller is not None
            print("  ✅ BatchOcrController 初始化成功")

            # 测试批量文档控制器
            batch_doc_controller = BatchDocController()
            assert batch_doc_controller is not None
            print("  ✅ BatchDocController 初始化成功")

            # 测试二维码控制器
            qrcode_controller = QRCodeController()
            assert qrcode_controller is not None
            print("  ✅ QRCodeController 初始化成功")

            self.test_results.append(("控制器层", True))

        except Exception as e:
            print(f"  ❌ 控制器层测试失败: {e}")
            self.test_results.append(("控制器层", False))

    def test_ui_layer(self):
        """测试UI层"""
        print("\n测试UI层...")

        try:
            # 测试截图OCR UI
            screenshot_ui = ScreenshotOCRView()
            assert screenshot_ui is not None
            assert hasattr(screenshot_ui, "_controller")
            print("  ✅ ScreenshotOCRView 初始化成功")

            # 测试批量OCR UI
            batch_ocr_ui = BatchOCRView()
            assert batch_ocr_ui is not None
            assert hasattr(batch_ocr_ui, "_controller")
            print("  ✅ BatchOCRView 初始化成功")

            # 测试批量文档 UI
            batch_doc_ui = BatchDocView()
            assert batch_doc_ui is not None
            assert hasattr(batch_doc_ui, "_controller")
            print("  ✅ BatchDocView 初始化成功")

            # 测试二维码 UI
            qrcode_ui = QRCodeView()
            assert qrcode_ui is not None
            assert hasattr(qrcode_ui, "_controller")
            print("  ✅ QRCodeView 初始化成功")

            self.test_results.append(("UI层", True))

        except Exception as e:
            print(f"  ❌ UI层测试失败: {e}")
            self.test_results.append(("UI层", False))

    def test_controller_methods(self):
        """测试控制器方法"""
        print("\n测试控制器方法...")

        try:
            # 测试BatchOcrController方法
            batch_ocr_controller = BatchOcrController()
            assert hasattr(batch_ocr_controller, "add_files")
            assert hasattr(batch_ocr_controller, "pause_ocr")
            assert hasattr(batch_ocr_controller, "resume_ocr")
            print("  ✅ BatchOcrController 方法完整")

            # 测试BatchDocController方法
            batch_doc_controller = BatchDocController()
            assert hasattr(batch_doc_controller, "process_pdfs")
            assert hasattr(batch_doc_controller, "export_as_searchable_pdf")
            assert hasattr(batch_doc_controller, "export_as_word")
            assert hasattr(batch_doc_controller, "export_as_excel")
            print("  ✅ BatchDocController 方法完整")

            # 测试QRCodeController方法
            qrcode_controller = QRCodeController()
            assert hasattr(qrcode_controller, "scan_qr_code")
            assert hasattr(qrcode_controller, "batch_generate_qr_codes")
            print("  ✅ QRCodeController 方法完整")

            self.test_results.append(("控制器方法", True))

        except Exception as e:
            print(f"  ❌ 控制器方法测试失败: {e}")
            self.test_results.append(("控制器方法", False))

    def test_signal_connections(self):
        """测试信号连接"""
        print("\n测试信号连接...")

        try:
            # 测试控制器信号
            batch_ocr_controller = BatchOcrController()
            assert hasattr(batch_ocr_controller, "tasks_submitted")
            assert hasattr(batch_ocr_controller, "progress_updated")
            assert hasattr(batch_ocr_controller, "tasks_completed")
            assert hasattr(batch_ocr_controller, "tasks_failed")
            print("  ✅ BatchOcrController 信号定义完整")

            batch_doc_controller = BatchDocController()
            assert hasattr(batch_doc_controller, "tasks_submitted")
            assert hasattr(batch_doc_controller, "progress_updated")
            assert hasattr(batch_doc_controller, "tasks_completed")
            assert hasattr(batch_doc_controller, "tasks_failed")
            print("  ✅ BatchDocController 信号定义完整")

            qrcode_controller = QRCodeController()
            assert hasattr(qrcode_controller, "scan_started")
            assert hasattr(qrcode_controller, "scan_completed")
            assert hasattr(qrcode_controller, "generate_started")
            assert hasattr(qrcode_controller, "generate_completed")
            print("  ✅ QRCodeController 信号定义完整")

            self.test_results.append(("信号连接", True))

        except Exception as e:
            print(f"  ❌ 信号连接测试失败: {e}")
            self.test_results.append(("信号连接", False))

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("Umi-OCR 重构阶段13-17集成测试")
        print("=" * 60)

        self.test_service_layer()
        self.test_controller_layer()
        self.test_ui_layer()
        self.test_controller_methods()
        self.test_signal_connections()

        self.print_summary()

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("测试摘要")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, passed in self.test_results if passed)

        for test_name, passed in self.test_results:
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"{test_name}: {status}")

        print("-" * 60)
        print(f"总计: {total_tests} 个测试")
        print(f"通过: {passed_tests} 个")
        print(f"失败: {total_tests - passed_tests} 个")
        print(f"通过率: {passed_tests / total_tests * 100:.1f}%")

        if passed_tests == total_tests:
            print("\n🎉 所有测试通过!")
        else:
            print(f"\n⚠️  有 {total_tests - passed_tests} 个测试失败")

        print("=" * 60)


def main():
    """主函数"""
    test = IntegrationTest()
    test.run_all_tests()


if __name__ == "__main__":
    main()
