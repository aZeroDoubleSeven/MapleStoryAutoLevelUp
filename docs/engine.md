# Engine 模块文档

`src/engine/` 目录包含机器人的核心引擎逻辑。

---

## 1. MapleStoryAutoLevelUp.py

### 概述
这是整个机器人的核心类 `MapleStoryAutoBot`，负责协调所有模块的工作。

### 类: MapleStoryAutoBot

#### 初始化参数
- `args` - 命令行参数对象，包含以下属性：
  - `disable_control` - 是否禁用键盘控制（调试用）
  - `cfg` - 配置文件名称
  - `debug` - 是否启用调试模式
  - `record` - 是否录制视频
  - `disable_viz` - 是否禁用可视化窗口
  - `test_image` - 测试图像路径
  - `init_state` - 初始状态名称
  - `is_ui` - 是否使用UI框架

#### 主要属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `cfg` | dict | 配置字典 |
| `fsm` | FiniteStateMachine | 有限状态机实例 |
| `kb` | KeyBoardController | 键盘控制器 |
| `capture` | GameWindowCapturor | 游戏窗口捕获器 |
| `health_monitor` | HealthMonitor | 健康监控器 |
| `rune_solver` | RuneSolver | 符文解谜器 |
| `profiler` | Profiler | 性能分析器 |
| `img_frame` | np.ndarray | 当前游戏画面 |
| `img_minimap` | np.ndarray | 小地图图像 |
| `loc_player` | tuple | 玩家在游戏窗口中的位置 |
| `loc_player_global` | tuple | 玩家在全局地图中的位置 |
| `monsters` | list | 检测到的怪物列表 |

#### 主要方法

##### `load_config(cfg) -> int`
加载配置并初始化各种资源。
- **参数**: `cfg` - 配置字典
- **返回**: 0 表示成功，-1 表示失败
- **逻辑**:
  1. 初始化反检测系统
  2. 解析颜色代码配置
  3. 加载地图图像和路线图
  4. 加载怪物模板图像
  5. 加载玩家名牌图像
  6. 标准化像素坐标

##### `start()`
启动所有线程和模块。
- 创建键盘控制器
- 创建游戏窗口捕获器
- 启动健康监控线程
- 初始化符文解谜器
- 设置初始状态
- 启动主循环线程

##### `run_once() -> int`
处理一帧游戏画面。
- **返回**: 0 表示成功，-1 表示无效帧
- **逻辑**:
  1. 获取游戏窗口画面
  2. 检测小地图位置
  3. 检测玩家位置
  4. 检查是否需要换频道
  5. 执行当前状态逻辑
  6. 更新调试窗口

##### `get_player_location_by_nametag() -> tuple`
通过名牌检测玩家位置。
- **逻辑**:
  1. 对游戏画面进行预处理（灰度化、白色遮罩等）
  2. 将名牌模板分割成多个部分
  3. 使用模板匹配找到最佳匹配位置
  4. 根据名牌位置计算玩家中心位置

##### `get_player_location_by_party_red_bar() -> tuple`
通过队伍红条检测玩家位置。
- **逻辑**:
  1. 将画面转换为HSV色彩空间
  2. 提取红色区域
  3. 找到符合红条几何特征的轮廓
  4. 根据红条位置计算玩家位置

##### `get_player_location_on_global_map() -> tuple`
获取玩家在全局地图上的位置。
- **逻辑**:
  1. 使用模板匹配将小地图定位到全局地图
  2. 结合玩家在小地图上的位置计算全局位置

##### `get_nearest_color_code() -> tuple`
搜索玩家周围最近的颜色代码指令。
- **返回**: (nearest, nearest_up_down) 两种颜色代码匹配结果
- **逻辑**:
  1. 在玩家周围的搜索范围内扫描
  2. 找到最近的匹配颜色像素
  3. 返回对应的移动指令

##### `get_monsters_in_range(top_left, bottom_right) -> list`
检测指定范围内的怪物。
- **参数**: 检测范围的左上角和右下角坐标
- **返回**: 怪物信息列表
- **检测模式**:
  - `template_free` - 基于黑色轮廓的无模板检测
  - `contour_only` - 仅使用轮廓匹配
  - `grayscale` - 灰度模板匹配
  - `color` - 彩色模板匹配

##### `update_cmd_by_route()`
根据路线图更新移动命令。
- **逻辑**:
  1. 获取最近的颜色代码
  2. 解析颜色代码对应的命令
  3. 处理边缘传送逻辑
  4. 设置移动命令

##### `update_cmd_by_mob_detection()`
根据怪物检测更新攻击命令。
- **逻辑**:
  1. 在攻击范围内搜索怪物
  2. 判断攻击方向
  3. 检查攻击冷却
  4. 设置攻击命令

##### `channel_change()`
执行换频道操作。
- **逻辑**:
  1. 点击游戏菜单
  2. 选择频道
  3. 等待登录按钮出现
  4. 重新登录游戏

##### `is_player_stuck() -> bool`
检查玩家是否卡住。
- **逻辑**:
  1. 比较当前位置与看门狗位置
  2. 如果移动超过阈值则重置看门狗
  3. 如果超时未移动则判定为卡住

#### 使用示例

```python
from argparse import Namespace
from src.engine.MapleStoryAutoLevelUp import MapleStoryAutoBot

# 创建参数
args = Namespace(
    disable_control=False,
    cfg="custom",
    debug=False,
    record=False,
    is_ui=False,
    disable_viz=False,
    test_image='',
    init_state='',
)

# 创建机器人实例
bot = MapleStoryAutoBot(args)

# 加载配置
cfg = load_yaml("config/config_custom.yaml")
bot.load_config(cfg)

# 启动机器人
bot.start()
```

---

## 2. FiniteStateMachine.py

### 概述
有限状态机（FSM）实现，用于管理机器人的不同行为状态。

### 类: FiniteStateMachine

#### 属性
| 属性 | 类型 | 说明 |
|------|------|------|
| `states` | dict | 状态名称到状态实例的映射 |
| `transitions` | dict | 状态名称到合法目标状态集合的映射 |
| `state` | State | 当前状态 |
| `t_last_transition` | float | 上次状态转换时间 |

#### 方法

##### `add_state(state: State)`
添加状态到状态机。

##### `add_transition(from_state, to_state)`
添加状态转换规则。

##### `set_init_state(state_name)`
设置初始状态并调用 `on_enter()`。

##### `transit_to(to_state_name)`
转换到指定状态。
- 忽略频繁转换（1秒内）
- 调用当前状态的 `on_exit()`
- 调用新状态的 `on_enter()`

##### `do_state_stuff()`
执行当前状态的每帧逻辑。
- 调用 `state.on_frame()`
- 检查状态转换条件

#### 状态转换图

```
                    ┌──────────────┐
                    │   Hunting    │◄────────────────┐
                    └──────┬───────┘                 │
                           │                          │
            检测到符文消息 │                          │ 符文解决完成
                           ▼                          │
                    ┌──────────────┐                 │
                    │ FindingRune  │                 │
                    └──────┬───────┘                 │
                           │                          │
              发现符文图标 │ ┌────────────┐          │
                           ▼ │            │          │
                    ┌──────────────┐      │          │
                    │   NearRune   │──────┘          │
                    └──────┬───────┘   超时          │
                           │                          │
              进入符文小游戏│                          │
                           ▼                          │
                    ┌──────────────┐                 │
                    │ SolvingRune  │─────────────────┘
                    └──────────────┘
```

---

## 3. HealthMonitor.py

### 概述
独立的健康监控线程，负责监控玩家的HP/MP/EXP并自动使用药水。

### 类: HealthMonitor

#### 初始化
```python
health_monitor = HealthMonitor(cfg, kb_controller)
```

#### 属性
| 属性 | 类型 | 说明 |
|------|------|------|
| `hp_percent` | float | 当前HP百分比 |
| `mp_percent` | float | 当前MP百分比 |
| `exp_percent` | float | 当前EXP百分比 |
| `loc_size_bars` | list | HP/MP/EXP条的位置和大小 |
| `is_need_force_heal` | bool | 是否需要强制回血 |

#### 主要方法

##### `start()`
启动健康监控线程。

##### `stop()`
停止健康监控线程。

##### `update_frame(img_frame)`
更新游戏画面帧（由主线程调用）。

##### `get_hp_mp_exp_percent() -> tuple`
获取当前HP、MP、EXP百分比。
- **逻辑**:
  1. 检测白色边框的血条区域
  2. 计算每个血条的填充比例
  3. 返回三个百分比值

##### `_heal()`
执行回血操作。

##### `_add_mp()`
执行回魔操作。

#### 工作流程
1. 以固定帧率（默认10fps）运行
2. 从当前画面中检测HP/MP条
3. 当HP/MP低于阈值时触发喝药
4. 支持强制回血模式
5. 支持药水用尽时返回城镇

---

## 4. RuneSolver.py

### 概述
符文解谜器，用于检测和解决游戏中的符文谜题。

### 类: RuneSolver

#### 初始化
```python
rune_solver = RuneSolver(cfg)
```

#### 属性
| 属性 | 类型 | 说明 |
|------|------|------|
| `img_arrows` | dict | 四个方向的箭头模板图像 |
| `img_rune_warning` | np.ndarray | 符文警告图像 |
| `img_runes` | list | 符文图标模板 |
| `loc_rune` | tuple | 符文位置 |

#### 主要方法

##### `is_rune_warning(img, img_debug) -> bool`
检查是否出现符文警告图标。

##### `is_rune_enable(img, img_debug) -> bool`
检查是否出现符文启用消息。

##### `is_in_rune_game(img, img_debug) -> bool`
检查是否进入符文小游戏。
- 使用 HSV 二值化检测箭头圆圈
- 使用霍夫圆检测

##### `update_rune_location(img, img_debug, loc_player)`
更新符文在画面中的位置。
- **逻辑**:
  1. 在玩家周围搜索符文图标
  2. 使用模板匹配检测符文部件
  3. 验证部件的几何关系
  4. 更新符文位置

##### `solve_rune(img, img_debug)`
自动解决符文谜题。
- **逻辑**:
  1. 检测当前高亮的箭头
  2. 使用模板匹配确定箭头方向
  3. 模拟按键输入对应方向
  4. 等待游戏响应

##### `arrow_hsv_binarized(img, low_hsv, high_hsv) -> np.ndarray`
使用HSV阈值进行二值化处理。

---

## 5. Profiler.py

### 概述
性能分析器，用于调试和优化性能问题。

### 类: Profiler

#### 初始化
```python
profiler = Profiler(cfg)
```

#### 方法

##### `start()`
开始一帧的计时。

##### `mark(label)`
标记某个代码段的结束，记录耗时。

##### `report() -> str`
生成性能报告，显示各代码段的平均耗时和占比。

#### 使用示例
```python
profiler.start()

# 图像预处理
img = process_image()
profiler.mark("Image Preprocessing")

# 玩家检测
player_loc = detect_player()
profiler.mark("Player Detection")

# 打印报告
print(profiler.report())
```

输出示例：
```
Image Preprocessing : 0.0120s avg (40.0%)
Player Detection    : 0.0080s avg (26.7%)
Monster Detection   : 0.0100s avg (33.3%)
AVG FRAME TIME      : 0.0300s over 100 frames
AVG FPS             : 33.33
```
