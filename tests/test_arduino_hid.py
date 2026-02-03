#!/usr/bin/env python3
'''
Arduino HID 测试脚本

此脚本用于测试 Arduino HID 后端的功能是否正常工作。

使用方法：
---------
1. 确保已将 MapleHID.ino 上传到 Arduino Leonardo/Pro Micro
2. 确保 Arduino 已连接到电脑
3. 运行此脚本: python tests/test_arduino_hid.py

测试内容：
---------
1. 设备连接测试
2. 心跳测试
3. 单键按下/释放测试
4. 批量命令测试
5. 延迟测试
6. 鼠标功能测试
'''

import sys
import os
import time
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.input.ArduinoHIDBackend import (
    ArduinoHIDBackend, 
    ConnectionState, 
    HIDLogEntry
)
from src.utils.logger import logger


class ArduinoHIDTester:
    '''Arduino HID 测试器'''
    
    def __init__(self, port: str = '', verbose: bool = True):
        self.port = port
        self.verbose = verbose
        self.backend = None
        self.test_results = []
        
    def log(self, msg: str):
        '''输出日志'''
        if self.verbose:
            print(f"[TEST] {msg}")
    
    def log_result(self, test_name: str, passed: bool, message: str = ''):
        '''记录测试结果'''
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}"
        if message:
            result += f": {message}"
        print(result)
        self.test_results.append((test_name, passed, message))
    
    def run_all_tests(self) -> bool:
        '''运行所有测试'''
        print("=" * 60)
        print("Arduino HID 功能测试")
        print("=" * 60)
        print()
        
        # 1. 连接测试
        if not self.test_connection():
            print("\n连接失败，无法继续其他测试")
            return False
        
        # 2. 心跳测试
        self.test_heartbeat()
        
        # 3. 单键测试
        self.test_single_key()
        
        # 4. 批量命令测试
        self.test_batch_commands()
        
        # 5. 延迟测试
        self.test_latency()
        
        # 6. 鼠标测试（可选）
        self.test_mouse()
        
        # 7. 断开重连测试
        self.test_reconnect()
        
        # 打印总结
        self.print_summary()
        
        return all(passed for _, passed, _ in self.test_results)
    
    def test_connection(self) -> bool:
        '''测试连接'''
        self.log("测试设备连接...")
        
        try:
            self.backend = ArduinoHIDBackend(
                port=self.port,
                auto_detect=True,
                enable_batch=True
            )
            
            time.sleep(0.5)  # 等待初始化
            
            if self.backend.is_available():
                info = self.backend.get_connection_info()
                self.log_result("连接测试", True, 
                               f"端口: {info.port}, 设备: {info.device_id}")
                return True
            else:
                info = self.backend.get_connection_info()
                self.log_result("连接测试", False, 
                               f"状态: {info.state}, 错误: {info.error_message}")
                return False
                
        except Exception as e:
            self.log_result("连接测试", False, str(e))
            return False
    
    def test_heartbeat(self):
        '''测试心跳'''
        self.log("测试心跳功能...")
        
        try:
            # 发送心跳
            response = self.backend._send_command('?')
            
            if response == 'OK':
                info = self.backend.get_connection_info()
                self.log_result("心跳测试", True, 
                               f"延迟: {info.latency_ms:.2f}ms")
            else:
                self.log_result("心跳测试", False, f"响应: {response}")
                
        except Exception as e:
            self.log_result("心跳测试", False, str(e))
    
    def test_single_key(self):
        '''测试单键操作'''
        self.log("测试单键操作 (按 'A' 键)...")
        
        print("\n  *** 请注意：将在3秒后模拟按键 'A' ***")
        print("  *** 请将光标放在安全的文本区域 ***\n")
        time.sleep(3)
        
        try:
            # 测试 key_down
            self.backend.key_down('a')
            time.sleep(0.1)
            
            # 测试 key_up
            self.backend.key_up('a')
            
            self.log_result("单键测试 (key_down/key_up)", True)
            
        except Exception as e:
            self.log_result("单键测试", False, str(e))
        
        # 测试 press_key
        time.sleep(0.5)
        
        try:
            self.backend.press_key('b', duration=0.05)
            self.log_result("单键测试 (press_key)", True)
            
        except Exception as e:
            self.log_result("单键测试 (press_key)", False, str(e))
    
    def test_batch_commands(self):
        '''测试批量命令'''
        self.log("测试批量命令...")
        
        print("\n  *** 将在2秒后发送批量按键: 'H', 'E', 'L', 'L', 'O' ***\n")
        time.sleep(2)
        
        try:
            # 使用批量命令发送多个按键
            for key in ['h', 'e', 'l', 'l', 'o']:
                self.backend.press_key(key, duration=0.03)
                time.sleep(0.05)
            
            # 检查日志
            hid_logger = self.backend.get_hid_logger()
            avg_latency = hid_logger.get_average_latency()
            
            self.log_result("批量命令测试", True, 
                           f"平均延迟: {avg_latency:.2f}ms")
            
        except Exception as e:
            self.log_result("批量命令测试", False, str(e))
    
    def test_latency(self):
        '''测试延迟'''
        self.log("测试延迟 (发送100次心跳)...")
        
        try:
            latencies = []
            
            for i in range(100):
                start = time.time()
                response = self.backend._send_command('?', log=False)
                latency = (time.time() - start) * 1000
                
                if response == 'OK':
                    latencies.append(latency)
            
            if latencies:
                avg = sum(latencies) / len(latencies)
                min_lat = min(latencies)
                max_lat = max(latencies)
                
                self.log_result("延迟测试", True, 
                               f"平均: {avg:.2f}ms, 最小: {min_lat:.2f}ms, "
                               f"最大: {max_lat:.2f}ms")
            else:
                self.log_result("延迟测试", False, "无有效响应")
                
        except Exception as e:
            self.log_result("延迟测试", False, str(e))
    
    def test_mouse(self):
        '''测试鼠标功能'''
        self.log("测试鼠标功能...")
        
        print("\n  *** 将在2秒后移动鼠标 ***\n")
        time.sleep(2)
        
        try:
            # 移动鼠标画一个小方块
            for _ in range(4):
                self.backend.mouse_move(50, 0)
                time.sleep(0.1)
            
            for _ in range(4):
                self.backend.mouse_move(0, 50)
                time.sleep(0.1)
            
            for _ in range(4):
                self.backend.mouse_move(-50, 0)
                time.sleep(0.1)
            
            for _ in range(4):
                self.backend.mouse_move(0, -50)
                time.sleep(0.1)
            
            self.log_result("鼠标移动测试", True)
            
        except Exception as e:
            self.log_result("鼠标移动测试", False, str(e))
    
    def test_reconnect(self):
        '''测试断开重连'''
        self.log("测试断开重连...")
        
        try:
            # 断开连接
            self.backend.disconnect()
            time.sleep(0.5)
            
            info = self.backend.get_connection_info()
            if info.state == ConnectionState.DISCONNECTED:
                self.log("断开成功")
            
            # 重新连接
            success = self.backend.reconnect()
            time.sleep(1)
            
            if success and self.backend.is_available():
                self.log_result("断开重连测试", True)
            else:
                self.log_result("断开重连测试", False, "重连失败")
                
        except Exception as e:
            self.log_result("断开重连测试", False, str(e))
    
    def print_summary(self):
        '''打印测试总结'''
        print()
        print("=" * 60)
        print("测试总结")
        print("=" * 60)
        
        passed = sum(1 for _, p, _ in self.test_results if p)
        total = len(self.test_results)
        
        print(f"\n通过: {passed}/{total}")
        
        failed = [(name, msg) for name, p, msg in self.test_results if not p]
        if failed:
            print("\n失败的测试:")
            for name, msg in failed:
                print(f"  - {name}: {msg}")
        
        # 显示日志统计
        if self.backend:
            hid_logger = self.backend.get_hid_logger()
            print(f"\n命令统计:")
            print(f"  总命令数: {hid_logger.total_commands}")
            print(f"  错误数: {hid_logger.total_errors}")
            print(f"  错误率: {hid_logger.get_error_rate()*100:.2f}%")
            print(f"  平均延迟: {hid_logger.get_average_latency():.2f}ms")
        
        print()
    
    def cleanup(self):
        '''清理资源'''
        if self.backend:
            self.backend.disconnect()


def test_log_callback():
    '''测试日志回调功能'''
    print("\n测试日志回调功能...")
    
    def on_log(entry: HIDLogEntry):
        print(f"  [LOG] {entry.direction} {entry.command} -> {entry.response} "
              f"({entry.latency_ms:.2f}ms)")
    
    backend = ArduinoHIDBackend(auto_detect=True)
    
    if backend.is_available():
        backend.hid_logger.register_callback(on_log)
        
        # 发送一些命令
        backend._send_command('?')
        backend._send_command('I')
        
        backend.hid_logger.unregister_callback(on_log)
        backend.disconnect()
        print("  日志回调测试完成")
    else:
        print("  设备不可用，跳过日志回调测试")


def list_serial_ports():
    '''列出所有可用的串口'''
    try:
        import serial.tools.list_ports
        
        print("\n可用串口列表:")
        print("-" * 50)
        
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("  未找到任何串口设备")
            return
        
        for port in ports:
            print(f"  {port.device}")
            print(f"    描述: {port.description}")
            print(f"    VID:PID = {port.vid:04X}:{port.pid:04X}" if port.vid else "    VID:PID = N/A")
            print()
            
    except ImportError:
        print("  pyserial 未安装，请执行: pip install pyserial")


def main():
    parser = argparse.ArgumentParser(description='Arduino HID 测试工具')
    parser.add_argument('--port', '-p', type=str, default='',
                       help='指定串口端口 (如 COM3 或 /dev/ttyACM0)')
    parser.add_argument('--list', '-l', action='store_true',
                       help='列出所有可用串口')
    parser.add_argument('--quick', '-q', action='store_true',
                       help='快速测试（仅测试连接和心跳）')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='显示详细输出')
    
    args = parser.parse_args()
    
    if args.list:
        list_serial_ports()
        return 0
    
    tester = ArduinoHIDTester(port=args.port, verbose=args.verbose)
    
    try:
        if args.quick:
            # 快速测试
            if tester.test_connection():
                tester.test_heartbeat()
            tester.print_summary()
        else:
            # 完整测试
            tester.run_all_tests()
            
            # 额外测试日志回调
            test_log_callback()
        
        success = all(passed for _, passed, _ in tester.test_results)
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
        
    finally:
        tester.cleanup()


if __name__ == '__main__':
    sys.exit(main())
