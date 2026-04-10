# Input 模块文档

> 路径: `src/input/`

本模块负责所有输入相关功能，包括键盘控制、游戏窗口截取和反检测输入后端。

---

## 目录

1. [模块概述](#模块概述)
2. [InputBackend.py - 输入后端抽象层](#inputbackendpy---输入后端抽象层)
3. [ArduinoHIDBackend.py - Arduino硬件HID后端](#arduinohidbackendpy---arduino硬件hid后端)
4. [KeyBoardController.py - 键盘控制器](#keyboardcontrollerpy---键盘控制器)
5. [KeyBoardListener.py - 键盘监听器](#keyboardlistenerpy---键盘监听器)
6. [GameWindowCapturor.py - Windows游戏窗口截取](#gamewindowcapturorpy---windows游戏窗口截取)
7. [GameWindowCapturorForMac.py - macOS游戏窗口截取](#gamewindowcapturorformacpy---macos游戏窗口截取)

---

## 模块概述

Input 模块采用分层架构设计：

```
┌─────────────────────────────────────────────────────────────┐
│                    KeyBoardController                        │
│                    (高层键盘控制接口)                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      InputBackend                            │
│                    (输入后端抽象层)                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────┐ ┌──────────────────┐
│ CtypesRawBackend│ │InterceptionB│ │ ArduinoHIDBackend│
│ (推荐，无需重启)  │ │(需要驱动)    │ │  (最安全，需硬件) │
└─────────────────┘ └─────────────┘ └──────────────────┘
```

---

## InputBackend.py - 输入后端抽象层

### 文件信息
- **路径**: `src/input/InputBackend.py`
- **行数**: 603 行
- **作用**: 提供多种输入后端以规避反作弊检测

### 核心概念

#### 为什么需要多种后端？

游戏反作弊系统检测脚本输入的主要方法：

1. **LLKHF_INJECTED 标志** - Windows 会给 SendInput 添加注入标志
2. **缺少硬件扫描码** - 真实键盘包含硬件扫描码
3. **时序分析** - 脚本按键间隔过于规律

### 后端类型对比

| 后端 | 安全性 | 延迟 | 需要 | 推荐度 |
|------|--------|------|------|--------|
| `arduino_hid` | ★★★★★ | 5-15ms | Arduino硬件 | 最高 |
| `ctypes_raw` | ★★★☆☆ | <1ms | 无 | 推荐 |
| `interception` | ★★★★☆ | <1ms | 驱动+重启 | 高 |
| `pyautogui` | ★☆☆☆☆ | <1ms | 无 | 不推荐 |

### InputBackend 抽象基类

```python
class InputBackend(ABC):
    @abstractmethod
    def key_down(self, key: str) -> None:
        '''按下按键（保持按住状态）'''
        pass
    
    @abstractmethod
    def key_up(self, key: str) -> None:
        '''释放按键'''
        pass
    
    @abstractmethod
    def press_key(self, key: str, duration: float = 0.05) -> None:
        '''按下并释放按键'''
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        '''检查后端是否可用'''
        pass
```

### CtypesRawBackend 类

直接调用 Windows API，使用硬件扫描码。

**优点**:
- 无需安装驱动
- 无需重启电脑
- 输入包含硬件扫描码

**缺点**:
- 仍有 LLKHF_INJECTED 标志

```python
# 配置使用
anti_detect:
  input_backend: "ctypes_raw"
```

### InterceptionBackend 类

使用 Interception 驱动实现内核级键盘模拟。

**安装步骤**:
```bash
# 1. 下载驱动
# https://github.com/oblitum/Interception/releases

# 2. 管理员运行安装
install-interception.exe /install

# 3. 重启电脑

# 4. 安装 Python 库
pip install interception-python
```

### PyAutoGuiBackend 类

使用 pyautogui 库（容易被检测，仅作兜底方案）。

### 硬件扫描码映射

```python
SCAN_CODES = {
    # 方向键
    'left': 0x4B, 'right': 0x4D, 'up': 0x48, 'down': 0x50,
    
    # 字母键
    'a': 0x1E, 'b': 0x30, 'c': 0x2E, ...
    
    # 数字键
    '0': 0x0B, '1': 0x02, '2': 0x03, ...
    
    # 功能键
    'f1': 0x3B, 'f2': 0x3C, ...
}

# 扩展键（需要 KEYEVENTF_EXTENDEDKEY 标志）
EXTENDED_KEYS = {'left', 'right', 'up', 'down', 'home', 'end', ...}
```

### 全局函数

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get_input_backend` | `backend_type='auto'` | `InputBackend` | 获取输入后端实例 |
| `init_input_backend` | `cfg: dict` | `InputBackend` | 根据配置初始化后端（同时初始化 Arduino HID 用于 UI 显示） |
| `get_arduino_backend` | - | `ArduinoHIDBackend` | 获取Arduino后端实例（可能为 None） |

### 使用示例

```python
from src.input.InputBackend import get_input_backend, init_input_backend, get_arduino_backend

# 自动选择最佳后端
backend = get_input_backend('auto')

# 根据配置初始化（会同时初始化 Arduino HID 用于 UI 面板显示）
backend = init_input_backend(cfg)

# 获取 Arduino 后端（用于 UI 面板）
arduino = get_arduino_backend()
if arduino:
    print(f"Arduino 已连接: {arduino._port}")

# 使用后端
backend.key_down('a')
backend.key_up('a')
backend.press_key('space', 0.1)
```

---

## ArduinoHIDBackend.py - Arduino硬件HID后端

### 文件信息
- **路径**: `src/input/ArduinoHIDBackend.py`
- **行数**: 770 行
- **作用**: 通过Arduino硬件实现真实USB HID输入

### 核心优势

由于输入来自真实USB设备，**完全无法被反作弊系统检测**。

| 特性 | 说明 |
|------|------|
| 不可检测 | 对OS来说就是真实键盘 |
| 无需驱动 | 不需要安装内核驱动 |
| 跨平台 | Windows/Mac/Linux 通用 |
| 绕过权限 | 不需要管理员权限 |

### 支持的硬件

- Arduino Leonardo
- Pro Micro (推荐，小巧便宜 ~15-30元)
- Teensy 2.0/4.0
- 任何带 ATmega32U4 的开发板

### 类结构

#### HIDLogEntry 数据类

```python
@dataclass
class HIDLogEntry:
    timestamp: datetime
    direction: str      # 'TX' / 'RX' / 'ERR'
    command: str
    response: str = ''
    latency_ms: float = 0.0
    success: bool = True
    error_message: str = ''
```

#### HIDLogger 类

记录所有HID操作，便于调试。

| 方法 | 说明 |
|------|------|
| `log(...)` | 记录一条日志 |
| `get_recent_logs(count)` | 获取最近日志 |
| `get_error_logs(count)` | 获取错误日志 |
| `get_average_latency()` | 获取平均延迟 |
| `register_callback(func)` | 注册日志回调 |

#### ConnectionState 枚举

```python
class ConnectionState:
    DISCONNECTED = 'disconnected'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    ERROR = 'error'
    RECONNECTING = 'reconnecting'
```

#### CommandBatcher 类

命令批处理器，将多个命令合并发送以降低延迟。

```python
batcher = CommandBatcher(max_batch_size=20, max_wait_ms=2.0)
batch_cmd = batcher.add('K1E')  # 添加命令
if batch_cmd:
    send(batch_cmd)  # 批次满了，发送
```

#### ArduinoHIDBackend 类

主要后端类。

**初始化参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `port` | `str` | `''` | 串口端口 |
| `baud_rate` | `int` | `115200` | 波特率 |
| `auto_detect` | `bool` | `True` | 自动检测端口 |
| `enable_batch` | `bool` | `True` | 启用批处理 |

**主要方法**:

| 方法 | 参数 | 说明 |
|------|------|------|
| `key_down(key)` | `key: str` | 按下按键 |
| `key_up(key)` | `key: str` | 释放按键 |
| `press_key(key, duration)` | `key: str, duration: float` | 按下并释放 |
| `mouse_move(dx, dy)` | `dx: int, dy: int` | 移动鼠标 |
| `mouse_click(button)` | `button: int` | 鼠标点击 |
| `release_all()` | - | 释放所有按键 |
| `reconnect()` | - | 手动重连 |
| `disconnect()` | - | 断开连接 |

### Arduino 命令协议

| 命令 | 格式 | 说明 |
|------|------|------|
| 按键按下 | `K{scancode_hex}` | 如 `K1E` = 按下A键 |
| 按键释放 | `R{scancode_hex}` | 如 `R1E` = 释放A键 |
| 按键点击 | `P{scancode_hex}` | 按下并释放 |
| 等待 | `W{ms}` | 等待毫秒 |
| 批量命令 | `B{cmd1};{cmd2};...` | 批量执行 |
| 鼠标移动 | `M{dx},{dy}` | 相对移动 |
| 鼠标点击 | `C{button}` | 1=左,2=右,3=中 |
| 释放所有 | `X` | 释放所有按键 |
| 心跳 | `?` | 返回 `OK` |
| 设备信息 | `I` | 返回设备ID |

### 配置示例

```yaml
anti_detect:
  input_backend: "arduino_hid"
  arduino:
    port: "COM3"              # Windows
    # port: "/dev/ttyACM0"    # Linux/Mac
    baud_rate: 115200
    auto_detect: true
    timeout: 0.1
    heartbeat_interval: 1.0
    reconnect_delay: 2.0
    enable_batch: true
```

---

## KeyBoardController.py - 键盘控制器

### 文件信息
- **路径**: `src/input/KeyBoardController.py`
- **行数**: 346 行
- **作用**: 高层键盘控制接口，管理按键状态和命令执行

### 全局函数

| 函数 | 参数 | 说明 |
|------|------|------|
| `key_down(key)` | `key: str` | 按下按键（带随机延迟） |
| `key_up(key)` | `key: str` | 释放按键（带随机延迟） |
| `press_key(key, duration)` | `key: str, duration: float` | 按下并释放（人性化） |
| `set_input_backend(cfg)` | `cfg: dict` | 设置输入后端 |

### KeyBoardController 类

管理游戏角色的键盘控制。

**初始化参数**:

```python
class KeyBoardController:
    def __init__(self, cfg):
        self.cfg = cfg
        self.cmd_action = "none"       # 当前动作命令
        self.cmd_up_down = "none"      # 上下移动命令
        self.cmd_left_right = "none"   # 左右移动命令
        self.is_enable = True          # 控制器启用状态
        # ...
```

**主要方法**:

| 方法 | 说明 |
|------|------|
| `set_command(cmd_str)` | 设置命令，格式: `"left up attack"` |
| `toggle_enable()` | 切换启用状态 |
| `enable()` | 启用控制器 |
| `disable()` | 禁用控制器 |
| `release_all_key()` | 释放所有按键 |
| `is_game_window_active()` | 检查游戏窗口是否激活 |

### 命令格式

```
"{左右移动} {上下移动} {动作}"
```

| 命令类型 | 可选值 |
|----------|--------|
| 左右移动 | `left`, `right`, `stop`, `none` |
| 上下移动 | `up`, `down`, `stop`, `none` |
| 动作 | `jump`, `teleport`, `attack`, `add_hp`, `add_mp`, `goal`, `none` |

### 工作流程

```
run() 线程循环:
    │
    ├── 检查游戏窗口是否激活
    │
    ├── 随机闲置行为（模拟人类）
    │
    ├── Buff技能自动释放
    │
    ├── 强制喝血检查
    │
    ├── 处理左右移动命令
    │       ├── left  → key_up(right), key_down(left)
    │       ├── right → key_up(left), key_down(right)
    │       └── stop  → key_up(left), key_up(right)
    │
    ├── 处理上下移动命令
    │       ├── up   → key_up(down), key_down(up)
    │       ├── down → key_up(up), key_down(down)
    │       └── stop → key_up(up), key_up(down)
    │
    ├── 处理动作命令
    │       ├── jump     → press_key(jump_key)
    │       ├── teleport → press_key(teleport_key)
    │       ├── attack   → press_key(attack_key)
    │       └── add_hp   → press_key(add_hp_key)
    │
    └── 限制FPS（带随机化）
```

### 使用示例

```python
from src.input.KeyBoardController import KeyBoardController, press_key

# 初始化
kb = KeyBoardController(cfg)

# 设置命令
kb.set_command("right none attack")

# 直接按键
press_key("space", 0.1)

# 禁用/启用
kb.disable()
kb.enable()
```

---

## KeyBoardListener.py - 键盘监听器

### 文件信息
- **路径**: `src/input/KeyBoardListener.py`
- **行数**: 176 行
- **作用**: 监听用户键盘输入，用于功能键和路线录制

### KeyBoardListener 类

**初始化参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `cfg` | `dict` | `None` | 配置字典 |
| `is_autobot` | `bool` | `True` | 是否为机器人模式 |

**主要属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `key_pressing` | `list` | 当前按下的按键列表 |
| `is_pressed_func_key` | `list[bool]` | F1-F12按键状态 |
| `is_enable` | `bool` | 监听器启用状态 |

**主要方法**:

| 方法 | 参数 | 说明 |
|------|------|------|
| `register_func_key_handler(key, handler)` | `key: str, handler: callable` | 注册功能键处理器 |
| `on_press(key)` | - | 按键按下回调 |
| `on_release(key)` | - | 按键释放回调 |
| `stop()` | - | 停止监听 |

### 运行模式

1. **AutoBot 模式** (`is_autobot=True`)
   - 仅监听功能键 F1-F12
   - 用于控制机器人启停

2. **路线录制模式** (`is_autobot=False`)
   - 监听方向键和功能键
   - 记录用户按键用于生成路线图

### 使用示例

```python
from src.input.KeyBoardListener import KeyBoardListener

# 创建监听器
listener = KeyBoardListener(cfg, is_autobot=True)

# 注册功能键处理器
listener.register_func_key_handler('f1', lambda: print("F1 pressed"))
listener.register_func_key_handler('f12', lambda: sys.exit())

# 获取当前按下的键
print(listener.key_pressing)  # ['left', 'up', ...]
```

---

## GameWindowCapturor.py - Windows游戏窗口截取

### 文件信息
- **路径**: `src/input/GameWindowCapturor.py`
- **行数**: 106 行
- **作用**: 使用 windows-capture 库截取游戏窗口

### GameWindowCapturor 类

**初始化参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `cfg` | `dict` | - | 配置字典 |
| `test_image_name` | `str` | `None` | 测试图片名（用于调试） |

**主要属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `frame` | `numpy.ndarray` | 当前帧图像 |
| `fps` | `int` | 当前帧率 |
| `window_title` | `str` | 游戏窗口标题 |

**主要方法**:

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `get_frame()` | `numpy.ndarray` | 获取最新帧（BGR格式） |
| `stop()` | - | 停止截取 |

### 工作原理

使用 `windows-capture` 库通过 Windows Graphics Capture API 实现高效截图：

```
WindowsCapture
    │
    ├── on_frame_arrived()  # 帧到达回调
    │       ├── 加锁存储帧
    │       └── FPS限制
    │
    └── on_closed()  # 窗口关闭回调
```

### 使用示例

```python
from src.input.GameWindowCapturor import GameWindowCapturor

# 初始化
capture = GameWindowCapturor(cfg)

# 获取帧
frame = capture.get_frame()
if frame is not None:
    cv2.imshow("Game", frame)

# 停止
capture.stop()
```

---

## GameWindowCapturorForMac.py - macOS游戏窗口截取

### 文件信息
- **路径**: `src/input/GameWindowCapturorForMac.py`
- **行数**: 159 行
- **作用**: 使用 mss + Quartz 实现 macOS 窗口截取

### 辅助函数

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get_window_title(token)` | `token: str` | `str` | 查找包含token的窗口标题 |
| `get_window_region(title)` | `title: str` | `dict` | 获取窗口区域 |

### GameWindowCapturor 类 (macOS版)

与Windows版接口相同，内部使用 `mss` 库进行屏幕截取。

**工作流程**:

```
start_capture() 线程循环:
    │
    ├── update_window_region()  # 更新窗口区域
    │
    ├── capture_frame()         # 截取屏幕
    │       └── mss.grab(region)
    │
    └── limit_fps()             # FPS限制
```

### 注意事项

1. macOS 需要授予屏幕录制权限
2. 窗口区域通过 Quartz API 获取
3. 帧率限制通过配置 `fps_limit_window_capturor` 控制

---

## 配置参考

### 完整输入配置

```yaml
system:
  fps_limit_keyboard_controller: 30  # 键盘控制器FPS
  fps_limit_window_capturor: 30      # 窗口截取FPS
  key_debounce_interval: 0.5         # 按键防抖间隔

game_window:
  title: "MapleStory"  # 游戏窗口标题

key:
  jump: "c"
  teleport: "f"
  aoe_skill: "e"
  directional_attack: "ctrl"
  add_hp: "insert"
  add_mp: "delete"
  party: "p"
  return_home: "h"

anti_detect:
  input_backend: "ctypes_raw"  # 或 "arduino_hid", "interception", "pyautogui"
  
  # Arduino 配置（当 input_backend = "arduino_hid" 时）
  arduino:
    port: "COM3"
    baud_rate: 115200
    auto_detect: true
    enable_batch: true
```
