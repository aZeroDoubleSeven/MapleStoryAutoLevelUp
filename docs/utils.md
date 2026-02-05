# Utils 模块文档

> 路径: `src/utils/`

本模块提供项目中使用的各种工具函数和类。

---

## 目录

1. [模块概述](#模块概述)
2. [common.py - 通用工具函数](#commonpy---通用工具函数)
3. [logger.py - 日志系统](#loggerpy---日志系统)
4. [anti_detect.py - 反检测系统](#anti_detectpy---反检测系统)
5. [global_var.py - 全局变量](#global_varpy---全局变量)
6. [ui.py - UI工具函数](#uipy---ui工具函数)

---

## 模块概述

Utils 模块包含以下功能：

- **common.py** - 图像处理、配置管理、通用工具
- **logger.py** - 统一日志系统
- **anti_detect.py** - 人性化行为模拟
- **global_var.py** - 全局常量
- **ui.py** - PySide6 UI辅助函数

---

## common.py - 通用工具函数

### 文件信息
- **路径**: `src/utils/common.py`
- **行数**: 848 行
- **作用**: 提供图像处理、配置管理等核心工具函数

### 平台检测

```python
from src.utils.common import is_mac, is_windows

if is_mac():
    # macOS 特定代码
elif is_windows():
    # Windows 特定代码
```

| 函数 | 返回值 | 说明 |
|------|--------|------|
| `is_mac()` | `bool` | 是否为 macOS |
| `is_windows()` | `bool` | 是否为 Windows |

### YAML 配置管理

#### 加载配置

```python
from src.utils.common import load_yaml, load_yaml_with_comments

# 简单加载
cfg = load_yaml("config/config_default.yaml")

# 带注释加载（用于UI）
data, comments, section_comments = load_yaml_with_comments("config/config_default.yaml")
```

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `load_yaml(path)` | 路径 | `dict` | 加载YAML配置 |
| `load_yaml_with_comments(path)` | 路径 | `(dict, dict, dict)` | 加载带注释的YAML |
| `save_yaml(data, path)` | 数据, 路径 | - | 保存YAML配置 |

#### 配置合并

```python
from src.utils.common import override_cfg, get_cfg_diff

# 合并配置（覆盖）
cfg = override_cfg(base_cfg, custom_cfg)

# 获取配置差异
diff = get_cfg_diff(base_cfg, current_cfg)
```

| 函数 | 说明 |
|------|------|
| `override_cfg(base, override)` | 递归覆盖配置 |
| `get_cfg_diff(base, current)` | 获取配置差异 |
| `normalize(value)` | 归一化值（用于比较） |
| `convert_tuples_to_lists(obj)` | 元组转列表 |
| `convert_lists_to_tuples(obj)` | 列表转元组 |

### 图像处理

#### 加载图像

```python
from src.utils.common import load_image
import cv2

img = load_image("path/to/image.png")
img_gray = load_image("path/to/image.png", mode=cv2.IMREAD_GRAYSCALE)
```

#### 模板匹配

```python
from src.utils.common import find_pattern_sqdiff, get_mask

# 获取模板掩码
mask = get_mask(template, ignore_color=(255, 255, 255))

# 模板匹配
loc, score, is_local = find_pattern_sqdiff(
    img,                    # 搜索图像
    template,               # 模板图像
    last_result=(100, 100), # 上次位置（加速）
    mask=mask,              # 掩码
    local_search_radius=50, # 局部搜索范围
    global_threshold=0.4    # 全局阈值
)
```

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `find_pattern_sqdiff(...)` | 见下 | `(loc, score, bool)` | SQDIFF_NORMED模板匹配 |
| `get_mask(img, color)` | 图像, 颜色 | `numpy.ndarray` | 生成掩码 |
| `pad_to_size(img, size)` | 图像, 尺寸 | `numpy.ndarray` | 填充到指定尺寸 |

`find_pattern_sqdiff` 参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `img` | `ndarray` | - | 搜索图像 |
| `img_pattern` | `ndarray` | - | 模板图像 |
| `last_result` | `tuple` | `None` | 上次匹配位置 |
| `mask` | `ndarray` | `None` | 模板掩码 |
| `local_search_radius` | `int` | `50` | 局部搜索范围 |
| `global_threshold` | `float` | `0.4` | 全局搜索阈值 |

#### NMS (非极大值抑制)

```python
from src.utils.common import nms, nms_matches, get_iou

# 对怪物检测结果应用NMS
monsters = [
    {"position": (100, 100), "size": (50, 50), "score": 0.9},
    {"position": (110, 100), "size": (50, 50), "score": 0.8},
]
filtered = nms(monsters, iou_threshold=0.3)

# 计算IoU
iou = get_iou(box1, box2)
```

| 函数 | 说明 |
|------|------|
| `nms(monsters, iou_threshold)` | 怪物检测NMS |
| `nms_matches(matches, iou_thresh)` | 模板匹配NMS |
| `get_iou(box1, box2)` | 计算交并比 |

#### 绘图函数

```python
from src.utils.common import draw_rectangle, screenshot

# 绘制矩形
draw_rectangle(img, top_left=(100, 100), size=(50, 50), 
               color=(0, 255, 0), text="Monster")

# 保存截图
screenshot(img, suffix="debug")
```

### 小地图处理

```python
from src.utils.common import (
    get_minimap_loc_size,
    get_player_location_on_minimap,
    get_all_other_player_locations_on_minimap
)

# 检测小地图位置
x, y, w, h = get_minimap_loc_size(img_frame)

# 获取玩家位置
loc = get_player_location_on_minimap(img_minimap, player_color=(136, 255, 255))

# 获取其他玩家位置
others = get_all_other_player_locations_on_minimap(img_minimap, red_bgr=(0, 0, 255))
```

| 函数 | 返回值 | 说明 |
|------|--------|------|
| `get_minimap_loc_size(img)` | `(x, y, w, h)` 或 `None` | 获取小地图位置和尺寸 |
| `get_player_location_on_minimap(img, color)` | `(x, y)` 或 `None` | 获取玩家位置 |
| `get_all_other_player_locations_on_minimap(img)` | `list[(x, y)]` | 获取其他玩家位置 |

### HP/MP/EXP 条

```python
from src.utils.common import get_bar_percent

# 获取血条百分比
hp_percent = get_bar_percent(img_hp_bar)  # 返回 0-100
```

### HSV 颜色转换

```python
from src.utils.common import to_opencv_hsv, to_standard_hsv

# 标准HSV (H:0-360, S:0-100, V:0-100) → OpenCV HSV (H:0-179, S:0-255, V:0-255)
opencv_hsv = to_opencv_hsv((180, 50, 50))

# OpenCV HSV → 标准HSV
std_hsv = to_standard_hsv((90, 127, 127))
```

### 窗口操作

```python
from src.utils.common import (
    get_game_window_title_by_token,
    activate_game_window,
    resize_window,
    click_in_game_window
)

# 查找窗口标题
title = get_game_window_title_by_token("MapleStory")

# 激活窗口
activate_game_window(title)

# 调整窗口大小
resize_window(title, width=1296, height=759)

# 在游戏窗口中点击
click_in_game_window(title, (640, 360))
```

### 邮件功能

```python
from src.utils.common import send_email, check_inbox

# 发送邮件
send_email(
    email_addr="sender@gmail.com",
    password="app_password",
    to="receiver@gmail.com",
    subject="Alert",
    body="Message",
    attachment_path="screenshot.png"
)

# 检查收件箱
reply = check_inbox(email_addr, password, token="Subject Token")
```

### 其他工具函数

| 函数 | 说明 |
|------|------|
| `mask_route_colors(img_map, img_route, color_code)` | 根据路线颜色遮罩图像 |
| `is_img_16_to_9(img, cfg)` | 检查图像是否为16:9 |
| `normalize_pixel_coordinate(coord, window_size)` | 标准化像素坐标 |
| `debug_minimap_colors(img, color)` | 调试小地图颜色 |

---

## logger.py - 日志系统

### 文件信息
- **路径**: `src/utils/logger.py`
- **行数**: 59 行
- **作用**: 提供统一的日志记录系统

### MSLogger 类

```python
from src.utils.logger import logger

# 使用全局logger
logger.info("信息消息")
logger.warning("警告消息")
logger.error("错误消息")
logger.debug("调试消息")

# 设置日志级别
import logging
logger.set_level(logging.DEBUG)
```

### 日志输出

日志同时输出到：
1. 控制台
2. 文件：`log/MSBot_YYYY-MM-DD_HH-MM-SS.log`

### 日志格式

```
[2024-01-15 12:30:45] INFO: 消息内容
```

### 添加自定义Handler

```python
from src.utils.logger import logger
import logging

# 添加自定义handler
custom_handler = logging.FileHandler("custom.log")
logger.addHandler(custom_handler)
```

---

## anti_detect.py - 反检测系统

### 文件信息
- **路径**: `src/utils/anti_detect.py`
- **行数**: 377 行
- **作用**: 提供人类化行为模拟，降低被检测风险

### 核心功能

1. **按键时长随机化** - 正态分布模拟人类按键
2. **动作延迟随机化** - 模拟人类反应时间
3. **冷却时间抖动** - 避免固定间隔
4. **微停顿模拟** - 模拟思考/分神
5. **闲置行为模拟** - 模拟走神
6. **疲劳系统** - 长时间运行后反应变慢

### HumanBehavior 类

```python
from src.utils.anti_detect import get_human_behavior, init_anti_detect

# 使用配置初始化
init_anti_detect(cfg)

# 获取全局实例
human = get_human_behavior()

# 获取随机按键时长
duration = human.get_key_duration()  # 默认约0.05秒

# 获取动作延迟
delay = human.get_action_delay()

# 随机化冷却时间
cooldown = human.randomize_cooldown(base_cooldown, 'attack')  # ±15%
cooldown = human.randomize_cooldown(base_cooldown, 'buff')    # ±20%
cooldown = human.randomize_cooldown(base_cooldown, 'potion')  # ±25%

# 微停顿检查
should_pause, pause_duration = human.should_micro_pause()
if should_pause:
    time.sleep(pause_duration)

# 闲置检查
should_idle, idle_duration = human.should_idle()
if should_idle:
    time.sleep(idle_duration)

# 更新疲劳度
human.update_fatigue()

# 添加移动噪声
noisy_x, noisy_y = human.add_movement_noise(100, 100, noise_level=3)

# 生成人类化移动路径
path = human.get_human_like_path(start=(0, 0), end=(100, 100), steps=10)
```

### 配置参数

```yaml
anti_detect:
  # 按键时长随机化
  key_duration_base: 0.05       # 基础按键时长（秒）
  key_duration_variance: 0.03   # 时长变化范围
  
  # 动作延迟随机化
  action_delay_min: 0.02        # 最小动作延迟
  action_delay_max: 0.08        # 最大动作延迟
  
  # 攻击冷却变化
  attack_cooldown_variance: 0.15  # ±15%
  
  # 微停顿设置
  micro_pause_probability: 0.05   # 5% 概率
  micro_pause_duration_min: 0.1
  micro_pause_duration_max: 0.3
  
  # 闲置行为设置
  idle_probability: 0.01          # 1% 概率
  idle_duration_min: 0.5
  idle_duration_max: 2.0
  
  # Buff技能时间变化
  buff_timing_variance: 0.2       # ±20%
  
  # 喝药时间变化
  potion_timing_variance: 0.25    # ±25%
  
  # 功能开关
  enable_random_delays: true
  enable_micro_pauses: true
  enable_idle_behavior: true
  enable_typing_variance: true
```

### TimingRandomizer 类

时间随机化工具类。

```python
from src.utils.anti_detect import TimingRandomizer

# 数值抖动
value = TimingRandomizer.jitter(1.0, variance_percent=0.15)  # 1.0 ± 15%

# 带抖动的睡眠
TimingRandomizer.sleep_with_jitter(1.0, variance_percent=0.2)

# 获取随机间隔（Beta分布，偏向中间值）
interval = TimingRandomizer.get_random_interval(0.5, 1.5)
```

---

## global_var.py - 全局变量

### 文件信息
- **路径**: `src/utils/global_var.py`
- **行数**: 4 行
- **作用**: 定义全局常量

### 常量

```python
from src.utils.global_var import WINDOW_WORKING_SIZE

# 标准工作窗口尺寸 (宽度, 高度)
WINDOW_WORKING_SIZE = (1296, 700)
```

---

## ui.py - UI工具函数

### 文件信息
- **路径**: `src/utils/ui.py`
- **行数**: 199 行
- **作用**: PySide6 UI辅助函数和自定义组件

### 输入验证

```python
from src.utils.ui import validate_numerical_input, create_error_label

# 创建错误标签
error_label = create_error_label()

# 验证数值输入
is_valid = validate_numerical_input(
    input_str="50",
    error_label=error_label,
    val_lowest=0,
    val_highest=100
)
```

### 组件创建

```python
from src.utils.ui import create_field, clear_debug_canvas

# 创建标签-输入对
container = create_field("标签:", QLineEdit())

# 清空画布
clear_debug_canvas(my_canvas)
```

### SingleKeyEdit 类

单键输入编辑框，防止输入组合键。

```python
from src.utils.ui import SingleKeyEdit

key_edit = SingleKeyEdit()
key_edit.set_key("A")      # 设置按键
key = key_edit.get_key()   # 获取按键 ("a")
```

### QtLogHandler 类

将日志输出到Qt界面。

```python
from src.utils.ui import QtLogHandler

handler = QtLogHandler()
handler.log_signal.connect(on_log)  # (message: str, level: int)
logger.addHandler(handler)
```

### create_advance_setting_gbox 函数

动态创建高级设置组件。

```python
from src.utils.ui import create_advance_setting_gbox

gbox = create_advance_setting_gbox(
    title="system",
    cfg=cfg,
    comments=comments,
    comments_section=section_comments
)
```

支持的值类型：
- `bool` → `QCheckBox`
- `int/float` → `QLineEdit` (带验证器)
- `list/tuple` → 多个 `QLineEdit`
- `str` (带 "Options:" 注释) → `QComboBox`
- `str` (普通) → `QLineEdit`

---

## 使用示例

### 完整配置加载流程

```python
from src.utils.common import load_yaml, override_cfg, is_mac
from src.utils.logger import logger
from src.utils.anti_detect import init_anti_detect

# 加载基础配置
cfg = load_yaml("config/config_default.yaml")

# 加载平台配置
if is_mac():
    cfg = override_cfg(cfg, load_yaml("config/config_macOS.yaml"))

# 加载自定义配置
try:
    cfg = override_cfg(cfg, load_yaml("config/config_custom.yaml"))
except FileNotFoundError:
    logger.warning("未找到自定义配置，使用默认配置")

# 初始化反检测
init_anti_detect(cfg)
```

### 图像处理流程

```python
from src.utils.common import (
    load_image, get_minimap_loc_size, 
    get_player_location_on_minimap, nms
)

# 加载图像
img = load_image("screenshot.png")

# 获取小地图
result = get_minimap_loc_size(img)
if result:
    x, y, w, h = result
    img_minimap = img[y:y+h, x:x+w]
    
    # 获取玩家位置
    player_loc = get_player_location_on_minimap(img_minimap)
    
# 怪物检测后应用NMS
monsters_filtered = nms(monsters_detected, iou_threshold=0.3)
```
