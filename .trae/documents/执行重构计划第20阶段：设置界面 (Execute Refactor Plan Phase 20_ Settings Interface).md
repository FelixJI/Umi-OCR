**1. 确认第19阶段完成情况 (Verify Phase 19 Completion)**

* 经检查，云端OCR模块（`tencent_ocr.py`, `aliyun_ocr.py`）及引擎管理器配置均已就绪。

* 引擎选择器控件 (`engine_selector.py`) 已实现并支持云引擎状态检测。

**2. 执行第20阶段：设置界面 (Execute Phase 20: Settings Interface)**

* **目标**: 构建全局设置中心，实现设置分类管理、即时搜索与云服务集中配置。

* **文件列表**:

  * `src/controllers/settings_controller.py`: 设置控制器，协调UI与ConfigManager。

  * `src/ui/settings/settings.ui`: 界面布局文件（基于侧边栏导航设计）。

  * `src/ui/settings/settings.py`: 界面逻辑类，处理页面切换与配置加载。

  * `src/ui/settings/settings_search.py`: 实现设置项的快速搜索与高亮定位。

* **关键功能**:

  * **侧边栏导航**: 常规设置、OCR引擎、快捷键等分类。

  * **云服务配置**: 集成百度、腾讯、阿里云的 API Key 管理与连通性测试。

  * **配置联动**: 设置变更后通过 `ConfigManager` 持久化并通知相关组件。

**3. 发现与建议：PaddleOCR-VL 模型 (Discovery & Proposal: PaddleOCR-VL Model)**

* **现状**: `paddle_doc` 文档显示项目包含 `PaddleOCR-VL` (Vision Language Model) 支持，但 `REFACTOR_PLAN.md` 未包含相关规划。

* **建议**: 鉴于该模型为重要的新特性（文档解析与多模态识别），建议在第20阶段完成后，新增“PaddleOCR-VL 集成”任务，作为新的本地引擎选项接入系统。

* **请求**: 批准在后续步骤中实施 PaddleOCR-VL 的集成。

**实施步骤**:

1. 创建 `src/ui/settings/settings.ui` 及对应的 Python 逻辑文件。
2. 实现 `settings_controller.py`。
3. 集成云服务配置逻辑至设置界面。
4. 启动 PaddleOCR-VL 集成工作。

