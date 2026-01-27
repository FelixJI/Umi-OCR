# src/utils/monitor_utils.py

import logging
from typing import List, Tuple, Optional
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

class MonitorUtils:
    """多显示器工具类"""
    
    @staticmethod
    def get_screens() -> List[QScreen]:
        """获取所有屏幕"""
        app = QApplication.instance()
        if not app:
            return []
        return app.screens()
        
    @staticmethod
    def get_primary_screen() -> Optional[QScreen]:
        """获取主屏幕"""
        app = QApplication.instance()
        if not app:
            return None
        return app.primaryScreen()
        
    @staticmethod
    def get_screen_geometry(screen_index: int = -1) -> Tuple[int, int, int, int]:
        """
        获取指定屏幕的几何信息 (x, y, width, height)
        
        Args:
            screen_index: 屏幕索引，-1 表示主屏幕
            
        Returns:
            Tuple: (x, y, width, height)
        """
        screens = MonitorUtils.get_screens()
        if not screens:
            return (0, 0, 1920, 1080) # Fallback
            
        if screen_index < 0 or screen_index >= len(screens):
            screen = MonitorUtils.get_primary_screen()
        else:
            screen = screens[screen_index]
            
        if not screen:
            return (0, 0, 1920, 1080)
            
        rect = screen.geometry()
        return (rect.x(), rect.y(), rect.width(), rect.height())
        
    @staticmethod
    def get_screen_containing_point(x: int, y: int) -> Optional[QScreen]:
        """获取包含指定坐标点的屏幕"""
        app = QApplication.instance()
        if not app:
            return None
        return app.screenAt(x, y)
        
    @staticmethod
    def move_window_to_center(window, screen_index: int = -1):
        """将窗口移动到指定屏幕中心"""
        if not window:
            return
            
        screen_rect = MonitorUtils.get_screen_geometry(screen_index)
        screen_x, screen_y, screen_w, screen_h = screen_rect
        
        window_rect = window.frameGeometry()
        window_w = window_rect.width()
        window_h = window_rect.height()
        
        new_x = screen_x + (screen_w - window_w) // 2
        new_y = screen_y + (screen_h - window_h) // 2
        
        window.move(new_x, new_y)
        logger.info(f"窗口已移动到屏幕 {screen_index} 中心: ({new_x}, {new_y})")
