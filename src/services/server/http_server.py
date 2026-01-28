# src/services/server/http_server.py

import logging
from aiohttp import web
from typing import Optional

from utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class HTTPServer:
    """
    HTTP API 服务器 (aiohttp)
    """

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 1224

    def __init__(self):
        self._app = web.Application()
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self.config_manager = ConfigManager.get_instance()

        # 延迟导入路由，避免循环依赖
        from .routes import setup_routes

        setup_routes(self._app)

    async def start(self):
        """启动 HTTP 服务"""
        # 从配置读取
        host = self.config_manager.get("system.http_server_host", self.DEFAULT_HOST)
        port = self.config_manager.get("system.http_server_port", self.DEFAULT_PORT)

        try:
            self._runner = web.AppRunner(self._app)
            await self._runner.setup()

            self._site = web.TCPSite(self._runner, host, port)
            await self._site.start()

            logger.info(f"HTTP 服务已启动: http://{host}:{port}")
        except Exception as e:
            logger.error(f"HTTP 服务启动失败: {e}")

    async def stop(self):
        """停止 HTTP 服务"""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        logger.info("HTTP 服务已停止")
