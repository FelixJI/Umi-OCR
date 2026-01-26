#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR 配置数据模型

定义应用程序的配置数据结构，包括：
- OCR 引擎配置
- 界面配置
- 快捷键配置
- 导出配置
- 系统配置

使用 dataclass 和 Pydantic 风格的验证，确保配置的类型安全。

Author: Umi-OCR Team
Date: 2025-01-25
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pathlib import Path


# =============================================================================
# 枚举类型定义
# =============================================================================

class OcrEngineType(Enum):
    """OCR 引擎类型"""
    PADDLE = "paddle"           # 本地 PaddleOCR
    BAIDU = "baidu"             # 百度云 OCR
    TENCENT = "tencent"         # 腾讯云 OCR
    ALIYUN = "aliyun"           # 阿里云 OCR


class ImageFormat(Enum):
    """图片格式"""
    PNG = "png"
    JPEG = "jpeg"
    BMP = "bmp"
    TIFF = "tiff"


class OutputFormat(Enum):
    """导出格式"""
    TXT = "txt"
    TXT_PLAIN = "txt_plain"
    JSON = "json"
    CSV = "csv"
    MD = "md"
    PDF_LAYERED = "pdf_layered"
    PDF_ONE_LAYER = "pdf_one_layer"


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    NONE = "none"


# =============================================================================
# OCR 配置
# =============================================================================

@dataclass
class OcrPreprocessingConfig:
    """OCR 图像预处理配置"""
    # 图像增强
    enable_denoise: bool = False           # 降噪
    enable_binarization: bool = False      # 二值化
    enable_deskew: bool = False            # 纠偏

    # 尺寸调整
    max_image_size: int = 0                # 最大图片尺寸（0表示不限制）
    min_image_size: int = 0                # 最小图片尺寸
    resize_factor: float = 1.0             # 缩放因子

    # 其他
    rotate_angle: float = 0.0              # 旋转角度（度）


@dataclass
class PaddleEngineConfig:
    """PaddleOCR 引擎配置"""
    # 模型选择
    det_model_name: str = "ch_PP-OCRv4_det"      # 检测模型
    rec_model_name: str = "ch_PP-OCRv4_rec"      # 识别模型
    use_angle_cls: bool = True                   # 是否使用方向分类器
    lang: str = "ch"                             # 语言

    # 性能参数
    use_gpu: bool = False                        # 是否使用 GPU
    cpu_threads: int = 4                         # CPU 线程数
    enable_mkldnn: bool = True                   # 是否使用 MKL-DNN 加速

    # 路径配置
    models_dir: str = ""                         # 模型目录（空表示使用默认路径）


@dataclass
class CloudOcrConfig:
    """云 OCR 配置（基类）"""
    api_key: str = ""                    # API Key
    secret_key: str = ""                 # Secret Key（用于签名）
    endpoint: str = ""                   # API 端点
    timeout: int = 30                    # 请求超时（秒）
    max_retry: int = 3                   # 最大重试次数


@dataclass
class BaiduOcrConfig(CloudOcrConfig):
    """百度云 OCR 配置"""
    # 百度云使用 API Key 和 Secret Key 获取 AccessToken
    token_cache_duration: int = 2592000  # Token 缓存时长（30天）


@dataclass
class TencentOcrConfig(CloudOcrConfig):
    """腾讯云 OCR 配置"""
    secret_id: str = ""                  # 腾讯云使用 SecretId
    region: str = "ap-guangzhou"         # 地域


@dataclass
class AliyunOcrConfig(CloudOcrConfig):
    """阿里云 OCR 配置"""
    access_key_id: str = ""              # 阿里云使用 AccessKeyId
    region_id: str = "cn-shanghai"       # 地域


@dataclass
class OcrConfig:
    """OCR 配置总类"""
    # 引擎选择
    engine_type: str = OcrEngineType.PADDLE.value

    # 本地引擎配置
    paddle: PaddleEngineConfig = field(default_factory=PaddleEngineConfig)

    # 云引擎配置
    baidu: BaiduOcrConfig = field(default_factory=BaiduOcrConfig)
    tencent: TencentOcrConfig = field(default_factory=TencentOcrConfig)
    aliyun: AliyunOcrConfig = field(default_factory=AliyunOcrConfig)

    # 预处理配置
    preprocessing: OcrPreprocessingConfig = field(default_factory=OcrPreprocessingConfig)

    # 识别参数
    confidence_threshold: float = 0.5    # 置信度阈值
    merge_lines: bool = True             # 是否合并相邻行


# =============================================================================
# 界面配置
# =============================================================================

@dataclass
class MainWindowConfig:
    """主窗口配置"""
    # 窗口状态
    width: int = 1000
    height: int = 700
    x: int = -1              # -1 表示居中
    y: int = -1              # -1 表示居中
    maximized: bool = False

    # 布局
    sidebar_width: int = 200
    sidebar_visible: bool = True


@dataclass
class ThemeConfig:
    """主题配置"""
    mode: str = "light"              # light / dark / auto
    accent_color: str = "#0078d4"    # 主题色
    font_family: str = ""            # 字体族（空表示系统默认）
    font_size: int = 9               # 字体大小


@dataclass
class UiConfig:
    """界面配置总类"""
    # 主窗口
    main_window: MainWindowConfig = field(default_factory=MainWindowConfig)

    # 主题
    theme: ThemeConfig = field(default_factory=ThemeConfig)

    # 语言
    language: str = "zh_CN"           # 界面语言

    # 其他
    show_tray_icon: bool = True      # 显示托盘图标
    minimize_to_tray: bool = False   # 最小化到托盘
    close_to_tray: bool = False      # 关闭到托盘


# =============================================================================
# 快捷键配置
# =============================================================================

@dataclass
class HotkeyConfig:
    """快捷键配置"""
    # 快捷键格式：modifiers+key
    # modifiers: Ctrl, Shift, Alt, Win
    # key: A-Z, 0-9, F1-F12, etc.

    screenshot: str = "Ctrl+Shift+A"         # 截图 OCR
    clipboard: str = "Ctrl+Shift+X"          # 剪贴板 OCR
    translate: str = ""                      # 划词翻译
    batch: str = ""                          # 批量 OCR
    show_hide: str = ""                      # 显示/隐藏主窗口


# =============================================================================
# 导出配置
# =============================================================================

@dataclass
class ExportConfig:
    """导出配置"""
    # 默认格式
    default_format: str = OutputFormat.TXT.value

    # 文本格式配置
    txt_line_break: str = "\n"               # 换行符
    txt_with_confidence: bool = False        # 是否包含置信度

    # JSON 格式配置
    json_indent: int = 2                     # 缩进空格数

    # PDF 格式配置
    pdf_image_quality: int = 90              # 图片质量 (1-100)
    pdf_page_size: str = "a4"               # 页面大小

    # 导出路径
    export_dir: str = ""                     # 默认导出目录（空表示系统默认）
    auto_copy: bool = True                   # 识别后自动复制到剪贴板


# =============================================================================
# 任务配置
# =============================================================================

@dataclass
class TaskConfig:
    """任务配置"""
    # 并发控制
    max_workers: int = 4                     # 最大并发任务数
    queue_size: int = 100                    # 任务队列大小

    # 重试配置
    max_retry: int = 2                       # 失败重试次数
    retry_delay: float = 1.0                 # 重试延迟（秒）

    # 超时配置
    task_timeout: int = 300                  # 单任务超时（秒）

    # 进度通知
    progress_throttle: float = 0.1           # 进度通知节流（秒）


# =============================================================================
# 系统配置
# =============================================================================

@dataclass
class SystemConfig:
    """系统配置"""
    # 日志
    log_level: str = LogLevel.INFO.value
    log_to_file: bool = True
    log_max_size: int = 10                   # 日志文件最大大小 (MB)
    log_backup_count: int = 5

    # 启动
    startup_launch: bool = False             # 开机自启
    check_update: bool = True                # 检查更新

    # 服务器
    http_server_enabled: bool = False
    http_server_port: int = 1224
    http_server_host: str = "127.0.0.1"


# =============================================================================
# 应用配置总类
# =============================================================================

@dataclass
class AppConfig:
    """
    应用配置总类

    包含所有配置模块，提供序列化和反序列化方法。
    """
    # 版本号（用于配置迁移）
    version: str = "2.0.0"

    # OCR 配置
    ocr: OcrConfig = field(default_factory=OcrConfig)

    # 界面配置
    ui: UiConfig = field(default_factory=UiConfig)

    # 快捷键配置
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)

    # 导出配置
    export: ExportConfig = field(default_factory=ExportConfig)

    # 任务配置
    task: TaskConfig = field(default_factory=TaskConfig)

    # 系统配置
    system: SystemConfig = field(default_factory=SystemConfig)

    # 其他配置（用于存储自定义键值对）
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            Dict[str, Any]: 配置字典
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """
        从字典创建配置对象

        Args:
            data: 配置字典

        Returns:
            AppConfig: 配置对象
        """
        # 处理嵌套对象
        ocr_data = data.get("ocr", {})
        ocr = OcrConfig(
            **{k: v for k, v in ocr_data.items() if k not in ("paddle", "baidu", "tencent", "aliyun", "preprocessing")}
        )
        if "paddle" in ocr_data:
            ocr.paddle = PaddleEngineConfig(**ocr_data["paddle"])
        if "baidu" in ocr_data:
            ocr.baidu = BaiduOcrConfig(**ocr_data["baidu"])
        if "tencent" in ocr_data:
            ocr.tencent = TencentOcrConfig(**ocr_data["tencent"])
        if "aliyun" in ocr_data:
            ocr.aliyun = AliyunOcrConfig(**ocr_data["aliyun"])
        if "preprocessing" in ocr_data:
            ocr.preprocessing = OcrPreprocessingConfig(**ocr_data["preprocessing"])

        ui_data = data.get("ui", {})
        ui = UiConfig(
            **{k: v for k, v in ui_data.items() if k not in ("main_window", "theme")}
        )
        if "main_window" in ui_data:
            ui.main_window = MainWindowConfig(**ui_data["main_window"])
        if "theme" in ui_data:
            ui.theme = ThemeConfig(**ui_data["theme"])

        hotkeys = HotkeyConfig(**data.get("hotkeys", {}))
        export = ExportConfig(**data.get("export", {}))
        task = TaskConfig(**data.get("task", {}))
        system = SystemConfig(**data.get("system", {}))

        return cls(
            version=data.get("version", "2.0.0"),
            ocr=ocr,
            ui=ui,
            hotkeys=hotkeys,
            export=export,
            task=task,
            system=system,
            extra=data.get("extra", {})
        )

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        通过点分隔的路径获取配置值

        Args:
            key_path: 配置路径，如 "ocr.engine_type" 或 "ui.theme.mode"
            default: 默认值

        Returns:
            Any: 配置值

        Examples:
            >>> config.get("ocr.engine_type")
            "paddle"
            >>> config.get("ui.main_window.width")
            1000
        """
        keys = key_path.split(".")
        value = self

        for key in keys:
            if hasattr(value, key):
                value = getattr(value, key)
            elif isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> bool:
        """
        通过点分隔的路径设置配置值

        Args:
            key_path: 配置路径，如 "ocr.engine_type"
            value: 新值

        Returns:
            bool: 是否设置成功
        """
        keys = key_path.split(".")
        obj = self

        # 导航到父对象
        for key in keys[:-1]:
            if hasattr(obj, key):
                obj = getattr(obj, key)
            else:
                return False

        # 设置值
        last_key = keys[-1]
        if hasattr(obj, last_key):
            setattr(obj, last_key, value)
            return True

        return False

    def validate(self) -> List[str]:
        """
        验证配置的有效性

        Returns:
            List[str]: 错误信息列表（空表示无错误）
        """
        errors = []

        # 验证 OCR 引擎类型
        try:
            OcrEngineType(self.ocr.engine_type)
        except ValueError:
            errors.append(f"无效的 OCR 引擎类型: {self.ocr.engine_type}")

        # 验证日志级别
        try:
            LogLevel(self.system.log_level)
        except ValueError:
            errors.append(f"无效的日志级别: {self.system.log_level}")

        # 验证端口号
        if not (1 <= self.system.http_server_port <= 65535):
            errors.append(f"无效的 HTTP 端口: {self.system.http_server_port}")

        # 验证线程数
        if self.task.max_workers < 1:
            errors.append(f"无效的最大并发数: {self.task.max_workers}")

        # 验证图片质量
        if not (1 <= self.export.pdf_image_quality <= 100):
            errors.append(f"无效的 PDF 图片质量: {self.export.pdf_image_quality}")

        return errors


# =============================================================================
# 配置变更事件
# =============================================================================

@dataclass
class ConfigChangeEvent:
    """
    配置变更事件

    当配置项发生变化时，通过 Qt Signal 发送此事件。
    """
    key_path: str                    # 变化的配置路径
    old_value: Any                   # 旧值
    new_value: Any                   # 新值
    source: str = "unknown"          # 变更来源（user/file/default）
