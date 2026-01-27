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

### 阶段依赖关系 (DAG)

```
╔═════════════════════ 基础设施层 ═════════════════════╗
║                                            ║
║     [1] 项目骨架搭建                          ║
║           │                                  ║
║     ┌─────┼──────────┬──────────┐             ║
║     ↓         ↓          ↓                  ║
║   [2] 日志  [3] 配置   [4] 多语言             ║
║                                            ║
╚════════════════════════════════════════════╝
                    │
        ┌──────────┴───────────┐
        ↓                      ↓
╔══════════════════╗   ╔════════════════════╗
║   OCR 核心层       ║   ║     UI 框架层         ║
║                  ║   ║                    ║
║  [6] 引擎抽象层   ║   ║  [5] 主窗口框架      ║
║       │          ║   ║       │              ║
║       ↓          ║   ║       ↓              ║
║  [7] Paddle引擎   ║   ║  [28] 通用控件       ║
║       │          ║   ║                    ║
║       ↓          ║   ╚════════════════════╝
║  [8] 引擎管理器   ║
║       │          ║
║   ┌───┴───┐       ║
║   ↓       ↓       ║
║ [18]    [19]      ║
║ 百度OCR  腾讯/阿里  ║
║                  ║
╚══════════════════╝
        │
        ↓
╔═══════════════════════════════════════════╗
║                任务系统层                    ║
║                                           ║
║  [9] 任务数据模型                             ║
║       │                                    ║
║       ↓                                    ║
║  [10] 任务队列与调度                           ║
║       │                                    ║
║       ↓                                    ║
║  [11] 任务执行器                              ║
║       │                                    ║
║       ↓                                    ║
║  [12] 任务管理器                              ║
║                                           ║
╚═══════════════════════════════════════════╝
        │
        │─────────────────┬───────────────────┐
        ↓                 ↓                   ↓
╔═══════════════════════════════════════════╗
║           功能模块层 (可并行开发)               ║
║                                           ║
║  [13] 截图OCR   [14] 批量图片  [15] 批量文档  ║
║       │              │              │       ║
║       └───────┬──────┴──────┬─────┘       ║
║               ↓              ↓              ║
║          [17] 导出功能   [16] 二维码         ║
║                                           ║
╚═══════════════════════════════════════════╝
        │
        │─────────────────┬───────────────────┐
        ↓                 ↓                   ↓
╔═════════════╗ ╔═════════════════╗ ╔═════════════╗
║ 系统功能层   ║ ║   UI 模块层     ║ ║  外部接口层 ║
║             ║ ║                 ║ ║             ║
║ [20] 设置   ║ ║ [24] 悬浮工具栏  ║ ║ [26] HTTP  ║
║ [21] 托盘   ║ ║ [25] 任务管理器UI ║ ║ [27] CLI   ║
║ [22] 快捷键 ║ ║                 ║ ║             ║
║ [23] 自启   ║ ║                 ║ ║             ║
║             ║ ║                 ║ ║             ║
╚═════════════╝ ╚═════════════════╝ ╚═════════════╝
        │                 │                   │
        └─────────────────┴───────────────────┘
                          │
                          ↓
              ╔════════════════════════╗
              ║       收尾层            ║
              ║                        ║
              ║  [29] 集成测试与优化    ║
              ║         │              ║
              ║         ↓              ║
              ║  [30] 文档与收尾        ║
              ║                        ║
              ╚════════════════════════╝
```

**关键路径说明**:

| 依赖路径 | 说明 |
|----------|------|
| 1 → 2,3,4 | 基础设施并行，依赖项目骨架 |
| 1 → 5 | 主窗口依赖项目骨架 |
| 6 → 7 → 8 | OCR 引擎链式依赖 |
| 8 → 18,19 | 云引擎依赖引擎管理器 |
| 9 → 10 → 11 → 12 | 任务系统链式依赖 |
| 12 → 13,14,15,16 | 功能模块依赖任务管理器 |
| 13,14,15 → 17 | 导出依赖 OCR 功能模块 |
| 5 → 28 | 通用控件依赖主窗口框架 |
| 12 → 26,27 | 外部接口依赖任务系统 |
| * → 29 → 30 | 收尾依赖所有模块完成 |

**可并行开发建议**:

```
并行组 A (1人): 基础设施 + 任务系统
  1 → 2 → 3 → 4 → 9 → 10 → 11 → 12

并行组 B (1人): OCR 核心 + 云服务
  6 → 7 → 8 → 18 → 19

并行组 C (1人): UI + 控件
  5 → 28 → 24 → 25

汇聚后并行开发: 功能模块 + 系统功能 + 外部接口
  13, 14, 15, 16, 17  (多人并行)
  20, 21, 22, 23      (多人并行)
  26, 27              (多人并行)

收尾阶段:
  29 → 30
```

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

**目标**: 定义任务系统的核心数据结构，支持通用任务类型、多步骤执行、可嵌套层级

**设计要点**:
- Task 和 TaskGroup 支持树形嵌套（TaskGroup 可包含子 TaskGroup）
- 动态优先级仅作用于 TaskGroup 级别
- 数据模型包含轻量业务逻辑（状态验证、进度聚合），不含调度逻辑
- 完整的序列化支持（用于持久化和恢复）

**任务清单**:
1. 定义 `services/task/task_model.py` - 核心数据模型
2. 定义任务状态枚举和状态转换规则
3. 实现 Task 类（单个原子任务）
4. 实现 TaskGroup 类（可嵌套的任务组）
5. 实现进度聚合计算
6. 实现序列化/反序列化
7. 编写模型单元测试

**核心数据结构**:

```python
# services/task/task_model.py

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"        # 等待执行
    RUNNING = "running"        # 执行中
    PAUSED = "paused"          # 已暂停（仅 TaskGroup 支持）
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败（重试耗尽）
    CANCELLED = "cancelled"    # 已取消

class CancelMode(Enum):
    """取消模式"""
    GRACEFUL = "graceful"      # 优雅取消：等待当前 Task 完成
    FORCE = "force"            # 强制取消：立即中断

class TaskType(Enum):
    """任务类型（用于处理器注册分发）"""
    OCR = "ocr"                # OCR 识别
    EXPORT = "export"          # 导出任务
    QRCODE = "qrcode"          # 二维码识别/生成
    PDF_PARSE = "pdf_parse"    # PDF 解析
    CUSTOM = "custom"          # 自定义扩展

@dataclass
class Task:
    """
    单个原子任务（不可再分的最小执行单元）
    
    职责: 持有数据、状态验证、序列化
    不包含: 执行逻辑（由 TaskHandler 处理）
    """
    id: str                              # 唯一标识 (UUID)
    task_type: TaskType                  # 任务类型
    input_data: Dict[str, Any]           # 输入数据
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0                # 进度 0.0 ~ 1.0
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    def is_terminal(self) -> bool:
        """是否处于终态"""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
    
    def is_retryable(self) -> bool:
        """是否可重试"""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries
    
    # 状态转换规则
    _VALID_TRANSITIONS = {
        TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
        TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
        TaskStatus.FAILED: {TaskStatus.PENDING},  # 重试时回到 PENDING
    }
    
    def can_transition_to(self, new_status: TaskStatus) -> bool:
        return new_status in self._VALID_TRANSITIONS.get(self.status, set())
    
    def transition_to(self, new_status: TaskStatus) -> None:
        if not self.can_transition_to(new_status):
            raise InvalidStateTransition(f"{self.status} -> {new_status}")
        self.status = new_status
        # 更新时间戳...
    
    def to_dict(self) -> Dict[str, Any]: ...  # 序列化
    @classmethod
    def from_dict(cls, data: Dict) -> "Task": ...  # 反序列化


@dataclass
class TaskGroup:
    """
    任务组（可嵌套，支持包含子 TaskGroup 或 Task）
    
    层级结构示例:
    TaskGroup (批量处理多个PDF)
      ├── TaskGroup (PDF-1)
      │     ├── Task (第1页OCR)
      │     └── Task (第2页OCR)
      └── TaskGroup (PDF-2)
            └── Task (第1页OCR)
    """
    id: str
    title: str
    children: List[Union["TaskGroup", Task]] = field(default_factory=list)
    priority: int = 0                    # 动态优先级（运行时可调）
    max_concurrency: int = 1             # 组内最大并发数
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime
    
    def add_task(self, task: Task) -> None: ...
    def add_group(self, group: "TaskGroup") -> None: ...
    def get_all_tasks(self) -> List[Task]: ...
    
    @property
    def progress(self) -> float:
        """聚合计算整体进度"""
        all_tasks = self.get_all_tasks()
        if not all_tasks: return 0.0
        return sum(t.progress for t in all_tasks) / len(all_tasks)
    
    def compute_status(self) -> TaskStatus:
        """
        根据子任务状态计算组状态
        规则: 任一 Task 失败且重试耗尽 → 整组 PAUSED
        """
        ...
    
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict) -> "TaskGroup": ...

class InvalidStateTransition(Exception):
    """非法状态转换异常"""
    pass
```

**交付物**: 完整的任务数据模型，支持嵌套结构和序列化

**关键文件**:
- `src/services/task/task_model.py`
- `src/tests/test_task_model.py`

**验证方式**: 
- 单元测试覆盖：状态转换、进度聚合、序列化/反序列化、嵌套结构
- 测试用例：创建三层嵌套结构并验证进度计算正确

---

### 阶段 10：任务队列与调度

**目标**: 实现支持动态优先级的任务队列，提供持久化能力

**设计要点**:
- 优先级队列（堆实现），支持运行时动态调整优先级
- 队列操作线程安全
- 支持按 TaskGroup 暂停/恢复
- 持久化：进行中任务保存 + 历史记录

**任务清单**:
1. 实现 `services/task/task_queue.py` - 优先级任务队列
2. 实现动态优先级调整（重新排序）
3. 实现 TaskGroup 级别的暂停/恢复
4. 实现任务持久化存储
5. 实现历史记录存储
6. 编写队列单元测试

**核心数据结构**:

```python
# services/task/task_queue.py

class TaskQueue(QObject):
    """
    优先级任务队列
    
    职责: 入队/出队、优先级排序、暂停/恢复、持久化
    不包含: 执行逻辑
    线程安全: 所有公共方法加锁
    """
    
    # Qt 信号
    queue_changed = Signal()              # 队列变化
    group_paused = Signal(str)            # (group_id)
    group_resumed = Signal(str)           # (group_id)
    
    def __init__(self, storage_path: Path):
        self._lock = threading.RLock()
        self._heap: List[tuple] = []      # (-priority, created_at, group)
        self._groups: Dict[str, TaskGroup] = {}
        self._paused_groups: Set[str] = set()
        self._storage_path = storage_path
        self._restore_from_storage()      # 启动时恢复
    
    # === 入队操作 ===
    def enqueue(self, group: TaskGroup) -> None:
        """with lock: 添加到队列, 持久化, emit queue_changed"""
    
    # === 出队操作 ===
    def dequeue(self) -> Optional[Task]:
        """
        获取下一个待执行的 Task
        逻辑: 跳过已暂停的 TaskGroup，返回最高优先级组中的第一个 PENDING Task
        """
    
    # === 优先级调整 ===
    def update_priority(self, group_id: str, new_priority: int) -> None:
        """动态调整优先级，重建堆"""
    
    # === 暂停/恢复 ===
    def pause_group(self, group_id: str) -> None:
        """暂停 TaskGroup（不会中断正在执行的 Task）"""
    
    def resume_group(self, group_id: str) -> None:
        """恢复 TaskGroup"""
    
    # === 取消 ===
    def cancel_group(self, group_id: str, mode: CancelMode) -> CancelMode:
        """取消 TaskGroup，返回 mode 供 TaskManager 决定如何处理正在执行的 Task"""
    
    # === 查询 ===
    def get_group(self, group_id: str) -> Optional[TaskGroup]: ...
    def get_all_groups(self) -> List[TaskGroup]: ...
    def get_pending_count(self) -> int: ...
    
    # === 持久化 ===
    def _persist_queue(self) -> None:
        """保存队列状态到 task_queue.json"""
    
    def _restore_from_storage(self) -> None:
        """
        从文件恢复队列状态
        注意: RUNNING 状态的任务重置为 PENDING（程序重启后需重新执行）
        """
    
    def save_to_history(self, group: TaskGroup) -> None:
        """保存已完成的 TaskGroup 到 task_history.jsonl"""
    
    def load_history(self, limit: int = 100) -> List[TaskGroup]:
        """加载历史记录"""
```

**交付物**: 支持动态优先级和持久化的任务队列

**关键文件**:
- `src/services/task/task_queue.py`
- `src/tests/test_task_queue.py`

**验证方式**:
- 单元测试覆盖：入队/出队、优先级调整、暂停/恢复、持久化恢复
- 测试用例：调整优先级后验证出队顺序变化
- 测试用例：模拟程序重启后队列恢复

---

### 阶段 11：任务执行器

**目标**: 实现基于 QThread 的任务执行器，支持处理器注册模式

**设计要点**:
- 处理器注册模式：按 TaskType 注册对应的 Handler
- 节流进度通知（100ms 间隔，避免 UI 刷新过频）
- 混合重试策略：自动重试 N 次后整组暂停等待用户决定
- 支持取消标志检查（配合强制/优雅取消）

**任务清单**:
1. 定义 `services/task/task_handler.py` - 任务处理器基类和注册表
2. 实现 `services/task/task_worker.py` - 任务执行器（QThread）
3. 实现节流进度信号
4. 实现重试逻辑
5. 实现取消检查机制
6. 编写执行器单元测试

**核心数据结构**:

```python
# services/task/task_handler.py

class TaskHandler(ABC):
    """
    任务处理器抽象基类
    
    实现者需要:
    1. 实现 execute() 方法
    2. 在执行过程中定期调用 report_progress()
    3. 在耗时操作前检查 is_cancelled()
    """
    
    @abstractmethod
    def execute(self, task: Task) -> Any:
        """执行任务，返回结果，失败抛异常"""
    
    def report_progress(self, progress: float) -> None:
        """报告进度 (0.0 ~ 1.0)"""
    
    def is_cancelled(self) -> bool:
        """检查是否已取消"""
    
    def request_cancel(self) -> None:
        """请求取消"""


class TaskHandlerRegistry:
    """
    任务处理器注册表（单例）
    
    使用:
        TaskHandlerRegistry.register(TaskType.OCR, OCRTaskHandler)
        handler = TaskHandlerRegistry.get(TaskType.OCR)
    """
    _handlers: Dict[TaskType, Type[TaskHandler]] = {}
    
    @classmethod
    def register(cls, task_type: TaskType, handler_class: Type[TaskHandler]): ...
    @classmethod
    def get(cls, task_type: TaskType) -> TaskHandler: ...


# === 示例：OCR 任务处理器 ===
class OCRTaskHandler(TaskHandler):
    def execute(self, task: Task) -> Dict[str, Any]:
        if self.is_cancelled(): raise TaskCancelledException()
        engine = EngineManager.get_current_engine()
        result = engine.recognize(task.input_data["image_path"])
        self.report_progress(1.0)
        return result.to_dict()

# 注册
TaskHandlerRegistry.register(TaskType.OCR, OCRTaskHandler)
```

```python
# services/task/task_worker.py

class TaskWorker(QThread):
    """
    任务执行器（单个工作线程）
    
    职责: 从队列取任务并执行、管理生命周期、发射信号、处理重试
    由 TaskManager 创建和管理多个 Worker 实例
    """
    
    # Qt 信号
    task_started = Signal(str, str)           # (task_id, group_id)
    task_progress = Signal(str, float)        # (task_id, progress) - 节流后
    task_completed = Signal(str, object)      # (task_id, result)
    task_failed = Signal(str, str)            # (task_id, error_message)
    task_cancelled = Signal(str)              # (task_id)
    group_paused_by_failure = Signal(str)     # (group_id) 因失败暂停
    
    PROGRESS_THROTTLE_MS = 100                # 进度节流间隔
    
    def __init__(self, task_queue: TaskQueue, worker_id: int): ...
    
    def run(self) -> None:
        """
        工作线程主循环:
        while running:
            task = queue.dequeue()
            if task: execute_task(task)
            else: sleep(100ms)
        """
    
    def _execute_task(self, task: Task, group_id: str) -> None:
        """
        执行单个任务:
        1. 状态 PENDING -> RUNNING, emit task_started
        2. 获取 Handler 并执行
        3. 成功: 状态 -> COMPLETED, emit task_completed
        4. 失败: 调用 _handle_failure()
        5. 取消: 状态 -> CANCELLED, emit task_cancelled
        """
    
    def _handle_failure(self, task: Task, group_id: str, error: str) -> None:
        """
        失败处理（混合重试策略）:
        1. retry_count < max_retries: 重置为 PENDING 等待重试
        2. 否则: 标记 FAILED, 整个 TaskGroup 暂停, emit group_paused_by_failure
        """
    
    def _on_progress(self, task_id: str, progress: float) -> None:
        """进度回调（带节流，每 100ms 最多发射一次）"""
    
    def request_cancel(self, mode: CancelMode) -> None:
        """请求取消当前任务"""
    
    def stop(self) -> None:
        """停止工作线程"""


class TaskCancelledException(Exception):
    """任务被取消异常"""
    pass
```

**交付物**: 可在后台执行任务的 Worker，支持处理器注册和重试

**关键文件**:
- `src/services/task/task_handler.py`
- `src/services/task/task_worker.py`
- `src/tests/test_task_worker.py`

**验证方式**:
- 单元测试覆盖：正常执行、失败重试、取消响应、进度节流
- 测试用例：模拟任务失败 3 次后验证 TaskGroup 暂停
- 测试用例：验证进度信号频率不超过 10Hz

---

### 阶段 12：任务管理器

**目标**: 实现任务调度中心，整合队列、执行器，提供统一接口

**设计要点**:
- 单例模式，全局唯一入口
- 混合并发控制：全局最大并发 + TaskGroup 级别并发限制
- 统一的任务提交和控制接口
- Qt 信号连接 UI 层

**任务清单**:
1. 实现 `services/task/task_manager.py` - 任务管理器（单例）
2. 实现混合并发控制
3. 实现任务提交接口
4. 实现暂停/恢复/取消接口
5. 实现优先级调整接口
6. 实现统计和查询接口
7. 编写管理器集成测试

**核心数据结构**:

```python
# services/task/task_manager.py

class TaskManager(QObject):
    """
    任务管理器（单例）
    
    职责: 统一入口、管理 Worker 线程池、混合并发控制、聚合信号
    
    使用:
        manager = TaskManager.instance()
        group_id = manager.submit_ocr_tasks(image_paths, config)
        manager.pause_group(group_id)
    """
    
    # === Qt 信号（供 UI 层连接）===
    task_submitted = Signal(str)              # (group_id)
    task_started = Signal(str, str)           # (task_id, group_id)
    task_progress = Signal(str, float)        # (task_id, progress)
    task_completed = Signal(str, object)      # (task_id, result)
    task_failed = Signal(str, str)            # (task_id, error)
    group_progress = Signal(str, float)       # (group_id, progress)
    group_completed = Signal(str)             # (group_id)
    group_paused = Signal(str, str)           # (group_id, reason: "user"/"failure")
    group_cancelled = Signal(str)             # (group_id)
    queue_changed = Signal()                  # 队列状态变化
    
    _instance: Optional["TaskManager"] = None
    
    @classmethod
    def instance(cls) -> "TaskManager":
        """获取单例"""
    
    def __init__(self):
        self._global_max_concurrency = 3
        self._queue = TaskQueue(storage_path)
        self._workers: List[TaskWorker] = []
        # 连接队列和 Worker 信号...
    
    # === 任务提交接口 ===
    
    def submit_group(self, group: TaskGroup) -> str:
        """提交已构建的 TaskGroup"""
    
    def submit_ocr_tasks(
        self,
        image_paths: List[str],
        title: str = "OCR任务",
        priority: int = 0,
        max_concurrency: int = 1,
        engine_config: Optional[Dict] = None,
    ) -> str:
        """便捷方法：提交 OCR 任务组"""
    
    def submit_pdf_tasks(
        self,
        pdf_paths: List[str],
        title: str = "PDF识别",
        priority: int = 0,
    ) -> str:
        """
        便捷方法：提交 PDF 识别任务组（嵌套结构）
        
        生成结构:
        TaskGroup (总任务)
          ├── TaskGroup (PDF-1) -> [Task(第1页), Task(第2页)...]
          └── TaskGroup (PDF-2) -> [...]
        """
    
    # === 控制接口 ===
    
    def pause_group(self, group_id: str) -> None:
        """暂停任务组"""
    
    def resume_group(self, group_id: str) -> None:
        """恢复任务组"""
    
    def cancel_group(self, group_id: str, mode: CancelMode = CancelMode.GRACEFUL) -> None:
        """
        取消任务组
        GRACEFUL: 等待当前 Task 完成
        FORCE: 立即中断
        """
    
    def retry_failed_tasks(self, group_id: str) -> None:
        """重试失败的任务（用户点击重试后调用）"""
    
    def skip_failed_tasks(self, group_id: str) -> None:
        """跳过失败的任务，继续执行其他任务"""
    
    def update_priority(self, group_id: str, new_priority: int) -> None:
        """动态调整优先级"""
    
    # === 查询接口 ===
    
    def get_group(self, group_id: str) -> Optional[TaskGroup]: ...
    def get_all_groups(self) -> List[TaskGroup]: ...
    def get_history(self, limit: int = 100) -> List[TaskGroup]: ...
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息:
        {
            "total_groups": int,
            "total_tasks": int,
            "completed_tasks": int,
            "pending_tasks": int,
            "active_workers": int,
        }
        """
    
    # === 配置接口 ===
    
    def set_global_concurrency(self, max_concurrency: int) -> None:
        """设置全局最大并发数"""
    
    # === 生命周期 ===
    
    def shutdown(self) -> None:
        """关闭管理器，停止所有 Worker，保存队列状态"""
```

**接口边界总结**:

```
┌────────────────────────────────────────────────────────────────┐
│                         UI 层                                  │
│   调用: submit_ocr_tasks(), pause_group(), get_statistics()    │
│   监听: task_progress, group_completed, group_paused           │
└─────────────────────────────────┬──────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │     TaskManager        │  ← 单例，统一入口
                    │   - 提交/控制/查询接口  │
                    │   - 混合并发控制        │
                    │   - 信号聚合转发        │
                    └───────┬───────┬───────┘
                            │       │
           ┌──────────────┘       └──────────────┐
           │                                      │
┌──────────┴─────────┐               ┌─────────┴─────────┐
│     TaskQueue         │               │    TaskWorker (x N)   │
│  - 优先级队列          │   dequeue()   │  - 从队列取任务         │
│  - 暂停/恢复          │ ─────────→  │  - 调用 Handler 执行   │
│  - 持久化             │               │  - 重试/取消            │
└─────────────────────┘               └──────────┬─────────┘
                                                   │
                                      ┌───────────┴──────────┐
                                      │   TaskHandlerRegistry   │
                                      │  - 注册: OCR/Export/...  │
                                      │  - 获取: get(TaskType)   │
                                      └────────────────────────┘
```

**交付物**: 完整的任务管理系统

**关键文件**:
- `src/services/task/task_manager.py`
- `src/services/task/__init__.py`
- `src/tests/test_task_manager.py`

**验证方式**:
- 集成测试覆盖：提交任务、并发执行、暂停/恢复/取消、优先级调整
- 测试用例：提交 10 个任务，验证并发数不超过全局限制
- 测试用例：模拟程序重启后未完成任务自动恢复

---

### 阶段 13：截图 OCR 模块

**目标**: 实现截图识别功能，全屏覆盖层方案，支持丰富的交互功能

**设计要点**:
- 全屏覆盖层实现（跨平台兼容）
- 支持多显示器（创建跨屏虚拟画布）
- 单张截图也走任务系统，保持架构统一

**任务清单**:
1. 实现 `services/screenshot/screen_capture.py` - 屏幕捕获
2. 实现 `services/screenshot/region_selector.py` - 区域选择器
3. 创建 `ui/screenshot_ocr/screenshot_ocr.ui` - 截图 OCR 界面
4. 实现 `ui/screenshot_ocr/screenshot_ocr.py` - 界面类
5. 实现 `controllers/screenshot_controller.py` - 控制器
6. 集成任务系统

**核心数据结构**:

```python
# services/screenshot/screen_capture.py

class ScreenCapture:
    """
    屏幕捕获服务
    
    职责: 截取屏幕指定区域，支持多显示器
    """
    
    def get_all_screens(self) -> List[ScreenInfo]:
        """获取所有显示器信息"""
    
    def get_virtual_screen_geometry(self) -> QRect:
        """获取跨屏虚拟画布范围"""
    
    def capture_region(self, rect: QRect) -> QPixmap:
        """截取指定区域"""
    
    def capture_full_screen(self) -> QPixmap:
        """截取全屏（包含所有显示器）"""

@dataclass
class ScreenInfo:
    """  显示器信息"""
    name: str
    geometry: QRect
    is_primary: bool
    scale_factor: float
```

```python
# services/screenshot/region_selector.py

class RegionSelector(QWidget):
    """
    区域选择器（全屏覆盖层窗口）
    
    功能:
    - 窗口识别: 鼠标悬停时高亮窗口边框
    - 坐标显示: 实时显示鼠标位置和选区尺寸
    - 比例约束: Shift+拖动锁定正方形/常用比例
    - 选区调整: 拖动边缘/角调整大小，拖动中心移动
    - 放大镜: 鼠标附近显示放大图像
    - 快捷键: Esc取消、Enter确认、数字键切换比例
    """
    
    # === 信号 ===
    region_selected = Signal(QRect)       # 选区完成
    selection_cancelled = Signal()        # 取消选择
    
    # === 比例预设 ===
    ASPECT_RATIOS = {
        "free": None,         # 自由比例
        "1:1": 1.0,           # 正方形
        "4:3": 4/3,
        "16:9": 16/9,
        "3:2": 3/2,
    }
    
    def __init__(self):
        # 创建跨屏无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._screen_capture = ScreenCapture()
        self._window_detector = WindowDetector()
        self._magnifier = Magnifier()
        
        self._selection_rect: Optional[QRect] = None
        self._current_aspect_ratio: Optional[float] = None
        self._is_dragging = False
        self._drag_mode: DragMode = DragMode.NONE  # NONE/CREATE/MOVE/RESIZE
    
    def start(self) -> None:
        """
        开始选区:
        1. 截取全屏作为背景
        2. 显示覆盖层
        3. 等待用户选择
        """
    
    def paintEvent(self, event) -> None:
        """
        绘制:
        - 半透明遮罩层
        - 选区显示原图
        - 选区边框和调整手柄
        - 坐标信息
        - 放大镜
        """
    
    def mouseMoveEvent(self, event) -> None:
        """
        鼠标移动:
        - 更新选区/调整大小/移动
        - 检测窗口悬停
        - 更新放大镜
        """
    
    def keyPressEvent(self, event) -> None:
        """
        快捷键:
        - Esc: 取消
        - Enter/Space: 确认
        - Shift: 锁定比例
        - 1-5: 切换预设比例
        - 方向键: 微调选区
        """


class DragMode(Enum):
    NONE = "none"
    CREATE = "create"      # 创建新选区
    MOVE = "move"          # 移动选区
    RESIZE_N = "resize_n"  # 调整上边
    RESIZE_S = "resize_s"
    RESIZE_E = "resize_e"
    RESIZE_W = "resize_w"
    RESIZE_NE = "resize_ne"
    RESIZE_NW = "resize_nw"
    RESIZE_SE = "resize_se"
    RESIZE_SW = "resize_sw"


class WindowDetector:
    """窗口检测器（用于窗口识别功能）"""
    
    def get_window_at(self, pos: QPoint) -> Optional[WindowInfo]:
        """获取指定位置的窗口"""
    
    def get_all_windows(self) -> List[WindowInfo]:
        """枚举所有可见窗口"""

@dataclass
class WindowInfo:
    hwnd: int
    title: str
    rect: QRect
    class_name: str


class Magnifier(QWidget):
    """放大镜控件"""
    ZOOM_FACTOR = 4  # 放大倍数
    SIZE = 120       # 放大镜尺寸
    
    def update_position(self, screen_pos: QPoint, source_image: QPixmap): ...
```

```python
# controllers/screenshot_controller.py

class ScreenshotController(QObject):
    """
    截图 OCR 控制器
    
    流程:
    1. 快捷键触发 -> start_capture()
    2. RegionSelector 选区 -> region_selected
    3. 创建 Task 提交到 TaskManager
    4. 监听结果 -> 显示在 UI
    """
    
    def __init__(self, view: ScreenshotOCRView):
        self._view = view
        self._selector = RegionSelector()
        self._task_manager = TaskManager.instance()
        
        self._selector.region_selected.connect(self._on_region_selected)
    
    def start_capture(self) -> None:
        """开始截图"""
        self._selector.start()
    
    def _on_region_selected(self, rect: QRect) -> None:
        """
        选区完成后:
        1. 截取图像
        2. 保存为临时文件
        3. 创建 OCR 任务提交
        """
        capture = ScreenCapture()
        image = capture.capture_region(rect)
        
        # 保存临时文件
        temp_path = self._save_temp_image(image)
        
        # 提交任务（单张图也走任务系统）
        group_id = self._task_manager.submit_ocr_tasks(
            image_paths=[temp_path],
            title="截图OCR",
            priority=10,  # 截图优先级较高
        )
        
        self._view.show_pending(group_id)
```

**交付物**: 可用的截图 OCR 功能，支持完整的区域选择交互

**关键文件**:
- `src/services/screenshot/screen_capture.py`
- `src/services/screenshot/region_selector.py`
- `src/services/screenshot/window_detector.py`
- `src/services/screenshot/magnifier.py`
- `src/ui/screenshot_ocr/screenshot_ocr.ui`
- `src/ui/screenshot_ocr/screenshot_ocr.py`
- `src/controllers/screenshot_controller.py`

**验证方式**:
- 截图后正确识别并显示结果
- 多显示器环境下正常工作
- 比例约束、放大镜、窗口识别功能正常

---

### 阶段 14：批量图片 OCR 模块

**目标**: 实现批量图片识别功能，支持多种文件添加方式

**设计要点**:
- 支持拖拽、文件选择器、剪贴板粘贴三种输入方式
- 文件列表显示进度和状态
- 完全走任务系统

**任务清单**:
1. 创建 `ui/batch_ocr/batch_ocr.ui` - 批量 OCR 界面
2. 实现 `ui/batch_ocr/batch_ocr.py` - 界面类
3. 实现文件拖拽添加
4. 实现文件列表管理（添加/删除/清空）
5. 实现 `controllers/batch_ocr_controller.py` - 控制器
6. 集成任务系统，显示批量进度

**核心数据结构**:

```python
# ui/batch_ocr/batch_ocr.py

class BatchOCRView(QWidget):
    """
    批量图片 OCR 界面
    
    布局:
    ┌─────────────────────────────────────────┐
    │  工具栏: [添加] [清空] [开始] [暂停]     │
    ├────────────────────┬────────────────────┤
    │  文件列表            │  识别结果             │
    │  - file1.jpg  ✔     │  [文本内容显示区]      │
    │  - file2.png  ▶     │                      │
    │  - file3.jpg  ⏸     │                      │
    ├────────────────────┴────────────────────┤
    │  状态栏: 进度 3/10  导出格式: [TXT▼]     │
    └─────────────────────────────────────────┘
    """
    
    def __init__(self):
        # 启用拖拽
        self.setAcceptDrops(True)
    
    # === 拖拽支持 ===
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """    处理拖拽文件/文件夹"""
        urls = event.mimeData().urls()
        paths = self._extract_image_paths(urls)
        self.controller.add_files(paths)
    
    # === 剪贴板支持 ===
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Paste):
            self._handle_paste()
    
    def _handle_paste(self):
        """
        处理 Ctrl+V:
        - 图片数据 -> 保存为临时文件
        - 文件路径文本 -> 解析路径
        """
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        
        if mime.hasImage():
            image = clipboard.image()
            temp_path = self._save_clipboard_image(image)
            self.controller.add_files([temp_path])
        elif mime.hasText():
            paths = self._parse_path_text(mime.text())
            self.controller.add_files(paths)


class FileListWidget(QListWidget):
    """
    文件列表控件
    
    显示内容:
    - 文件名
    - 状态图标（等待/执行中/完成/失败）
    - 进度条（执行中时）
    """
    
    def update_item_status(self, file_path: str, status: TaskStatus, progress: float = 0): ...
    def get_selected_paths(self) -> List[str]: ...
    def remove_selected(self) -> None: ...
    def clear_all(self) -> None: ...
```

```python
# controllers/batch_ocr_controller.py

class BatchOCRController(QObject):
    """
    批量图片 OCR 控制器
    """
    
    # 支持的图片格式
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff"}
    
    def __init__(self, view: BatchOCRView):
        self._view = view
        self._task_manager = TaskManager.instance()
        self._pending_files: List[str] = []  # 待处理文件
        self._current_group_id: Optional[str] = None
        
        # 连接任务管理器信号
        self._task_manager.task_progress.connect(self._on_task_progress)
        self._task_manager.task_completed.connect(self._on_task_completed)
        self._task_manager.group_completed.connect(self._on_group_completed)
    
    def add_files(self, paths: List[str]) -> None:
        """
        添加文件
        - 过滤不支持的格式
        - 展开文件夹
        - 去重
        """
        for path in paths:
            if os.path.isdir(path):
                self._add_folder(path)
            elif self._is_supported(path):
                if path not in self._pending_files:
                    self._pending_files.append(path)
                    self._view.file_list.add_item(path)
    
    def start_ocr(self) -> None:
        """开始 OCR"""
        if not self._pending_files:
            return
        
        self._current_group_id = self._task_manager.submit_ocr_tasks(
            image_paths=self._pending_files.copy(),
            title=f"批量识别 ({len(self._pending_files)}张)",
            max_concurrency=2,  # 批量任务可并行
        )
    
    def pause_ocr(self) -> None:
        if self._current_group_id:
            self._task_manager.pause_group(self._current_group_id)
    
    def resume_ocr(self) -> None:
        if self._current_group_id:
            self._task_manager.resume_group(self._current_group_id)
    
    def cancel_ocr(self) -> None:
        if self._current_group_id:
            self._task_manager.cancel_group(self._current_group_id)
    
    def clear_files(self) -> None:
        self._pending_files.clear()
        self._view.file_list.clear_all()
    
    def _on_task_progress(self, task_id: str, progress: float):
        """更新单个文件进度"""
    
    def _on_task_completed(self, task_id: str, result: Any):
        """单个文件完成，显示结果"""
    
    def _on_group_completed(self, group_id: str):
        """整组完成，提示导出"""
```

**交付物**: 可用的批量图片 OCR 功能

**关键文件**:
- `src/ui/batch_ocr/batch_ocr.ui`
- `src/ui/batch_ocr/batch_ocr.py`
- `src/controllers/batch_ocr_controller.py`

**验证方式**:
- 拖拽文件/文件夹添加正常
- Ctrl+V 粘贴图片/路径正常
- 批量识别进度显示正确
- 暂停/恢复/取消功能正常

---

### 阶段 15：批量文档 OCR 模块

**目标**: 实现 PDF 等文档的批量识别，支持混合处理策略

**设计要点**:
- PDF 混合处理：自动检测，有文字层直接提取，无则 OCR
- 支持生成双层 PDF（带可搜索文字层）
- 支持转换为 Word/Excel/Markdown
- 使用嵌套 TaskGroup 结构（每个 PDF 一个子组）

**任务清单**:
1. 实现 `services/document/pdf_parser.py` - PDF 解析服务
2. 实现 `services/document/pdf_generator.py` - 双层 PDF 生成
3. 创建 `ui/batch_doc/batch_doc.ui` - 文档 OCR 界面
4. 实现 `ui/batch_doc/batch_doc.py` - 界面类
5. 实现 `controllers/batch_doc_controller.py` - 控制器
6. 集成任务系统

**核心数据结构**:

```python
# services/document/pdf_parser.py

import fitz  # pymupdf

class PDFParser:
    """
    PDF 解析服务
    
    功能:
    - 检测是否有文字层
    - 提取文字层内容
    - 提取页面为图像（用于 OCR）
    """
    
    def __init__(self, pdf_path: str):
        self._doc = fitz.open(pdf_path)
        self._path = pdf_path
    
    @property
    def page_count(self) -> int:
        return len(self._doc)
    
    def has_text_layer(self, page_num: int) -> bool:
        """检测指定页是否有文字层"""
        page = self._doc[page_num]
        text = page.get_text()
        return len(text.strip()) > 10  # 简单阈值判断
    
    def extract_text(self, page_num: int) -> str:
        """提取文字层内容"""
        page = self._doc[page_num]
        return page.get_text()
    
    def page_to_image(self, page_num: int, dpi: int = 200) -> bytes:
        """
        页面转换为图像
        
        Args:
            page_num: 页码
            dpi: 分辨率
        
        Returns:
            PNG 图像字节
        """
        page = self._doc[page_num]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")
    
    def get_page_info(self, page_num: int) -> PageInfo:
        """获取页面信息"""
        page = self._doc[page_num]
        return PageInfo(
            width=page.rect.width,
            height=page.rect.height,
            has_text=self.has_text_layer(page_num),
        )
    
    def close(self):
        self._doc.close()


@dataclass
class PageInfo:
    width: float
    height: float
    has_text: bool
```

```python
# services/document/pdf_generator.py

class PDFGenerator:
    """
    双层 PDF 生成器
    
    功能: 生成带可搜索文字层的 PDF
    """
    
    def __init__(self, output_path: str):
        self._output_path = output_path
        self._doc = fitz.open()  # 新建空文档
    
    def add_page_with_ocr(
        self,
        image_bytes: bytes,
        ocr_result: OCRResult,
        page_size: tuple[float, float],
    ) -> None:
        """
        添加带 OCR 结果的页面
        
        Args:
            image_bytes: 页面图像
            ocr_result: OCR 识别结果（包含位置信息）
            page_size: 页面尺寸 (width, height)
        """
        # 创建新页
        page = self._doc.new_page(width=page_size[0], height=page_size[1])
        
        # 插入背景图像
        page.insert_image(page.rect, stream=image_bytes)
        
        # 插入不可见文字层（用于搜索/复制）
        for block in ocr_result.blocks:
            # 使用透明文字覆盖在图像上
            text_rect = fitz.Rect(block.x1, block.y1, block.x2, block.y2)
            page.insert_text(
                text_rect.tl,
                block.text,
                fontsize=1,  # 极小字体，不影响视觉
                render_mode=3,  # 不可见模式
            )
    
    def save(self) -> None:
        self._doc.save(self._output_path)
        self._doc.close()
```

```python
# controllers/batch_doc_controller.py

class BatchDocController(QObject):
    """
    批量文档 OCR 控制器
    """
    
    def __init__(self, view: BatchDocView):
        self._view = view
        self._task_manager = TaskManager.instance()
    
    def process_pdfs(self, pdf_paths: List[str]) -> str:
        """
        处理 PDF 文件
        
        创建嵌套任务结构:
        TaskGroup ("批量 PDF 识别")
          ├── TaskGroup ("doc1.pdf")
          │     ├── Task ("第1页") - OCR 或 提取
          │     ├── Task ("第2页")
          │     └── ...
          └── TaskGroup ("doc2.pdf")
                └── ...
        """
        root_group = TaskGroup(
            id=str(uuid.uuid4()),
            title=f"PDF识别 ({len(pdf_paths)}个文件)",
            max_concurrency=1,  # PDF 串行处理
        )
        
        for pdf_path in pdf_paths:
            parser = PDFParser(pdf_path)
            pdf_group = TaskGroup(
                id=str(uuid.uuid4()),
                title=Path(pdf_path).name,
                max_concurrency=2,  # 页面可并行
            )
            
            for page_num in range(parser.page_count):
                page_info = parser.get_page_info(page_num)
                
                if page_info.has_text:
                    # 有文字层，直接提取
                    task = Task(
                        id=str(uuid.uuid4()),
                        task_type=TaskType.PDF_PARSE,
                        input_data={
                            "pdf_path": pdf_path,
                            "page_num": page_num,
                            "mode": "extract",
                        },
                    )
                else:
                    # 无文字层，需要 OCR
                    task = Task(
                        id=str(uuid.uuid4()),
                        task_type=TaskType.PDF_PARSE,
                        input_data={
                            "pdf_path": pdf_path,
                            "page_num": page_num,
                            "mode": "ocr",
                        },
                    )
                
                pdf_group.add_task(task)
            
            parser.close()
            root_group.add_group(pdf_group)
        
        return self._task_manager.submit_group(root_group)
    
    def export_as_searchable_pdf(self, group_id: str, output_path: str) -> None:
        """导出为可搜索 PDF"""
    
    def export_as_word(self, group_id: str, output_path: str) -> None:
        """导出为 Word"""
    
    def export_as_excel(self, group_id: str, output_path: str) -> None:
        """导出为 Excel"""
    
    def export_as_markdown(self, group_id: str, output_path: str) -> None:
        """导出为 Markdown"""
```

**交付物**: 可用的批量文档 OCR 功能，支持混合处理和多格式导出

**关键文件**:
- `src/services/document/pdf_parser.py`
- `src/services/document/pdf_generator.py`
- `src/ui/batch_doc/batch_doc.ui`
- `src/ui/batch_doc/batch_doc.py`
- `src/controllers/batch_doc_controller.py`

**验证方式**:
- 混合 PDF（部分页有文字层）处理正确
- 生成的双层 PDF 可搜索、可复制文字
- Word/Excel/Markdown 导出正常

---

### 阶段 16：二维码模块

**目标**: 实现二维码/条形码识别和生成功能

**设计要点**:
- 识别：支持二维码 + 条形码，支持一张图片多个码
- 生成：自定义选项（尺寸、容错、Logo、颜色），支持批量生成
- 完全走任务系统

**任务清单**:
1. 实现 `services/qrcode/qrcode_scanner.py` - 码识别服务
2. 实现 `services/qrcode/qrcode_generator.py` - 码生成服务
3. 创建 `ui/qrcode/qrcode.ui` - 二维码界面
4. 实现 `ui/qrcode/qrcode.py` - 界面类
5. 实现 `controllers/qrcode_controller.py` - 控制器

**核心数据结构**:

```python
# services/qrcode/qrcode_scanner.py

from pyzbar import pyzbar
from PIL import Image

class QRCodeScanner:
    """
    二维码/条形码识别服务
    
    支持的码类型:
    - 二维码: QR Code, Data Matrix, PDF417, Aztec
    - 条形码: EAN-13, EAN-8, UPC-A, Code 128, Code 39, ITF
    """
    
    @dataclass
    class ScanResult:
        """    识别结果"""
        data: str              # 解码内容
        type: str              # 码类型 (QRCODE, EAN13, etc.)
        rect: tuple            # 位置 (x, y, w, h)
        polygon: List[tuple]   # 边界点
    
    def scan(self, image_path: str) -> List[ScanResult]:
        """
        识别图片中的所有码
        
        Args:
            image_path: 图片路径
        
        Returns:
            识别结果列表（支持多码）
        """
        image = Image.open(image_path)
        decoded = pyzbar.decode(image)
        
        results = []
        for obj in decoded:
            results.append(self.ScanResult(
                data=obj.data.decode("utf-8"),
                type=obj.type,
                rect=obj.rect,
                polygon=[(p.x, p.y) for p in obj.polygon],
            ))
        return results
    
    def scan_bytes(self, image_bytes: bytes) -> List[ScanResult]:
        """从字节数据识别"""
        image = Image.open(io.BytesIO(image_bytes))
        # ...
```

```python
# services/qrcode/qrcode_generator.py

import qrcode
from PIL import Image

class QRCodeGenerator:
    """
    二维码生成服务
    """
    
    @dataclass
    class GenerateOptions:
        """生成选项"""
        size: int = 300                    # 图片尺寸 (px)
        error_correction: str = "M"       # 容错级别: L(7%), M(15%), Q(25%), H(30%)
        fill_color: str = "#000000"       # 前景色
        back_color: str = "#FFFFFF"       # 背景色
        logo_path: Optional[str] = None   # Logo 图片路径
        logo_size_ratio: float = 0.25     # Logo 占比
        border: int = 4                   # 边框宽度
    
    ERROR_CORRECTION_MAP = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }
    
    def generate(self, data: str, options: GenerateOptions = None) -> Image.Image:
        """
        生成二维码
        
        Args:
            data: 编码内容
            options: 生成选项
        
        Returns:
            PIL Image 对象
        """
        options = options or self.GenerateOptions()
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=self.ERROR_CORRECTION_MAP[options.error_correction],
            box_size=10,
            border=options.border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(
            fill_color=options.fill_color,
            back_color=options.back_color,
        ).convert("RGBA")
        
        # 调整尺寸
        img = img.resize((options.size, options.size), Image.LANCZOS)
        
        # 添加 Logo
        if options.logo_path:
            img = self._add_logo(img, options.logo_path, options.logo_size_ratio)
        
        return img
    
    def _add_logo(self, qr_img: Image.Image, logo_path: str, ratio: float) -> Image.Image:
        """在二维码中心添加 Logo"""
        logo = Image.open(logo_path).convert("RGBA")
        
        # 计算 Logo 尺寸
        logo_size = int(qr_img.size[0] * ratio)
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        
        # 居中粘贴
        pos = ((qr_img.size[0] - logo_size) // 2, (qr_img.size[1] - logo_size) // 2)
        qr_img.paste(logo, pos, logo)
        
        return qr_img
    
    def save(self, img: Image.Image, output_path: str) -> None:
        """保存图片"""
        img.save(output_path)
    
    def batch_generate(
        self,
        data_list: List[str],
        output_dir: str,
        options: GenerateOptions = None,
    ) -> List[str]:
        """
        批量生成二维码
        
        Args:
            data_list: 编码内容列表
            output_dir: 输出目录
            options: 生成选项
        
        Returns:
            生成的文件路径列表
        """
        output_paths = []
        for i, data in enumerate(data_list):
            img = self.generate(data, options)
            output_path = os.path.join(output_dir, f"qrcode_{i+1}.png")
            self.save(img, output_path)
            output_paths.append(output_path)
        return output_paths
```

```python
# controllers/qrcode_controller.py

class QRCodeController(QObject):
    """
    二维码控制器
    """
    
    def __init__(self, view: QRCodeView):
        self._view = view
        self._scanner = QRCodeScanner()
        self._generator = QRCodeGenerator()
        self._task_manager = TaskManager.instance()
    
    def scan_image(self, image_path: str) -> str:
        """
        识别图片中的码（通过任务系统）
        """
        return self._task_manager.submit_group(TaskGroup(
            id=str(uuid.uuid4()),
            title="二维码识别",
            children=[Task(
                id=str(uuid.uuid4()),
                task_type=TaskType.QRCODE,
                input_data={"image_path": image_path, "mode": "scan"},
            )],
        ))
    
    def generate_qrcode(self, data: str, options: dict) -> str:
        """生成单个二维码"""
        # 走任务系统
    
    def batch_generate(self, data_list: List[str], options: dict) -> str:
        """批量生成二维码"""
        # 创建 TaskGroup，每个二维码一个 Task
```

**交付物**: 可用的二维码识别和生成功能

**关键文件**:
- `src/services/qrcode/qrcode_scanner.py`
- `src/services/qrcode/qrcode_generator.py`
- `src/ui/qrcode/qrcode.ui`
- `src/ui/qrcode/qrcode.py`
- `src/controllers/qrcode_controller.py`

**验证方式**:
- 识别二维码和条形码正确
- 一张图片多个码能全部识别
- 生成的二维码可正常扫描
- 自定义选项（颜色、Logo等）生效
- 批量生成正常

---

### 阶段 17：导出功能

**目标**: 实现多种格式的结果导出，支持普通/高级两种模式

**设计要点**:
- 支持格式：TXT、JSON、HTML、Word、Excel、Markdown、双层 PDF
- 普通模式：仅导出文本内容
- 高级模式：保留位置信息、置信度等元数据

**任务清单**:
1. 定义 `services/export/base_exporter.py` - 导出器基类
2. 实现 `services/export/text_exporter.py` - TXT 导出
3. 实现 `services/export/json_exporter.py` - JSON 导出
4. 实现 `services/export/html_exporter.py` - HTML 导出
5. 实现 `services/export/word_exporter.py` - Word 导出
6. 实现 `services/export/excel_exporter.py` - Excel 导出
7. 实现 `services/export/markdown_exporter.py` - Markdown 导出
8. 实现 `services/export/pdf_exporter.py` - 双层 PDF 导出
9. 编写导出器单元测试

**核心数据结构**:

```python
# services/export/base_exporter.py

class ExportMode(Enum):
    """导出模式"""
    SIMPLE = "simple"      # 普通模式：仅文本
    ADVANCED = "advanced"  # 高级模式：包含元数据

@dataclass
class ExportData:
    """
    导出数据结构
    
    普通模式只使用 text 字段
    高级模式使用所有字段
    """
    source_file: str               # 源文件路径
    text: str                      # 识别文本
    blocks: List[TextBlock] = None # 文本块列表（高级模式）
    metadata: Dict[str, Any] = None # 元数据

@dataclass
class TextBlock:
    """文本块（包含位置信息）"""
    text: str
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float              # 置信度 0.0 ~ 1.0
    line_num: int                  # 行号


class BaseExporter(ABC):
    """
    导出器抽象基类
    """
    
    def __init__(self, mode: ExportMode = ExportMode.SIMPLE):
        self._mode = mode
    
    @property
    @abstractmethod
    def file_extension(self) -> str:
        """文件扩展名"""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """显示名称（用于 UI）"""
        pass
    
    @abstractmethod
    def export(self, data: List[ExportData], output_path: str) -> None:
        """
        执行导出
        
        Args:
            data: 导出数据列表
            output_path: 输出文件路径
        """
        pass
```

```python
# services/export/text_exporter.py

class TextExporter(BaseExporter):
    """TXT 导出器"""
    
    @property
    def file_extension(self) -> str:
        return ".txt"
    
    @property
    def display_name(self) -> str:
        return "纯文本 (TXT)"
    
    def export(self, data: List[ExportData], output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(f"=== {item.source_file} ===\n")
                f.write(item.text)
                f.write("\n\n")
```

```python
# services/export/json_exporter.py

class JSONExporter(BaseExporter):
    """JSON 导出器"""
    
    @property
    def file_extension(self) -> str:
        return ".json"
    
    @property
    def display_name(self) -> str:
        return "结构化数据 (JSON)"
    
    def export(self, data: List[ExportData], output_path: str) -> None:
        result = []
        for item in data:
            entry = {
                "source": item.source_file,
                "text": item.text,
            }
            
            # 高级模式包含详细信息
            if self._mode == ExportMode.ADVANCED and item.blocks:
                entry["blocks"] = [
                    {
                        "text": b.text,
                        "bbox": [b.x1, b.y1, b.x2, b.y2],
                        "confidence": b.confidence,
                        "line": b.line_num,
                    }
                    for b in item.blocks
                ]
                entry["metadata"] = item.metadata
            
            result.append(entry)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
```

```python
# services/export/html_exporter.py

class HTMLExporter(BaseExporter):
    """HTML 导出器"""
    
    @property
    def file_extension(self) -> str:
        return ".html"
    
    @property
    def display_name(self) -> str:
        return "HTML"
    
    def export(self, data: List[ExportData], output_path: str) -> None:
        """
        普通模式: 简单 HTML 结构
        高级模式: 包含 CSS 样式、位置信息、可交互元素
        """
        if self._mode == ExportMode.SIMPLE:
            self._export_simple(data, output_path)
        else:
            self._export_advanced(data, output_path)
    
    def _export_simple(self, data: List[ExportData], output_path: str) -> None:
        """    普通 HTML 导出"""
        html = "<html><body>"
        for item in data:
            html += f"<h2>{item.source_file}</h2>"
            html += f"<pre>{item.text}</pre>"
        html += "</body></html>"
        # ...
    
    def _export_advanced(self, data: List[ExportData], output_path: str) -> None:
        """高级 HTML 导出（包含位置信息、样式）"""
        # 生成包含 CSS 、位置信息的完整 HTML
        # ...
```

```python
# services/export/word_exporter.py

from docx import Document

class WordExporter(BaseExporter):
    """Word 导出器"""
    
    @property
    def file_extension(self) -> str:
        return ".docx"
    
    @property
    def display_name(self) -> str:
        return "Word 文档 (DOCX)"
    
    def export(self, data: List[ExportData], output_path: str) -> None:
        doc = Document()
        
        for item in data:
            doc.add_heading(item.source_file, level=1)
            doc.add_paragraph(item.text)
            doc.add_page_break()
        
        doc.save(output_path)
```

```python
# services/export/excel_exporter.py

import openpyxl

class ExcelExporter(BaseExporter):
    """Excel 导出器"""
    
    @property
    def file_extension(self) -> str:
        return ".xlsx"
    
    @property
    def display_name(self) -> str:
        return "Excel (XLSX)"
    
    def export(self, data: List[ExportData], output_path: str) -> None:
        """
        普通模式: 每行一个文件（文件名 | 内容）
        高级模式: 多列（文件名 | 内容 | 坐标 | 置信度）
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        
        if self._mode == ExportMode.SIMPLE:
            ws.append(["    文件", "识别内容"])
            for item in data:
                ws.append([item.source_file, item.text])
        else:
            ws.append(["文件", "内容", "X1", "Y1", "X2", "Y2", "置信度"])
            for item in data:
                if item.blocks:
                    for block in item.blocks:
                        ws.append([
                            item.source_file,
                            block.text,
                            block.x1, block.y1, block.x2, block.y2,
                            block.confidence,
                        ])
        
        wb.save(output_path)
```

```python
# services/export/exporter_registry.py

class ExporterRegistry:
    """导出器注册表"""
    
    _exporters: Dict[str, Type[BaseExporter]] = {}
    
    @classmethod
    def register(cls, name: str, exporter_class: Type[BaseExporter]):
        cls._exporters[name] = exporter_class
    
    @classmethod
    def get(cls, name: str, mode: ExportMode = ExportMode.SIMPLE) -> BaseExporter:
        return cls._exporters[name](mode)
    
    @classmethod
    def get_all(cls) -> List[str]:
        return list(cls._exporters.keys())

# 注册所有导出器
ExporterRegistry.register("txt", TextExporter)
ExporterRegistry.register("json", JSONExporter)
ExporterRegistry.register("html", HTMLExporter)
ExporterRegistry.register("word", WordExporter)
ExporterRegistry.register("excel", ExcelExporter)
ExporterRegistry.register("markdown", MarkdownExporter)
ExporterRegistry.register("pdf", PDFExporter)
```

**交付物**: 支持多种格式的导出系统，包含普通/高级两种模式

**关键文件**:
- `src/services/export/base_exporter.py`
- `src/services/export/text_exporter.py`
- `src/services/export/json_exporter.py`
- `src/services/export/html_exporter.py`
- `src/services/export/word_exporter.py`
- `src/services/export/excel_exporter.py`
- `src/services/export/markdown_exporter.py`
- `src/services/export/pdf_exporter.py`
- `src/services/export/exporter_registry.py`
- `src/tests/test_exporters.py`

**验证方式**:
- 各格式导出文件可正常打开
- 普通模式仅包含文本
- 高级模式包含位置、置信度等信息
- 双层 PDF 可搜索、可复制文字

---

### 阶段 18：云 OCR - 基础架构与百度

**目标**: 建立云 OCR 分层架构，集成百度云 OCR API

**设计要点**:
- 分层架构：`BaseEngine` → `BaseCloudEngine` → 各云引擎
- 凭证存储：Windows Credential Manager（安全存储 API Key）
- 错误处理：指数退避重试 + 可用引擎降级链
- 频率限制：队列缓冲，按各厂商 QPS 限制依次发送
- 返回格式：双层结构（统一基础字段 + `extra` 字典存厂商特有数据）

**任务清单**:
1. 实现 `services/ocr/cloud/base_cloud.py` - 云引擎基类
2. 实现 `utils/credential_manager.py` - Windows 凭证管理
3. 实现 `services/ocr/cloud/request_queue.py` - 请求队列（QPS 控制）
4. 实现 `services/ocr/cloud/baidu_ocr.py` - 百度 OCR
5. 实现 OAuth2 Token 获取和自动刷新
6. 编写云 OCR 单元测试

**核心数据结构**:

```python
# services/ocr/cloud/base_cloud.py

class CloudOCRType(Enum):
    """云 OCR 识别类型（全量支持）"""
    GENERAL = "general"              # 通用文字识别
    GENERAL_ACCURATE = "accurate"    # 高精度版
    IDCARD = "idcard"                # 身份证
    BANK_CARD = "bank_card"          # 银行卡
    BUSINESS_LICENSE = "license"     # 营业执照
    INVOICE = "invoice"              # 发票
    TRAIN_TICKET = "train_ticket"    # 火车票
    TABLE = "table"                  # 表格
    FORMULA = "formula"              # 公式
    HANDWRITING = "handwriting"      # 手写体


@dataclass
class CloudOCRResult:
    """
    云 OCR 统一返回格式（双层结构）
    
    基础字段：所有云厂商统一
    extra：厂商特有数据
    """
    text: str                            # 识别文本
    confidence: float                    # 置信度 (0.0 ~ 1.0)
    location: Optional[List[int]]        # 坐标 [x, y, width, height]
    extra: Dict[str, Any] = field(default_factory=dict)
    # extra 示例:
    # - 百度: {"words_result_num": 10, "direction": 0}
    # - 腾讯: {"ItemPolygon": {...}, "DetectedText": "..."}
    # - 阿里: {"prob": 0.99, "charInfo": [...]}


class BaseCloudEngine(BaseEngine, ABC):
    """
    云 OCR 引擎基类
    
    职责:
    - HTTP 请求封装（异步）
    - 图片 Base64 编码
    - 指数退避重试
    - 降级链管理
    - 请求队列（QPS 控制）
    """
    
    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # 指数退避：1s, 2s, 4s
    
    def __init__(self, qps_limit: int = 10):
        self._request_queue = RequestQueue(qps_limit)
        self._fallback_engines: List["BaseCloudEngine"] = []
    
    @abstractmethod
    def _get_credentials(self) -> Dict[str, str]:
        """从 Windows Credential Manager 获取凭证"""
    
    @abstractmethod
    def _build_request(self, image_data: bytes, ocr_type: CloudOCRType) -> Dict:
        """构建 HTTP 请求（各厂商不同）"""
    
    @abstractmethod
    def _parse_response(self, response: Dict) -> List[CloudOCRResult]:
        """解析响应为统一格式"""
    
    def recognize(self, image_path: str, 
                  ocr_type: CloudOCRType = CloudOCRType.GENERAL) -> OCRResult:
        """
        统一识别接口（与本地引擎一致）
        
        流程:
        1. 读取图片并 Base64 编码
        2. 通过请求队列发送（QPS 控制）
        3. 指数退避重试
        4. 失败则尝试降级引擎
        5. 解析响应为统一格式
        """
    
    def set_fallback_chain(self, engines: List["BaseCloudEngine"]) -> None:
        """设置降级链（如：百度 → 腾讯 → 本地）"""
        self._fallback_engines = engines
    
    def _encode_image(self, image_path: str) -> str:
        """图片转 Base64"""
    
    async def _send_request_with_retry(self, request: Dict) -> Dict:
        """
        带重试的请求发送
        
        失败时按 RETRY_DELAYS 指数退避
        全部失败后尝试降级链
        """
```

```python
# services/ocr/cloud/request_queue.py

class RequestQueue:
    """
    请求队列（QPS 控制）
    
    按各云厂商 QPS 限制依次发送请求
    避免触发云端限流
    """
    
    def __init__(self, qps_limit: int):
        self._qps_limit = qps_limit
        self._queue: asyncio.Queue = asyncio.Queue()
        self._last_request_times: List[float] = []
    
    async def enqueue(self, request_func: Callable) -> Any:
        """请求入队，按 QPS 限制依次执行"""
    
    def _can_send(self) -> bool:
        """检查是否可发送（滑动窗口限流）"""
```

```python
# utils/credential_manager.py

class CredentialManager:
    """
    Windows Credential Manager 封装
    
    安全存储云 API 凭证
    """
    
    TARGET_PREFIX = "UmiOCR_Cloud_"  # 凭证前缀
    
    @staticmethod
    def save(provider: str, credentials: Dict[str, str]) -> None:
        """
        保存凭证到 Windows Credential Manager
        
        provider: 'baidu' / 'tencent' / 'aliyun'
        credentials: {'api_key': '...', 'secret_key': '...'}
        """
    
    @staticmethod
    def load(provider: str) -> Optional[Dict[str, str]]:
        """从 Windows Credential Manager 加载凭证"""
    
    @staticmethod
    def delete(provider: str) -> None:
        """删除凭证"""
    
    @staticmethod
    def exists(provider: str) -> bool:
        """检查凭证是否存在"""
```

```python
# services/ocr/cloud/baidu_ocr.py

class BaiduOCREngine(BaseCloudEngine):
    """
    百度云 OCR 引擎
    
    认证方式: OAuth2 Access Token
    特点: Token 有效期 30 天，需自动刷新
    """
    
    API_BASE = "https://aip.baidubce.com"
    TOKEN_URL = "/oauth/2.0/token"
    
    # 各识别类型对应的 API 端点
    API_ENDPOINTS = {
        CloudOCRType.GENERAL: "/rest/2.0/ocr/v1/general_basic",
        CloudOCRType.GENERAL_ACCURATE: "/rest/2.0/ocr/v1/accurate_basic",
        CloudOCRType.IDCARD: "/rest/2.0/ocr/v1/idcard",
        CloudOCRType.BANK_CARD: "/rest/2.0/ocr/v1/bankcard",
        CloudOCRType.BUSINESS_LICENSE: "/rest/2.0/ocr/v1/business_license",
        CloudOCRType.INVOICE: "/rest/2.0/ocr/v1/vat_invoice",
        CloudOCRType.TRAIN_TICKET: "/rest/2.0/ocr/v1/train_ticket",
        CloudOCRType.TABLE: "/rest/2.0/ocr/v1/table",
        CloudOCRType.FORMULA: "/rest/2.0/ocr/v1/formula",
        CloudOCRType.HANDWRITING: "/rest/2.0/ocr/v1/handwriting",
    }
    
    def __init__(self):
        super().__init__(qps_limit=10)  # 百度 QPS 限制
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
    
    def _get_credentials(self) -> Dict[str, str]:
        """从 Credential Manager 获取 API Key 和 Secret Key"""
        return CredentialManager.load("baidu")
    
    def _ensure_token(self) -> str:
        """
        确保 Access Token 有效
        
        过期或即将过期时自动刷新
        """
    
    def _build_request(self, image_data: bytes, 
                       ocr_type: CloudOCRType) -> Dict:
        """
        构建百度 OCR 请求
        
        Headers: Content-Type: application/x-www-form-urlencoded
        Body: image=<base64>&access_token=<token>
        """
    
    def _parse_response(self, response: Dict) -> List[CloudOCRResult]:
        """
        解析百度响应为统一格式
        
        百度返回: {"words_result": [{"words": "...", "location": {...}}]}
        转换为: [CloudOCRResult(text="...", location=[...], extra={...})]
        """


# 注册到引擎管理器
EngineManager.register("baidu_cloud", BaiduOCREngine)
```

**交付物**: 云 OCR 基础架构 + 百度云 OCR

**关键文件**:
- `src/services/ocr/cloud/base_cloud.py` - 云引擎基类
- `src/services/ocr/cloud/request_queue.py` - 请求队列
- `src/services/ocr/cloud/baidu_ocr.py` - 百度引擎
- `src/utils/credential_manager.py` - 凭证管理
- `src/tests/test_cloud_ocr.py`

**验证方式**:
- 配置百度 API Key 后识别成功
- Token 自动刷新测试
- QPS 限流测试（连续请求不触发云端限流）

---

### 阶段 19：云 OCR - 腾讯、阿里与配置界面

**目标**: 集成腾讯云、阿里云 OCR，实现云引擎配置界面

**设计要点**:
- 腾讯云：签名 V3 算法（TC3-HMAC-SHA256）
- 阿里云：AccessKey 签名
- 配置方式：设置页集中管理 + 首次使用即时引导

**任务清单**:
1. 实现 `services/ocr/cloud/tencent_ocr.py` - 腾讯 OCR
2. 实现腾讯云签名 V3 算法
3. 实现 `services/ocr/cloud/aliyun_ocr.py` - 阿里 OCR
4. 实现阿里云 API 签名
5. 实现 `ui/dialogs/cloud_config_dialog.py` - 云配置弹窗
6. 更新引擎管理器，注册云引擎
7. 补充云 OCR 单元测试

**核心数据结构**:

```python
# services/ocr/cloud/tencent_ocr.py

class TencentOCREngine(BaseCloudEngine):
    """
    腾讯云 OCR 引擎
    
    认证方式: 签名 V3 (TC3-HMAC-SHA256)
    特点: 每次请求都需要计算签名，无需 Token 刷新
    """
    
    API_HOST = "ocr.tencentcloudapi.com"
    SERVICE = "ocr"
    REGION = "ap-guangzhou"
    
    # 各识别类型对应的 Action
    ACTIONS = {
        CloudOCRType.GENERAL: "GeneralBasicOCR",
        CloudOCRType.GENERAL_ACCURATE: "GeneralAccurateOCR",
        CloudOCRType.IDCARD: "IDCardOCR",
        CloudOCRType.BANK_CARD: "BankCardOCR",
        CloudOCRType.BUSINESS_LICENSE: "BizLicenseOCR",
        CloudOCRType.INVOICE: "VatInvoiceOCR",
        CloudOCRType.TRAIN_TICKET: "TrainTicketOCR",
        CloudOCRType.TABLE: "RecognizeTableOCR",
        CloudOCRType.FORMULA: "FormulaOCR",
        CloudOCRType.HANDWRITING: "GeneralHandwritingOCR",
    }
    
    def __init__(self):
        super().__init__(qps_limit=10)  # 腾讯 QPS 限制
    
    def _get_credentials(self) -> Dict[str, str]:
        """获取 SecretId 和 SecretKey"""
        return CredentialManager.load("tencent")
    
    def _sign_v3(self, method: str, payload: str, 
                 timestamp: int, action: str) -> Dict[str, str]:
        """
        腾讯云签名 V3 算法
        
        步骤:
        1. 拼接规范请求串 CanonicalRequest
        2. 拼接待签名字符串 StringToSign
        3. 计算签名 Signature
        4. 拼接 Authorization
        """
    
    def _build_request(self, image_data: bytes, 
                       ocr_type: CloudOCRType) -> Dict:
        """
        构建腾讯云请求
        
        Headers: 
          - Authorization: TC3-HMAC-SHA256 ...
          - X-TC-Action: GeneralBasicOCR
          - X-TC-Timestamp: ...
          - X-TC-Version: 2018-11-19
        Body: {"ImageBase64": "..."}
        """
    
    def _parse_response(self, response: Dict) -> List[CloudOCRResult]:
        """
        解析腾讯响应
        
        腾讯返回: {"Response": {"TextDetections": [{"DetectedText": "..."}]}}
        """


# 注册到引擎管理器
EngineManager.register("tencent_cloud", TencentOCREngine)
```

```python
# services/ocr/cloud/aliyun_ocr.py

class AliyunOCREngine(BaseCloudEngine):
    """
    阿里云 OCR 引擎
    
    认证方式: AccessKey 签名
    特点: 每次请求计算签名
    """
    
    API_HOST = "ocr-api.cn-hangzhou.aliyuncs.com"
    API_VERSION = "2021-07-07"
    
    # 各识别类型对应的 Action
    ACTIONS = {
        CloudOCRType.GENERAL: "RecognizeGeneral",
        CloudOCRType.GENERAL_ACCURATE: "RecognizeAdvanced",
        CloudOCRType.IDCARD: "RecognizeIdcard",
        CloudOCRType.BANK_CARD: "RecognizeBankCard",
        CloudOCRType.BUSINESS_LICENSE: "RecognizeBusinessLicense",
        CloudOCRType.INVOICE: "RecognizeInvoice",
        CloudOCRType.TRAIN_TICKET: "RecognizeTrainTicket",
        CloudOCRType.TABLE: "RecognizeTable",
        CloudOCRType.FORMULA: "RecognizeFormula",
        CloudOCRType.HANDWRITING: "RecognizeHandwriting",
    }
    
    def __init__(self):
        super().__init__(qps_limit=10)  # 阿里 QPS 限制
    
    def _get_credentials(self) -> Dict[str, str]:
        """获取 AccessKeyId 和 AccessKeySecret"""
        return CredentialManager.load("aliyun")
    
    def _sign_request(self, params: Dict, method: str) -> str:
        """
        阿里云签名算法
        
        步骤:
        1. 参数排序
        2. 构造待签名字符串
        3. HMAC-SHA1 计算签名
        4. Base64 编码
        """
    
    def _build_request(self, image_data: bytes, 
                       ocr_type: CloudOCRType) -> Dict:
        """构建阿里云请求"""
    
    def _parse_response(self, response: Dict) -> List[CloudOCRResult]:
        """解析阿里响应"""


# 注册到引擎管理器
EngineManager.register("aliyun_cloud", AliyunOCREngine)
```

```python
# ui/widgets/engine_selector.py

class EngineSelector(QWidget):
    """
    引擎选择器控件
    
    嵌入到 OCR 功能界面，支持实时切换引擎
    """
    
    engine_changed = Signal(str)  # 引擎切换信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_available_engines()
    
    def _setup_ui(self) -> None:
        """
        UI 布局:
        ┌──────────────────────────────────┐
        │  识别引擎: [▼ PaddleOCR (本地)]   │
        └──────────────────────────────────┘
        
        下拉选项:
        - PaddleOCR (本地)
        - 百度云 OCR      [未配置] → 灰色不可选
        - 腾讯云 OCR      [已配置] → 可选
        - 阿里云 OCR      [未配置] → 灰色不可选
        """
    
    def _load_available_engines(self) -> None:
        """
        加载可用引擎列表
        
        未配置的云引擎显示为灰色不可选
        """
        engines = EngineManager.get_all_engines()
        for engine_id, engine in engines.items():
            is_configured = self._check_engine_configured(engine_id)
            self._combo.addItem(
                engine.display_name,
                userData=engine_id,
                enabled=is_configured
            )
    
    def _check_engine_configured(self, engine_id: str) -> bool:
        """检查引擎是否已配置（云引擎检查 API Key）"""
    
    def _on_engine_changed(self, index: int) -> None:
        """引擎切换时触发"""
        engine_id = self._combo.itemData(index)
        self.engine_changed.emit(engine_id)
    
    def get_current_engine_id(self) -> str:
        """获取当前选中的引擎 ID"""
    
    def refresh(self) -> None:
        """刷新引擎列表（配置更新后调用）"""
```

```python
# services/ocr/engine_manager.py 更新

class EngineManager:
    """引擎管理器（支持本地 + 云引擎）"""
    
    # 降级链配置
    DEFAULT_FALLBACK_CHAIN = [
        "baidu_cloud",
        "tencent_cloud", 
        "aliyun_cloud",
        "paddle_local"  # 最终降级到本地
    ]
    
    def get_engine(self, engine_id: str) -> BaseEngine:
        """
        获取引擎实例
        
        云引擎检查配置，未配置则抛异常
        """
        engine = self._engines.get(engine_id)
        
        # 云引擎检查配置
        if isinstance(engine, BaseCloudEngine):
            provider = engine_id.replace("_cloud", "")
            if not CredentialManager.exists(provider):
                raise EngineNotConfiguredError(engine_id)
        
        return engine
    
    @classmethod
    def get_all_engines(cls) -> Dict[str, BaseEngine]:
        """获取所有已注册的引擎"""
    
    @classmethod
    def is_engine_configured(cls, engine_id: str) -> bool:
        """检查引擎是否已配置（用于 UI 显示）"""
    
    def setup_fallback_chain(self, primary_engine: str) -> None:
        """
        设置降级链
        
        仅包含已配置的引擎
        从 primary_engine 开始，按 DEFAULT_FALLBACK_CHAIN 顺序降级
        """
```

**接口边界图**:
```
┌─────────────────────────────────────────────────────────────────┐
│                      配置与切换流程                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  设置页 (集中配置)                                        │  │
│  │    └─ 云服务配置                                          │  │
│  │        ├─ 百度云: [API Key] [Secret Key] [测试]         │  │
│  │        ├─ 腾讯云: [SecretId] [SecretKey] [测试]        │  │
│  │        └─ 阿里云: [AccessKeyId] [Secret] [测试]        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│                          ▼ 保存到 Credential Manager             │
│                          │                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  OCR 功能界面 (实时切换)                                   │  │
│  │    └─ EngineSelector 控件                                 │  │
│  │        ┌───────────────────────────────────────────┐   │  │
│  │        │  识别引擎: [▼ PaddleOCR (本地)         ]  │   │  │
│  │        │             ├─ PaddleOCR (本地)           │   │  │
│  │        │             ├─ 百度云 ✔                  │   │  │
│  │        │             ├─ 腾讯云 ✔                  │   │  │
│  │        │             └─ 阿里云 (未配置) 灰色       │   │  │
│  │        └───────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  BaseEngine (统一接口: recognize)                               │
│      │                                                          │
│      ├── PaddleEngine (本地)                                    │
│      │                                                          │
│      └── BaseCloudEngine (云基类)                               │
│              ├── BaiduOCREngine                                 │
│              ├── TencentOCREngine                               │
│              └── AliyunOCREngine                                │
├─────────────────────────────────────────────────────────────────┤
│  CredentialManager ←→ Windows Credential Manager                │
└─────────────────────────────────────────────────────────────────┘
```

**交付物**: 完整的云 OCR 支持（百度/腾讯/阿里）+ 引擎选择器

**关键文件**:
- `src/services/ocr/cloud/tencent_ocr.py`
- `src/services/ocr/cloud/aliyun_ocr.py`
- `src/ui/widgets/engine_selector.py` - 引擎选择器控件
- `src/services/ocr/engine_manager.py`（更新）

**验证方式**:
- 各云平台识别成功
- 设置页配置后刷新引擎列表，云引擎变为可选
- 实时切换引擎后立即生效
- 降级链测试（模拟百度失败后自动切换腾讯）
- 签名算法正确性测试

---

### 阶段 20：设置界面

**目标**: 实现应用设置功能（侧边栏导航 + 搜索框）

**设计要点**:
- 布局：左侧分类列表 + 右侧设置内容
- 搜索：顶部搜索框，快速定位设置项
- 云服务配置：集中管理所有云 API Key
- 即时生效：部分设置无需重启

**任务清单**:
1. 创建 `ui/settings/settings.ui` - 设置界面
2. 实现 `ui/settings/settings.py` - 界面类
3. 实现 `ui/settings/settings_search.py` - 设置搜索功能
4. 实现 `controllers/settings_controller.py` - 控制器
5. 实现云 API Key 集中配置
6. 实现其他通用设置

**核心数据结构**:

```python
# ui/settings/settings.py

class SettingsCategory(Enum):
    """设置分类"""
    GENERAL = "general"           # 常规
    OCR_ENGINE = "ocr_engine"     # OCR 引擎
    CLOUD_SERVICE = "cloud"       # 云服务
    HOTKEY = "hotkey"             # 快捷键
    APPEARANCE = "appearance"     # 外观
    ADVANCED = "advanced"         # 高级


class SettingsWindow(QWidget):
    """
    设置界面
    
    布局: 侧边栏导航 + 搜索框
    ┌───────────────────────────────────────────────────────┐
    │  [🔍 搜索设置...                              ]  │
    ├─────────────┬─────────────────────────────────────────┤
    │  常规       │  语言: [▼ 简体中文]                  │
    │  OCR 引擎  │  主题: [▼ 深色]                      │
    │  云服务    │  开机自启: [☐]                       │
    │  快捷键    │  最小化到托盘: [☑]                  │
    │  外观       │  ...                                 │
    │  高级       │                                      │
    └─────────────┴─────────────────────────────────────────┘
    """
    
    settings_changed = Signal(str, object)  # (key, value)
    
    def _setup_search(self) -> None:
        """初始化设置搜索"""


class SettingsSearch:
    """设置搜索功能，支持模糊匹配设置项名称和关键词"""
    
    def search(self, query: str) -> List[SettingItem]: ...
    def highlight_item(self, item: SettingItem) -> None: ...


class CloudSettingsPanel(QWidget):
    """
    云服务设置面板（集中配置所有云 API Key）
    
    ┌────────────────────────────────────────────────────┐
    │  ▼ 百度云 OCR                                    │
    │    API Key:    [********************] [显示]  │
    │    Secret Key: [********************] [显示]  │
    │    [测试连接]  [获取 Key 指引]                  │
    ├────────────────────────────────────────────────────┤
    │  ▼ 腾讯云 OCR / ▼ 阿里云 OCR ...               │
    └────────────────────────────────────────────────────┘
    """
```

**交付物**: 带搜索功能的设置界面 + 云服务集中配置

**关键文件**:
- `src/ui/settings/settings.py`
- `src/ui/settings/settings_search.py`
- `src/ui/settings/cloud_settings.py`
- `src/controllers/settings_controller.py`

**验证方式**:
- 设置保存后即时生效（部分需重启）
- 搜索框输入关键词后快速定位
- 云 API Key 配置后刷新引擎列表

---

### 阶段 21：系统托盘

**目标**: 实现系统托盘功能（快捷操作版）

**设计要点**:
- 右键菜单：显示/隐藏、截图 OCR、剪贴板 OCR、暂停所有任务、退出
- 双击：显示主窗口
- 气泡通知：任务完成时提示

**任务清单**:
1. 实现 `utils/tray_manager.py` - 系统托盘管理
2. 实现托盘图标和右键菜单
3. 实现最小化到托盘
4. 实现托盘气泡通知
5. 实现双击托盘显示主窗口
6. 集成任务系统信号

**核心数据结构**:

```python
# utils/tray_manager.py

class TrayManager(QObject):
    """
    系统托盘管理器（快捷操作版）
    
    右键菜单:
    ┌──────────────────┐
    │  显示主窗口       │
    ├──────────────────┤
    │  📷 截图 OCR      │
    │  📋 剪贴板 OCR   │
    ├──────────────────┤
    │  ⏸ 暂停所有任务  │
    ├──────────────────┤
    │  退出             │
    └──────────────────┘
    """
    
    show_window_requested = Signal()
    screenshot_requested = Signal()
    clipboard_ocr_requested = Signal()
    pause_all_requested = Signal()
    quit_requested = Signal()
    
    def show_notification(self, title: str, message: str, 
                          duration_ms: int = 3000) -> None:
        """显示气泡通知"""
    
    def update_pause_state(self, is_paused: bool) -> None:
        """更新暂停菜单项状态"""
```

**交付物**: 快捷操作版系统托盘

**关键文件**:
- `src/utils/tray_manager.py`

**验证方式**:
- 托盘图标显示正常
- 右键菜单各功能正常
- 任务完成时气泡通知
- 双击显示主窗口

---

### 阶段 22：全局快捷键

**目标**: 实现全局热键功能（Windows API）

**设计要点**:
- 使用 `RegisterHotKey` Windows API（无需管理员权限）
- 支持自定义快捷键
- 快捷键冲突检测
- 与设置界面集成

**任务清单**:
1. 实现 `platform/win32/hotkey_manager.py` - 全局快捷键管理
2. 实现 Windows API 封装
3. 实现快捷键冲突检测
4. 实现自定义快捷键配置
5. 集成到设置界面

**核心数据结构**:

```python
# platform/win32/hotkey_manager.py

import ctypes
user32 = ctypes.windll.user32

class Modifiers:
    ALT = 0x0001
    CTRL = 0x0002
    SHIFT = 0x0004
    WIN = 0x0008

@dataclass
class HotkeyConfig:
    id: int              # 快捷键 ID
    modifiers: int       # 修饰符
    key_code: int        # 虚拟键码
    action: str          # 动作名称
    description: str     # 显示名称

class HotkeyManager(QObject):
    """全局快捷键管理器（使用 RegisterHotKey API）"""
    
    hotkey_triggered = Signal(str)  # action name
    
    DEFAULT_HOTKEYS = [
        HotkeyConfig(1, Modifiers.ALT, ord('Q'), "screenshot_ocr", "截图 OCR"),
        HotkeyConfig(2, Modifiers.ALT, ord('W'), "clipboard_ocr", "剪贴板 OCR"),
        HotkeyConfig(3, Modifiers.ALT, ord('E'), "show_window", "显示主窗口"),
    ]
    
    def register_all(self) -> List[str]: """注册所有快捷键，返回失败列表"""
    def unregister_all(self) -> None: """注销所有快捷键"""
    def check_conflict(self, modifiers: int, key_code: int) -> Optional[str]: """检查冲突"""
```

**交付物**: 可自定义的全局快捷键

**关键文件**:
- `src/platform/win32/hotkey_manager.py`
- `src/ui/settings/hotkey_settings.py`

**验证方式**:
- 按快捷键触发截图等功能
- 自定义快捷键后生效
- 冲突检测提示正常

---

### 阶段 23：开机自启

**目标**: 实现开机自启功能（注册表 Run 键）

**设计要点**:
- 使用注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- 无需管理员权限
- 用户可在任务管理器查看

**任务清单**:
1. 实现 `utils/startup_manager.py` - 开机自启管理
2. 实现注册表操作
3. 集成到设置界面

**核心数据结构**:

```python
# utils/startup_manager.py

import winreg
import sys

class StartupManager:
    """开机自启管理器（注册表 Run 键）"""
    
    REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "UmiOCR"
    
    @classmethod
    def is_enabled(cls) -> bool: """检查是否已启用"""
    
    @classmethod
    def enable(cls) -> bool:
        """启用开机自启"""
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REGISTRY_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, sys.executable)
        winreg.CloseKey(key)
    
    @classmethod
    def disable(cls) -> bool: """禁用开机自启"""
```

**交付物**: 开机自启功能

**关键文件**:
- `src/utils/startup_manager.py`

**验证方式**:
- 启用后重启电脑自动运行
- 任务管理器启动项显示正常

---

### 阶段 24：悬浮工具栏

**目标**: 实现屏幕边缘悬浮工具栏（边缘触发 / 常驻显示，用户可选）

**设计要点**:
- 两种模式：边缘触发滑出 / 常驻显示
- 支持拖拽移动和位置记忆
- 窗口置顶 + 透明度

**任务清单**:
1. 创建 `ui/floating_bar/floating_bar.ui`
2. 实现 `ui/floating_bar/floating_bar.py`
3. 实现边缘触发显示/隐藏
4. 实现常驻显示模式
5. 实现工具栏按钮
6. 实现拖拽移动和位置记忆

**核心数据结构**:

```python
# ui/floating_bar/floating_bar.py

class FloatingBarMode(Enum):
    EDGE_TRIGGER = "edge"      # 边缘触发
    ALWAYS_VISIBLE = "always"  # 常驻显示

class FloatingBar(QWidget):
    """
    悬浮工具栏（支持两种模式）
    
    布局 (竖向):
    ┌───────┐
    │  📷   │  截图 OCR
    │  📋   │  剪贴板 OCR
    │  📂   │  批量 OCR
    │  ⚙️   │  设置
    └───────┘
    """
    
    screenshot_clicked = Signal()
    clipboard_ocr_clicked = Signal()
    batch_ocr_clicked = Signal()
    settings_clicked = Signal()
    
    EDGE_MARGIN = 5           # 边缘检测距离
    ANIMATION_DURATION = 200  # 动画时长(ms)
    
    def set_mode(self, mode: FloatingBarMode) -> None: """设置模式"""
    def _check_mouse_at_edge(self) -> None: """检查鼠标是否在边缘"""
    def _slide_in(self) -> None: """滑入动画"""
    def _slide_out(self) -> None: """滑出动画"""
    def _save_position(self) -> None: """保存位置"""
```

**交付物**: 可配置的悬浮工具栏

**关键文件**:
- `src/ui/floating_bar/floating_bar.py`

**验证方式**:
- 边缘触发模式：鼠标移到边缘时滑出
- 常驻模式：始终显示
- 拖拽移动后位置记忆

---

### 阶段 25：任务管理器界面

**目标**: 实现任务管理可视化界面（树形结构 + 卡片视图）

**设计要点**:
- 展示方式：树形结构（展开查看子任务）+ 卡片视图（每个 TaskGroup 一张卡片）
- 实时进度更新
- 支持暂停/恢复/取消/重试操作

**任务清单**:
1. 创建 `ui/task_manager/task_manager.ui`
2. 实现 `ui/task_manager/task_manager.py`
3. 实现树形任务列表
4. 实现任务卡片组件
5. 实现任务操作按钮
6. 实现优先级调整

**核心数据结构**:

```python
# ui/task_manager/task_manager.py

class TaskManagerView(QWidget):
    """
    任务管理器界面
    
    布局:
    ┌─────────────────────────────────────────────────────────┐
    │  任务管理器                  [暂停全部] [清空已完成]  │
    ├─────────────────────────────────────────────────────────┤
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │  📚 批量图片 OCR (12/50)              ▶ ⏸ ✖    │  │
    │  │  ██████████████████░░░░░░░░░░░░  24%        │  │
    │  │  ▼ 展开子任务                                      │  │
    │  │    ├─ img_001.png  ✔ 完成                       │  │
    │  │    ├─ img_002.png  ✔ 完成                       │  │
    │  │    ├─ img_003.png  ▶ 进行中...                   │  │
    │  │    └─ img_004.png  ⏳ 等待中                       │  │
    │  └─────────────────────────────────────────────────────┘  │
    │                                                         │
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │  📄 PDF 文档 OCR (3/10)                ▶ ⏸ ✖    │  │
    │  │  █████████░░░░░░░░░░░░░░░░░░░░░  30%        │  │
    │  └─────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────┘
    """
    
    def __init__(self, task_manager: TaskManager, parent=None): ...
    def _on_task_progress(self, group_id: str, progress: float) -> None: ...
    def _on_task_status_changed(self, group_id: str, status: TaskStatus) -> None: ...


class TaskGroupCard(QFrame):
    """
    任务组卡片
    
    显示: 标题、进度条、状态、操作按钮
    可展开: 显示子任务列表
    """
    
    pause_clicked = Signal(str)   # group_id
    resume_clicked = Signal(str)
    cancel_clicked = Signal(str)
    retry_clicked = Signal(str)
    
    def set_group(self, group: TaskGroup) -> None: ...
    def update_progress(self, progress: float) -> None: ...
    def set_expanded(self, expanded: bool) -> None: ...
```

**交付物**: 树形 + 卡片的任务管理器界面

**关键文件**:
- `src/ui/task_manager/task_manager.py`
- `src/ui/task_manager/task_card.py`

**验证方式**:
- 任务列表实时更新
- 展开/收起子任务正常
- 操作按钮有效

---

### 阶段 26：HTTP API 服务

**目标**: 实现 HTTP 接口服务（aiohttp，支持无头模式）

**设计要点**:
- 框架：aiohttp（纯异步，与 Qt 事件循环兼容）
- 运行模式：GUI 模式（qasync 集成）/ 无头模式（纯 asyncio）
- 与 CLI 共享 Service 层

**任务清单**:
1. 实现 `services/server/http_server.py` - HTTP 服务器
2. 实现 `services/server/routes.py` - 路由定义
3. 实现 OCR 识别接口
4. 实现任务提交和查询接口
5. 实现鉴权机制（可选）
6. 编写 HTTP API 测试

**核心数据结构**:

```python
# services/server/http_server.py

from aiohttp import web

class HTTPServer:
    """
    HTTP API 服务器 (aiohttp)
    
    支持两种运行模式:
    - GUI 模式: 通过 qasync 集成到 Qt 事件循环
    - 无头模式: 使用标准 asyncio 事件循环
    """
    
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 1224
    
    def __init__(self, ocr_service: OCRService):
        self._ocr_service = ocr_service
        self._app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """
        API 路由:
        POST /api/ocr         - 单张图片 OCR
        POST /api/ocr/batch   - 批量 OCR (提交任务)
        GET  /api/task/{id}   - 查询任务状态
        POST /api/qrcode/scan - 二维码识别
        POST /api/qrcode/gen  - 二维码生成
        GET  /api/health      - 健康检查
        """
        self._app.router.add_post("/api/ocr", self._handle_ocr)
        self._app.router.add_post("/api/ocr/batch", self._handle_batch_ocr)
        self._app.router.add_get("/api/task/{task_id}", self._handle_task_status)
        self._app.router.add_post("/api/qrcode/scan", self._handle_qrcode_scan)
        self._app.router.add_post("/api/qrcode/gen", self._handle_qrcode_gen)
        self._app.router.add_get("/api/health", self._handle_health)
    
    async def _handle_ocr(self, request: web.Request) -> web.Response:
        """
        单张图片 OCR
        
        请求: {"image": "base64...", "engine": "paddle_local"}
        响应: {"text": "...", "boxes": [...], "confidence": 0.95}
        """
    
    async def _handle_batch_ocr(self, request: web.Request) -> web.Response:
        """批量 OCR，返回 task_id"""
    
    def run_headless(self) -> None:
        """无头模式启动（纯 HTTP 服务）"""
        web.run_app(self._app, host=self.DEFAULT_HOST, port=self.DEFAULT_PORT)
    
    async def start_with_qt(self) -> None:
        """GUI 模式启动（集成到 Qt 事件循环）"""
```

**交付物**: 可用的 HTTP API（支持 GUI/无头模式）

**关键文件**:
- `src/services/server/http_server.py`
- `src/services/server/routes.py`

**验证方式**:
- curl/Postman 调用接口成功
- 无头模式 (`--headless`) 正常运行
- GUI 模式下 HTTP 服务不卡 UI

---

### 阶段 27：CLI 接口

**目标**: 实现命令行调用功能（argparse + 直调 Service 层）

**设计要点**:
- 使用 argparse（零依赖）
- 直接调用 Service 层，不走 HTTP
- 与 HTTP API 共享业务逻辑

**任务清单**:
1. 实现 `cli.py` - CLI 入口
2. 实现命令行参数解析
3. 支持单图识别命令
4. 支持批量识别命令
5. 支持输出格式选择

**核心数据结构**:

```python
# cli.py

import argparse
import sys
from services.ocr import OCRService
from services.qrcode import QRCodeService

def main():
    parser = argparse.ArgumentParser(
        prog="umi-ocr",
        description="Umi-OCR 命令行工具"
    )
    
    subparsers = parser.add_subparsers(dest="command")
    
    # ocr 子命令
    ocr_parser = subparsers.add_parser("ocr", help="OCR 识别")
    ocr_parser.add_argument("--image", "-i", help="单张图片路径")
    ocr_parser.add_argument("--dir", "-d", help="批量识别目录")
    ocr_parser.add_argument("--output", "-o", default="stdout", 
                            choices=["stdout", "json", "txt"], help="输出格式")
    ocr_parser.add_argument("--engine", "-e", default="paddle_local", 
                            help="OCR 引擎")
    
    # qrcode 子命令
    qr_parser = subparsers.add_parser("qrcode", help="二维码")
    qr_parser.add_argument("--scan", "-s", help="识别二维码图片")
    qr_parser.add_argument("--gen", "-g", help="生成二维码内容")
    
    # server 子命令
    server_parser = subparsers.add_parser("server", help="启动 HTTP 服务")
    server_parser.add_argument("--port", "-p", type=int, default=1224)
    server_parser.add_argument("--host", default="127.0.0.1")
    
    args = parser.parse_args()
    
    if args.command == "ocr":
        service = OCRService()
        if args.image:
            result = service.recognize(args.image, engine=args.engine)
            output_result(result, args.output)
        elif args.dir:
            results = service.batch_recognize(args.dir, engine=args.engine)
            output_results(results, args.output)
    # ...


def output_result(result, format: str):
    """按格式输出结果"""
    if format == "json":
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.text)


if __name__ == "__main__":
    main()
```

**使用示例**:
```bash
# 单张图片 OCR
umi-ocr ocr --image test.png

# 批量识别，输出 JSON
umi-ocr ocr --dir ./images --output json

# 二维码识别
umi-ocr qrcode --scan qr.png

# 启动 HTTP 服务（无头模式）
umi-ocr server --port 1224
```

**交付物**: 可用的命令行接口

**关键文件**:
- `src/cli.py`

**验证方式**:
- 命令行调用识别成功
- 各输出格式正确

---

### 阶段 28：通用控件

**目标**: 实现可复用的自定义控件

**控件列表**:
- `ImageViewer` - 图像查看器（缩放/平移/标注框）
- `ResultPanel` - 结果展示面板（文本/表格/JSON 切换）
- `ProgressCard` - 进度卡片（带进度条和状态图标）
- `FileDropZone` - 文件拖放区域
- `HotkeyInput` - 快捷键输入框

**任务清单**:
1. 实现 `ui/widgets/image_viewer.py`
2. 实现 `ui/widgets/result_panel.py`
3. 实现 `ui/widgets/progress_card.py`
4. 实现 `ui/widgets/file_drop_zone.py`
5. 实现 `ui/widgets/hotkey_input.py`
6. 统一控件样式

**核心数据结构**:

```python
# ui/widgets/image_viewer.py

class ImageViewer(QWidget):
    """
    图像查看器
    
    功能: 缩放、平移、显示 OCR 标注框
    复用: 截图 OCR、批量 OCR、二维码
    """
    
    def set_image(self, image: QImage) -> None: ...
    def set_boxes(self, boxes: List[Rect]) -> None: """显示 OCR 框"""
    def zoom_in(self) -> None: ...
    def zoom_out(self) -> None: ...
    def fit_to_window(self) -> None: ...


# ui/widgets/result_panel.py

class ResultPanel(QWidget):
    """
    结果展示面板
    
    支持三种视图切换: 文本 / 表格 / JSON
    复用: 所有 OCR 结果展示
    """
    
    class ViewMode(Enum):
        TEXT = "text"
        TABLE = "table"
        JSON = "json"
    
    def set_result(self, result: OCRResult) -> None: ...
    def set_view_mode(self, mode: ViewMode) -> None: ...
    def copy_to_clipboard(self) -> None: ...


# ui/widgets/progress_card.py

class ProgressCard(QFrame):
    """
    进度卡片
    
    显示: 标题、进度条、状态图标、操作按钮
    复用: 任务管理器
    """
    
    def set_title(self, title: str) -> None: ...
    def set_progress(self, progress: float) -> None: ...
    def set_status(self, status: TaskStatus) -> None: ...


# ui/widgets/file_drop_zone.py

class FileDropZone(QWidget):
    """
    文件拖放区域
    
    支持: 拖放文件/文件夹、点击选择、Ctrl+V 粘贴
    复用: 批量图片/文档 OCR
    """
    
    files_dropped = Signal(list)  # List[str]
    
    def __init__(self, accept_extensions: List[str], parent=None): ...


# ui/widgets/hotkey_input.py

class HotkeyInput(QLineEdit):
    """
    快捷键输入框
    
    捕获用户按下的组合键
    复用: 设置界面快捷键配置
    """
    
    hotkey_changed = Signal(int, int)  # (modifiers, key_code)
    
    def start_capture(self) -> None: """开始捕获"""
    def get_hotkey(self) -> Tuple[int, int]: """获取当前快捷键"""
```

**控件复用图**:
```
ImageViewer ─┬─ 截图 OCR 预览
             ├─ 批量 OCR 查看原图
             └─ 二维码 图片显示

ResultPanel ─── 所有 OCR 结果展示

ProgressCard ── 任务管理器

FileDropZone ── 批量图片/文档 OCR 文件输入

HotkeyInput ─── 设置界面快捷键配置
```

**交付物**: 可复用的通用控件库

**关键文件**:
- `src/ui/widgets/image_viewer.py`
- `src/ui/widgets/result_panel.py`
- `src/ui/widgets/progress_card.py`
- `src/ui/widgets/file_drop_zone.py`
- `src/ui/widgets/hotkey_input.py`

**验证方式**:
- 各界面使用控件正常

---

### 阶段 29：集成测试与优化

**目标**: 进行系统集成测试和性能优化

**设计要点**:
- 集成测试覆盖：五大核心流程
- 性能优化：内存/响应/并发/启动/资源释放

**任务清单**:
1. 编写端到端集成测试
2. 进行内存泄漏检测
3. 优化 OCR 引擎内存占用
4. 优化任务并发性能
5. 优化 UI 响应速度
6. 优化启动速度
7. 修复发现的 Bug

**核心数据结构**:

```python
# tests/test_integration.py

import pytest
from unittest.mock import patch

class TestIntegration:
    """集成测试套件"""
    
    # ========== A. 截图 OCR 端到端 ==========
    
    def test_screenshot_ocr_e2e(self, qtbot):
        """
        截图 OCR 完整流程:
        模拟截图 → OCR 识别 → 结果展示 → 复制到剪贴板
        """
        # 1. 模拟截图
        mock_screenshot = create_test_image_with_text("测试文本")
        
        # 2. 触发 OCR
        result = ocr_service.recognize(mock_screenshot)
        
        # 3. 验证结果
        assert "测试文本" in result.text
        assert result.confidence > 0.8
    
    # ========== B. 批量任务流程 ==========
    
    def test_batch_task_flow(self, qtbot, tmp_path):
        """
        批量任务完整流程:
        添加文件 → 创建 TaskGroup → 入队 → 并发执行 → 导出
        """
        # 1. 准备测试文件
        test_files = create_test_images(tmp_path, count=10)
        
        # 2. 创建批量任务
        group = task_manager.create_batch_task(test_files)
        
        # 3. 等待完成
        qtbot.waitUntil(lambda: group.status == TaskStatus.COMPLETE, timeout=30000)
        
        # 4. 验证结果
        assert len(group.results) == 10
        assert all(r.status == TaskStatus.COMPLETE for r in group.results)
    
    # ========== C. 任务中断恢复 ==========
    
    def test_task_interrupt_resume(self, qtbot, tmp_path):
        """
        任务中断恢复:
        启动任务 → 暂停 → 序列化状态 → 模拟重启 → 恢复执行
        """
        # 1. 创建并启动任务
        test_files = create_test_images(tmp_path, count=20)
        group = task_manager.create_batch_task(test_files)
        
        # 2. 等待部分完成后暂停
        qtbot.waitUntil(lambda: group.progress > 0.3, timeout=10000)
        task_manager.pause_group(group.id)
        
        # 3. 序列化状态
        saved_state = task_manager.serialize_state()
        
        # 4. 模拟重启（新建 TaskManager）
        new_task_manager = TaskManager()
        new_task_manager.restore_state(saved_state)
        
        # 5. 恢复执行
        new_task_manager.resume_group(group.id)
        qtbot.waitUntil(lambda: new_task_manager.get_group(group.id).status == TaskStatus.COMPLETE)
        
        # 6. 验证完整性
        assert new_task_manager.get_group(group.id).progress == 1.0
    
    # ========== D. 云引擎降级 ==========
    
    def test_cloud_engine_fallback(self, qtbot):
        """
        云引擎降级:
        云 API 失败 → 自动切换本地引擎
        """
        # 1. 设置降级链
        cloud_engine = BaiduOCREngine()
        local_engine = PaddleLocalEngine()
        cloud_engine.set_fallback_chain([local_engine])
        
        # 2. 模拟云 API 失败
        with patch.object(cloud_engine, '_call_api', side_effect=APIError("Rate limit")):
            result = cloud_engine.recognize(test_image)
        
        # 3. 验证降级成功
        assert result.engine == "paddle_local"
        assert result.text is not None
    
    # ========== E. HTTP/CLI 接口 ==========
    
    def test_http_api_ocr(self, aiohttp_client):
        """
        HTTP API 完整流程:
        发送图片 → 返回 OCR 结果
        """
        app = create_app()
        client = await aiohttp_client(app)
        
        # 发送 OCR 请求
        with open("test.png", "rb") as f:
            resp = await client.post("/api/ocr", data={"image": f})
        
        assert resp.status == 200
        data = await resp.json()
        assert "text" in data
    
    def test_cli_single_image(self, tmp_path):
        """
        CLI 单图识别:
        命令行调用 → 返回结果
        """
        test_image = create_test_image(tmp_path / "test.png")
        
        result = subprocess.run(
            ["python", "cli.py", "ocr", "--image", str(test_image)],
            capture_output=True, text=True
        )
        
        assert result.returncode == 0
        assert len(result.stdout) > 0


# ========== 性能测试 ==========

class TestPerformance:
    """性能测试套件"""
    
    # A. 内存占用
    def test_memory_stability(self):
        """批量任务内存应稳定不增长"""
        import tracemalloc
        tracemalloc.start()
        
        # 执行 100 张图片 OCR
        for _ in range(100):
            ocr_service.recognize(test_image)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # 内存增长不超过 50MB
        assert (peak - current) < 50 * 1024 * 1024
    
    # B. 响应速度
    def test_single_ocr_response_time(self):
        """单张 OCR < 2s"""
        import time
        start = time.time()
        ocr_service.recognize(test_image)
        elapsed = time.time() - start
        
        assert elapsed < 2.0
    
    # C. 并发能力
    def test_concurrent_http_requests(self, aiohttp_client):
        """并发 10 个 HTTP 请求"""
        import asyncio
        
        async def send_request():
            resp = await client.post("/api/ocr", data={"image": test_image_b64})
            return resp.status == 200
        
        results = await asyncio.gather(*[send_request() for _ in range(10)])
        assert all(results)
    
    # D. 启动速度
    def test_cold_start_time(self):
        """冷启动 < 5s"""
        import time
        start = time.time()
        
        # 初始化应用
        app = Application()
        app.init()
        
        elapsed = time.time() - start
        assert elapsed < 5.0
    
    # E. 资源释放
    def test_engine_unload(self):
        """引擎卸载后内存释放"""
        import gc
        import tracemalloc
        
        tracemalloc.start()
        
        # 加载引擎
        engine = PaddleLocalEngine()
        engine.load()
        _, peak_loaded = tracemalloc.get_traced_memory()
        
        # 卸载引擎
        engine.unload()
        del engine
        gc.collect()
        
        current, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # 内存应显著下降
        assert current < peak_loaded * 0.5
```

**性能指标清单**:

| 指标 | 目标值 | 测试方法 |
|------|--------|----------|
| 单张 OCR 响应 | < 2s | `test_single_ocr_response_time` |
| 批量内存增长 | < 50MB | `test_memory_stability` |
| 冷启动时间 | < 5s | `test_cold_start_time` |
| HTTP 并发 | 10 req/s | `test_concurrent_http_requests` |
| 引擎卸载 | 内存释放 > 50% | `test_engine_unload` |

**交付物**: 稳定的集成系统

**关键文件**:
- `src/tests/test_integration.py`
- `src/tests/test_performance.py`

**验证方式**:
- 所有集成测试通过
- 性能指标全部达标

---

### 阶段 30：文档与收尾

**目标**: 完善开发者文档、API 文档和代码注释

**设计要点**:
- 开发者文档：架构说明、模块关系、扩展指南
- API 文档：HTTP/CLI 接口说明
- 代码注释：关键模块中文注释

**任务清单**:
1. 编写开发者文档
2. 编写 HTTP API 文档
3. 编写 CLI 使用文档
4. 完善关键模块中文注释
5. 清理废弃代码

**文档结构**:

```markdown
# docs/developer_guide.md - 开发者文档

## 1. 架构概述

### 1.1 整体架构
```
┌─────────────────────────────────────────┐
│              表示层 (UI)                  │
│  MainWindow / 功能页面 / 通用控件        │
├─────────────────────────────────────────┤
│             控制层 (Controllers)           │
│  MainController / 页面控制器              │
├─────────────────────────────────────────┤
│              服务层 (Services)             │
│  OCRService / TaskManager / ExportService │
├─────────────────────────────────────────┤
│              引擎层 (Engines)              │
│  PaddleLocal / RapidOCR / 云OCR引擎      │
└─────────────────────────────────────────┘
```

### 1.2 模块关系图

### 1.3 目录结构
```
src/
├── ui/              # 表示层
├── controllers/     # 控制层
├── services/        # 服务层
├── models/          # 数据模型
├── utils/           # 工具类
└── platform/        # 平台相关
```

## 2. 核心模块说明

### 2.1 任务系统
- TaskManager: 任务调度器
- TaskQueue: 优先级队列
- TaskExecutor: 执行器

### 2.2 OCR 引擎
- BaseEngine: 引擎基类
- EngineManager: 引擎管理器
- 本地/云引擎实现

### 2.3 导出系统
- ExportService: 导出服务
- 各格式 Exporter

## 3. 扩展指南

### 3.1 添加新 OCR 引擎
1. 继承 BaseEngine
2. 实现 recognize() 方法
3. 在 EngineManager 注册

### 3.2 添加新导出格式
1. 继承 BaseExporter
2. 实现 export() 方法
3. 在 ExportService 注册

### 3.3 添加新功能页面
1. 创建 UI 文件
2. 创建 Controller
3. 在 MainWindow 注册
```

```markdown
# docs/http_api.md - HTTP API 文档

## 基础信息

- 基础 URL: `http://localhost:1224`
- 内容类型: `application/json`

## 接口列表

### POST /api/ocr - 单张图片 OCR

**请求**:
```json
{
    "image": "base64...",
    "engine": "paddle_local"
}
```

**响应**:
```json
{
    "code": 0,
    "data": {
        "text": "识别结果",
        "boxes": [[x1,y1,x2,y2], ...],
        "confidence": 0.95
    }
}
```

### POST /api/ocr/batch - 批量 OCR
### GET /api/task/{id} - 查询任务状态
### POST /api/qrcode/scan - 二维码识别
### POST /api/qrcode/gen - 二维码生成
### GET /api/health - 健康检查
```

```markdown
# docs/cli_usage.md - CLI 使用文档

## 基本用法

```bash
# 单张图片 OCR
umi-ocr ocr --image test.png

# 批量识别
umi-ocr ocr --dir ./images --output json

# 二维码识别
umi-ocr qrcode --scan qr.png

# 启动 HTTP 服务
umi-ocr server --port 1224
```

## 命令详解
...
```

**代码注释规范**:

```python
# 注释规范示例

class TaskManager:
    """
    任务管理器
    
    职责:
    - 管理任务生命周期
    - 协调队列和执行器
    - 提供任务状态查询
    
    依赖:
    - TaskQueue: 优先级队列
    - TaskExecutor: 任务执行器
    
    线程安全: 是（内部使用锁保护）
    """
    
    def submit_task(self, task: Task) -> str:
        """
        提交任务
        
        参数:
            task: 任务对象
        
        返回:
            task_id: 任务 ID
        
        异常:
            TaskError: 任务提交失败
        """
```

**交付物**:
- 开发者文档 (`docs/developer_guide.md`)
- HTTP API 文档 (`docs/http_api.md`)
- CLI 使用文档 (`docs/cli_usage.md`)
- 关键模块中文注释

**关键文件**:
- `docs/developer_guide.md`
- `docs/http_api.md`
- `docs/cli_usage.md`

**验证方式**:
- 新开发者能根据文档理解架构
- API 文档与实际接口一致

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

### 6.6 代码规模限制
- **单文件行数限制**: 每个 .py 文件不超过 **500 行**
- **超过限制时**: 必须拆分模块，提取公共逻辑到独立文件
- **拆分策略**:
  - 工具函数 → `utils/` 目录
  - 数据结构 → `models/` 目录
  - 业务逻辑 → 拆分为多个小类，各司其职
- **例外**: 自动生成的代码（如 .ui 转换的 Python 文件）不受此限制

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
