
import sys
import os
sys.path.append(os.getcwd())

import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QColor, QPainter
from PySide6.QtCore import QPoint
from src.services.screenshot.magnifier import Magnifier

# Ensure QApplication exists
app = QApplication.instance() or QApplication([])

class TestMagnifier(unittest.TestCase):
    def setUp(self):
        self.magnifier = Magnifier()
        self.image = QPixmap(800, 600)
        self.image.fill(QColor("white"))
        
        # Draw something on the image
        painter = QPainter(self.image)
        painter.fillRect(100, 100, 50, 50, QColor("red"))
        painter.end()

    def test_initialization(self):
        self.assertIsNotNone(self.magnifier)
        self.assertEqual(self.magnifier.ZOOM_FACTOR, 5)
        self.assertTrue(self.magnifier.windowFlags())

    def test_update_position(self):
        # Test updating position
        pos = QPoint(100, 100)
        self.magnifier.update_position(pos, self.image)
        
        # Check if color was captured (red)
        # Note: update_position calls pixelColor(0,0) of the 1x1 crop.
        # At 100,100 we drew a red rect.
        # However, update_position uses QCursor.pos() for moving the window, 
        # but uses local_pos for image data.
        
        # We can't easily check internal state _current_color unless we access it.
        # It is protected/private by convention but accessible in Python.
        self.assertEqual(self.magnifier._current_color, QColor("red"))
        
        # Test white area
        pos_white = QPoint(10, 10)
        self.magnifier.update_position(pos_white, self.image)
        self.assertEqual(self.magnifier._current_color, QColor("white"))

    def test_calculate_position(self):
        # This relies on screen geometry which might be virtual in this env.
        # We just check it returns a point.
        pos = QPoint(100, 100)
        new_pos = self.magnifier._calculate_magnifier_position(pos)
        self.assertIsInstance(new_pos, QPoint)
        # Default offset is 20
        # If screens are detected, it might shift.
        # But at 100,100 it should be 120,120 unless screen is tiny.
        
    def test_paint_event(self):
        # Trigger a paint event safely
        # We can use render to paint into a pixmap
        target = QPixmap(self.magnifier.size())
        self.magnifier.render(target)
        self.assertFalse(target.isNull())

    def test_pixel_ratio(self):
        # Test pixel ratio scaling
        # Create a 200x200 image (Physical)
        high_dpi_image = QPixmap(200, 200)
        high_dpi_image.fill(QColor("blue"))
        
        # Draw green at 100,100 (Physical)
        painter = QPainter(high_dpi_image)
        painter.fillRect(100, 100, 10, 10, QColor("green"))
        painter.end()
        
        # Logical position 50,50 with ratio 2.0 should hit 100,100
        logical_pos = QPoint(50, 50)
        pixel_ratio = 2.0
        
        self.magnifier.update_position(logical_pos, high_dpi_image, pixel_ratio=pixel_ratio)
        
        self.assertEqual(self.magnifier._current_color, QColor("green"))
        self.assertEqual(self.magnifier._center_pixel_pos, QPoint(100, 100))

if __name__ == '__main__':
    unittest.main()
