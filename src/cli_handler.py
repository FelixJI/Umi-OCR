# src/cli_handler.py
"""
Umi-OCR 命令行处理器

提供命令行模式下的 OCR 功能和 HTTP 服务启动。

功能:
- 单图/批量 OCR（通过任务系统）
- HTTP 服务模式
- 输出格式支持（txt/json）

Author: Umi-OCR Team
Date: 2026-01-27
"""

import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Optional
import argparse

from services.server.http_server import HTTPServer
from services.task.task_manager import TaskManager
from services.task.task_model import TaskStatus
from services.ocr.engine_manager import EngineManager, set_config_manager
from utils.config_manager import get_config_manager

# 配置日志输出到控制台
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("CLI")


class CliHandler:
    """命令行处理器"""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.loop = None
        self._task_manager: Optional[TaskManager] = None
        self._initialized = False

    def run(self) -> int:
        """运行 CLI 任务"""
        # 设置事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            return self.loop.run_until_complete(self._run_async())
        except KeyboardInterrupt:
            logger.info("\n操作已取消")
            return 0
        except Exception as e:
            logger.error(f"Error: {e}")
            return 1
        finally:
            # 清理
            if self._task_manager:
                self._task_manager.shutdown()
            self.loop.close()

    async def _run_async(self) -> int:
        """异步运行主逻辑"""
        # 1. 初始化系统（如果需要 OCR）
        if self.args.image or self.args.server:
            if not await self._initialize():
                logger.error("系统初始化失败")
                return 1

        # 2. 处理 HTTP 服务模式
        if self.args.server:
            return await self._run_server()

        # 3. 处理单次 OCR 任务
        if self.args.image:
            return await self._run_ocr_task()

        logger.error("未指定操作。使用 --help 查看用法。")
        return 1

    async def _initialize(self) -> bool:
        """
        初始化 OCR 系统

        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("正在初始化 OCR 系统...")

            # 1. 初始化配置管理器
            config_manager = get_config_manager()
            set_config_manager(config_manager)

            # 2. 初始化引擎管理器
            engine_manager = EngineManager()
            if not engine_manager.initialize():
                logger.error("引擎管理器初始化失败")
                return False

            # 3. 初始化任务管理器
            self._task_manager = TaskManager.instance()
            if not self._task_manager.initialize():
                logger.error("任务管理器初始化失败")
                return False

            self._initialized = True
            logger.info("OCR 系统初始化完成")
            return True

        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False

    async def _run_server(self) -> int:
        """运行 HTTP 服务"""
        logger.info("正在启动 HTTP 服务...")
        server = HTTPServer()
        await server.start()

        logger.info("HTTP 服务已启动，按 Ctrl+C 停止")

        # 保持运行
        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await server.stop()
            logger.info("HTTP 服务已停止")

        return 0

    async def _run_ocr_task(self) -> int:
        """
        运行 OCR 任务（通过任务系统）

        Returns:
            int: 退出码
        """
        images: List[str] = self.args.image
        output_format = getattr(self.args, 'format', 'txt')
        output_file = getattr(self.args, 'output', None)

        # 验证文件
        valid_images = []
        for img_path in images:
            p = Path(img_path)
            if p.exists() and p.is_file():
                valid_images.append(str(p.resolve()))
            else:
                logger.warning(f"文件不存在: {img_path}")

        if not valid_images:
            logger.error("没有找到有效的图片文件")
            return 1

        logger.info(f"准备处理 {len(valid_images)} 张图片...")

        # 通过 TaskManager 提交任务（强制路由原则）
        group_id = self._task_manager.submit_ocr_tasks(
            image_paths=valid_images,
            title="CLI-OCR",
            priority=10,
            max_concurrency=1
        )

        logger.info(f"任务已提交: {group_id}")

        # 等待任务完成并显示进度
        last_progress = -1
        while True:
            group = self._task_manager.get_group(group_id)
            if not group:
                logger.error("任务组不存在")
                return 1

            # 显示进度
            current_progress = int(group.progress * 100)
            if current_progress != last_progress:
                logger.info(f"进度: {current_progress}% ({group.completed_tasks}/{group.total_tasks})")
                last_progress = current_progress

            # 检查是否完成
            if group.is_terminal():
                break

            await asyncio.sleep(0.5)

        # 获取并输出结果
        group = self._task_manager.get_group(group_id)

        if group.status == TaskStatus.COMPLETED:
            logger.info("所有任务已完成")
        elif group.status == TaskStatus.FAILED:
            logger.warning(f"部分任务失败: {group.failed_tasks}/{group.total_tasks}")
        elif group.status == TaskStatus.CANCELLED:
            logger.warning("任务已取消")
            return 1

        # 输出结果
        self._output_results(group, output_format, output_file)

        return 0

    def _output_results(self, group, output_format: str, output_file: Optional[str]) -> None:
        """
        输出识别结果

        Args:
            group: 任务组
            output_format: 输出格式 (txt/json)
            output_file: 输出文件路径（可选）
        """
        tasks = group.get_all_tasks()

        if output_format == 'json':
            # JSON 格式输出
            results = []
            for task in tasks:
                result_item = {
                    "image_path": task.input_data.get("image_path", ""),
                    "status": task.status.value,
                }
                if task.status == TaskStatus.COMPLETED and task.result:
                    result_item["result"] = task.result
                elif task.status == TaskStatus.FAILED:
                    result_item["error"] = task.error
                results.append(result_item)

            json_output = json.dumps(results, ensure_ascii=False, indent=2)

            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(json_output)
                logger.info(f"结果已保存到: {output_file}")
            else:
                print(json_output)

        else:
            # 纯文本格式输出
            output_lines = []

            for task in tasks:
                image_path = task.input_data.get("image_path", "")
                output_lines.append(f"\n--- {Path(image_path).name} ---")

                if task.status == TaskStatus.COMPLETED and task.result:
                    result = task.result

                    # 提取文本
                    if isinstance(result, dict):
                        text = result.get("text", "")
                        if not text and "blocks" in result:
                            # 从 blocks 提取文本
                            blocks = result["blocks"]
                            text_lines = []
                            for block in blocks:
                                if isinstance(block, dict):
                                    text_lines.append(block.get("text", ""))
                                else:
                                    text_lines.append(str(block))
                            text = "\n".join(text_lines)
                        output_lines.append(text if text else "(无识别结果)")
                    else:
                        output_lines.append(str(result))

                elif task.status == TaskStatus.FAILED:
                    output_lines.append(f"[错误] {task.error or '识别失败'}")

                else:
                    output_lines.append(f"[状态] {task.status.value}")

            text_output = "\n".join(output_lines)

            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(text_output)
                logger.info(f"结果已保存到: {output_file}")
            else:
                print(text_output)
