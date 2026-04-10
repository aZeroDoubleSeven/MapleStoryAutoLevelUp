# Arduino HID UI 界面使用指南

本文档详细说明如何在 MapleStory AutoLevelUp 的图形界面 (GUI) 中使用和监控 Arduino HID 硬件输入系统。

## 1. 启用方式

在使用 UI 监控之前，必须先在配置文件中启用 Arduino HID 后端。

1. 打开或创建 `config/config_custom.yaml`
2. 修改 `anti_detect` 部分如下：

```yaml
anti_detect:
  # 将输入后端设置为 arduino_hid
  input_backend: "arduino_hid"

  arduino:
    port: ""              # 留空自动检测（如需要指定：COM5）
    auto_detect: true     # 启用自动检测
    baudrate: 115200      # 波特率（默认 115200）
    timeout: 1.0          # 超时时间
    enable_batch: true    # 启用批处理（推荐开启，显著降低延迟）
```

3. 重新启动程序：`python -m src.main`

## 2. 界面概览

程序启动后，点击主界面上方的 **"Arduino HID"** 标签页进入监控面板。

该面板主要分为两个区域：
1. **连接状态区域 (顶部)**：显示实时硬件连接状态
2. **日志区域 (底部)**：显示详细的通信日志和错误信息

## 3. 连接状态区域

这里显示了 Arduino 设备的实时健康状况。

| 项目 | 说明 | 正常状态 |
|------|------|----------|
| **状态指示灯** | ● 绿色: 已连接<br>● 灰色: 未连接<br>● 橙色: 连接/重连中<br>● 红色: 错误 | **● 已连接** |
| **端口** | 当前连接的 COM 端口号 | 如 `COM5` |
| **设备** | 设备识别 ID | 如 `MAPLE_HID_V1` |
| **延迟** | 往返通信延迟 (Round-trip time) | `< 15ms` (开启批处理时) |
| **统计** | 命令总数 / 错误总数 / 平均延迟 | 错误数应保持为 0 |

### 控制按钮

- **重新连接**: 当连接断开或出现错误时，点击此按钮尝试重新建立连接。
- **断开连接**: 暂时断开与设备的连接（此时机器人将无法执行按键操作）。

## 4. 日志监控功能

日志区域包含两个标签页：**命令日志** 和 **错误日志**。

### 4.1 命令日志 (Command Log)

实时显示计算机与 Arduino 之间的每一次通信。

**颜色编码：**
- **🔵 TX (发送)**: 电脑发送给 Arduino 的命令
  - 格式: `TX: <命令> -> <响应> (<延迟>ms)`
- **🟢 RX (接收)**: Arduino 返回的响应
- **🔴 ERR (错误)**: 通信错误

**工具栏功能：**
- **过滤**: 可选择只查看 "发送"、"接收" 或 "错误"
- **清空**: 清除当前屏幕上的日志
- **暂停**: 暂停日志滚动（方便查看快速刷新的日志），不影响后台记录

### 4.2 错误日志 (Error Log)

专门记录运行过程中发生的异常情况，如超时、校验错误或设备断开。

- 如果此面板出现内容，说明硬件通信存在不稳定性。
- 常见错误：`SerialException` (设备断开), `Timeout` (响应超时)。

## 5. UI 初始化流程

### 启动顺序

Arduino HID 面板的初始化流程如下：

```
1. 程序启动
   ↓
2. UI 初始化 → setup_arduino_hid_tab()
   ↓ （此时 Arduino 后端尚未初始化，面板显示"未连接"）
3. 用户点击 "Start" 按钮
   ↓
4. start_bot() → init_input_backend()
   ↓ （Arduino HID 后端被初始化并尝试连接）
5. refresh_arduino_panel() → 更新面板引用
   ↓
6. 切换到 "Arduino HID" 标签页
   ↓ （此时应显示"已连接"）
```

### 为什么初始显示"未连接"？

这是正常现象。Arduino HID 后端的初始化发生在用户点击 **Start** 按钮之后，因为：

1. 输入后端需要在加载用户配置后才初始化
2. 配置中可能指定了不同的输入后端（如 ctypes_raw）
3. **代码已优化**：即使使用其他输入后端，Arduino HID 面板仍会显示连接状态

### 关键代码变更

**AutoBotController.py - start_bot() 方法新增：**

```python
def start_bot(self, cfg_path):
    # ... 原有代码 ...
    self.auto_bot.start()

    # 刷新 UI 的 Arduino HID 面板引用（在输入后端初始化完成后）
    if self.ui:
        self.ui.refresh_arduino_panel()

    return 0
```

**ui.py - 新增 refresh_arduino_panel() 方法：**

```python
def refresh_arduino_panel(self):
    '''刷新 Arduino HID 面板的后端引用'''
    if hasattr(self, 'arduino_hid_panel'):
        from src.input.InputBackend import get_arduino_backend
        arduino_backend = get_arduino_backend()
        if arduino_backend:
            self.arduino_hid_panel.set_backend(arduino_backend)
            logger.info("[UI] Arduino HID panel backend refreshed")
```

**InputBackend.py - init_input_backend() 新增逻辑：**

```python
def init_input_backend(cfg: dict) -> InputBackend:
    # 始终尝试初始化 Arduino HID 后端（用于 UI 显示状态）
    # 即使配置了其他后端，Arduino 面板也能显示连接状态
    if _arduino_backend is None:
        try:
            from src.input.ArduinoHIDBackend import create_arduino_hid_backend
            _arduino_backend = create_arduino_hid_backend(cfg)
        except Exception as e:
            logger.debug(f"[InputBackend] 初始化Arduino后端失败: {e}")
            _arduino_backend = None
    # ... 其余代码 ...
```

## 6. 常见状态分析

### 状态：连接中... (橙色) 长时间不消失
- **原因**: 找不到 Arduino 设备或端口被占用。
- **解决**:
  1. 检查 USB 线连接。
  2. 确认 Arduino IDE 未占用该端口。
  3. 尝试拔插设备，然后点击 "重新连接"。
  4. 使用 `python tests/test_arduino_hid.py --list` 查看当前端口。

### 状态：已连接 但 延迟显示 "-"
- **原因**: 尚未发送任何命令，因此无法计算延迟。
- **解决**: 启动机器人 (F1) 开始挂机，或者进行按键测试，延迟数据会自动更新。

### 日志显示大量 "Resyncing..."
- **原因**: 通信不同步，可能是波特率不匹配或数据线质量差。
- **解决**:
  1. 检查 `config_custom.yaml` 中的波特率是否为 115200。
  2. 更换高质量 USB 数据线。

## 7. 性能调优

在 UI 中观察 **平均延迟** 数据：

- **正常范围**: 5ms - 20ms
- **性能警告**: > 30ms

**如何降低延迟？**
1. 确保在配置中开启 `enable_batch: true`。
2. 将 Arduino 连接到 USB 3.0 接口（通常供电更稳）。
3. 减少日志刷新频率（UI 日志仅用于调试，实际挂机时可以切回 "Main" 标签页以节省资源）。
