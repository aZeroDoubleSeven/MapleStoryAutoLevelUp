'''
Arduino HID UI 组件

提供用于显示Arduino连接状态、输入输出日志和错误日志的UI组件

线程安全说明:
-------------
Arduino 后端在后台线程中运行（心跳线程、批处理线程），回调函数可能从这些线程调用。
为保证线程安全，所有 UI 更新必须通过 Qt Signal/Slot 机制传递到主线程执行。
'''

# Standard Import
import threading

# Library Import
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QPlainTextEdit, QTabWidget, QFormLayout,
    QComboBox, QLineEdit, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, Slot
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor

# Local Import
from datetime import datetime
from typing import Optional

from src.utils.logger import logger


class ConnectionStatusWidget(QWidget):
    '''
    Arduino 连接状态显示组件

    显示:
    - 连接状态 (已连接/断开/错误等)
    - 端口信息
    - 设备ID
    - 延迟
    - 错误信息

    线程安全:
    --------
    重连/断开操作在后台线程执行，通过信号通知 UI 更新
    '''

    # 信号: 后台操作完成后通知 UI
    operation_finished = Signal(str, bool)  # (operation_name, success)

    # 信号: 连接状态变化（供 ArduinoHIDPanel 监听）
    connection_state_changed = Signal(bool)  # True=已连接, False=未连接

    # 状态颜色映射
    STATUS_COLORS = {
        'connected': '#4CAF50',      # 绿色
        'disconnected': '#9E9E9E',   # 灰色
        'connecting': '#FF9800',      # 橙色
        'reconnecting': '#FF9800',    # 橙色
        'error': '#F44336',           # 红色
    }

    # 状态文本映射
    STATUS_TEXT = {
        'connected': '已连接',
        'disconnected': '未连接',
        'connecting': '连接中...',
        'reconnecting': '重连中...',
        'error': '错误',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

        # 定时更新 (3秒间隔，减少不必要的轮询开销)
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_display)
        self._update_timer.start(3000)  # 每3秒更新

        # 后端引用
        self._backend = None

        # 记录上次状态，用于检测变化
        self._last_known_state = None

        # 连接信号到槽
        self.operation_finished.connect(self._on_operation_finished)
    
    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 预检测提示标签
        self._precheck_label = QLabel()
        self._precheck_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        self._precheck_label.setWordWrap(True)
        layout.addRow("", self._precheck_label)
        
        # 状态指示器
        status_layout = QHBoxLayout()
        self._status_indicator = QLabel("●")
        self._status_indicator.setStyleSheet("color: #9E9E9E; font-size: 16px;")
        self._status_label = QLabel("未连接")
        self._status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self._status_indicator)
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()
        layout.addRow("状态:", status_layout)
        
        # 端口
        self._port_label = QLabel("-")
        layout.addRow("端口:", self._port_label)
        
        # 设备ID
        self._device_label = QLabel("-")
        layout.addRow("设备:", self._device_label)
        
        # 延迟
        self._latency_label = QLabel("-")
        layout.addRow("延迟:", self._latency_label)
        
        # 统计信息
        self._stats_label = QLabel("-")
        layout.addRow("统计:", self._stats_label)
        
        # 错误信息
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #F44336;")
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        layout.addRow("", self._error_label)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        self._reconnect_btn = QPushButton("重新连接")
        self._reconnect_btn.clicked.connect(self._on_reconnect_clicked)
        self._disconnect_btn = QPushButton("断开连接")
        self._disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        btn_layout.addWidget(self._reconnect_btn)
        btn_layout.addWidget(self._disconnect_btn)
        layout.addRow("", btn_layout)
    
    def set_backend(self, backend):
        '''设置后端引用'''
        self._backend = backend
        self._precheck_label.hide()
        self._update_display()
    
    def set_precheck_mode(self, enabled: bool):
        '''设置预检测模式（显示提示信息）'''
        if enabled:
            self._precheck_label.setText(
                "⚠️ 请先连接 Arduino 设备后再启动机器人\n"
                "Arduino HID 模式需要硬件设备支持"
            )
            self._precheck_label.show()
        else:
            self._precheck_label.hide()
    
    def _update_display(self):
        '''更新显示'''
        if not self._backend:
            # 无后端时显示未连接状态
            self._status_indicator.setStyleSheet("color: #9E9E9E; font-size: 16px;")
            self._status_label.setText("未连接")
            self._port_label.setText("-")
            self._device_label.setText("-")
            self._latency_label.setText("-")
            self._stats_label.setText("-")
            self._error_label.hide()
            # 如果之前是连接状态，发送断开信号
            if self._last_known_state == 'connected':
                self._last_known_state = 'disconnected'
                self.connection_state_changed.emit(False)
            return

        try:
            info = self._backend.get_connection_info()

            # 状态
            state = info.state
            color = self.STATUS_COLORS.get(state, '#9E9E9E')
            text = self.STATUS_TEXT.get(state, state)
            self._status_indicator.setStyleSheet(f"color: {color}; font-size: 16px;")
            self._status_label.setText(text)

            # 如果连接成功，自动隐藏预检测警告
            if state == 'connected':
                self.set_precheck_mode(False)

            # 检测连接状态变化
            if state != self._last_known_state:
                self._last_known_state = state
                is_connected = (state == 'connected')
                self.connection_state_changed.emit(is_connected)
                logger.info(f"[ConnectionStatusWidget] 连接状态变化: {state}")

            # 端口
            self._port_label.setText(info.port or "-")

            # 设备
            self._device_label.setText(info.device_id or "-")

            # 延迟
            if info.latency_ms > 0:
                self._latency_label.setText(f"{info.latency_ms:.1f} ms")
            else:
                self._latency_label.setText("-")

            # 统计
            hid_logger = self._backend.get_hid_logger()
            self._stats_label.setText(
                f"命令: {hid_logger.total_commands}, "
                f"错误: {hid_logger.total_errors}, "
                f"平均延迟: {hid_logger.get_average_latency():.1f}ms"
            )

            # 错误
            if info.error_message:
                self._error_label.setText(info.error_message)
                self._error_label.show()
            else:
                self._error_label.hide()

        except Exception as e:
            logger.warning(f"[ConnectionStatusWidget] Update failed: {e}")
    
    def _on_reconnect_clicked(self):
        '''重新连接 - 在后台线程执行避免阻塞 UI'''
        if self._backend:
            # 禁用按钮，显示操作中状态
            self._reconnect_btn.setEnabled(False)
            self._reconnect_btn.setText("连接中...")
            self._disconnect_btn.setEnabled(False)
            
            # 在后台线程执行耗时操作
            thread = threading.Thread(
                target=self._do_reconnect,
                daemon=True,
                name="Arduino-Reconnect"
            )
            thread.start()
    
    def _do_reconnect(self):
        '''后台线程执行重连'''
        try:
            result = self._backend.reconnect()
            self.operation_finished.emit("reconnect", result)
        except Exception as e:
            logger.warning(f"[ConnectionStatusWidget] Reconnect failed: {e}")
            self.operation_finished.emit("reconnect", False)
    
    def _on_disconnect_clicked(self):
        '''断开连接 - 在后台线程执行避免阻塞 UI'''
        if self._backend:
            # 禁用按钮，显示操作中状态
            self._disconnect_btn.setEnabled(False)
            self._disconnect_btn.setText("断开中...")
            self._reconnect_btn.setEnabled(False)
            
            # 在后台线程执行耗时操作
            thread = threading.Thread(
                target=self._do_disconnect,
                daemon=True,
                name="Arduino-Disconnect"
            )
            thread.start()
    
    def _do_disconnect(self):
        '''后台线程执行断开'''
        try:
            self._backend.disconnect()
            self.operation_finished.emit("disconnect", True)
        except Exception as e:
            logger.warning(f"[ConnectionStatusWidget] Disconnect failed: {e}")
            self.operation_finished.emit("disconnect", False)
    
    @Slot(str, bool)
    def _on_operation_finished(self, operation: str, success: bool):
        '''后台操作完成后恢复 UI 状态 (主线程)'''
        # 恢复按钮状态
        self._reconnect_btn.setEnabled(True)
        self._reconnect_btn.setText("重新连接")
        self._disconnect_btn.setEnabled(True)
        self._disconnect_btn.setText("断开连接")

        # 立即更新显示
        self._update_display()

        # 如果重连成功但还没隐藏预检测警告（通过 _update_display 中的 _check_connection_state 触发）
        if success and operation == "reconnect":
            logger.info(f"[ConnectionStatusWidget] {operation} 成功")

        if not success:
            logger.warning(f"[ConnectionStatusWidget] {operation} operation failed")


class HIDLogWidget(QWidget):
    '''
    HID 日志显示组件
    
    实时显示所有HID命令的输入输出
    
    线程安全:
    --------
    日志回调可能从后端线程调用，通过 Qt Signal 传递到主线程处理
    '''
    
    MAX_LOG_LINES = 500
    
    # 信号: 从任意线程安全地传递日志到主线程
    log_entry_received = Signal(object)  # HIDLogEntry
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._backend = None
        self._log_callback = None
        
        # 连接信号到槽 (确保在主线程处理)
        self.log_entry_received.connect(self._process_log_entry)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        # 过滤器
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["全部", "发送 (TX)", "接收 (RX)", "错误 (ERR)"])
        self._filter_combo.currentTextChanged.connect(self._apply_filter)
        toolbar.addWidget(QLabel("过滤:"))
        toolbar.addWidget(self._filter_combo)
        
        toolbar.addStretch()
        
        # 清空按钮
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear_logs)
        toolbar.addWidget(clear_btn)
        
        # 暂停/继续按钮
        self._pause_btn = QPushButton("暂停")
        self._pause_btn.setCheckable(True)
        self._pause_btn.clicked.connect(self._toggle_pause)
        toolbar.addWidget(self._pause_btn)
        
        layout.addLayout(toolbar)
        
        # 日志文本框
        self._log_text = QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumBlockCount(self.MAX_LOG_LINES)
        self._log_text.setStyleSheet("""
            QPlainTextEdit {
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                background-color: #1E1E1E;
                color: #D4D4D4;
            }
        """)
        layout.addWidget(self._log_text)
        
        self._is_paused = False
        self._current_filter = "全部"
    
    def set_backend(self, backend):
        '''设置后端并注册日志回调'''
        # 注销旧回调
        if self._backend and self._log_callback:
            try:
                self._backend.get_hid_logger().unregister_callback(self._log_callback)
            except (AttributeError, TypeError):
                pass
        
        self._backend = backend
        
        if backend:
            self._log_callback = self._on_log_entry
            try:
                backend.get_hid_logger().register_callback(self._log_callback)
            except AttributeError:
                pass  # 后端没有 HIDLogger 时静默忽略
    
    def _on_log_entry(self, entry):
        '''
        日志条目回调 - 可能从任意线程调用
        
        通过信号将日志传递到主线程处理，确保线程安全
        '''
        # 发送信号到主线程 (线程安全)
        self.log_entry_received.emit(entry)
    
    @Slot(object)
    def _process_log_entry(self, entry):
        '''
        处理日志条目 - 在主线程执行
        
        这个方法由 log_entry_received 信号触发，保证在 GUI 线程执行
        '''
        if self._is_paused:
            return
        
        # 检查过滤
        if self._current_filter == "发送 (TX)" and entry.direction != 'TX':
            return
        elif self._current_filter == "接收 (RX)" and entry.direction != 'RX':
            return
        elif self._current_filter == "错误 (ERR)" and entry.direction != 'ERR':
            return
        
        # 格式化日志
        timestamp = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]
        
        if entry.direction == 'TX':
            color = "#4FC3F7"  # 蓝色
            line = f"[{timestamp}] TX: {entry.command}"
            if entry.response:
                line += f" -> {entry.response}"
            if entry.latency_ms > 0:
                line += f" ({entry.latency_ms:.1f}ms)"
        elif entry.direction == 'RX':
            color = "#81C784"  # 绿色
            line = f"[{timestamp}] RX: {entry.response}"
        else:  # ERR
            color = "#E57373"  # 红色
            line = f"[{timestamp}] ERR: {entry.error_message}"
            if entry.command:
                line += f" (cmd: {entry.command})"
        
        self._append_colored_text(line, color)
    
    def _append_colored_text(self, text: str, color: str):
        '''添加带颜色的文本'''
        cursor = self._log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        
        cursor.insertText(text + "\n", fmt)
        
        # 自动滚动到底部
        self._log_text.setTextCursor(cursor)
        self._log_text.ensureCursorVisible()
    
    def _apply_filter(self, filter_text: str):
        '''应用过滤器'''
        self._current_filter = filter_text
        # 清空当前显示，重新加载符合条件的日志
        self._log_text.clear()
        
        if self._backend:
            logs = self._backend.get_hid_logger().get_recent_logs(self.MAX_LOG_LINES)
            for entry in logs:
                # 直接调用处理方法，因为已在主线程中
                self._process_log_entry(entry)
    
    def _clear_logs(self):
        '''清空日志'''
        self._log_text.clear()
        if self._backend:
            self._backend.get_hid_logger().clear()
    
    def _toggle_pause(self):
        '''切换暂停状态'''
        self._is_paused = self._pause_btn.isChecked()
        self._pause_btn.setText("继续" if self._is_paused else "暂停")


class ErrorLogWidget(QWidget):
    '''
    错误日志显示组件
    
    专门显示错误信息
    
    线程安全:
    --------
    日志回调可能从后端线程调用，通过 Qt Signal 传递到主线程处理
    '''
    
    MAX_LOG_LINES = 200
    
    # 信号: 从任意线程安全地传递错误日志到主线程
    error_entry_received = Signal(object)  # HIDLogEntry
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._backend = None
        self._log_callback = None
        
        # 连接信号到槽 (确保在主线程处理)
        self.error_entry_received.connect(self._process_error_entry)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        
        # 清空按钮
        clear_btn = QPushButton("清空错误")
        clear_btn.clicked.connect(self._clear_errors)
        toolbar.addWidget(clear_btn)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh_errors)
        toolbar.addWidget(refresh_btn)
        
        layout.addLayout(toolbar)
        
        # 错误日志文本框
        self._error_text = QPlainTextEdit()
        self._error_text.setReadOnly(True)
        self._error_text.setMaximumBlockCount(self.MAX_LOG_LINES)
        self._error_text.setStyleSheet("""
            QPlainTextEdit {
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                background-color: #2D2020;
                color: #FFCDD2;
            }
        """)
        layout.addWidget(self._error_text)
    
    def set_backend(self, backend):
        '''设置后端'''
        # 注销旧回调 (防止重复注册)
        if self._backend and self._log_callback:
            try:
                self._backend.get_hid_logger().unregister_callback(self._log_callback)
            except (AttributeError, TypeError):
                pass
        
        self._backend = backend
        
        if backend:
            self._log_callback = self._on_log_entry
            try:
                backend.get_hid_logger().register_callback(self._log_callback)
            except AttributeError:
                pass  # 后端没有 HIDLogger 时静默忽略
            self._refresh_errors()
    
    def _on_log_entry(self, entry):
        '''
        日志条目回调 - 可能从任意线程调用
        
        通过信号将错误日志传递到主线程处理，确保线程安全
        '''
        if not entry.success or entry.direction == 'ERR':
            # 发送信号到主线程 (线程安全)
            self.error_entry_received.emit(entry)
    
    @Slot(object)
    def _process_error_entry(self, entry):
        '''
        处理错误日志条目 - 在主线程执行
        
        这个方法由 error_entry_received 信号触发，保证在 GUI 线程执行
        '''
        timestamp = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] {entry.error_message or 'Unknown error'}"
        if entry.command:
            line += f" (cmd: {entry.command})"
        self._error_text.appendPlainText(line)
    
    def _refresh_errors(self):
        '''刷新错误列表'''
        self._error_text.clear()
        
        if self._backend:
            errors = self._backend.get_hid_logger().get_error_logs(self.MAX_LOG_LINES)
            for entry in errors:
                timestamp = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]
                line = f"[{timestamp}] {entry.error_message or 'Unknown error'}"
                if entry.command:
                    line += f" (cmd: {entry.command})"
                self._error_text.appendPlainText(line)
    
    def _clear_errors(self):
        '''清空错误'''
        self._error_text.clear()


class ArduinoHIDPanel(QGroupBox):
    '''
    Arduino HID 完整面板
    
    包含:
    - 连接状态
    - 输入输出日志
    - 错误日志
    
    信号:
        connection_changed(bool): 连接状态变化时触发
    '''
    
    # 信号: Arduino 连接状态变化
    connection_changed = Signal(bool)  # True=已连接, False=未连接
    
    def __init__(self, title: str = "Arduino HID", parent=None):
        super().__init__(title, parent)
        self._backend = None
        self._precheck_enabled = True  # 预检测模式默认开启
        self._last_connection_state = False
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 状态部分
        self._status_widget = ConnectionStatusWidget()
        self._status_widget.set_precheck_mode(self._precheck_enabled)

        # 连接状态变化信号
        self._status_widget.connection_state_changed.connect(self._check_connection_state)

        layout.addWidget(self._status_widget)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 标签页
        tabs = QTabWidget()
        
        # IO日志标签页
        self._log_widget = HIDLogWidget()
        tabs.addTab(self._log_widget, "命令日志")
        
        # 错误日志标签页
        self._error_widget = ErrorLogWidget()
        tabs.addTab(self._error_widget, "错误日志")
        
        layout.addWidget(tabs)
    
    def set_backend(self, backend):
        '''设置后端'''
        # 如果后端改变，注销旧回调
        if self._backend and self._backend != backend:
            self._log_widget.set_backend(None)
            self._error_widget.set_backend(None)
        
        self._backend = backend
        self._status_widget.set_backend(backend)
        
        if backend:
            self._log_widget.set_backend(backend)
            self._error_widget.set_backend(backend)
        
        # 更新预检测模式显示
        self._status_widget.set_precheck_mode(self._precheck_enabled)
        
        # 检查连接状态并发送信号
        self._check_connection_state()
    
    def set_precheck_mode(self, enabled: bool):
        '''设置预检测模式'''
        self._precheck_enabled = enabled
        self._status_widget.set_precheck_mode(enabled)
    
    def is_connected(self) -> bool:
        '''检查是否已连接'''
        if not self._backend:
            return False
        try:
            info = self._backend.get_connection_info()
            return info.state == 'connected'
        except:
            return False
    
    def _check_connection_state(self, connected: bool = None):
        '''检查并通知连接状态变化'''
        if connected is None:
            connected = self.is_connected()
        if connected != self._last_connection_state:
            self._last_connection_state = connected
            self.connection_changed.emit(connected)
    
    def get_status_widget(self) -> ConnectionStatusWidget:
        '''获取状态组件'''
        return self._status_widget
    
    def get_log_widget(self) -> HIDLogWidget:
        '''获取日志组件'''
        return self._log_widget
    
    def get_error_widget(self) -> ErrorLogWidget:
        '''获取错误组件'''
        return self._error_widget


def create_arduino_settings_widget() -> QWidget:
    '''
    创建 Arduino 设置组件
    
    用于配置Arduino连接参数
    '''
    widget = QWidget()
    layout = QFormLayout(widget)
    
    # 端口选择
    port_combo = QComboBox()
    port_combo.setEditable(True)
    port_combo.addItem("自动检测")
    
    # 尝试列出可用端口
    try:
        import serial.tools.list_ports
        for port in serial.tools.list_ports.comports():
            port_combo.addItem(f"{port.device} - {port.description}")
    except:
        pass
    
    layout.addRow("端口:", port_combo)
    
    # 波特率
    baud_combo = QComboBox()
    baud_combo.addItems(["115200", "57600", "38400", "19200", "9600"])
    baud_combo.setCurrentText("115200")
    layout.addRow("波特率:", baud_combo)
    
    # 启用批处理
    from PySide6.QtWidgets import QCheckBox
    batch_check = QCheckBox("启用命令批处理 (降低延迟)")
    batch_check.setChecked(True)
    layout.addRow("", batch_check)
    
    # 自动重连
    reconnect_check = QCheckBox("自动重连")
    reconnect_check.setChecked(True)
    layout.addRow("", reconnect_check)
    
    # 存储引用
    widget.port_combo = port_combo
    widget.baud_combo = baud_combo
    widget.batch_check = batch_check
    widget.reconnect_check = reconnect_check
    
    return widget
