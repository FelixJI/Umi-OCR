# Umi-OCR 平台模块
# 仅支持 Windows 10+

import sys

# 检查操作系统
if not sys.platform.startswith("win32"):
    raise ImportError(f"Umi-OCR 仅支持 Windows 系统。当前系统：{sys.platform}")

# 导入 Windows API
from .win32.win32_api import Api

# 构造单例：平台对象
Platform = Api()
