# Umi-OCR 项目架构重构计划

## 一、重构背景与目标

### 1.1 当前问题
- 目录结构混乱，文件组织不合理
- 模块职责不清，存在职责重叠
- 命名不规范，风格不统一（tag_pages vs TabPages）
- QML + Python 双语言架构增加了复杂度
- 之前的重构引入了新问题，代码处于过渡状态

### 1.2 重构目标
- **技术栈统一**: 从 QML 迁移到 Qt Widgets，全部使用 Python
- **架构清晰**: 采用分层架构，UI/逻辑/服务完全分离
- **代码质量**: 完善的单元测试、日志系统、中文文档
- **功能增强**: 支持云 OCR API、完整任务管理器、悬浮工具栏

---

## 二、技术选型

| 项目 | 选择 | 说明 |
|------|------|------|
| UI 框架 | Qt Widgets (PySide6) | 使用 .ui 文件实现 UI/逻辑分离 |
| 信号机制 | Qt Signal/Slot | 放弃自定义事件总线 |
| 文件命名 | snake_case | 符合 Python 规范 |
| 目标平台 | Windows 10/11 | 专注单一平台 |
| OCR 引擎 | PaddleOCR + 云 API | 支持百度、腾讯、阿里云 |

---

## 三、目录结构设计

```
src/
├── main.py                     # 程序入口
├── app.py                      # QApplication 初始化
│
├── ui/                         # 界面层 (View)
│   ├── main_window/            # 主窗口
│   │   ├── main_window.ui
│   │   └── main_window.py
│   ├── screenshot_ocr/         # 截图 OCR 界面
│   │   ├── screenshot_ocr.ui
│   │   └── screenshot_ocr.py
│   ├── batch_ocr/              # 批量图片 OCR 界面
│   │   ├── batch_ocr.ui
│   │   └── batch_ocr.py
│   ├── batch_doc/              # 批量文档 OCR 界面
│   │   ├── batch_doc.ui
│   │   └── batch_doc.py
│   ├── qrcode/                 # 二维码界面
│   │   ├── qrcode.ui
│   │   └── qrcode.py
│   ├── task_manager/           # 任务管理器界面
│   │   ├── task_manager.ui
│   │   └── task_manager.py
│   ├── settings/               # 设置界面
│   │   ├── settings.ui
│   │   └── settings.py
│   ├── floating_bar/           # 悬浮工具栏
│   │   ├── floating_bar.ui
│   │   └── floating_bar.py
│   ├── widgets/                # 通用自定义控件
│   │   ├── image_viewer.py
│   │   ├── result_panel.py
│   │   └── progress_card.py
│   └── resources/              # Qt 资源文件
│       ├── icons/
│       ├── themes/
│       └── resources.qrc
│
├── controllers/                # 控制层 (Controller)
│   ├── main_controller.py      # 主窗口控制器
│   ├── screenshot_controller.py
│   ├── batch_ocr_controller.py
│   ├── batch_doc_controller.py
│   ├── qrcode_controller.py
│   └── settings_controller.py
│
├── services/                   # 服务层 (Service)
│   ├── ocr/                    # OCR 引擎服务
│   │   ├── base_engine.py      # 抽象基类
│   │   ├── paddle_engine.py    # PaddleOCR 实现
│   │   ├── cloud/              # 云 API 实现
│   │   │   ├── base_cloud.py
│   │   │   ├── baidu_ocr.py
│   │   │   ├── tencent_ocr.py
│   │   │   └── aliyun_ocr.py
│   │   ├── engine_manager.py   # 引擎管理器
│   │   └── ocr_result.py       # 结果数据类
│   ├── task/                   # 任务管理服务
│   │   ├── task_manager.py     # 任务调度中心
│   │   ├── task_model.py       # 任务数据模型
│   │   ├── task_worker.py      # 任务执行器
│   │   └── task_queue.py       # 任务队列
│   ├── export/                 # 导出服务
│   │   ├── base_exporter.py
│   │   ├── text_exporter.py
│   │   ├── json_exporter.py
│   │   ├── excel_exporter.py
│   │   └── pdf_exporter.py
│   ├── screenshot/             # 截图服务
│   │   ├── screen_capture.py
│   │   └── region_selector.py
│   └── server/                 # HTTP/CLI 服务
│       ├── http_server.py
│       └── cli_handler.py
│
├── models/                     # 数据模型层 (Model)
│   ├── config_model.py         # 配置数据结构
│   ├── ocr_config.py           # OCR 相关配置
│   └── app_settings.py         # 应用设置
│
├── utils/                      # 工具类
│   ├── config_manager.py       # 配置管理器
│   ├── logger.py               # 日志系统
│   ├── i18n.py                 # 多语言支持
│   ├── hotkey_manager.py       # 全局快捷键
│   ├── tray_manager.py         # 系统托盘
│   ├── startup_manager.py      # 开机自启
│   └── image_utils.py          # 图像处理工具
│
└── tests/                      # 单元测试
    ├── test_ocr_engines.py
    ├── test_task_manager.py
    ├── test_exporters.py
    └── test_config.py

resources/                      # 静态资源（项目根目录）
├── i18n/                       # 语言包
│   ├── zh_CN.json
│   └── en_US.json
├── models/                     # OCR 模型文件
└── icons/                      # 图标资源

UmiOCR-data/                    # 用户数据目录
├── config.json                 # 用户配置
├── logs/                       # 日志文件
└── cache/                      # 缓存目录
```

---

## 四、核心模块设计

### 4.1 OCR 引擎抽象层

```python
# services/ocr/base_engine.py
class BaseOCREngine(ABC):
    """OCR 引擎抽象基类"""
    
    @abstractmethod
    def initialize(self, config: dict) -> bool:
        """初始化引擎"""
        pass
    
    @abstractmethod
    def recognize(self, image: Union[str, bytes, Image]) -> OCRResult:
        """执行 OCR 识别"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止引擎，释放资源"""
        pass
    
    @abstractmethod
    def get_config_schema(self) -> dict:
        """返回配置项定义，用于 UI 动态生成"""
        pass
```

**引擎管理器功能**:
- 单例模式管理当前活跃引擎
- 支持引擎热切换
- 失败时自动回退到备用引擎
- 统一的错误码定义

### 4.2 任务管理系统

```python
# services/task/task_model.py
class TaskStatus(Enum):
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 执行中
    PAUSED = "paused"        # 已暂停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消

class Task:
    """单个任务"""
    id: str
    input_data: Any
    status: TaskStatus
    progress: float
    result: Optional[Any]
    error: Optional[str]

class TaskGroup:
    """任务组（一次用户操作）"""
    id: str
    title: str
    tasks: List[Task]
    priority: int
    status: TaskStatus
    created_at: datetime
```

**任务管理器功能**:
- 支持暂停/恢复/取消
- 优先级调度
- 并发控制（可配置线程数）
- 实时进度通知（节流处理）
- 失败自动重试

### 4.3 界面架构

**主窗口布局**:
```
┌─────────────────────────────────────────────────┐
│  菜单栏 | 工具栏                                  │
├─────────┬───────────────────────────────────────┤
│         │                                       │
│  侧边栏  │           内容区域                    │
│  导航    │     (根据选择显示不同功能界面)          │
│         │                                       │
│  - 截图  │                                       │
│  - 批量  │                                       │
│  - 文档  │                                       │
│  - 二维码│                                       │
│  - 任务  │                                       │
│  - 设置  │                                       │
│         │                                       │
├─────────┴───────────────────────────────────────┤
│  状态栏（任务进度、系统状态）                      │
└─────────────────────────────────────────────────┘
```

**悬浮工具栏**:
- 屏幕顶部边缘触发显示
- 快捷访问：截图 OCR、剪贴板 OCR、划词翻译
- 可拖拽、可隐藏

---

## 五、阶段总览

| 阶段 | 名称 | 类别 | 主要产出 |
|:----:|------|------|----------|
| 1 | 项目骨架搭建 | 基础设施 | 目录结构、程序入口 |
| 2 | 日志系统 | 基础设施 | logger.py |
| 3 | 配置管理系统 | 基础设施 | config_manager.py |
| 4 | 多语言支持 | 基础设施 | i18n.py、语言包 |
| 5 | 主窗口框架 | UI框架 | main_window.ui/.py |
| 6 | OCR引擎抽象层 | OCR核心 | base_engine.py |
| 7 | PaddleOCR本地引擎 | OCR核心 | paddle_engine.py |
| 8 | 引擎管理器 | OCR核心 | engine_manager.py |
| 9 | 任务数据模型 | 任务系统 | task_model.py |
| 10 | 任务队列与调度 | 任务系统 | task_queue.py |
| 11 | 任务执行器 | 任务系统 | task_worker.py |
| 12 | 任务管理器 | 任务系统 | task_manager.py |
| 13 | 截图OCR模块 | 功能模块 | screenshot_ocr界面 |
| 14 | 批量图片OCR模块 | 功能模块 | batch_ocr界面 |
| 15 | 批量文档OCR模块 | 功能模块 | batch_doc界面 |
| 16 | 二维码模块 | 功能模块 | qrcode界面 |
| 17 | 导出功能 | 功能模块 | exporters |
| 18 | 云OCR-百度 | 云服务 | baidu_ocr.py |
| 19 | 云OCR-腾讯和阿里 | 云服务 | tencent/aliyun_ocr.py |
| 20 | 设置界面 | UI模块 | settings界面 |
| 21 | 系统托盘 | 系统功能 | tray_manager.py |
| 22 | 全局快捷键 | 系统功能 | hotkey_manager.py |
| 23 | 开机自启与多显示器 | 系统功能 | startup_manager.py |
| 24 | 悬浮工具栏 | UI模块 | floating_bar界面 |
| 25 | 任务管理器界面 | UI模块 | task_manager界面 |
| 26 | HTTP API服务 | 外部接口 | http_server.py |
| 27 | CLI接口 | 外部接口 | cli_handler.py |
| 28 | 通用控件 | UI组件 | widgets/* |
| 29 | 集成测试与优化 | 质量保障 | 测试用例、性能优化 |
| 30 | 文档与收尾 | 收尾工作 | 文档、发布准备 |

---

## 六、重构实施阶段详细说明

> **工作量估算说明**: 每个阶段预估工作量相近，便于迭代管理

---

### 阶段 1：项目骨架搭建

**目标**: 创建新的目录结构和程序入口

**任务清单**:
1. 创建完整的目录结构（ui/, controllers/, services/, models/, utils/）
2. 实现 `src/main.py` - 程序入口
3. 实现 `src/app.py` - QApplication 初始化和全局配置
4. 创建 `resources/` 目录，迁移图标等静态资源
5. 配置 `pyproject.toml` 依赖管理

**交付物**: 可启动的空白 Python 程序

**关键文件**:
- `src/main.py`
- `src/app.py`
- `pyproject.toml`

**验证方式**: `python src/main.py` 正常启动不报错

---

### 阶段 2：日志系统

**目标**: 实现完整的日志记录功能

**任务清单**:
1. 实现 `utils/logger.py` - 日志管理器
2. 支持控制台和文件双输出
3. 支持日志级别配置（DEBUG/INFO/WARNING/ERROR）
4. 支持日志文件自动轮转
5. 编写日志系统单元测试

**交付物**: 可在全局使用的日志系统

**关键文件**:
- `src/utils/logger.py`
- `src/tests/test_logger.py`

**验证方式**: 运行测试，检查日志文件生成

---

### 阶段 3：配置管理系统

**目标**: 实现配置的读取、保存和变更通知

**任务清单**:
1. 定义 `models/config_model.py` - 配置数据结构
2. 实现 `utils/config_manager.py` - 配置管理器（单例）
3. 支持 JSON 格式配置文件读写
4. 支持配置变更信号通知（Qt Signal）
5. 实现默认配置和配置校验
6. 编写配置系统单元测试

**交付物**: 可持久化的配置管理系统

**关键文件**:
- `src/models/config_model.py`
- `src/utils/config_manager.py`
- `src/tests/test_config.py`

**验证方式**: 运行测试，验证配置读写正确

---

### 阶段 4：多语言支持

**目标**: 实现界面多语言切换功能

**任务清单**:
1. 实现 `utils/i18n.py` - 多语言管理器
2. 定义语言包格式（JSON）
3. 创建中文语言包 `resources/i18n/zh_CN.json`
4. 创建英文语言包 `resources/i18n/en_US.json`
5. 支持运行时语言切换
6. 编写多语言单元测试

**交付物**: 可动态切换的多语言系统

**关键文件**:
- `src/utils/i18n.py`
- `resources/i18n/zh_CN.json`
- `resources/i18n/en_US.json`

**验证方式**: 切换语言后文本正确显示

---

### 阶段 5：主窗口框架

**目标**: 创建主窗口基础布局

**任务清单**:
1. 使用 Qt Designer 创建 `ui/main_window/main_window.ui`
2. 实现 `ui/main_window/main_window.py` - 主窗口类
3. 实现侧边栏导航组件
4. 实现内容区域的 QStackedWidget
5. 实现菜单栏和工具栏
6. 实现状态栏

**交付物**: 可运行的主窗口，带侧边栏导航

**关键文件**:
- `src/ui/main_window/main_window.ui`
- `src/ui/main_window/main_window.py`
- `src/controllers/main_controller.py`

**验证方式**: 启动程序，侧边栏可点击切换视图

---

### 阶段 6：OCR 引擎抽象层

**目标**: 定义 OCR 引擎的统一接口

**任务清单**:
1. 定义 `services/ocr/base_engine.py` - 抽象基类
2. 定义 `services/ocr/ocr_result.py` - 统一结果格式
3. 定义错误码枚举
4. 定义引擎配置 Schema 格式
5. 编写接口文档（中文注释）

**交付物**: OCR 引擎抽象接口定义

**关键文件**:
- `src/services/ocr/base_engine.py`
- `src/services/ocr/ocr_result.py`

**验证方式**: 接口定义完整，无语法错误

---

### 阶段 7：PaddleOCR 本地引擎

**目标**: 集成 PaddleOCR 作为本地识别引擎

**任务清单**:
1. 实现 `services/ocr/paddle_engine.py` - PaddleOCR 引擎
2. 实现引擎初始化和资源加载
3. 实现图像预处理（支持路径、字节、PIL Image）
4. 实现识别结果解析和格式转换
5. 实现线程安全（加锁）
6. 编写引擎单元测试

**交付物**: 可调用的本地 OCR 引擎

**关键文件**:
- `src/services/ocr/paddle_engine.py`
- `src/tests/test_ocr_engines.py`

**验证方式**: 单元测试通过，识别测试图片正确

---

### 阶段 8：引擎管理器

**目标**: 实现多引擎的统一管理

**任务清单**:
1. 实现 `services/ocr/engine_manager.py` - 引擎管理器（单例）
2. 实现引擎注册和工厂方法
3. 实现引擎热切换
4. 实现失败回退机制
5. 编写管理器单元测试

**交付物**: 可动态切换的引擎管理系统

**关键文件**:
- `src/services/ocr/engine_manager.py`
- `src/services/ocr/__init__.py`

**验证方式**: 测试引擎切换和回退逻辑

---

### 阶段 9：任务数据模型

**目标**: 定义任务系统的数据结构

**任务清单**:
1. 定义 `services/task/task_model.py` - Task 和 TaskGroup 类
2. 定义任务状态枚举（PENDING/RUNNING/PAUSED/COMPLETED/FAILED/CANCELLED）
3. 实现任务进度计算
4. 实现任务序列化（用于持久化）
5. 编写模型单元测试

**交付物**: 完整的任务数据模型

**关键文件**:
- `src/services/task/task_model.py`
- `src/tests/test_task_model.py`

**验证方式**: 单元测试通过

---

### 阶段 10：任务队列与调度

**目标**: 实现任务队列和优先级调度

**任务清单**:
1. 实现 `services/task/task_queue.py` - 优先级任务队列
2. 实现任务入队和出队
3. 实现优先级排序
4. 实现任务查找和状态更新
5. 编写队列单元测试

**交付物**: 支持优先级的任务队列

**关键文件**:
- `src/services/task/task_queue.py`
- `src/tests/test_task_queue.py`

**验证方式**: 单元测试通过，优先级排序正确

---

### 阶段 11：任务执行器

**目标**: 实现基于 QThread 的任务执行器

**任务清单**:
1. 实现 `services/task/task_worker.py` - 任务执行器
2. 实现 QThread 封装
3. 实现进度信号发送（节流处理）
4. 实现任务暂停/恢复/取消
5. 实现错误处理和重试
6. 编写执行器单元测试

**交付物**: 可在后台执行任务的 Worker

**关键文件**:
- `src/services/task/task_worker.py`
- `src/tests/test_task_worker.py`

**验证方式**: 测试后台任务执行和取消

---

### 阶段 12：任务管理器

**目标**: 实现任务调度中心

**任务清单**:
1. 实现 `services/task/task_manager.py` - 任务管理器（单例）
2. 实现任务提交接口
3. 实现并发控制（可配置线程数）
4. 实现任务组管理
5. 实现与 UI 的信号连接
6. 编写管理器集成测试

**交付物**: 完整的任务管理系统

**关键文件**:
- `src/services/task/task_manager.py`
- `src/tests/test_task_manager.py`

**验证方式**: 集成测试通过，多任务并发正确

---

### 阶段 13：截图 OCR 模块

**目标**: 实现截图识别功能

**任务清单**:
1. 实现 `services/screenshot/screen_capture.py` - 屏幕捕获
2. 实现 `services/screenshot/region_selector.py` - 区域选择器（覆盖层窗口）
3. 创建 `ui/screenshot_ocr/screenshot_ocr.ui` - 截图 OCR 界面
4. 实现 `ui/screenshot_ocr/screenshot_ocr.py` - 界面类
5. 实现 `controllers/screenshot_controller.py` - 控制器
6. 集成任务系统

**交付物**: 可用的截图 OCR 功能

**关键文件**:
- `src/services/screenshot/screen_capture.py`
- `src/services/screenshot/region_selector.py`
- `src/ui/screenshot_ocr/screenshot_ocr.ui`
- `src/ui/screenshot_ocr/screenshot_ocr.py`
- `src/controllers/screenshot_controller.py`

**验证方式**: 截图后正确识别并显示结果

---

### 阶段 14：批量图片 OCR 模块

**目标**: 实现批量图片识别功能

**任务清单**:
1. 创建 `ui/batch_ocr/batch_ocr.ui` - 批量 OCR 界面
2. 实现 `ui/batch_ocr/batch_ocr.py` - 界面类
3. 实现文件拖拽添加
4. 实现文件列表管理（添加/删除/清空）
5. 实现 `controllers/batch_ocr_controller.py` - 控制器
6. 集成任务系统，显示批量进度

**交付物**: 可用的批量图片 OCR 功能

**关键文件**:
- `src/ui/batch_ocr/batch_ocr.ui`
- `src/ui/batch_ocr/batch_ocr.py`
- `src/controllers/batch_ocr_controller.py`

**验证方式**: 批量添加图片后正确识别

---

### 阶段 15：批量文档 OCR 模块

**目标**: 实现 PDF 等文档的批量识别

**任务清单**:
1. 实现 PDF 解析服务（使用 pymupdf）
2. 实现 PDF 页面提取为图像
3. 创建 `ui/batch_doc/batch_doc.ui` - 文档 OCR 界面
4. 实现 `ui/batch_doc/batch_doc.py` - 界面类
5. 实现 `controllers/batch_doc_controller.py` - 控制器
6. 集成任务系统

**交付物**: 可用的批量文档 OCR 功能

**关键文件**:
- `src/ui/batch_doc/batch_doc.ui`
- `src/ui/batch_doc/batch_doc.py`
- `src/controllers/batch_doc_controller.py`

**验证方式**: PDF 文档正确识别

---

### 阶段 16：二维码模块

**目标**: 实现二维码识别和生成功能

**任务清单**:
1. 实现二维码识别服务（使用 pyzbar 或类似库）
2. 实现二维码生成服务（使用 qrcode 库）
3. 创建 `ui/qrcode/qrcode.ui` - 二维码界面
4. 实现 `ui/qrcode/qrcode.py` - 界面类
5. 实现 `controllers/qrcode_controller.py` - 控制器

**交付物**: 可用的二维码识别和生成功能

**关键文件**:
- `src/ui/qrcode/qrcode.ui`
- `src/ui/qrcode/qrcode.py`
- `src/controllers/qrcode_controller.py`

**验证方式**: 识别二维码正确，生成二维码可扫描

---

### 阶段 17：导出功能

**目标**: 实现多种格式的结果导出

**任务清单**:
1. 定义 `services/export/base_exporter.py` - 导出器基类
2. 实现 `services/export/text_exporter.py` - TXT 导出
3. 实现 `services/export/json_exporter.py` - JSON 导出
4. 实现 `services/export/excel_exporter.py` - Excel/CSV 导出
5. 实现 `services/export/pdf_exporter.py` - 双层 PDF 导出
6. 编写导出器单元测试

**交付物**: 支持多种格式的导出系统

**关键文件**:
- `src/services/export/base_exporter.py`
- `src/services/export/text_exporter.py`
- `src/services/export/json_exporter.py`
- `src/services/export/excel_exporter.py`
- `src/services/export/pdf_exporter.py`
- `src/tests/test_exporters.py`

**验证方式**: 各格式导出文件可正常打开

---

### 阶段 18：云 OCR - 百度

**目标**: 集成百度云 OCR API

**任务清单**:
1. 实现 `services/ocr/cloud/base_cloud.py` - 云 API 基类
2. 实现 HTTP 请求封装
3. 实现图片 Base64 编码
4. 实现 `services/ocr/cloud/baidu_ocr.py` - 百度 OCR
5. 实现 OAuth2 Token 获取和刷新
6. 编写百度 OCR 单元测试

**交付物**: 可调用的百度云 OCR

**关键文件**:
- `src/services/ocr/cloud/base_cloud.py`
- `src/services/ocr/cloud/baidu_ocr.py`
- `src/tests/test_cloud_ocr.py`

**验证方式**: 配置 API Key 后识别成功

---

### 阶段 19：云 OCR - 腾讯和阿里

**目标**: 集成腾讯云和阿里云 OCR API

**任务清单**:
1. 实现 `services/ocr/cloud/tencent_ocr.py` - 腾讯 OCR
2. 实现腾讯云签名 3.0 算法
3. 实现 `services/ocr/cloud/aliyun_ocr.py` - 阿里 OCR
4. 实现阿里云 API 网关签名
5. 补充云 OCR 单元测试
6. 更新引擎管理器，注册云引擎

**交付物**: 完整的云 OCR 支持

**关键文件**:
- `src/services/ocr/cloud/tencent_ocr.py`
- `src/services/ocr/cloud/aliyun_ocr.py`

**验证方式**: 各云平台识别成功

---

### 阶段 20：设置界面

**目标**: 实现应用设置功能

**任务清单**:
1. 创建 `ui/settings/settings.ui` - 设置界面
2. 实现 `ui/settings/settings.py` - 界面类
3. 实现 `controllers/settings_controller.py` - 控制器
4. 实现 OCR 引擎配置（本地/云选择）
5. 实现云 API Key 配置（加密存储）
6. 实现其他通用设置（语言、快捷键等）

**交付物**: 可用的设置界面

**关键文件**:
- `src/ui/settings/settings.ui`
- `src/ui/settings/settings.py`
- `src/controllers/settings_controller.py`

**验证方式**: 设置保存后重启生效

---

### 阶段 21：系统托盘

**目标**: 实现系统托盘功能

**任务清单**:
1. 实现 `utils/tray_manager.py` - 系统托盘管理
2. 实现托盘图标和右键菜单
3. 实现最小化到托盘
4. 实现托盘气泡通知
5. 实现双击托盘显示主窗口

**交付物**: 可用的系统托盘

**关键文件**:
- `src/utils/tray_manager.py`

**验证方式**: 托盘图标显示，菜单功能正常

---

### 阶段 22：全局快捷键

**目标**: 实现全局热键功能

**任务清单**:
1. 实现 `utils/hotkey_manager.py` - 全局快捷键管理
2. 使用 Windows API (RegisterHotKey) 注册热键
3. 实现快捷键冲突检测
4. 实现自定义快捷键配置
5. 集成到设置界面

**交付物**: 可自定义的全局快捷键

**关键文件**:
- `src/utils/hotkey_manager.py`

**验证方式**: 按快捷键触发截图等功能

---

### 阶段 23：开机自启与多显示器

**目标**: 实现系统级功能

**任务清单**:
1. 实现 `utils/startup_manager.py` - 开机自启管理
2. 实现注册表操作（添加/移除自启）
3. 实现多显示器屏幕枚举
4. 实现跨显示器截图支持
5. 集成到设置界面

**交付物**: 开机自启和多显示器支持

**关键文件**:
- `src/utils/startup_manager.py`

**验证方式**: 开机后自动启动，多显示器截图正确

---

### 阶段 24：悬浮工具栏

**目标**: 实现屏幕边缘悬浮工具栏

**任务清单**:
1. 创建 `ui/floating_bar/floating_bar.ui` - 悬浮工具栏界面
2. 实现 `ui/floating_bar/floating_bar.py` - 悬浮窗口类
3. 实现边缘触发显示/隐藏
4. 实现工具栏按钮（截图、剪贴板OCR等）
5. 实现拖拽移动和位置记忆
6. 实现窗口置顶和透明度

**交付物**: 可用的悬浮工具栏

**关键文件**:
- `src/ui/floating_bar/floating_bar.ui`
- `src/ui/floating_bar/floating_bar.py`

**验证方式**: 鼠标移到屏幕边缘时显示工具栏

---

### 阶段 25：任务管理器界面

**目标**: 实现任务管理可视化界面

**任务清单**:
1. 创建 `ui/task_manager/task_manager.ui` - 任务管理器界面
2. 实现 `ui/task_manager/task_manager.py` - 界面类
3. 实现任务列表显示（进度、状态）
4. 实现任务操作按钮（暂停/恢复/取消/删除）
5. 实现优先级调整
6. 实现任务详情查看

**交付物**: 可用的任务管理器界面

**关键文件**:
- `src/ui/task_manager/task_manager.ui`
- `src/ui/task_manager/task_manager.py`

**验证方式**: 任务列表实时更新，操作按钮有效

---

### 阶段 26：HTTP API 服务

**目标**: 实现 HTTP 接口服务

**任务清单**:
1. 实现 `services/server/http_server.py` - HTTP 服务器
2. 实现 OCR 识别接口
3. 实现任务提交和查询接口
4. 实现鉴权机制（可选）
5. 编写接口文档
6. 编写 HTTP API 测试

**交付物**: 可用的 HTTP API

**关键文件**:
- `src/services/server/http_server.py`
- `docs/http_api.md`

**验证方式**: 使用 curl 或 Postman 调用接口成功

---

### 阶段 27：CLI 接口

**目标**: 实现命令行调用功能

**任务清单**:
1. 实现 `services/server/cli_handler.py` - CLI 处理器
2. 实现命令行参数解析
3. 支持单图识别命令
4. 支持批量识别命令
5. 支持输出格式选择
6. 编写 CLI 文档

**交付物**: 可用的命令行接口

**关键文件**:
- `src/services/server/cli_handler.py`
- `docs/cli_usage.md`

**验证方式**: 命令行调用识别成功

---

### 阶段 28：通用控件

**目标**: 实现可复用的自定义控件

**任务清单**:
1. 实现 `ui/widgets/image_viewer.py` - 图像查看器
2. 实现 `ui/widgets/result_panel.py` - 结果展示面板
3. 实现 `ui/widgets/progress_card.py` - 进度卡片
4. 实现 `ui/widgets/file_list.py` - 文件列表控件
5. 统一控件样式

**交付物**: 可复用的通用控件库

**关键文件**:
- `src/ui/widgets/image_viewer.py`
- `src/ui/widgets/result_panel.py`
- `src/ui/widgets/progress_card.py`

**验证方式**: 各界面使用控件正常

---

### 阶段 29：集成测试与优化

**目标**: 进行系统集成测试和性能优化

**任务清单**:
1. 编写端到端集成测试
2. 进行内存泄漏检测
3. 优化 OCR 引擎内存占用
4. 优化任务并发性能
5. 优化 UI 响应速度
6. 修复发现的 Bug

**交付物**: 稳定的集成系统

**关键文件**:
- `src/tests/test_integration.py`

**验证方式**: 集成测试通过，性能指标达标

---

### 阶段 30：文档与收尾

**目标**: 完善文档和最终收尾

**任务清单**:
1. 完善代码注释（中文）
2. 编写开发者文档
3. 更新用户手册
4. 清理废弃代码
5. 更新 CHANGE_LOG
6. 准备发布版本

**交付物**: 完整的文档和可发布版本

**关键文件**:
- `docs/developer_guide.md`
- `docs/user_manual.md`
- `CHANGE_LOG.md`

**验证方式**: 文档完整，新用户可根据文档使用

---

## 七、命名规范

### 6.1 文件命名
- 使用 snake_case: `screenshot_ocr.py`, `task_manager.py`
- UI 文件与 Python 文件同名: `main_window.ui` + `main_window.py`

### 6.2 类命名
- 使用 PascalCase: `TaskManager`, `OCREngine`, `MainWindow`

### 6.3 函数/方法命名
- 使用 snake_case: `start_task()`, `get_config()`
- 私有方法加下划线前缀: `_internal_method()`

### 6.4 常量命名
- 使用大写 SNAKE_CASE: `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`

### 6.5 信号命名
- 使用 snake_case，带描述性后缀: `task_completed`, `progress_updated`

---

## 八、验证方案

### 7.1 单元测试
```bash
# 运行所有测试
python -m pytest src/tests/ -v

# 运行特定模块测试
python -m pytest src/tests/test_ocr_engines.py -v
```

### 7.2 功能验证清单
- [ ] 主窗口正常启动，侧边栏导航可用
- [ ] 截图 OCR 功能正常
- [ ] 批量图片 OCR 功能正常
- [ ] 批量文档 OCR 功能正常
- [ ] 二维码识别/生成正常
- [ ] 任务暂停/恢复/取消正常
- [ ] 云 OCR API 调用正常
- [ ] 系统托盘功能正常
- [ ] 全局快捷键正常
- [ ] HTTP API 可用
- [ ] CLI 命令可用

### 7.3 性能指标
- 单张图片 OCR 响应时间 < 2s
- 批量任务内存占用稳定
- UI 响应流畅，无卡顿

---

## 九、风险与注意事项

1. **QML 到 Widgets 迁移**: 需要重写所有界面代码，工作量较大
2. **功能回归**: 迁移过程中需确保原有功能不丢失
3. **配置兼容**: 新旧配置格式可能不兼容，需提供迁移方案
4. **PaddleOCR 集成**: 注意内存管理和线程安全
5. **云 API 安全**: API Key 需加密存储

---

## 十、现有关键文件参考

迁移时需重点参考的现有文件:
- `src/tag_pages/ScreenshotOCR.py` - 截图 OCR 逻辑
- `src/tag_pages/BatchOCR.py` - 批量 OCR 逻辑
- `src/tag_pages/BatchDOC.py` - 文档 OCR 逻辑
- `src/tag_pages/QRCode.py` - 二维码逻辑
- `src/mission/mission_ocr.py` - 任务处理逻辑
- `src/ocr/paddleocr_direct.py` - PaddleOCR 集成
- `src/server/` - HTTP/CLI 接口
- `src/utils/` - 工具类
