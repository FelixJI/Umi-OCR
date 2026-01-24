# Umi-OCR Native PaddleOCR Integration
# Replaces plugin system with direct PaddleOCR Python API

import threading
import logging
from paddleocr import PaddleOCR
from typing import List, Dict, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class PaddleOCREngine:
    """
    Direct PaddleOCR implementation for Umi-OCR.
    Replaces the PaddleOCR-json plugin wrapper with native Python API.
    """

    def __init__(self, globalArgd: Dict):
        """
        Initialize PaddleOCR engine.

        Args:
            globalArgd: Dictionary containing global configuration
                - lang: Language code (default 'ch')
                - use_angle_cls: Enable text orientation detection (default True)
                - cpu_threads: Number of CPU threads
                - ram_max: Max memory in MB before restart (for memory management)
                - ram_time: Time in seconds before restart
        """
        self.config = globalArgd
        self.lock = threading.Lock()

        # Memory management parameters
        self.ramInfo = {
            "max": globalArgd.get("ram_max", -1),
            "time": globalArgd.get("ram_time", -1),
            "timerID": "",
        }

        # PaddleOCR configuration
        self.ocr = None
        self._initialize_paddleocr()

    def _initialize_paddleocr(self):
        """Initialize PaddleOCR with configuration from self.config"""
        try:
            # Map Umi-OCR config to PaddleOCR parameters
            lang = self.config.get("lang", "ch")
            use_angle_cls = self.config.get("use_angle_cls", True)

            # Language mapping for PaddleOCR
            lang_map = {
                "chinese": "ch",
                "chinese_cht": "ch",
                "english": "en",
                "japan": "japan",
                "korean": "korean",
                "cyrillic": "cyrillic",
            }
            paddle_lang = lang_map.get(lang, "en")

            # Initialize PaddleOCR
            self.ocr = PaddleOCR(
                lang=paddle_lang,
                use_angle_cls=use_angle_cls,
                show_log=False,  # Disable PaddleOCR internal logs
                # det_model_dir=self.config.get("det_model_dir"),  # Optional: custom model paths
                # rec_model_dir=self.config.get("rec_model_dir"),
                # cls_model_dir=self.config.get("cls_model_dir")
            )

            logger.info(
                f"PaddleOCR initialized successfully with language: {paddle_lang}"
            )

        except Exception as e:
            logger.error(f"PaddleOCR initialization failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize PaddleOCR: {e}")

    def start(self, argd: Dict) -> str:
        """
        Start/restart the engine with new parameters.

        Args:
            argd: Dictionary containing runtime configuration

        Returns:
            "" on success, "[Error] xxx" on failure
        """
        with self.lock:
            try:
                # Check if we need to restart (if parameters changed)
                needs_restart = self._needs_restart(argd)

                if needs_restart:
                    logger.info("Restarting PaddleOCR with new parameters")
                    self._initialize_paddleocr()
                    self.config.update(argd)
                else:
                    logger.debug("No parameter change, using existing instance")

                return ""

            except Exception as e:
                logger.error(f"Failed to start PaddleOCR: {e}", exc_info=True)
                return f"[Error] OCR init fail. Argd: {argd}\n{e}"

    def _needs_restart(self, argd: Dict) -> bool:
        """Check if engine needs to restart based on parameter changes"""
        # Compare current config with new config
        # For PaddleOCR, we need to restart if language or angle_cls changes
        current_lang = self.config.get("lang", "ch")
        new_lang = argd.get("lang", "ch")
        current_angle_cls = self.config.get("use_angle_cls", True)
        new_angle_cls = argd.get("use_angle_cls", True)

        return current_lang != new_lang or current_angle_cls != new_angle_cls

    def stop(self):
        """Stop the OCR engine"""
        with self.lock:
            if self.ocr is not None:
                # PaddleOCR doesn't have a explicit stop method
                # We'll just clear the reference
                self.ocr = None
                logger.info("PaddleOCR engine stopped")

    def runPath(self, imgPath: str) -> Dict:
        """
        Perform OCR on image file path.

        Args:
            imgPath: Path to image file

        Returns:
            Dictionary with OCR results in Umi-OCR format
        """
        with self.lock:
            self._ramClear()
            try:
                if self.ocr is None:
                    self._initialize_paddleocr()

                result = self.ocr.ocr(imgPath, cls=True)
                return self._parse_result(result)
            except Exception as e:
                logger.error(f"OCR failed for path {imgPath}: {e}", exc_info=True)
                return {"code": 901, "data": f"[Error] OCR processing failed: {e}"}

    def runBytes(self, imageBytes: bytes) -> Dict:
        """
        Perform OCR on image bytes.

        Args:
            imageBytes: Raw image bytes

        Returns:
            Dictionary with OCR results in Umi-OCR format
        """
        with self.lock:
            self._ramClear()
            try:
                if self.ocr is None:
                    self._initialize_paddleocr()

                # Convert bytes to numpy array for PaddleOCR
                import numpy as np
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(imageBytes))
                img_array = np.array(img)

                result = self.ocr.ocr(img_array, cls=True)
                return self._parse_result(result)
            except Exception as e:
                logger.error(f"OCR failed for bytes input: {e}", exc_info=True)
                return {"code": 901, "data": f"[Error] OCR processing failed: {e}"}

    def runBase64(self, imageBase64: str) -> Dict:
        """
        Perform OCR on base64 encoded image.

        Args:
            imageBase64: Base64 encoded image string

        Returns:
            Dictionary with OCR results in Umi-OCR format
        """
        with self.lock:
            self._ramClear()
            try:
                if self.ocr is None:
                    self._initialize_paddleocr()

                # Decode base64
                import base64
                import numpy as np
                from PIL import Image
                import io

                imageBytes = base64.b64decode(imageBase64)
                img = Image.open(io.BytesIO(imageBytes))
                img_array = np.array(img)

                result = self.ocr.ocr(img_array, cls=True)
                return self._parse_result(result)
            except Exception as e:
                logger.error(f"OCR failed for base64 input: {e}", exc_info=True)
                return {"code": 901, "data": f"[Error] OCR processing failed: {e}"}

    def _parse_result(self, raw_result: List) -> Dict:
        """
        Parse PaddleOCR result to Umi-OCR format.

        PaddleOCR returns:
        [
            [  # For each image
                [  # For each detected text block
                    [  # Bounding box (4 points)
                        [x1, y1],
                        [x2, y2],
                        [x3, y3],
                        [x4, y4]
                    ],
                    ("text", confidence_score)  # Text and confidence
                ]
            ]
        ]

        Umi-OCR expects:
        {
            "code": 100,  # Success code
            "data": [
                {
                    "text": "detected text",
                    "score": 0.95,  # Confidence
                    "box": {  # Bounding box
                        "x1": 10, "y1": 10,
                        "x2": 100, "y2": 10,
                        "x3": 100, "y3": 50,
                        "x4": 10, "y4": 50
                    }
                }
            ]
        }
        """
        if not raw_result or not raw_result[0]:
            return {"code": 100, "data": []}

        parsed_data = []

        for block in raw_result[0]:
            if len(block) >= 2:
                bbox = block[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text_info = block[1]  # (text, confidence)

                text = text_info[0] if text_info else ""
                confidence = text_info[1] if len(text_info) > 1 else 0

                # Convert bbox to flat dictionary
                if len(bbox) == 4:
                    box_dict = {
                        "x1": int(bbox[0][0]),
                        "y1": int(bbox[0][1]),
                        "x2": int(bbox[1][0]),
                        "y2": int(bbox[1][1]),
                        "x3": int(bbox[2][0]),
                        "y3": int(bbox[2][1]),
                        "x4": int(bbox[3][0]),
                        "y4": int(bbox[3][1]),
                    }
                else:
                    box_dict = {}

                parsed_data.append(
                    {"text": text, "score": float(confidence), "box": box_dict}
                )

        return {"code": 100, "data": parsed_data}

    def _ramClear(self):
        """
        Memory management - check and restart if needed.
        For native PaddleOCR, we implement lighter-weight monitoring.
        """
        if self.ramInfo["max"] > 0:
            import psutil
            import os

            # Get current process memory
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024

            if memory_mb > self.ramInfo["max"]:
                logger.warning(f"Memory exceeded {memory_mb:.1f}MB, restarting...")
                self._initialize_paddleocr()

        # Time-based restart
        if self.ramInfo["time"] > 0:
            from ..utils.call_func import CallFunc

            self.ramInfo["timerID"] = CallFunc.delay(
                self._initialize_paddleocr,
                self.ramInfo["time"] * 1000,  # Convert to milliseconds
            )
