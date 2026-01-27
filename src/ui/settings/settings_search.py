#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 设置搜索

Author: Umi-OCR Team
Date: 2026-01-27
"""

from PySide6.QtCore import QObject, Signal

class SettingsSearch(QObject):
    """设置搜索逻辑"""
    
    def __init__(self):
        super().__init__()
    
    def search(self, query: str):
        # TODO: Implement search logic
        pass
