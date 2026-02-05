# AGENTS.md

> 本文件为 AI 助手提供项目上下文和开发指南。

## 项目概述

**MapleStory AutoLevelUp** 是一个冒险岛（MapleStory）自动练级机器人，使用 Python 开发，具有以下核心功能：

- **计算机视觉**: 使用 OpenCV 进行游戏画面分析、怪物检测、小地图解析
- **有限状态机**: 管理狩猎、巡逻、符文解谜等状态
- **多输入后端**: 支持 Arduino HID、ctypes_raw、Interception 等反检测方案
- **PySide6 GUI**: 提供可视化配置和调试界面

---

## 核心架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         UI Layer                                 │
│  src/ui/ui.py (MainWindow) ←→ src/ui/AutoBotController.py       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Engine Layer                               │
│              src/engine/MapleStoryAutoLevelUp.py                 │
│                    (MapleStoryAutoBot)                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐          │
│  │     FSM     │  │HealthMonitor│  │   RuneSolver   │          │
│  │ (状态机)    │  │ (HP/MP监控)  │  │  (符文解谜)    │          │
│  └─────────────┘  └──────────────┘  └────────────────┘          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│  States Layer   │  │  Input Layer    │  │   Utils Layer       │
│  src/states/    │  │  src/input/     │  │   src/utils/        │
│  - hunting      │  │  - InputBackend │  │   - common (CV)     │
│  - patrol       │  │  - ArduinoHID   │  │   - anti_detect     │
│  - finding_rune │  │  - KeyBoard*    │  │   - logger          │
│  - solving_rune │  │  - GameCapture  │  │                     │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
```

### 主要类关系

| 类名 | 文件 | 职责 |
|------|------|------|
| `MapleStoryAutoBot` | `engine/MapleStoryAutoLevelUp.py` | 核心机器人，协调所有组件 |
| `FiniteStateMachine` | `engine/FiniteStateMachine.py` | 状态机管理 |
| `HealthMonitor` | `engine/HealthMonitor.py` | HP/MP 监控和自动喝药 |
| `RuneSolver` | `engine/RuneSolver.py` | 符文检测和解谜 |
| `KeyBoardController` | `input/KeyBoardController.py` | 键盘命令执行 |
| `InputBackend` | `input/InputBackend.py` | 输入后端抽象层 |
| `MainWindow` | `ui/ui.py` | 主界面窗口 |
| `AutoBotController` | `ui/AutoBotController.py` | UI-Engine 中间层 |

---

## 状态机流程

### 状态转换图

```
                         ┌──────────────────┐
                         │     Hunting      │ ◀─────────────┐
                         │   (主狩猎状态)    │               │
                         └────────┬─────────┘               │
                                  │                         │
                    检测到符文消息 │                         │
                                  ▼                         │
                         ┌──────────────────┐               │
                         │   Finding Rune   │               │
                         │   (寻找符文)      │               │
                         └────────┬─────────┘               │
                                  │                         │
              ┌───────────────────┼───────────────────┐     │
              │                   │                   │     │
              ▼                   ▼                   │     │
     ┌──────────────┐    ┌──────────────────┐        │     │
     │  Near Rune   │───▶│   Solving Rune   │────────┴─────┘
     │  (接近符文)   │    │   (解决符文)      │
     └──────────────┘    └──────────────────┘
```

### 各状态职责

| 状态 | 类 | 主要行为 |
|------|-----|----------|
| `hunting` | `HuntingState` | 根据路线图移动 + 怪物检测攻击 |
| `patrol` | `PatrolState` | 简单左右巡逻 + 定时攻击 |
| `finding_rune` | `FindingRuneState` | 寻找符文位置，继续狩猎 |
| `near_rune` | `NearRuneState` | 接近符文，尝试触发 |
| `solving_rune` | `SolvingRuneState` | 解决方向键小游戏 |
| `auxiliary` | `AuxiliaryState` | 空闲/辅助模式 |

---

## 关键数据流

### 每帧处理流程 (MapleStoryAutoBot.run)

```python
while not is_terminated:
    # 1. 获取游戏画面
    img_frame = capture.get_frame()
    
    # 2. 检测小地图和玩家位置
    minimap_result = get_minimap_loc_size(img_frame)
    loc_player = get_player_location_on_minimap(img_minimap)
    
    # 3. 状态机执行
    fsm.check_transitions()  # 检查状态转换
    current_state.on_frame() # 执行当前状态逻辑
    
    # 4. 状态逻辑产生命令
    # cmd = "{左右} {上下} {动作}"  例: "left none attack"
    
    # 5. 键盘控制器执行命令
    kb.set_command(cmd)
```

### 命令格式

键盘控制器接受格式为 `"{左右} {上下} {动作}"` 的命令：

| 位置 | 可选值 | 说明 |
|------|--------|------|
| 左右 | `left`, `right`, `stop`, `none` | 水平移动 |
| 上下 | `up`, `down`, `stop`, `none` | 垂直移动（爬绳/下跳） |
| 动作 | `jump`, `attack`, `teleport`, `add_hp`, `add_mp`, `goal`, `none` | 技能动作 |

示例: `"right up jump"` = 右移 + 上移 + 跳跃

---

## 输入后端系统

### 后端优先级（自动选择）

1. **arduino_hid** - 最安全，完全不可检测（需要硬件）
2. **ctypes_raw** - 推荐，使用硬件扫描码（无需安装）
3. **interception** - 内核级模拟（需要驱动+重启）
4. **pyautogui** - 兜底方案（容易被检测）

### Arduino 命令协议

| 命令 | 格式 | 说明 |
|------|------|------|
| 按键按下 | `K{hex}` | `K1E` = 按下 A 键 |
| 按键释放 | `R{hex}` | `R1E` = 释放 A 键 |
| 批量命令 | `B{cmd1};{cmd2}` | 减少串口延迟 |
| 心跳 | `?` | 返回 `OK` |

---

## Build / Lint / Test Commands

### Installation
```bash
# Setup virtual environment (make sure to use Python 3.12)
make setup
# or manually:
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Running the Application
```bash
# Run with UI (recommended)
python -m src.main

# Run without UI
python -m src.engine.MapleStoryAutoLevelUp

# Run with custom config
python -m src.engine.MapleStoryAutoLevelUp --cfg custom

# Run specific map presets (see Makefile for more)
python -m src.engine.MapleStoryAutoLevelUp --map cloud_balcony --cfg custom
```

### Running Tests
```bash
# Run Arduino HID tests
python tests/test_arduino_hid.py

# Run with specific port
python tests/test_arduino_hid.py --port COM3

# Quick test (connection + heartbeat only)
python tests/test_arduino_hid.py --quick

# List available serial ports
python tests/test_arduino_hid.py --list
```

### Building Executable
```bash
# Build standalone executable
build.bat

# Manual build with PyInstaller
pyinstaller --noconsole --onefile src/main.py -p . --icon=media/icon.ico -n MapleStoryAutoLevelUp --hidden-import=pkg_resources.py2_warn --hidden-import=pkg_resources.extern
```

---

## 文件结构详解

```
MapleStoryAutoLevelUp/
├── src/
│   ├── main.py                 # UI 启动入口
│   ├── engine/
│   │   ├── MapleStoryAutoLevelUp.py  # 核心机器人 (~1954行)
│   │   ├── FiniteStateMachine.py     # 状态机框架
│   │   ├── HealthMonitor.py          # HP/MP 监控
│   │   ├── RuneSolver.py             # 符文解谜
│   │   └── Profiler.py               # 性能分析
│   ├── states/
│   │   ├── base_state.py       # State 基类
│   │   ├── hunting.py          # 狩猎状态（默认）
│   │   ├── patrol.py           # 巡逻状态
│   │   ├── finding_rune.py     # 寻找符文
│   │   ├── near_rune.py        # 接近符文
│   │   ├── solving_rune.py     # 解决符文
│   │   └── auxiliary.py        # 辅助状态
│   ├── input/
│   │   ├── InputBackend.py     # 输入后端抽象 (★重要)
│   │   ├── ArduinoHIDBackend.py # Arduino HID
│   │   ├── KeyBoardController.py # 键盘控制
│   │   ├── KeyBoardListener.py   # 键盘监听
│   │   ├── GameWindowCapturor.py # Windows 截图
│   │   └── GameWindowCapturorForMac.py # macOS 截图
│   ├── ui/
│   │   ├── ui.py               # 主窗口 (~1183行)
│   │   ├── AutoBotController.py # UI-Engine 桥接
│   │   └── ArduinoHIDWidget.py  # Arduino UI 组件
│   └── utils/
│       ├── common.py           # 图像处理/配置管理 (~848行)
│       ├── logger.py           # 日志系统
│       ├── anti_detect.py      # 反检测/人性化
│       ├── global_var.py       # 全局常量
│       └── ui.py               # UI 工具函数
├── config/
│   ├── config_default.yaml     # 默认配置（勿修改）
│   ├── config_custom.yaml      # 用户自定义配置
│   ├── config_macOS.yaml       # macOS 平台配置
│   └── config_data.yaml        # 数据库（地图名等）
├── minimaps/                   # 地图路线图资源
├── arduino/                    # Arduino 固件
├── docs/                       # 详细文档
└── tests/                      # 测试脚本
```

---

## 常见修改场景

### 1. 添加新状态

```python
# 1. 创建 src/states/new_state.py
from src.states.base_state import State

class NewState(State):
    def on_enter(self):
        # 进入状态时的初始化
        pass
    
    def on_exit(self):
        # 退出状态时的清理
        pass
    
    def check_transitions(self):
        # 返回目标状态名或 None
        if some_condition:
            return "hunting"
        return None
    
    def on_frame(self):
        # 每帧执行的逻辑
        self.bot.kb.set_command("right none attack")

# 2. 在 MapleStoryAutoLevelUp.py 中注册
from src.states.new_state import NewState
self.fsm.add_state(NewState("new_state", self))
```

### 2. 添加新输入后端

```python
# 在 InputBackend.py 中添加
class NewBackend(InputBackend):
    def key_down(self, key: str) -> None:
        # 实现按键按下
        pass
    
    def key_up(self, key: str) -> None:
        # 实现按键释放
        pass
    
    def press_key(self, key: str, duration: float = 0.05) -> None:
        self.key_down(key)
        time.sleep(duration)
        self.key_up(key)
    
    def is_available(self) -> bool:
        return True  # 检查后端是否可用
```

### 3. 添加新配置项

```yaml
# 1. 在 config/config_default.yaml 添加
new_feature:
  enabled: true
  threshold: 0.5  # 阈值说明
```

```python
# 2. 在代码中使用
if self.cfg["new_feature"]["enabled"]:
    threshold = self.cfg["new_feature"]["threshold"]
```

### 4. 添加图像检测功能

```python
from src.utils.common import find_pattern_sqdiff, load_image, get_mask

# 加载模板
template = load_image("path/to/template.png")
mask = get_mask(template, ignore_color=(255, 255, 255))

# 模板匹配
loc, score, is_local = find_pattern_sqdiff(
    img_frame,
    template,
    last_result=self.last_loc,  # 加速局部搜索
    mask=mask,
    global_threshold=0.4
)

if score < 0.4:  # SQDIFF: 越小越好
    print(f"Found at {loc}")
```

---

## Code Style Guidelines

### Import Order (STRICT)
All Python files must follow this exact import order with section separators:
```python
# Standard Import
import time
import os
import sys
from collections import defaultdict

# Library Import
import numpy as np
import cv2
import yaml
from PySide6.QtWidgets import QApplication

# macOS Import (platform-specific)
if platform.system() == 'Darwin':
    import Quartz
else:
    import win32gui
    import win32con

# Local Import
from src.utils.logger import logger
from src.utils.common import load_yaml, is_mac
from src.input.KeyBoardController import KeyBoardController
```

### Naming Conventions
- **Classes**: PascalCase (e.g., `MapleStoryAutoBot`, `HealthMonitor`, `ArduinoHIDBackend`)
- **Functions/Methods**: snake_case (e.g., `update_cmd_by_route`, `get_player_location`)
- **Private methods**: _snake_case (e.g., `_monitor_loop`, `_heal`)
- **Variables**: snake_case (e.g., `img_frame`, `hp_percent`, `loc_player`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `WINDOW_WORKING_SIZE`, `SCAN_CODES`)
- **Config keys**: snake_case (e.g., `key_duration_base`, `search_range`)

### Type Hints
Use type hints for clarity, especially for function signatures:
```python
def process_command(self, cmd: str) -> bool:
    """Process a command and return success status."""
    pass

from typing import Optional, List, Tuple, Callable

def get_location(self) -> Optional[Tuple[int, int]]:
    """Get player location or None if not found."""
    pass
```

### Docstrings
Use triple quotes for docstrings. Keep them concise:
```python
def update_cmd_by_route(self):
    '''
    Update movement commands based on route map color codes.
    Reads nearest color pixel around player and sets corresponding command.
    '''
    pass
```

### Error Handling
- Use logger for all errors/warnings
- Return None, -1, or False on failure (check documentation for expected return type)
- Use try-except for expected exceptions, especially I/O operations:
```python
try:
    self.capture = GameWindowCapturor(self.cfg)
except Exception as e:
    logger.error(f"[load_config] Failed to initialize capture: {e}")
    return -1
```

### Threading
- Always use `daemon=True` for background threads
- Use locks for shared resources:
```python
self.lock = threading.Lock()
with self.lock:
    # access shared data
```

### Configuration
- Never modify `config/config_default.yaml` directly
- Use `config/config_custom.yaml` for user settings
- Config values are accessed via dictionary: `self.cfg["bot"]["map"]`

### Platform Compatibility
- Use `is_mac()` or `is_windows()` from `src.utils.common` for platform checks
- Keep macOS-specific imports separate
- Game window title must match `cfg["game_window"]["title"]`

### Testing
- Tests are standalone scripts (not pytest-based yet)
- Use `logger` for test output, not `print()`
- Tests should be self-contained and clean up resources
- Use `try-finally` to ensure cleanup even on failure

---

## 关键常量和配置

### 窗口尺寸
```python
WINDOW_WORKING_SIZE = (1296, 700)  # (宽度, 高度)
```

### 小地图玩家颜色
```python
minimap_player_color = (136, 255, 255)  # BGR 格式
```

### 路线图颜色编码
```yaml
route_color_code:
  "0,255,0": "left"      # 绿色 = 向左
  "255,0,0": "right"     # 蓝色 = 向右
  "0,255,255": "up"      # 黄色 = 向上
  "255,255,0": "down"    # 青色 = 向下
  "0,0,255": "goal"      # 红色 = 目标点
```

### 硬件扫描码
```python
SCAN_CODES = {
    'left': 0x4B, 'right': 0x4D, 'up': 0x48, 'down': 0x50,
    'a': 0x1E, 'space': 0x39, 'enter': 0x1C, ...
}
```

---

## 调试技巧

### 1. 查看调试画面
切换到 "Game Window Viz" 标签页，可以看到：
- 怪物检测框（红色）
- 玩家位置（绿色）
- 符文位置（蓝色）
- 小地图分析

### 2. 使用测试图片
```bash
python -m src.engine.MapleStoryAutoLevelUp --test_image screenshot_name
```
会从 `test/screenshot_name.png` 加载图片进行调试。

### 3. 日志分析
日志文件保存在 `log/MSBot_YYYY-MM-DD_HH-MM-SS.log`

### 4. 性能分析
```python
from src.engine.Profiler import Profiler

profiler = Profiler()
profiler.start("detection")
# ... 执行检测 ...
profiler.stop("detection")
profiler.report()  # 打印统计
```

---

## 常见问题排查

### 1. 找不到游戏窗口
- 检查 `cfg["game_window"]["title"]` 是否匹配
- 确保游戏以窗口模式运行
- 使用 `get_game_window_title_by_token()` 查找可用窗口

### 2. 玩家位置检测失败
- 确保小地图可见且在左上角
- 检查 `minimap_player_color` 配置
- 确保创建了队伍（显示红色队伍条）

### 3. 怪物检测不准确
- 检查 `minimaps/{map}/mobs/` 下的模板图片
- 调整 `mob_detection.threshold` 配置
- 使用 `tools/mobMaker.py` 创建新模板

### 4. 键盘输入无效
- 确保游戏窗口是激活状态
- 检查输入后端是否可用
- 尝试切换 `anti_detect.input_backend`

### 5. Arduino 连接问题
- 检查端口设置或启用自动检测
- 确保上传了正确的固件 (`arduino/MapleHID/`)
- 使用 `tests/test_arduino_hid.py --list` 查看可用端口

---

## Anti-Detection 最佳实践

```python
from src.utils.anti_detect import get_human_behavior

human = get_human_behavior()

# 1. 使用随机按键时长
duration = human.get_key_duration()  # 默认约 0.05±0.03 秒

# 2. 添加动作延迟
delay = human.get_action_delay()
time.sleep(delay)

# 3. 随机化冷却时间
cooldown = human.randomize_cooldown(base_cooldown, 'attack')  # ±15%

# 4. 微停顿（模拟思考）
should_pause, pause_duration = human.should_micro_pause()
if should_pause:
    time.sleep(pause_duration)

# 5. 更新疲劳度（长时间运行后反应变慢）
human.update_fatigue()
```

---

## 相关文档

详细的模块文档请参考 `docs/` 目录：
- `docs/README.md` - 项目总览
- `docs/engine.md` - 引擎模块详解
- `docs/states.md` - 状态机状态详解
- `docs/input.md` - 输入控制模块详解
- `docs/ui.md` - UI 模块详解
- `docs/utils.md` - 工具模块详解
- `docs/ARDUINO_HID_GUIDE.md` - Arduino HID 使用指南
