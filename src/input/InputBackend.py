'''
InputBackend - 键盘输入后端抽象层

此模块提供多种输入后端以规避反作弊检测：

1. ctypes_raw (推荐，无需重启)
   - 直接调用 Windows API
   - 添加硬件扫描码 (Hardware Scancode)
   - 模拟真实键盘的输入特征
   - 无需安装驱动，无需重启电脑

2. interception (效果最好，但需要重启)
   - 使用 Interception 驱动
   - 内核级别的键盘模拟
   - 需要安装驱动并重启电脑

3. pyautogui (默认，容易被检测)
   - 使用 Windows SendInput API
   - 会被标记为"注入输入"
   - 不推荐用于有反作弊的游戏

工作原理：
---------
游戏反作弊系统检测脚本输入的主要方法：

1. LLKHF_INJECTED 标志
   - Windows 会自动给 SendInput 添加注入标志
   - 反作弊可以检查这个标志判断是否为脚本

2. 缺少硬件扫描码 (Hardware Scancode)
   - 真实键盘输入包含硬件扫描码
   - pyautogui 默认不提供扫描码

3. 时序分析
   - 脚本的按键间隔过于规律
   - 需要添加随机延迟模拟人类行为

ctypes_raw 后端通过以下方式规避检测：
- 使用 KEYEVENTF_SCANCODE 标志
- 提供硬件扫描码
- 配合 anti_detect 模块的随机化
'''

import time
import random
from abc import ABC, abstractmethod
from src.utils.logger import logger
from src.utils.common import is_mac

# ============================================================
# 硬件扫描码映射表
# 这些是键盘硬件层面的扫描码，与虚拟键码 (VK) 不同
# 使用扫描码可以让输入看起来更像真实硬件产生的
# ============================================================
SCAN_CODES = {
    # 方向键 (扩展键，需要 KEYEVENTF_EXTENDEDKEY 标志)
    'left': 0x4B,
    'right': 0x4D,
    'up': 0x48,
    'down': 0x50,
    
    # 字母键
    'a': 0x1E, 'b': 0x30, 'c': 0x2E, 'd': 0x20, 'e': 0x12, 'f': 0x21,
    'g': 0x22, 'h': 0x23, 'i': 0x17, 'j': 0x24, 'k': 0x25, 'l': 0x26,
    'm': 0x32, 'n': 0x31, 'o': 0x18, 'p': 0x19, 'q': 0x10, 'r': 0x13,
    's': 0x1F, 't': 0x14, 'u': 0x16, 'v': 0x2F, 'w': 0x11, 'x': 0x2D,
    'y': 0x15, 'z': 0x2C,
    
    # 数字键
    '0': 0x0B, '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05,
    '5': 0x06, '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A,
    
    # 特殊键
    'space': 0x39,
    'enter': 0x1C,
    'escape': 0x01,
    'esc': 0x01,
    'tab': 0x0F,
    'backspace': 0x0E,
    'shift': 0x2A,
    'ctrl': 0x1D,
    'alt': 0x38,
    'capslock': 0x3A,
    
    # 功能键
    'f1': 0x3B, 'f2': 0x3C, 'f3': 0x3D, 'f4': 0x3E,
    'f5': 0x3F, 'f6': 0x40, 'f7': 0x41, 'f8': 0x42,
    'f9': 0x43, 'f10': 0x44, 'f11': 0x57, 'f12': 0x58,
    
    # 其他键
    'home': 0x47,
    'end': 0x4F,
    'insert': 0x52,
    'delete': 0x53,
    'pageup': 0x49,
    'pagedown': 0x51,
}

# 扩展键列表 (这些键需要添加 KEYEVENTF_EXTENDEDKEY 标志)
EXTENDED_KEYS = {'left', 'right', 'up', 'down', 'home', 'end', 
                 'insert', 'delete', 'pageup', 'pagedown'}


class InputBackend(ABC):
    '''
    输入后端的抽象基类
    所有输入后端都必须实现这些方法
    '''
    
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
        '''按下并释放按键，持续指定时间'''
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        '''检查此后端是否可用'''
        pass
    
    def get_name(self) -> str:
        '''获取后端名称'''
        return self.__class__.__name__


class CtypesRawBackend(InputBackend):
    '''
    直接使用 ctypes 调用 Windows API 的输入后端
    
    ★ 推荐使用 - 无需安装驱动，无需重启电脑 ★
    
    原理：
    -----
    1. 直接调用 user32.dll 的 SendInput 函数
    2. 使用 KEYEVENTF_SCANCODE 标志
    3. 提供硬件扫描码 (Hardware Scancode)
    4. 对于扩展键添加 KEYEVENTF_EXTENDEDKEY 标志
    
    优点：
    -----
    - 无需安装额外驱动
    - 无需重启电脑
    - 无需管理员权限（大多数情况）
    - 输入包含硬件扫描码
    
    缺点：
    -----
    - 仍然会有 LLKHF_INJECTED 标志（Windows 限制）
    - 对于非常严格的反作弊可能仍被检测
    
    使用方法：
    --------
    在 config/config_default.yaml 中设置：
    anti_detect:
      input_backend: "ctypes_raw"
    '''
    
    def __init__(self):
        self._available = False
        
        # macOS 不支持此后端
        if is_mac():
            logger.info("[CtypesRawBackend] macOS 不支持此后端")
            return
        
        try:
            import ctypes
            from ctypes import wintypes
            
            self.ctypes = ctypes
            self.user32 = ctypes.windll.user32
            
            # ============================================================
            # 定义 Windows API 所需的结构体
            # 这些结构体定义必须与 Windows SDK 中的定义完全匹配
            # ============================================================
            
            # KEYBDINPUT 结构体 - 键盘输入信息
            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [
                    ("wVk", wintypes.WORD),       # 虚拟键码 (我们设为0，使用扫描码代替)
                    ("wScan", wintypes.WORD),     # 硬件扫描码 (关键！)
                    ("dwFlags", wintypes.DWORD),  # 标志位
                    ("time", wintypes.DWORD),     # 时间戳 (0=系统自动填充)
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))  # 额外信息
                ]
            
            # INPUT 结构体 - 通用输入结构
            class INPUT(ctypes.Structure):
                class _INPUT_UNION(ctypes.Union):
                    _fields_ = [("ki", KEYBDINPUT)]
                _anonymous_ = ("_input",)
                _fields_ = [
                    ("type", wintypes.DWORD),     # 输入类型 (1=键盘)
                    ("_input", _INPUT_UNION)
                ]
            
            self.KEYBDINPUT = KEYBDINPUT
            self.INPUT = INPUT
            
            # Windows API 常量
            self.INPUT_KEYBOARD = 1              # 键盘输入类型
            self.KEYEVENTF_SCANCODE = 0x0008     # 使用扫描码而非虚拟键码
            self.KEYEVENTF_KEYUP = 0x0002        # 按键释放
            self.KEYEVENTF_EXTENDEDKEY = 0x0001  # 扩展键 (方向键等)
            
            self._available = True
            logger.info("[CtypesRawBackend] 初始化成功 - 使用硬件扫描码模式")
            
        except Exception as e:
            logger.warning(f"[CtypesRawBackend] 初始化失败: {e}")
    
    def _send_key_event(self, key: str, key_up: bool = False) -> None:
        '''
        发送键盘事件
        
        参数：
            key: 按键名称（如 'a', 'space', 'left' 等）
            key_up: True=释放按键, False=按下按键
        '''
        if not self._available:
            return
        
        # 获取硬件扫描码
        scan_code = SCAN_CODES.get(key.lower(), 0)
        if scan_code == 0:
            logger.warning(f"[CtypesRawBackend] 未知按键: {key}")
            return
        
        # 构建标志位
        flags = self.KEYEVENTF_SCANCODE  # 使用扫描码模式
        
        if key_up:
            flags |= self.KEYEVENTF_KEYUP  # 添加按键释放标志
            
        if key.lower() in EXTENDED_KEYS:
            flags |= self.KEYEVENTF_EXTENDEDKEY  # 扩展键标志
        
        # 创建输入结构
        extra = self.ctypes.pointer(self.ctypes.c_ulong(0))
        inp = self.INPUT(
            type=self.INPUT_KEYBOARD,
            ki=self.KEYBDINPUT(
                wVk=0,              # 不使用虚拟键码
                wScan=scan_code,    # 使用硬件扫描码
                dwFlags=flags,
                time=0,             # 让系统自动填充时间戳
                dwExtraInfo=extra
            )
        )
        
        # 调用 Windows API 发送输入
        self.user32.SendInput(1, self.ctypes.byref(inp), self.ctypes.sizeof(inp))
    
    def key_down(self, key: str) -> None:
        '''按下按键'''
        self._send_key_event(key, key_up=False)
    
    def key_up(self, key: str) -> None:
        '''释放按键'''
        self._send_key_event(key, key_up=True)
    
    def press_key(self, key: str, duration: float = 0.05) -> None:
        '''按下并释放按键'''
        if key and self._available:
            self.key_down(key)
            time.sleep(duration)
            self.key_up(key)
    
    def is_available(self) -> bool:
        '''检查后端是否可用'''
        return self._available


class PyAutoGuiBackend(InputBackend):
    '''
    PyAutoGUI 后端 - 使用 Windows SendInput API
    
    ⚠️ 警告：容易被反作弊系统检测 ⚠️
    
    检测原因：
    ---------
    - SendInput 会自动设置 LLKHF_INJECTED 标志
    - 默认不提供硬件扫描码
    - 时序模式可被分析
    
    仅在其他后端不可用时使用此后端
    '''
    
    def __init__(self):
        try:
            import pyautogui
            self.pyautogui = pyautogui
            # 设置一个小的随机暂停，避免完全无延迟
            self.pyautogui.PAUSE = random.uniform(0.001, 0.005)
            self._available = True
            logger.info("[PyAutoGuiBackend] 初始化成功 (注意：容易被检测)")
        except ImportError:
            self._available = False
            logger.warning("[PyAutoGuiBackend] pyautogui 未安装")
    
    def key_down(self, key: str) -> None:
        if self._available:
            try:
                self.pyautogui.keyDown(key)
            except Exception as e:
                logger.error(f"[PyAutoGuiBackend] key_down 失败: {e}")
    
    def key_up(self, key: str) -> None:
        if self._available:
            try:
                self.pyautogui.keyUp(key)
            except Exception as e:
                logger.error(f"[PyAutoGuiBackend] key_up 失败: {e}")
    
    def press_key(self, key: str, duration: float = 0.05) -> None:
        if key and self._available:
            self.key_down(key)
            time.sleep(duration)
            self.key_up(key)
    
    def is_available(self) -> bool:
        return self._available


class InterceptionBackend(InputBackend):
    '''
    Interception 驱动后端 - 硬件级别的键盘模拟
    
    ★ 效果最好，但需要安装驱动并重启电脑 ★
    
    安装步骤：
    ---------
    1. 下载 Interception 驱动：
       https://github.com/oblitum/Interception/releases
    
    2. 以管理员身份运行命令提示符，执行：
       install-interception.exe /install
    
    3. 重启电脑（必须）
    
    4. 安装 Python 库：
       pip install interception-python
    
    5. 以管理员身份运行脚本
    
    优点：
    -----
    - 内核级别的输入模拟
    - 无 LLKHF_INJECTED 标志
    - 几乎无法被检测
    
    缺点：
    -----
    - 需要安装驱动
    - 需要重启电脑
    - 需要管理员权限
    '''
    
    def __init__(self):
        self._available = False
        self._context = None
        self._device = None
        
        if is_mac():
            logger.info("[InterceptionBackend] macOS 不支持此后端")
            return
        
        try:
            import interception
            self.interception = interception
            
            # 初始化 Interception 上下文
            self._context = interception.interception()
            
            # 查找键盘设备
            for i in range(interception.MAX_DEVICES):
                if interception.is_keyboard(i):
                    self._device = i
                    break
            
            if self._device is not None:
                self._available = True
                logger.info(f"[InterceptionBackend] 初始化成功，设备ID: {self._device}")
            else:
                logger.warning("[InterceptionBackend] 未找到键盘设备")
                
        except ImportError:
            logger.info("[InterceptionBackend] interception-python 未安装")
            logger.info("  如需使用，请执行: pip install interception-python")
        except Exception as e:
            logger.warning(f"[InterceptionBackend] 初始化失败: {e}")
            logger.info("  请确保已安装 Interception 驱动并以管理员身份运行")
    
    def _get_scan_code(self, key: str) -> int:
        '''获取按键的硬件扫描码'''
        return SCAN_CODES.get(key.lower(), 0)
    
    def _is_extended_key(self, key: str) -> bool:
        '''检查是否为扩展键'''
        return key.lower() in EXTENDED_KEYS
    
    def key_down(self, key: str) -> None:
        if not self._available or not key:
            return
            
        try:
            scan_code = self._get_scan_code(key)
            if scan_code == 0:
                logger.warning(f"[InterceptionBackend] 未知按键: {key}")
                return
            
            stroke = self.interception.key_stroke()
            stroke.code = scan_code
            stroke.state = self.interception.INTERCEPTION_KEY_DOWN
            
            if self._is_extended_key(key):
                stroke.state |= self.interception.INTERCEPTION_KEY_E0
            
            self._context.send(self._device, stroke)
            
        except Exception as e:
            logger.error(f"[InterceptionBackend] key_down 失败: {e}")
    
    def key_up(self, key: str) -> None:
        if not self._available or not key:
            return
            
        try:
            scan_code = self._get_scan_code(key)
            if scan_code == 0:
                return
            
            stroke = self.interception.key_stroke()
            stroke.code = scan_code
            stroke.state = self.interception.INTERCEPTION_KEY_UP
            
            if self._is_extended_key(key):
                stroke.state |= self.interception.INTERCEPTION_KEY_E0
            
            self._context.send(self._device, stroke)
            
        except Exception as e:
            logger.error(f"[InterceptionBackend] key_up 失败: {e}")
    
    def press_key(self, key: str, duration: float = 0.05) -> None:
        if key and self._available:
            self.key_down(key)
            time.sleep(duration)
            self.key_up(key)
    
    def is_available(self) -> bool:
        return self._available
    
    def __del__(self):
        '''清理资源'''
        if self._context is not None:
            try:
                self._context.destroy()
            except:
                pass


# ============================================================
# 全局后端实例管理
# ============================================================

_current_backend = None
_arduino_backend = None  # Arduino后端单独管理，支持UI显示状态

def get_arduino_backend():
    '''获取Arduino HID后端实例（用于UI状态显示）'''
    return _arduino_backend

def get_input_backend(backend_type: str = 'auto') -> InputBackend:
    '''
    获取输入后端实例
    
    参数：
        backend_type: 后端类型
            - 'auto': 自动选择最佳可用后端（推荐）
            - 'arduino_hid': 使用 Arduino 硬件 HID（最安全，需要硬件）
            - 'ctypes_raw': 使用 ctypes 直接调用 Windows API（无需重启）
            - 'interception': 使用 Interception 驱动（需要重启）
            - 'pyautogui': 使用 pyautogui（容易被检测）
            
    返回：
        InputBackend 实例
        
    自动选择顺序（考虑安全性）：
        1. arduino_hid - 如果已连接，最安全
        2. ctypes_raw - 无需安装，无需重启
        3. interception - 如果已安装驱动
        4. pyautogui - 兜底方案
    '''
    global _current_backend, _arduino_backend
    
    if _current_backend is not None:
        return _current_backend
    
    if backend_type == 'auto':
        # 优先使用 Arduino HID（最安全）
        backends_to_try = [
            ('arduino_hid', _create_arduino_backend),
            ('ctypes_raw', lambda: CtypesRawBackend()),
            ('interception', lambda: InterceptionBackend()),
            ('pyautogui', lambda: PyAutoGuiBackend()),
        ]
        
        for name, create_func in backends_to_try:
            try:
                backend = create_func()
                if backend and backend.is_available():
                    logger.info(f"[InputBackend] 使用 {name} 后端")
                    _current_backend = backend
                    if name == 'arduino_hid':
                        _arduino_backend = backend
                    return backend
            except Exception as e:
                logger.debug(f"[InputBackend] {name} 不可用: {e}")
        
        # 兜底使用 pyautogui
        logger.warning("[InputBackend] 降级使用 pyautogui（容易被检测）")
        _current_backend = PyAutoGuiBackend()
    
    elif backend_type == 'arduino_hid':
        _current_backend = _create_arduino_backend()
        _arduino_backend = _current_backend
        if not _current_backend or not _current_backend.is_available():
            logger.warning("[InputBackend] Arduino HID 不可用，尝试 ctypes_raw")
            _current_backend = CtypesRawBackend()
            if not _current_backend.is_available():
                _current_backend = PyAutoGuiBackend()
        
    elif backend_type == 'ctypes_raw':
        _current_backend = CtypesRawBackend()
        if not _current_backend.is_available():
            logger.error("[InputBackend] ctypes_raw 不可用，降级使用 pyautogui")
            _current_backend = PyAutoGuiBackend()
            
    elif backend_type == 'interception':
        _current_backend = InterceptionBackend()
        if not _current_backend.is_available():
            logger.warning("[InputBackend] Interception 不可用，尝试 ctypes_raw")
            _current_backend = CtypesRawBackend()
            if not _current_backend.is_available():
                _current_backend = PyAutoGuiBackend()
                
    else:  # pyautogui
        _current_backend = PyAutoGuiBackend()
    
    return _current_backend


def _create_arduino_backend():
    '''创建Arduino HID后端'''
    try:
        from src.input.ArduinoHIDBackend import ArduinoHIDBackend
        return ArduinoHIDBackend(auto_detect=True)
    except Exception as e:
        logger.debug(f"[InputBackend] 创建Arduino后端失败: {e}")
        return None


def init_input_backend(cfg: dict) -> InputBackend:
    '''
    根据配置初始化输入后端

    参数：
        cfg: 配置字典，需包含 'anti_detect.input_backend' 设置

    返回：
        初始化后的 InputBackend 实例
    '''
    global _arduino_backend

    backend_type = cfg.get('anti_detect', {}).get('input_backend', 'auto')
    logger.info(f"[InputBackend] init_input_backend: backend_type={backend_type}, _arduino_backend={'已存在' if _arduino_backend else 'None'}")

    # 始终尝试初始化 Arduino HID 后端（用于 UI 显示状态）
    # 即使配置了其他后端，Arduino 面板也能显示连接状态
    if _arduino_backend is None:
        try:
            from src.input.ArduinoHIDBackend import create_arduino_hid_backend
            _arduino_backend = create_arduino_hid_backend(cfg)
            logger.info(f"[InputBackend] Arduino 后端已创建, available={_arduino_backend.is_available() if _arduino_backend else False}")
        except Exception as e:
            logger.debug(f"[InputBackend] 初始化Arduino后端失败: {e}")
            _arduino_backend = None

    # 如果配置了Arduino，使用配置参数
    if backend_type == 'arduino_hid':
        try:
            from src.input.ArduinoHIDBackend import create_arduino_hid_backend
            backend = create_arduino_hid_backend(cfg)
            if backend:
                _arduino_backend = backend
                logger.info(f"[InputBackend] 使用 Arduino 后端, available={backend.is_available()}")
                if backend.is_available():
                    global _current_backend
                    _current_backend = backend
                    return backend
        except Exception as e:
            logger.warning(f"[InputBackend] 创建配置Arduino后端失败: {e}")

    # 返回实际创建的后端（可能是 Arduino HID，也可能是其他）
    if _arduino_backend is not None:
        logger.info(f"[InputBackend] 返回 _arduino_backend, available={_arduino_backend.is_available()}")
        return _arduino_backend
    return get_input_backend(backend_type)
