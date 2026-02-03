'''
ArduinoHIDBackend - 通过Arduino硬件实现真实USB HID输入

此模块提供通过Arduino硬件（Leonardo/Pro Micro/Teensy）实现的键盘鼠标输入。
由于输入来自真实USB设备，完全无法被反作弊系统检测。

优势：
------
1. 完全不可检测 - 对操作系统来说就是真实的键盘/鼠标
2. 无需驱动 - 不需要安装任何内核驱动
3. 跨平台 - Windows/Mac/Linux 通用
4. 绕过权限 - 不需要管理员权限

劣势：
------
1. 需要硬件 - 需要购买 Arduino 开发板 (~15-30元)
2. 延迟较高 - 串口通信有约5-15ms额外延迟
3. 需要USB口 - 占用一个USB端口

支持的硬件：
-----------
- Arduino Leonardo
- Pro Micro (推荐，小巧便宜)
- Teensy 2.0/4.0
- 任何带 ATmega32U4 的开发板

使用步骤：
---------
1. 将 arduino/MapleHID/MapleHID.ino 上传到开发板
2. 在配置中设置 input_backend: "arduino_hid"
3. 配置正确的串口 (如 COM3 或 /dev/ttyACM0)
'''

import time
import threading
import queue
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Tuple
from datetime import datetime
from collections import deque

from src.utils.logger import logger
from src.utils.common import is_mac
from src.input.InputBackend import InputBackend, SCAN_CODES, EXTENDED_KEYS

# ============================================================
# 日志记录类
# ============================================================

@dataclass
class HIDLogEntry:
    '''单条HID日志记录'''
    timestamp: datetime
    direction: str  # 'TX' 发送 / 'RX' 接收 / 'ERR' 错误
    command: str
    response: str = ''
    latency_ms: float = 0.0
    success: bool = True
    error_message: str = ''


class HIDLogger:
    '''
    HID操作日志记录器
    
    记录所有发送和接收的命令，便于调试和监控
    '''
    
    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self._logs: deque = deque(maxlen=max_entries)
        self._error_logs: deque = deque(maxlen=500)
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[HIDLogEntry], None]] = []
        
        # 统计信息
        self.total_commands = 0
        self.total_errors = 0
        self.total_latency_ms = 0.0
        
    def log(self, direction: str, command: str, response: str = '', 
            latency_ms: float = 0.0, success: bool = True, error_message: str = ''):
        '''记录一条日志'''
        entry = HIDLogEntry(
            timestamp=datetime.now(),
            direction=direction,
            command=command,
            response=response,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message
        )
        
        with self._lock:
            self._logs.append(entry)
            self.total_commands += 1
            self.total_latency_ms += latency_ms
            
            if not success:
                self._error_logs.append(entry)
                self.total_errors += 1
        
        # 触发回调
        for callback in self._callbacks:
            try:
                callback(entry)
            except Exception as e:
                logger.warning(f"[HIDLogger] Callback error: {e}")
    
    def log_error(self, error_message: str, command: str = ''):
        '''记录错误'''
        self.log('ERR', command, error_message=error_message, success=False)
    
    def register_callback(self, callback: Callable[[HIDLogEntry], None]):
        '''注册日志回调，用于UI实时显示'''
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[HIDLogEntry], None]):
        '''注销日志回调'''
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_recent_logs(self, count: int = 100) -> List[HIDLogEntry]:
        '''获取最近的日志'''
        with self._lock:
            return list(self._logs)[-count:]
    
    def get_error_logs(self, count: int = 100) -> List[HIDLogEntry]:
        '''获取错误日志'''
        with self._lock:
            return list(self._error_logs)[-count:]
    
    def get_average_latency(self) -> float:
        '''获取平均延迟'''
        if self.total_commands == 0:
            return 0.0
        return self.total_latency_ms / self.total_commands
    
    def get_error_rate(self) -> float:
        '''获取错误率'''
        if self.total_commands == 0:
            return 0.0
        return self.total_errors / self.total_commands
    
    def clear(self):
        '''清空日志'''
        with self._lock:
            self._logs.clear()
            self._error_logs.clear()
            self.total_commands = 0
            self.total_errors = 0
            self.total_latency_ms = 0.0


# ============================================================
# 连接状态
# ============================================================

class ConnectionState:
    '''连接状态枚举'''
    DISCONNECTED = 'disconnected'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    ERROR = 'error'
    RECONNECTING = 'reconnecting'


@dataclass
class ConnectionInfo:
    '''连接信息'''
    state: str = ConnectionState.DISCONNECTED
    port: str = ''
    device_id: str = ''
    last_heartbeat: float = 0.0
    error_message: str = ''
    reconnect_attempts: int = 0
    latency_ms: float = 0.0


# ============================================================
# 命令批处理器 (延迟优化)
# ============================================================

class CommandBatcher:
    '''
    命令批处理器
    
    将多个命令合并为一个批量命令发送，减少串口往返延迟
    这是降低延迟的关键优化
    '''
    
    def __init__(self, max_batch_size: int = 20, max_wait_ms: float = 2.0):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self._batch: List[str] = []
        self._lock = threading.Lock()
        self._last_add_time = 0.0
    
    def add(self, command: str) -> Optional[str]:
        '''
        添加命令到批次
        
        返回:
            如果批次已满或超时，返回批量命令字符串
            否则返回 None
        '''
        with self._lock:
            self._batch.append(command)
            self._last_add_time = time.time()
            
            if len(self._batch) >= self.max_batch_size:
                return self._flush()
        return None
    
    def flush(self) -> Optional[str]:
        '''强制刷新批次'''
        with self._lock:
            return self._flush()
    
    def _flush(self) -> Optional[str]:
        '''内部刷新方法'''
        if not self._batch:
            return None
        
        if len(self._batch) == 1:
            # 单个命令直接发送
            cmd = self._batch[0]
            self._batch.clear()
            return cmd
        
        # 多个命令合并为批量命令
        batch_cmd = 'B' + ';'.join(self._batch)
        self._batch.clear()
        return batch_cmd
    
    def should_flush(self) -> bool:
        '''检查是否应该刷新'''
        if not self._batch:
            return False
        elapsed = (time.time() - self._last_add_time) * 1000
        return elapsed >= self.max_wait_ms


# ============================================================
# Arduino HID 后端
# ============================================================

class ArduinoHIDBackend(InputBackend):
    '''
    Arduino HID 输入后端
    
    通过串口与Arduino通信，Arduino模拟真实USB键盘/鼠标输入
    这是最难被检测的输入方式，因为输入来自真实硬件设备
    
    配置示例：
    ---------
    anti_detect:
      input_backend: "arduino_hid"
      arduino:
        port: "COM3"          # Windows
        # port: "/dev/ttyACM0"  # Linux/Mac
        baud_rate: 115200
        auto_detect: true     # 自动检测端口
        timeout: 0.1          # 串口超时
        heartbeat_interval: 1.0  # 心跳间隔
        reconnect_delay: 2.0     # 重连延迟
        enable_batch: true       # 启用批量命令
    '''
    
    DEVICE_ID_PREFIX = 'MAPLE_HID'
    DEFAULT_BAUD_RATE = 115200
    DEFAULT_TIMEOUT = 0.1
    HEARTBEAT_INTERVAL = 1.0
    RECONNECT_DELAY = 2.0
    
    def __init__(self, port: str = '', baud_rate: int = DEFAULT_BAUD_RATE,
                 auto_detect: bool = True, enable_batch: bool = True):
        '''
        初始化Arduino HID后端
        
        参数:
            port: 串口端口 (如 COM3, /dev/ttyACM0)
            baud_rate: 波特率 (默认115200)
            auto_detect: 是否自动检测端口
            enable_batch: 是否启用命令批处理
        '''
        self._available = False
        self._serial = None
        self._port = port
        self._baud_rate = baud_rate
        self._auto_detect = auto_detect
        self._enable_batch = enable_batch
        
        # 状态管理
        self._connection_info = ConnectionInfo()
        self._lock = threading.Lock()
        
        # 日志记录
        self.hid_logger = HIDLogger()
        
        # 命令批处理器
        self._batcher = CommandBatcher() if enable_batch else None
        
        # 后台线程
        self._heartbeat_thread = None
        self._batch_thread = None
        self._running = False
        
        # 状态回调
        self._state_callbacks: List[Callable[[ConnectionInfo], None]] = []
        
        # 尝试连接
        self._init_connection()
    
    def _init_connection(self):
        '''初始化连接'''
        try:
            import serial
            import serial.tools.list_ports
            self._serial_module = serial
            self._list_ports = serial.tools.list_ports
        except ImportError:
            logger.warning("[ArduinoHIDBackend] pyserial 未安装")
            logger.info("  请执行: pip install pyserial")
            self._update_state(ConnectionState.ERROR, error="pyserial not installed")
            return
        
        # 查找端口
        port = self._find_port()
        if not port:
            logger.warning("[ArduinoHIDBackend] 未找到Arduino设备")
            self._update_state(ConnectionState.DISCONNECTED)
            return
        
        # 连接
        if self._connect(port):
            self._start_background_threads()
    
    def _find_port(self) -> Optional[str]:
        '''查找Arduino端口'''
        if self._port:
            return self._port
        
        if not self._auto_detect:
            return None
        
        logger.info("[ArduinoHIDBackend] 自动检测Arduino端口...")
        
        # 常见的Arduino设备VID/PID
        arduino_ids = [
            (0x2341, 0x8036),  # Arduino Leonardo
            (0x2341, 0x8037),  # Arduino Micro
            (0x1B4F, 0x9205),  # SparkFun Pro Micro 5V
            (0x1B4F, 0x9206),  # SparkFun Pro Micro 3.3V
            (0x239A, None),    # Adafruit
            (0x16C0, 0x0483),  # Teensy
        ]
        
        for port_info in self._list_ports.comports():
            vid = port_info.vid
            pid = port_info.pid
            
            for target_vid, target_pid in arduino_ids:
                if vid == target_vid and (target_pid is None or pid == target_pid):
                    logger.info(f"[ArduinoHIDBackend] 找到设备: {port_info.device} "
                               f"({port_info.description})")
                    return port_info.device
            
            # 也检查描述中是否包含Arduino关键字
            desc = (port_info.description or '').lower()
            if 'arduino' in desc or 'leonardo' in desc or 'pro micro' in desc:
                logger.info(f"[ArduinoHIDBackend] 找到设备: {port_info.device}")
                return port_info.device
        
        return None
    
    def _connect(self, port: str) -> bool:
        '''连接到Arduino'''
        self._update_state(ConnectionState.CONNECTING, port=port)
        
        try:
            self._serial = self._serial_module.Serial(
                port=port,
                baudrate=self._baud_rate,
                timeout=self.DEFAULT_TIMEOUT,
                write_timeout=self.DEFAULT_TIMEOUT
            )
            
            # 等待Arduino重置
            time.sleep(2.0)
            
            # 清空缓冲区
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            
            # 检查设备响应
            if self._verify_device():
                self._port = port
                self._available = True
                self._update_state(ConnectionState.CONNECTED, port=port)
                logger.info(f"[ArduinoHIDBackend] 连接成功: {port}")
                return True
            else:
                self._serial.close()
                self._serial = None
                self._update_state(ConnectionState.ERROR, error="Device verification failed")
                return False
                
        except Exception as e:
            logger.error(f"[ArduinoHIDBackend] 连接失败: {e}")
            self._update_state(ConnectionState.ERROR, error=str(e))
            if self._serial:
                try:
                    self._serial.close()
                except:
                    pass
                self._serial = None
            return False
    
    def _verify_device(self) -> bool:
        '''验证设备是否为MapleHID'''
        try:
            # 发送信息查询命令
            self._serial.write(b'I\n')
            time.sleep(0.1)
            
            response = self._serial.readline().decode('utf-8').strip()
            if response.startswith(self.DEVICE_ID_PREFIX):
                self._connection_info.device_id = response
                logger.info(f"[ArduinoHIDBackend] 设备验证成功: {response}")
                return True
            
            # 尝试心跳命令
            self._serial.write(b'?\n')
            time.sleep(0.1)
            response = self._serial.readline().decode('utf-8').strip()
            if response == 'OK':
                logger.info("[ArduinoHIDBackend] 设备验证成功 (心跳)")
                return True
                
        except Exception as e:
            logger.warning(f"[ArduinoHIDBackend] 设备验证失败: {e}")
        
        return False
    
    def _start_background_threads(self):
        '''启动后台线程'''
        self._running = True
        
        # 心跳线程
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, 
            daemon=True,
            name="ArduinoHID-Heartbeat"
        )
        self._heartbeat_thread.start()
        
        # 批处理刷新线程
        if self._batcher:
            self._batch_thread = threading.Thread(
                target=self._batch_flush_loop,
                daemon=True,
                name="ArduinoHID-BatchFlush"
            )
            self._batch_thread.start()
    
    def _heartbeat_loop(self):
        '''心跳循环'''
        while self._running:
            try:
                if self._available:
                    start = time.time()
                    response = self._send_command('?', log=False)
                    latency = (time.time() - start) * 1000
                    
                    if response == 'OK':
                        self._connection_info.last_heartbeat = time.time()
                        self._connection_info.latency_ms = latency
                    else:
                        logger.warning("[ArduinoHIDBackend] 心跳失败")
                        self._handle_disconnect()
                        
            except Exception as e:
                logger.warning(f"[ArduinoHIDBackend] 心跳错误: {e}")
                self._handle_disconnect()
            
            time.sleep(self.HEARTBEAT_INTERVAL)
    
    def _batch_flush_loop(self):
        '''批处理刷新循环'''
        while self._running:
            try:
                if self._batcher and self._batcher.should_flush():
                    cmd = self._batcher.flush()
                    if cmd:
                        self._send_command(cmd)
            except Exception as e:
                logger.warning(f"[ArduinoHIDBackend] 批处理刷新错误: {e}")
            
            time.sleep(0.001)  # 1ms检查间隔
    
    def _handle_disconnect(self):
        '''处理断开连接'''
        self._available = False
        self._update_state(ConnectionState.RECONNECTING)
        
        # 尝试重连
        self._connection_info.reconnect_attempts += 1
        logger.info(f"[ArduinoHIDBackend] 尝试重连 ({self._connection_info.reconnect_attempts})...")
        
        time.sleep(self.RECONNECT_DELAY)
        
        if self._serial:
            try:
                self._serial.close()
            except:
                pass
        
        port = self._find_port()
        if port and self._connect(port):
            self._connection_info.reconnect_attempts = 0
    
    def _update_state(self, state: str, port: str = '', error: str = ''):
        '''更新连接状态'''
        self._connection_info.state = state
        if port:
            self._connection_info.port = port
        if error:
            self._connection_info.error_message = error
            self.hid_logger.log_error(error)
        
        # 触发回调
        for callback in self._state_callbacks:
            try:
                callback(self._connection_info)
            except Exception as e:
                logger.warning(f"[ArduinoHIDBackend] State callback error: {e}")
    
    def _send_command(self, cmd: str, log: bool = True) -> str:
        '''
        发送命令到Arduino
        
        返回响应字符串
        '''
        if not self._serial or not self._available:
            if log:
                self.hid_logger.log('TX', cmd, success=False, error_message='Not connected')
            return ''
        
        start_time = time.time()
        
        try:
            with self._lock:
                # 发送命令
                self._serial.write((cmd + '\n').encode('utf-8'))
                
                # 读取响应
                response = self._serial.readline().decode('utf-8').strip()
            
            latency = (time.time() - start_time) * 1000
            
            if log:
                success = response.startswith('OK') or response.startswith(self.DEVICE_ID_PREFIX)
                self.hid_logger.log('TX', cmd, response, latency, success)
            
            return response
            
        except Exception as e:
            if log:
                self.hid_logger.log('TX', cmd, success=False, error_message=str(e))
            logger.warning(f"[ArduinoHIDBackend] 发送命令失败: {e}")
            return ''
    
    def _key_to_scancode_hex(self, key: str) -> str:
        '''将按键名转换为扫描码十六进制字符串'''
        scancode = SCAN_CODES.get(key.lower(), 0)
        return f'{scancode:02X}'
    
    # ============================================================
    # InputBackend 接口实现
    # ============================================================
    
    def key_down(self, key: str) -> None:
        '''按下按键'''
        if not key or not self._available:
            return
        
        scancode = self._key_to_scancode_hex(key)
        cmd = f'K{scancode}'
        
        if self._batcher:
            batch_cmd = self._batcher.add(cmd)
            if batch_cmd:
                self._send_command(batch_cmd)
        else:
            self._send_command(cmd)
    
    def key_up(self, key: str) -> None:
        '''释放按键'''
        if not key or not self._available:
            return
        
        scancode = self._key_to_scancode_hex(key)
        cmd = f'R{scancode}'
        
        if self._batcher:
            batch_cmd = self._batcher.add(cmd)
            if batch_cmd:
                self._send_command(batch_cmd)
        else:
            self._send_command(cmd)
    
    def press_key(self, key: str, duration: float = 0.05) -> None:
        '''按下并释放按键'''
        if not key or not self._available:
            return
        
        if self._batcher:
            # 使用批处理：key_down, wait, key_up
            scancode = self._key_to_scancode_hex(key)
            wait_ms = int(duration * 1000)
            
            self._batcher.add(f'K{scancode}')
            self._batcher.add(f'W{wait_ms}')
            batch_cmd = self._batcher.add(f'R{scancode}')
            
            # 强制刷新以确保立即执行
            if not batch_cmd:
                batch_cmd = self._batcher.flush()
            if batch_cmd:
                self._send_command(batch_cmd)
        else:
            # 不使用批处理
            scancode = self._key_to_scancode_hex(key)
            self._send_command(f'P{scancode}')
    
    def is_available(self) -> bool:
        '''检查后端是否可用'''
        return self._available
    
    def get_name(self) -> str:
        '''获取后端名称'''
        return f"ArduinoHIDBackend ({self._port or 'disconnected'})"
    
    # ============================================================
    # 鼠标操作
    # ============================================================
    
    def mouse_move(self, dx: int, dy: int) -> None:
        '''移动鼠标'''
        if not self._available:
            return
        self._send_command(f'M{dx},{dy}')
    
    def mouse_click(self, button: int = 1) -> None:
        '''鼠标点击 (1=左键, 2=右键, 3=中键)'''
        if not self._available:
            return
        self._send_command(f'C{button}')
    
    def mouse_down(self, button: int = 1) -> None:
        '''鼠标按下'''
        if not self._available:
            return
        self._send_command(f'D{button}')
    
    def mouse_up(self, button: int = 1) -> None:
        '''鼠标释放'''
        if not self._available:
            return
        self._send_command(f'U{button}')
    
    # ============================================================
    # 状态查询
    # ============================================================
    
    def get_connection_info(self) -> ConnectionInfo:
        '''获取连接信息'''
        return self._connection_info
    
    def get_hid_logger(self) -> HIDLogger:
        '''获取HID日志记录器'''
        return self.hid_logger
    
    def register_state_callback(self, callback: Callable[[ConnectionInfo], None]):
        '''注册状态变化回调'''
        self._state_callbacks.append(callback)
    
    def unregister_state_callback(self, callback: Callable[[ConnectionInfo], None]):
        '''注销状态变化回调'''
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)
    
    def release_all(self) -> None:
        '''释放所有按键'''
        if self._available:
            self._send_command('X')
    
    def reconnect(self) -> bool:
        '''手动重连'''
        if self._serial:
            try:
                self._serial.close()
            except:
                pass
        
        port = self._find_port()
        if port:
            return self._connect(port)
        return False
    
    def disconnect(self) -> None:
        '''断开连接'''
        self._running = False
        self._available = False
        
        if self._serial:
            try:
                self._send_command('X')  # 释放所有按键
                self._serial.close()
            except:
                pass
            self._serial = None
        
        self._update_state(ConnectionState.DISCONNECTED)
    
    def __del__(self):
        '''析构函数'''
        self.disconnect()


# ============================================================
# 工厂函数
# ============================================================

def create_arduino_hid_backend(cfg: dict) -> Optional[ArduinoHIDBackend]:
    '''
    根据配置创建Arduino HID后端
    
    参数:
        cfg: 配置字典，需包含 'anti_detect.arduino' 设置
        
    返回:
        ArduinoHIDBackend 实例，如果创建失败返回 None
    '''
    arduino_cfg = cfg.get('anti_detect', {}).get('arduino', {})
    
    port = arduino_cfg.get('port', '')
    baud_rate = arduino_cfg.get('baud_rate', ArduinoHIDBackend.DEFAULT_BAUD_RATE)
    auto_detect = arduino_cfg.get('auto_detect', True)
    enable_batch = arduino_cfg.get('enable_batch', True)
    
    try:
        backend = ArduinoHIDBackend(
            port=port,
            baud_rate=baud_rate,
            auto_detect=auto_detect,
            enable_batch=enable_batch
        )
        
        if backend.is_available():
            return backend
        else:
            logger.warning("[ArduinoHIDBackend] 后端创建成功但设备不可用")
            return backend  # 仍然返回，可能稍后可用
            
    except Exception as e:
        logger.error(f"[ArduinoHIDBackend] 创建失败: {e}")
        return None
