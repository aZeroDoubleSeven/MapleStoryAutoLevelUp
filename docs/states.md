# States 模块文档

> 路径: `src/states/`

本模块实现了有限状态机（FSM）的各种状态类，用于控制机器人在不同情况下的行为。

---

## 目录

1. [模块概述](#模块概述)
2. [状态转换图](#状态转换图)
3. [base_state.py - 状态基类](#base_statepy---状态基类)
4. [hunting.py - 狩猎状态](#huntingpy---狩猎状态)
5. [patrol.py - 巡逻状态](#patrolpy---巡逻状态)
6. [finding_rune.py - 寻找符文状态](#finding_runepy---寻找符文状态)
7. [near_rune.py - 接近符文状态](#near_runepy---接近符文状态)
8. [solving_rune.py - 解决符文状态](#solving_runepy---解决符文状态)
9. [auxiliary.py - 辅助状态](#auxiliarypy---辅助状态)

---

## 模块概述

States 模块采用状态模式（State Pattern）设计，每个状态类负责：
- 定义该状态下的行为逻辑（`on_frame`）
- 定义进入/退出状态时的操作（`on_enter`/`on_exit`）
- 定义状态转换条件（`check_transitions`）

所有状态类都继承自 `State` 基类，并持有对主机器人（`MapleStoryAutoBot`）的引用。

---

## 状态转换图

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
                    ▼                                         │
┌─────────────────────────────────────────┐                   │
│              Hunting                     │                   │
│   (主要狩猎状态，根据路线图打怪)          │                   │
└────────────────────┬────────────────────┘                   │
                     │                                         │
                     │ 检测到符文启用消息                        │
                     │ is_rune_enable() or is_rune_warning()   │
                     ▼                                         │
┌─────────────────────────────────────────┐                   │
│           Finding Rune                   │                   │
│     (寻找符文位置，继续狩猎)              │                   │
└────────────────────┬────────────────────┘                   │
                     │                                         │
        ┌────────────┴────────────┐                           │
        │                         │                           │
        │ 找到符文位置              │ 进入符文小游戏            │
        │ loc_rune != None        │ is_in_rune_game()         │
        ▼                         ▼                           │
┌──────────────────┐    ┌──────────────────┐                  │
│   Near Rune      │    │   Solving Rune   │                  │
│  (接近符文位置)   │───▶│  (解决符文谜题)   │──────────────────┘
└────────┬─────────┘    └──────────────────┘
         │                      │
         │ 超时                  │ 完成解谜
         │ (near_rune_duration)  │ !is_in_rune_game()
         ▼                      │
┌──────────────────┐            │
│  Finding Rune    │◀───────────┘
│   (重新寻找)      │
└──────────────────┘
```

**独立状态：**
- `Patrol` - 简单巡逻模式，左右移动攻击
- `Auxiliary` - 辅助模式，空闲状态

---

## base_state.py - 状态基类

### 文件信息
- **路径**: `src/states/base_state.py`
- **行数**: 17 行
- **作用**: 定义所有状态类的基础接口

### State 类

```python
class State:
    def __init__(self, name, bot):
        self.name = name  # 状态名称
        self.bot = bot    # MapleStoryAutoBot 引用
```

### 方法说明

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `__init__` | `name: str`, `bot: MapleStoryAutoBot` | - | 初始化状态 |
| `on_enter` | - | - | 进入状态时调用 |
| `on_exit` | - | - | 退出状态时调用 |
| `check_transitions` | - | `str` 或 `None` | 检查转换条件，返回目标状态名或None |
| `do_state_stuff` | - | - | 执行状态逻辑（已弃用，使用 `on_frame`） |

### 使用示例

```python
from src.states.base_state import State

class CustomState(State):
    def on_enter(self):
        print(f"进入 {self.name} 状态")
    
    def on_exit(self):
        print(f"退出 {self.name} 状态")
    
    def check_transitions(self):
        if some_condition:
            return "next_state"
        return None
    
    def on_frame(self):
        # 每帧执行的逻辑
        pass
```

---

## hunting.py - 狩猎状态

### 文件信息
- **路径**: `src/states/hunting.py`
- **行数**: 41 行
- **作用**: 主要狩猎状态，根据路线图和怪物检测自动打怪

### HuntingState 类

继承自 `State`，是机器人的默认工作状态。

### 工作流程

```
on_frame() 每帧执行:
    │
    ├── 1. update_cmd_by_route()      # 根据路线图更新移动命令
    │
    ├── 2. check_reach_goal()         # 检查是否到达目标点
    │
    ├── 3. update_cmd_by_mob_detection()  # 根据怪物检测更新攻击命令
    │
    ├── 4. is_player_stuck()          # 检查是否卡住
    │       └── update_cmd_by_random()    # 如果卡住，随机移动
    │
    └── 5. kb.set_command(...)        # 发送组合命令到键盘控制器
```

### 状态转换

| 条件 | 目标状态 |
|------|----------|
| `is_rune_enable()` 或 `is_rune_warning()` | `finding_rune` |

### 命令格式

状态通过 `kb.set_command()` 发送命令，格式为：
```
"{cmd_move_x} {cmd_move_y} {cmd_action}"
```

示例: `"left none attack"`, `"right up jump"`

---

## patrol.py - 巡逻状态

### 文件信息
- **路径**: `src/states/patrol.py`
- **行数**: 61 行
- **作用**: 简单的左右巡逻模式，不依赖路线图

### PatrolState 类

适用于简单地图或不需要复杂路线的场景。

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_patrol_to_left` | `bool` | 当前巡逻方向（True=向左） |
| `patrol_turn_point_cnt` | `int` | 转向计数器 |

### 工作流程

```
on_frame() 每帧执行:
    │
    ├── 1. 获取玩家位置比例 (x / 画面宽度)
    │
    ├── 2. 检查是否需要转向
    │       ├── 向左移动 && 位置 < left_ratio  → 增加转向计数
    │       └── 向右移动 && 位置 > right_ratio → 增加转向计数
    │
    ├── 3. 如果转向计数 > 阈值，反转方向
    │
    ├── 4. 更新移动命令 (left/right)
    │
    ├── 5. update_cmd_by_mob_detection()  # 怪物检测攻击
    │
    ├── 6. 定期攻击 (patrol_attack_interval)
    │
    ├── 7. is_player_stuck() → update_cmd_by_random()
    │
    └── 8. kb.set_command(...)
```

### 配置参数

```yaml
patrol:
  range: [0.2, 0.8]           # 巡逻范围 [左边界比例, 右边界比例]
  turn_point_thres: 5         # 转向阈值
  patrol_attack_interval: 2.0 # 巡逻攻击间隔（秒）
```

---

## finding_rune.py - 寻找符文状态

### 文件信息
- **路径**: `src/states/finding_rune.py`
- **行数**: 73 行
- **作用**: 在地图中寻找符文位置，同时继续狩猎

### FindingRuneState 类

当检测到符文启用消息时，进入此状态开始寻找符文。

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_attack` | `bool` | 是否启用攻击（符文警告时禁用） |

### 方法

| 方法 | 说明 |
|------|------|
| `disable_attack()` | 禁用攻击 |
| `enable_attack()` | 启用攻击 |

### 工作流程

```
on_enter():
    └── rune_solver.reset()  # 重置符文解谜器

on_frame():
    │
    ├── 1. update_rune_location()     # 更新符文位置
    │
    ├── 2. 检查HP减少 → enable_attack()
    │
    ├── 3. 检查符文警告 → disable_attack()
    │
    ├── 4. update_cmd_by_route()      # 路线移动
    │
    ├── 5. check_reach_goal()         # 目标检查
    │
    ├── 6. if is_attack: update_cmd_by_mob_detection()
    │
    ├── 7. is_player_stuck() → update_cmd_by_random()
    │
    └── 8. kb.set_command(...)
```

### 状态转换

| 条件 | 目标状态 |
|------|----------|
| `is_in_rune_game()` | `solving_rune` |
| `loc_rune is not None` | `near_rune` |

---

## near_rune.py - 接近符文状态

### 文件信息
- **路径**: `src/states/near_rune.py`
- **行数**: 60 行
- **作用**: 接近符文位置并尝试触发符文

### NearRuneState 类

当找到符文位置后，引导玩家移动到符文附近并触发。

### 工作流程

```
on_exit():
    └── rune_solver.reset()  # 退出时重置

on_frame():
    │
    ├── 1. update_rune_location()     # 持续更新符文位置
    │
    ├── 2. 计算与符文的距离 (dx, dy)
    │
    ├── 3. 如果足够接近:
    │       └── press_key("up", 0.02)  # 按上触发符文
    │
    ├── 4. update_cmd_by_route()      # 继续移动
    │
    ├── 5. check_reach_goal()
    │
    └── 6. kb.set_command(...)
```

### 触发条件

```python
dx < cfg["rune_find"]["rune_trigger_distance_x"]  # 默认 30
dy < cfg["rune_find"]["rune_trigger_distance_y"]  # 默认 15
```

### 状态转换

| 条件 | 目标状态 |
|------|----------|
| `is_in_rune_game()` | `solving_rune` |
| 超时 (`near_rune_duration`) | `finding_rune` |

---

## solving_rune.py - 解决符文状态

### 文件信息
- **路径**: `src/states/solving_rune.py`
- **行数**: 25 行
- **作用**: 解决符文方向键小游戏

### SolvingRuneState 类

进入符文小游戏后，自动识别并输入正确的方向键序列。

### 工作流程

```
on_enter():
    ├── kb.set_command("none none none")  # 停止所有移动
    ├── kb.release_all_key()              # 释放所有按键
    └── rune_solver.reset()               # 重置解谜器

on_frame():
    └── rune_solver.solve_rune(img_frame, img_frame_debug)
        # 识别方向箭头并自动输入
```

### 状态转换

| 条件 | 目标状态 |
|------|----------|
| `!is_in_rune_game()` | `hunting` |

### 注意事项

- 进入此状态时会停止所有键盘输入，防止干扰符文解谜
- 符文解谜完成后自动返回狩猎状态

---

## auxiliary.py - 辅助状态

### 文件信息
- **路径**: `src/states/auxiliary.py`
- **行数**: 16 行
- **作用**: 辅助/空闲状态，不执行任何操作

### AuxiliaryState 类

用于辅助模式或需要暂停机器人操作的场景。

```python
class AuxiliaryState(State):
    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def check_transitions(self):
        return None  # 不自动转换

    def on_frame(self):
        pass  # 不执行任何操作
```

### 使用场景

- 多账号挂机时的辅助角色
- 需要暂停机器人但保持监控
- 手动控制模式

---

## 扩展状态指南

### 创建新状态

1. 继承 `State` 基类
2. 实现必要的方法
3. 在 `FiniteStateMachine` 中注册

```python
# src/states/custom_state.py
from src.states.base_state import State

class CustomState(State):
    def __init__(self, name, bot):
        super().__init__(name, bot)
        # 初始化自定义属性
    
    def on_enter(self):
        # 进入状态时的设置
        pass
    
    def on_exit(self):
        # 退出状态时的清理
        pass
    
    def check_transitions(self):
        # 检查转换条件
        if self.bot.some_condition:
            return "target_state"
        return None
    
    def on_frame(self):
        # 每帧执行的逻辑
        self.bot.update_cmd_by_route()
        self.bot.kb.set_command(...)
```

### 注册新状态

```python
# 在 MapleStoryAutoLevelUp.py 中
from src.states.custom_state import CustomState

# 在 __init__ 中添加
self.fsm.add_state(CustomState("custom", self))
```
