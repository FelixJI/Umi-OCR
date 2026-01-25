# ========================================
# =============== 截图控制 ===============
# ========================================

from ..image_controller.image_provider import PixmapProvider  # 图片提供器
from ..utils.file_finder import findFiles

import time
from PySide6.QtGui import QGuiApplication, QImage, QPixmap  # 截图


# PySide6 中 QClipboard 不能直接实例化，需要从 QApplication 获取
def getClipboard():
    from PySide6.QtWidgets import QApplication

    return QApplication.clipboard()


Clipboard = getClipboard  # 剪贴板（改为函数调用）


class _ScreenshotControllerClass:
    def getScreenshot(self, wait=0):
        """
        延时wait秒后，获取所有屏幕的截图。返回列表(不为空)，每项为：\n
        {
            "imgID": 图片ID 或 报错信息 "[Error]开头" ,
            "screenName": 显示器名称 ,
            "width": 截图宽度 ,
            "height": 截图高度 ,
        }
        """
        if wait > 0:
            time.sleep(wait)
        try:
            grabList = []
            screensList = QGuiApplication.screens()
            for screen in screensList:
                name = screen.name()
                # 获取截图 - 使用 PySide6 推荐方法
                try:
                    # PySide6/Qt6: grabWindow(0) 截取整个屏幕
                    pixmap = screen.grabWindow(0)
                except Exception as grab_err:
                    # 降级方案：通过虚拟桌面窗口ID截取
                    try:
                        # 获取主窗口并截取（使用文件开头已导入的 QGuiApplication）
                        pixmap = screen.grabWindow(0)
                        # 如果失败，尝试创建临时全屏窗口
                        if pixmap.isNull() or pixmap.width() == 0:
                            raise Exception("grabWindow returned invalid pixmap")
                    except Exception as e2:
                        return [
                            {
                                "imgID": f"[Error] Failed to grab screen {name}: {str(e2)}"
                            }
                        ]

                width = pixmap.width()
                height = pixmap.height()
                # 检查截图失败
                if width <= 0 or height <= 0:
                    imgID = f"[Error] width={width}, height={height}"
                # 检查有效，存入提供器，获取imgID
                else:
                    imgID = PixmapProvider.addPixmap(pixmap)
                grabList.append(
                    {
                        "imgID": imgID,
                        "screenName": name,
                        "width": width,
                        "height": height,
                    }
                )
            if not grabList:  # 获取到的截图列表为空
                return [{"imgID": f"[Error] grabList is empty."}]
            return grabList
        except Exception as e:
            return [{"imgID": f"[Error] Screenshot: {e}"}]

    # 对一张图片做裁切。传入原图imgID和裁切参数，返回裁切后的imgID或[Error]
    def getClipImgID(self, imgID, x, y, w, h):
        try:
            pixmap = PixmapProvider.getPixmap(imgID)
            if not pixmap:
                return f'[Error] Screenshot: Key "{imgID}" does not exist in the PixmapProvider dict.'
            if x < 0 or y < 0 or w <= 0 or h <= 0:
                return f"[Error] Screenshot: x/y/w/h value error. {x}/{y}/{w}/{h}"
            pixmap = pixmap.copy(x, y, w, h)  # 进行裁切
            clipID = PixmapProvider.addPixmap(pixmap)  # 存入提供器，获取imgID
            return clipID
        except Exception as e:
            return f"[Error] Screenshot: {e}"

    # 获取当前剪贴板的内容
    # type: imgID paths text
    def getPaste(self):
        # 获取剪贴板数据
        clipboard = getClipboard()
        mimeData = clipboard.mimeData()
        res = {"type": ""}  # 结果字典
        # 检查剪贴板的内容，若是图片，则提取它并扔给OCR
        if mimeData.hasImage():
            try:
                # 尝试多种方式获取剪贴板图片
                image = clipboard.image()

                # 如果直接获取失败，尝试从pixmap获取
                if image.isNull():
                    pixmap = clipboard.pixmap()
                    if pixmap.isNull():
                        res = {
                            "type": "error",
                            "error": "[Warning] Image in clipboard is invalid.",
                        }
                        return res
                    # QPixmap转QImage再转回QPixmap确保格式正确
                    image = pixmap.toImage()

                # QImage转QPixmap
                pixmap = QPixmap.fromImage(image)

                # 检查转换结果
                if pixmap.isNull():
                    res = {
                        "type": "error",
                        "error": "[Warning] Failed to convert clipboard image to QPixmap.",
                    }
                    return res

                pasteID = PixmapProvider.addPixmap(pixmap)  # 存入提供器
                res = {"type": "imgID", "imgID": pasteID}
            except Exception as e:
                res = {
                    "type": "error",
                    "error": f"[Warning] Failed to get image from clipboard: {e}",
                }

        # 若为URL
        elif mimeData.hasUrls():
            urlList = mimeData.urls()
            paths = []
            for url in urlList:  # 遍历URL列表，提取其中的文件
                if url.isLocalFile():
                    p = url.toLocalFile()
                    paths.append(p)
            paths = findFiles(paths, "image", False)  # 过滤，保留图片的路径
            if len(paths) == 0:  # 没有有效图片
                res = {"type": "error", "error": "[Warning] No image in clipboard."}
            else:  # 将有效图片地址传入OCR，返回地址列表
                res = {"type": "paths", "paths": paths}
        elif mimeData.hasText():
            text = mimeData.text()
            res = {"type": "text", "text": text}
        else:
            res = {"type": "error", "error": "[Warning] Unknown mimeData in clipboard."}
        return res  # 返回结果字典


ScreenshotController = _ScreenshotControllerClass()
