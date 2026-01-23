# 负责 keyboard 库的按键转换
# 将 keyboard 库的键名转换为统一格式

from umi_log import logger


# 键名映射表：将 keyboard 库的键名映射到项目使用的格式
_KEY_MAPPING = {
    # 修饰键
    "ctrl_l": "ctrl",
    "ctrl_r": "ctrl",
    "shift_l": "shift",
    "shift_r": "shift",
    "alt_l": "alt",
    "alt_r": "alt",
    "windows": "win",
    "cmd": "win",
    "win": "win",
    # 特殊键
    "space": "space",
    "enter": "enter",
    "return": "enter",
    "tab": "tab",
    "backspace": "backspace",
    "delete": "delete",
    "del": "delete",
    "insert": "insert",
    "home": "home",
    "end": "end",
    "page up": "pageup",
    "page down": "pagedown",
    "pgup": "pageup",
    "pgdn": "pagedown",
    # 方向键
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    # 功能键
    "f1": "f1",
    "f2": "f2",
    "f3": "f3",
    "f4": "f4",
    "f5": "f5",
    "f6": "f6",
    "f7": "f7",
    "f8": "f8",
    "f9": "f9",
    "f10": "f10",
    "f11": "f11",
    "f12": "f12",
    # 其他
    "escape": "esc",
    "esc": "esc",
    "caps lock": "caps",
    "caps": "caps",
    "num lock": "num",
    "scroll lock": "scroll",
}


def getKeyName(key):
    """
    传入 keyboard 库的键名，返回统一格式的键名字符串

    Args:
        key: keyboard 库的键名字符串

    Returns:
        统一格式的键名（小写）
    """
    if not key:
        return "unknown"

    # 转为小写
    key = key.lower().strip()

    # 查找映射
    if key in _KEY_MAPPING:
        return _KEY_MAPPING[key]

    # 处理带空格的键名（如 "page up"）
    key_normalized = key.replace(" ", "").replace("_", "")

    # 检查是否是单字符键
    if len(key) == 1:
        return key.lower()

    # 未知键名，返回原始值
    return key_normalized if key_normalized else "unknown"
