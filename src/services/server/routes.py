# src/services/server/routes.py
"""
Umi-OCR HTTP API 路由

提供 OCR 相关的 HTTP API 接口。

接口列表:
- POST /api/ocr - 单图 OCR（同步等待结果）
- POST /api/ocr/batch - 批量 OCR（异步，返回 group_id）
- GET /api/task/{task_id} - 查询任务状态
- GET /api/task/{task_id}/result - 查询任务结果
- GET /api/health - 健康检查

Author: Umi-OCR Team
Date: 2026-01-27
"""

import os
import base64
import logging
import asyncio
import tempfile
import time
from typing import List, Optional

from aiohttp import web

from services.task.task_manager import TaskManager
from services.task.task_model import TaskStatus

logger = logging.getLogger(__name__)


# =============================================================================
# 工具函数
# =============================================================================


async def wait_for_group_completion(group_id: str, timeout: float = 30.0) -> bool:
    """
    等待任务组完成

    Args:
        group_id: 任务组 ID
        timeout: 超时时间（秒）

    Returns:
        bool: 是否在超时前完成
    """
    task_manager = TaskManager.instance()
    start_time = time.time()

    while time.time() - start_time < timeout:
        group = task_manager.get_group(group_id)
        if group and group.is_terminal():
            return True
        await asyncio.sleep(0.1)

    return False


def save_temp_image(image_b64: str) -> Optional[str]:
    """
    将 base64 图片保存为临时文件

    Args:
        image_b64: base64 编码的图片数据

    Returns:
        Optional[str]: 临时文件路径，失败返回 None
    """
    try:
        image_bytes = base64.b64decode(image_b64)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(image_bytes)
            return tmp.name

    except Exception as e:
        logger.error(f"保存临时图片失败: {e}")
        return None


def cleanup_temp_files(file_paths: List[str]) -> None:
    """
    清理临时文件

    Args:
        file_paths: 文件路径列表
    """
    for path in file_paths:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {path}, {e}")


def error_response(
    message: str, code: str = "ERROR", status: int = 500
) -> web.Response:
    """
    生成错误响应

    Args:
        message: 错误消息
        code: 错误码
        status: HTTP 状态码

    Returns:
        web.Response: JSON 响应
    """
    return web.json_response(
        {"success": False, "error_code": code, "error_message": message}, status=status
    )


# =============================================================================
# API 路由处理
# =============================================================================


async def handle_ocr(request: web.Request) -> web.Response:
    """
    单张图片 OCR（同步等待结果）

    POST /api/ocr
    Body: {
        "image": "base64...",     # base64 编码的图片
        "timeout": 30             # 超时时间（秒），可选，默认 30
    }

    Returns: {
        "success": true,
        "result": {
            "text": "识别文本",
            "blocks": [...],
            "confidence": 0.95,
            "duration_ms": 123
        }
    }
    """
    tmp_path = None

    try:
        data = await request.json()
        image_b64 = data.get("image")
        timeout = data.get("timeout", 30)

        if not image_b64:
            return error_response("缺少 image 字段", "MISSING_IMAGE", 400)

        # 保存临时文件
        tmp_path = save_temp_image(image_b64)
        if not tmp_path:
            return error_response("图片解码失败", "DECODE_ERROR", 400)

        # 通过 TaskManager 提交任务（强制路由原则）
        task_manager = TaskManager.instance()
        group_id = task_manager.submit_ocr_tasks(
            image_paths=[tmp_path], title="HTTP-OCR", priority=10, max_concurrency=1
        )

        logger.info(f"OCR 任务已提交: {group_id}")

        # 等待任务完成
        completed = await wait_for_group_completion(group_id, timeout)

        if not completed:
            # 超时，取消任务
            task_manager.cancel_group(group_id)
            return error_response("OCR 任务超时", "TIMEOUT", 408)

        # 获取结果
        group = task_manager.get_group(group_id)
        if not group:
            return error_response("任务结果不存在", "RESULT_NOT_FOUND", 500)

        tasks = group.get_all_tasks()
        if not tasks:
            return error_response("任务为空", "EMPTY_TASK", 500)

        task = tasks[0]

        if task.status == TaskStatus.COMPLETED and task.result:
            return web.json_response({"success": True, "result": task.result})
        elif task.status == TaskStatus.FAILED:
            return error_response(task.error or "OCR 识别失败", "OCR_FAILED", 500)
        else:
            return error_response(
                f"任务状态异常: {task.status.value}", "UNEXPECTED_STATUS", 500
            )

    except Exception as e:
        logger.error(f"OCR 请求处理失败: {e}", exc_info=True)
        return error_response(str(e), "INTERNAL_ERROR", 500)

    finally:
        # 清理临时文件
        if tmp_path:
            cleanup_temp_files([tmp_path])


async def handle_ocr_batch(request: web.Request) -> web.Response:
    """
    批量 OCR（异步，立即返回 group_id）

    POST /api/ocr/batch
    Body: {
        "images": ["base64...", "base64..."],  # base64 编码的图片数组
        "title": "批量任务",                    # 任务标题，可选
        "max_concurrency": 3                   # 最大并发数，可选，默认 3
    }

    Returns: {
        "success": true,
        "group_id": "xxx-xxx-xxx",
        "total_count": 10
    }
    """
    tmp_paths = []

    try:
        data = await request.json()
        images = data.get("images", [])
        title = data.get("title", "HTTP-BatchOCR")
        max_concurrency = data.get("max_concurrency", 3)

        if not images:
            return error_response("缺少 images 字段", "MISSING_IMAGES", 400)

        if not isinstance(images, list):
            return error_response("images 必须是数组", "INVALID_IMAGES", 400)

        # 保存所有临时文件
        for i, img_b64 in enumerate(images):
            tmp_path = save_temp_image(img_b64)
            if tmp_path:
                tmp_paths.append(tmp_path)
            else:
                logger.warning(f"第 {i+1} 张图片解码失败，跳过")

        if not tmp_paths:
            return error_response("所有图片解码失败", "ALL_DECODE_ERROR", 400)

        # 提交任务组
        task_manager = TaskManager.instance()
        group_id = task_manager.submit_ocr_tasks(
            image_paths=tmp_paths,
            title=title,
            priority=5,
            max_concurrency=max_concurrency,
        )

        logger.info(f"批量 OCR 任务已提交: {group_id}, 共 {len(tmp_paths)} 张")

        # 注意：批量任务的临时文件需要在任务完成后清理
        # 这里简化处理，实际应该在任务完成回调中清理
        # 或者使用带清理机制的临时目录

        return web.json_response(
            {"success": True, "group_id": group_id, "total_count": len(tmp_paths)}
        )

    except Exception as e:
        logger.error(f"批量 OCR 请求处理失败: {e}", exc_info=True)
        # 清理已创建的临时文件
        cleanup_temp_files(tmp_paths)
        return error_response(str(e), "INTERNAL_ERROR", 500)


async def handle_task_status(request: web.Request) -> web.Response:
    """
    查询任务状态

    GET /api/task/{task_id}

    Returns: {
        "success": true,
        "id": "xxx",
        "status": "running",
        "progress": 0.5,
        "title": "任务标题",
        "total_tasks": 10,
        "completed_tasks": 5,
        "failed_tasks": 0
    }
    """
    task_id = request.match_info["task_id"]
    task_manager = TaskManager.instance()
    group = task_manager.get_group(task_id)

    if not group:
        return error_response("任务不存在", "TASK_NOT_FOUND", 404)

    return web.json_response(
        {
            "success": True,
            "id": group.id,
            "status": group.status.value,
            "progress": group.progress,
            "title": group.title,
            "total_tasks": group.total_tasks,
            "completed_tasks": group.completed_tasks,
            "failed_tasks": group.failed_tasks,
        }
    )


async def handle_task_result(request: web.Request) -> web.Response:
    """
    查询任务结果

    GET /api/task/{task_id}/result

    Returns: {
        "success": true,
        "group_id": "xxx",
        "status": "completed",
        "progress": 1.0,
        "results": [
            {
                "task_id": "xxx",
                "status": "completed",
                "result": {...}
            },
            ...
        ]
    }
    """
    task_id = request.match_info["task_id"]
    task_manager = TaskManager.instance()
    group = task_manager.get_group(task_id)

    if not group:
        return error_response("任务不存在", "TASK_NOT_FOUND", 404)

    # 收集所有任务结果
    results = []
    for task in group.get_all_tasks():
        results.append(
            {
                "task_id": task.id,
                "status": task.status.value,
                "result": task.result,
                "error": task.error,
            }
        )

    return web.json_response(
        {
            "success": True,
            "group_id": group.id,
            "status": group.status.value,
            "progress": group.progress,
            "results": results,
        }
    )


async def handle_task_cancel(request: web.Request) -> web.Response:
    """
    取消任务

    POST /api/task/{task_id}/cancel

    Returns: {
        "success": true,
        "message": "任务已取消"
    }
    """
    task_id = request.match_info["task_id"]
    task_manager = TaskManager.instance()
    group = task_manager.get_group(task_id)

    if not group:
        return error_response("任务不存在", "TASK_NOT_FOUND", 404)

    if group.is_terminal():
        return error_response("任务已结束，无法取消", "TASK_FINISHED", 400)

    task_manager.cancel_group(task_id)

    return web.json_response({"success": True, "message": "任务已取消"})


async def handle_health(request: web.Request) -> web.Response:
    """
    健康检查

    GET /api/health

    Returns: {
        "status": "ok",
        "version": "2.0.0"
    }
    """
    return web.json_response({"status": "ok", "version": "2.0.0"})


# =============================================================================
# 路由注册
# =============================================================================


def setup_routes(app: web.Application):
    """
    注册所有路由

    Args:
        app: aiohttp Application
    """
    # OCR 接口
    app.router.add_post("/api/ocr", handle_ocr)
    app.router.add_post("/api/ocr/batch", handle_ocr_batch)

    # 任务接口
    app.router.add_get("/api/task/{task_id}", handle_task_status)
    app.router.add_get("/api/task/{task_id}/result", handle_task_result)
    app.router.add_post("/api/task/{task_id}/cancel", handle_task_cancel)

    # 系统接口
    app.router.add_get("/api/health", handle_health)

    logger.info("HTTP API 路由已注册")
