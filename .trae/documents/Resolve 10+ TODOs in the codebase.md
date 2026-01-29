I have identified 12 TODOs across 6 files and have a plan to resolve them.

### Plan to Resolve TODOs

1.  **`src/ui/dialogs/__init__.py`**
    *   **Task:** `TODO: 添加OCR图标`
    *   **Action:** The icon file is missing. I will clean up the code to use the existing text emoji "🔍" as the permanent solution for now, removing the commented-out code and the TODO, and adding a comment explaining the fallback.

2.  **`src/utils/file_finder.py`**
    *   **Task:** `TODO: mission 模块未实现` (imports for `MissionDOC`, `MissionOCR`)
    *   **Action:**
        *   Implement a local `MissionDOC` adapter class that uses `src.services.pdf.pdf_parser.PDFParser` to retrieve document info.
        *   Define `ImageSuf` and `DocSuf` locally (or import `SUPPORTED_FORMATS` from controllers) to replace the missing `MissionOCR` import.
        *   Remove the broken imports.

3.  **`src/utils/global_configs_connector.py`**
    *   **Task:** `TODO: server 模块未实现` (imports for `web_server`, `CmdActuator`)
    *   **Task:** `TODO: 导入路径问题` (imports from `umi_log`)
    *   **Action:**
        *   Import `HTTPServer` from `src.services.server.http_server` and implement `web_server.runUmiWeb` to use it.
        *   Remove the `umi_log` import TODO because the methods `change_save_log_level` and `open_logs_dir` are already implemented in the class using `src.utils.logger`.
        *   For `CmdActuator`, since the command server logic is not fully present in `services`, I will leave a cleaner placeholder or link it to `src/cli_handler.py` if appropriate, but primarily focus on fixing the `web_server` and `umi_log` issues.

4.  **`src/controllers/main_controller.py`**
    *   **Task:** `TODO: 将文件路径传递给批量 OCR 控制器`
    *   **Task:** `TODO: 切换到批量文档页面`
    *   **Task:** `TODO: 根据当前活动页面确定要导出的内容`
    *   **Task:** `TODO: 将图片传递给截图 OCR 控制器进行识别`
    *   **Action:**
        *   Implement `handle_open_file` to detect file type, switch to the correct page (`switch_to_page`), and call `add_files` on `BatchOcrController` or `BatchDocController`.
        *   Implement `handle_export` to check the current page index and call the corresponding export method on the active controller (e.g., `BatchOcrController.export_results`).
        *   Implement `handle_clipboard_ocr` to save the clipboard image to a temporary file and submit it using `ScreenshotController`'s internal logic (or `TaskManager` directly if `ScreenshotController` doesn't expose a public submission method for external images, but I can add one or use `submit_ocr_tasks` from task manager).

5.  **`src/controllers/settings_controller.py`**
    *   **Task:** `TODO: 发送一个测试请求来验证`
    *   **Action:** Implement `validate_cloud_config` to perform a basic connection check (or a dummy check if full implementation is too complex without valid credentials) to replace the TODO.

6.  **`src/app.py`**
    *   **Task:** `TODO: 在后续阶段中，通知所有 UI 组件更新文本`
    *   **Action:** The `MainController` already listens to language changes. I will update this TODO to a comment confirming that `MainController` handles this via `_on_language_changed`, or implement a simple broadcast if needed.

I will proceed with these changes file by file.