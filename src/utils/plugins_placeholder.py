# Placeholder for removed PluginsConnector
# This module is deprecated as the plugin system has been removed

from PySide6.QtCore import QObject, Slot, Signal


class PluginsConnector(QObject):
    """Placeholder for removed plugin system"""

    initCompleted = Signal()

    @Slot(result=dict)
    def init(self):
        """Initialize placeholder - returns empty"""
        return {
            "options": {"ocr": None},  # No plugin system, OCR is built-in
            "errors": {},
        }

    @Slot(str, result=str)
    def setOcrLang(self, lang):
        """Set OCR language (no-op in new system)"""
        return ""
