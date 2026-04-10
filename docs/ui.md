# UI 模块文档

> 路径: `src/ui/`

本模块使用 PySide6 (Qt6) 实现图形用户界面，提供机器人控制、配置管理和可视化功能。

---

## 目录

1. [模块概述](#模块概述)
2. [ui.py - 主窗口](#uipy---主窗口)
3. [AutoBotController.py - 机器人控制器](#autobotcontrollerpy---机器人控制器)
4. [ArduinoHIDWidget.py - Arduino HID UI组件](#arduinohidwidgetpy---arduino-hid-ui组件)

---

## 模块概述

UI模块采用 MVC 架构设计：

```
┌─────────────────────────────────────────────────────────────┐
│                       MainWindow (View)                      │
│                        src/ui/ui.py                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  AutoBotController (Controller)              │
│                 src/ui/AutoBotController.py                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  MapleStoryAutoBot (Model)                   │
│              src/engine/MapleStoryAutoLevelUp.py             │
└─────────────────────────────────────────────────────────────┘
```

---

## ui.py - 主窗口

### 文件信息
- **路径**: `src/ui/ui.py`
- **行数**: 1183 行
- **作用**: 实现主界面窗口，包含所有UI组件

### 窗口尺寸配置

```python
TAB_WINDOW_SIZE = {
    'Main': (700, 800),
    'Advanced Settings': (750, 800),
    'Game Window Viz': (1280, 650),
    'Route Map Viz': (800, 800),
    'Arduino HID': (800, 700),
}
```

### MainWindow 类

继承自 `QMainWindow`，是应用程序的主窗口。

#### 信号

| 信号 | 参数 | 说明 |
|------|------|------|
| `request_close` | - | 请求关闭窗口 |

#### 主要属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `controller` | `AutoBotController` | 机器人控制器 |
| `cfg` | `dict` | 当前配置 |
| `cfg_base` | `dict` | 基础配置 |
| `tabs` | `QTabWidget` | 标签页容器 |

### 标签页结构

```
QTabWidget (tabs)
    │
    ├── Main Tab (主控制页)
    │       ├── Control GroupBox       # 启动/暂停/截图/录制
    │       ├── Attack GroupBox        # 攻击设置
    │       ├── Key Binding GroupBox   # 按键绑定
    │       ├── Pet Skill GroupBox     # 宠物技能/Buff
    │       ├── Map Selection GroupBox # 地图选择
    │       └── Log GroupBox           # 日志输出
    │
    ├── Advanced Settings Tab (高级设置)
    │       └── 动态生成的配置组
    │
    ├── Game Window Viz Tab (游戏画面可视化)
    │       └── debug_canvas (QLabel)
    │
    ├── Route Map Viz Tab (路线图可视化)
    │       └── route_map_canvas (QLabel)
    │
    └── Arduino HID Tab (Arduino控制)
            └── ArduinoHIDPanel
```

### 主要方法

#### 标签页设置

| 方法 | 说明 |
|------|------|
| `setup_main_tab()` | 创建主控制标签页 |
| `setup_advance_setting_tab()` | 创建高级设置标签页 |
| `setup_game_window_viz_tab()` | 创建游戏画面可视化标签页 |
| `setup_route_map_viz_tab()` | 创建路线图可视化标签页 |
| `setup_arduino_hid_tab()` | 创建Arduino HID标签页 |

#### 组件创建

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `create_control_gbox()` | `QGroupBox` | 创建控制组 |
| `create_attack_gbox()` | `QGroupBox` | 创建攻击设置组 |
| `create_key_binding_gbox()` | `QGroupBox` | 创建按键绑定组 |
| `create_pet_skill_gbox()` | `QGroupBox` | 创建宠物技能组 |
| `create_map_selection_gbox()` | `QGroupBox` | 创建地图选择组 |
| `create_log_gbox()` | `QGroupBox` | 创建日志组 |
| `create_buff_skill_section()` | `QWidget` | 创建Buff技能区域 |

#### 配置管理

| 方法 | 参数 | 说明 |
|------|------|------|
| `load_config(error_label, path)` | 错误标签, 路径 | 加载配置文件 |
| `apply_config_to_ui()` | - | 应用配置到UI |
| `update_cfg_from_main_ui()` | - | 从UI收集配置 |
| `save_ui_state()` | - | 保存UI状态 |
| `load_ui_state()` | - | 加载UI状态 |
| `refresh_arduino_panel()` | - | 刷新 Arduino HID 面板后端引用 |
| `update_arduino_backend()` | - | 更新 Arduino 后端引用 |

#### 事件处理

| 方法 | 说明 |
|------|------|
| `on_tab_changed(index)` | 标签页切换 |
| `on_map_selected(item)` | 地图选择 |
| `toggle_start_ui()` | 启动/暂停切换 |
| `toggle_screenshot_ui()` | 截图 |
| `toggle_record_ui()` | 录制切换 |
| `toggle_auto_add_hp(state)` | 自动加血切换 |
| `toggle_auto_add_mp(state)` | 自动加蓝切换 |
| `toggle_auto_buff(state)` | 自动Buff切换 |

#### 画布更新

| 方法 | 参数 | 说明 |
|------|------|------|
| `update_debug_canvas(img)` | `numpy.ndarray` | 更新游戏画面 |
| `update_route_map_canvas(img)` | `numpy.ndarray` | 更新路线图 |
| `append_log(message, level)` | 消息, 级别 | 添加日志 |

### 工作流程

#### 启动流程

```
__init__():
    │
    ├── 加载默认配置 (config_default.yaml)
    │
    ├── 加载平台配置 (config_macOS.yaml if macOS)
    │
    ├── 加载数据库 (config_data.yaml)
    │
    ├── 创建所有标签页
    │
    ├── 加载上次UI状态
    │
    └── 连接信号
```

#### 启动机器人流程

```
toggle_start_ui():
    │
    ├── update_cfg_from_main_ui()     # 收集UI配置
    │
    ├── save_yaml(cfg, ".config_tmp.yaml")  # 保存临时配置
    │
    ├── controller.start_bot(cfg_path)      # 启动机器人
    │
    ├── 成功 → 更新按钮状态，禁用设置
    │
    └── 失败 → 恢复按钮状态
```

#### 关闭流程

```
closeEvent():
    │
    ├── update_cfg_from_main_ui()     # 收集当前配置
    │
    ├── get_cfg_diff()                # 计算配置差异
    │
    ├── save_yaml()                   # 保存自定义配置
    │
    ├── save_ui_state()               # 保存UI状态
    │
    └── controller.terminate_bot()    # 终止机器人
```

### 使用示例

```python
from PySide6.QtWidgets import QApplication
from src.ui.ui import MainWindow
from src.ui.AutoBotController import AutoBotController

app = QApplication([])

# 创建控制器
controller = AutoBotController()

# 创建主窗口
window = MainWindow(controller)
controller.update_signal(window)

window.show()
app.exec()
```

---

## AutoBotController.py - 机器人控制器

### 文件信息
- **路径**: `src/ui/AutoBotController.py`
- **行数**: 139 行
- **作用**: 作为UI和机器人引擎之间的中间层

### AutoBotController 类

继承自 `QObject`，管理机器人引擎和UI之间的通信。

#### 信号

| 信号 | 参数 | 说明 |
|------|------|------|
| `debug_image_signal` | `object` | 调试图像更新 |
| `route_map_viz_signal` | `object` | 路线图更新 |

#### 主要属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `auto_bot` | `MapleStoryAutoBot` | 机器人引擎实例 |
| `kb_listener` | `KeyBoardListener` | 键盘监听器 |

#### 初始化

```python
def __init__(self):
    # 创建机器人引擎
    args = Namespace(
        disable_control=False,
        cfg="default",
        debug=False,
        record=False,
        is_ui=True,
        disable_viz=True,
        test_image='',
        init_state='',
    )
    self.auto_bot = MapleStoryAutoBot(args)
    
    # 创建键盘监听器
    self.kb_listener = KeyBoardListener(is_autobot=True)
```

#### 主要方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `update_signal(ui)` | `MainWindow` | - | 连接信号到UI |
| `start_bot(cfg_path)` | `str` | `int` | 启动机器人 (0=成功, -1=失败)，并刷新 Arduino HID 面板 |
| `pause_bot()` | - | - | 暂停机器人 |
| `terminate_bot()` | - | - | 终止机器人 |
| `take_screenshot()` | - | - | 截图 |
| `start_recording()` | - | - | 开始录制 |
| `stop_recording()` | - | - | 停止录制 |
| `enable_bot_viz()` | - | - | 启用可视化 |
| `disable_bot_viz()` | - | - | 禁用可视化 |

### 功能键绑定

```python
def update_signal(self, ui):
    # 注册功能键处理器
    self.kb_listener.register_func_key_handler('f1', ui.button_start_pause.click)
    self.kb_listener.register_func_key_handler('f2', ui.button_screenshot.click)
    self.kb_listener.register_func_key_handler('f3', ui.button_record.click)
    self.kb_listener.register_func_key_handler('f12', lambda: ui.request_close.emit())
```

| 功能键 | 功能 |
|--------|------|
| F1 | 启动/暂停 |
| F2 | 截图 |
| F3 | 开始/停止录制 |
| F12 | 关闭程序 |

---

## ArduinoHIDWidget.py - Arduino HID UI组件

### 文件信息
- **路径**: `src/ui/ArduinoHIDWidget.py`
- **行数**: 647 行
- **作用**: 提供Arduino连接状态、日志显示的UI组件

### 线程安全说明

Arduino后端在后台线程中运行，所有UI更新通过 Qt Signal/Slot 机制传递到主线程。

### ConnectionStatusWidget 类

显示Arduino连接状态。

#### 信号

| 信号 | 参数 | 说明 |
|------|------|------|
| `operation_finished` | `str, bool` | 后台操作完成 |

#### 状态颜色

```python
STATUS_COLORS = {
    'connected': '#4CAF50',      # 绿色
    'disconnected': '#9E9E9E',   # 灰色
    'connecting': '#FF9800',      # 橙色
    'reconnecting': '#FF9800',    # 橙色
    'error': '#F44336',           # 红色
}
```

#### 显示内容

- 连接状态（带颜色指示器）
- 端口信息
- 设备ID
- 延迟
- 统计信息（命令数、错误数、平均延迟）
- 错误信息
- 重连/断开按钮

#### 主要方法

| 方法 | 说明 |
|------|------|
| `set_backend(backend)` | 设置后端引用 |
| `_update_display()` | 更新显示（定时调用） |
| `_on_reconnect_clicked()` | 重连按钮点击 |
| `_on_disconnect_clicked()` | 断开按钮点击 |

### HIDLogWidget 类

实时显示HID命令日志。

#### 信号

| 信号 | 参数 | 说明 |
|------|------|------|
| `log_entry_received` | `object` | 收到日志条目 |

#### 功能

- 日志过滤（全部/发送/接收/错误）
- 暂停/继续
- 清空日志
- 颜色编码显示

#### 日志颜色

| 类型 | 颜色 |
|------|------|
| TX (发送) | 蓝色 `#4FC3F7` |
| RX (接收) | 绿色 `#81C784` |
| ERR (错误) | 红色 `#E57373` |

#### 主要方法

| 方法 | 说明 |
|------|------|
| `set_backend(backend)` | 设置后端并注册回调 |
| `_on_log_entry(entry)` | 日志条目回调（线程安全） |
| `_apply_filter(filter_text)` | 应用过滤器 |
| `_clear_logs()` | 清空日志 |
| `_toggle_pause()` | 暂停/继续 |

### ErrorLogWidget 类

专门显示错误日志。

#### 信号

| 信号 | 参数 | 说明 |
|------|------|------|
| `error_entry_received` | `object` | 收到错误日志 |

#### 主要方法

| 方法 | 说明 |
|------|------|
| `set_backend(backend)` | 设置后端 |
| `_refresh_errors()` | 刷新错误列表 |
| `_clear_errors()` | 清空错误 |

### ArduinoHIDPanel 类

完整的Arduino HID面板，包含状态、日志、错误三个部分。

```
ArduinoHIDPanel (QGroupBox)
    │
    ├── ConnectionStatusWidget    # 连接状态
    │
    ├── QFrame (分隔线)
    │
    └── QTabWidget
            ├── HIDLogWidget      # 命令日志
            └── ErrorLogWidget    # 错误日志
```

#### 主要方法

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `set_backend(backend)` | - | 设置后端 |
| `get_status_widget()` | `ConnectionStatusWidget` | 获取状态组件 |
| `get_log_widget()` | `HIDLogWidget` | 获取日志组件 |
| `get_error_widget()` | `ErrorLogWidget` | 获取错误组件 |

### create_arduino_settings_widget 函数

创建Arduino设置组件，用于配置连接参数。

```python
widget = create_arduino_settings_widget()

# 访问组件
widget.port_combo       # 端口选择
widget.baud_combo       # 波特率
widget.batch_check      # 批处理开关
widget.reconnect_check  # 自动重连开关
```

---

## 自定义组件

### SingleKeyEdit 类

单键输入编辑框，继承自 `QKeySequenceEdit`。

```python
from src.utils.ui import SingleKeyEdit

key_edit = SingleKeyEdit()
key_edit.set_key("A")
current_key = key_edit.get_key()  # "a"
```

### QtLogHandler 类

Qt日志处理器，将日志输出到UI。

```python
from src.utils.ui import QtLogHandler

handler = QtLogHandler()
handler.log_signal.connect(self.append_log)
logger.addHandler(handler)
```

---

## UI 工具函数

位于 `src/utils/ui.py`:

| 函数 | 参数 | 说明 |
|------|------|------|
| `validate_numerical_input(...)` | 输入, 错误标签, 范围 | 验证数值输入 |
| `create_error_label()` | - | 创建错误标签 |
| `create_field(label_text, widget)` | 标签, 组件 | 创建标签-输入对 |
| `clear_debug_canvas(canvas)` | QLabel | 清空画布 |
| `create_advance_setting_gbox(...)` | 标题, 配置 | 创建高级设置组 |
