'''
Anti-Detection 反检测模块

此模块提供人类化行为模拟，使机器人操作更接近真人，降低被检测的风险。

主要功能：
---------
1. 按键时长随机化 - 使用正态分布模拟人类按键习惯
2. 动作延迟随机化 - 模拟人类反应时间
3. 冷却时间抖动 - 避免固定间隔被检测
4. 微停顿模拟 - 偶尔短暂停顿，像真人在思考
5. 闲置行为模拟 - 偶尔发呆，像真人在走神
6. 疲劳系统 - 长时间运行后反应变慢

使用方法：
--------
from src.utils.anti_detect import get_human_behavior

human = get_human_behavior()
duration = human.get_key_duration()  # 获取随机按键时长
cooldown = human.randomize_cooldown(base_cooldown)  # 随机化冷却时间
'''

import random
import time
import math


class HumanBehavior:
    '''
    人类行为模拟器
    
    提供各种随机化方法，使机器人行为更像真人操作
    '''
    
    def __init__(self, cfg=None):
        '''
        初始化人类行为模拟器
        
        参数：
            cfg: 配置字典（可选）
        '''
        self.cfg = cfg or {}
        
        # 默认反检测设置
        self.settings = {
            # 按键时长随机化
            'key_duration_base': 0.05,       # 基础按键时长（秒）
            'key_duration_variance': 0.03,   # 时长变化范围（±30毫秒）
            
            # 动作延迟随机化
            'action_delay_min': 0.02,        # 最小动作延迟（秒）
            'action_delay_max': 0.08,        # 最大动作延迟（秒）
            
            # 攻击冷却变化（百分比）
            'attack_cooldown_variance': 0.15,  # ±15%
            
            # 微停顿设置
            'micro_pause_probability': 0.05,   # 5% 概率触发微停顿
            'micro_pause_duration_min': 0.1,   # 最短微停顿时间
            'micro_pause_duration_max': 0.3,   # 最长微停顿时间
            
            # 闲置行为设置
            'idle_probability': 0.01,          # 1% 概率触发闲置
            'idle_duration_min': 0.5,          # 最短闲置时间
            'idle_duration_max': 2.0,          # 最长闲置时间
            
            # Buff技能时间变化
            'buff_timing_variance': 0.2,       # ±20%
            
            # 喝药时间变化
            'potion_timing_variance': 0.25,    # ±25%
            
            # 功能开关
            'enable_random_delays': True,      # 启用随机延迟
            'enable_micro_pauses': True,       # 启用微停顿
            'enable_idle_behavior': True,      # 启用闲置行为
            'enable_typing_variance': True,    # 启用按键时长变化
        }
        
        # 从配置文件覆盖默认设置
        if 'anti_detect' in self.cfg:
            self.settings.update(self.cfg['anti_detect'])
        
        # 状态追踪（用于模拟自然行为模式）
        self._last_action_time = time.time()
        self._action_count = 0
        self._fatigue_level = 0.0  # 疲劳度（0.0 ~ 1.0）
        
    def get_key_duration(self, base_duration=None):
        '''
        获取随机化的按键持续时间
        
        人类按键通常遵循正态分布，偶尔会有快按或慢按的情况
        
        参数：
            base_duration: 基础时长（秒），默认为 0.05
            
        返回：
            float: 随机化后的时长（秒）
        '''
        if not self.settings['enable_typing_variance']:
            return base_duration or self.settings['key_duration_base']
            
        base = base_duration or self.settings['key_duration_base']
        variance = self.settings['key_duration_variance']
        
        # 使用正态分布生成更真实的随机值
        # 人类按键有自然节奏，但存在随机变化
        duration = random.gauss(base, variance / 2)
        
        # 5% 概率出现"疲劳"导致的慢按（模拟长时间游戏后的反应变慢）
        if random.random() < 0.05:
            duration *= random.uniform(1.2, 1.5)
        
        # 确保最小时长
        return max(0.02, duration)
    
    def get_action_delay(self):
        '''
        获取动作之间的随机延迟
        
        人类不会以完美的时序执行命令，总会有反应时间
        
        返回：
            float: 随机延迟时间（秒）
        '''
        if not self.settings['enable_random_delays']:
            return 0
            
        min_delay = self.settings['action_delay_min']
        max_delay = self.settings['action_delay_max']
        
        # 疲劳度会增加延迟（模拟长时间游戏后反应变慢）
        fatigue_factor = 1.0 + (self._fatigue_level * 0.5)
        
        return random.uniform(min_delay, max_delay) * fatigue_factor
    
    def randomize_cooldown(self, base_cooldown, variance_type='attack'):
        '''
        为冷却时间添加随机变化
        
        避免固定间隔被检测为脚本行为
        
        参数：
            base_cooldown: 基础冷却时间（秒）
            variance_type: 变化类型 ('attack', 'buff', 'potion')
            
        返回：
            float: 随机化后的冷却时间
        '''
        variance_key = f'{variance_type}_cooldown_variance'
        if variance_type == 'buff':
            variance_key = 'buff_timing_variance'
        elif variance_type == 'potion':
            variance_key = 'potion_timing_variance'
            
        variance = self.settings.get(variance_key, 0.15)
        
        # 使用正态分布应用变化
        multiplier = random.gauss(1.0, variance / 2)
        
        # 限制在合理范围内
        multiplier = max(0.7, min(1.3, multiplier))
        
        return base_cooldown * multiplier
    
    def should_micro_pause(self):
        '''
        判断是否应该进行微停顿
        
        人类在重复操作时偶尔会短暂停顿，模拟思考或分神
        
        返回：
            tuple: (是否停顿, 停顿时长)
        '''
        if not self.settings['enable_micro_pauses']:
            return False, 0
            
        if random.random() < self.settings['micro_pause_probability']:
            duration = random.uniform(
                self.settings['micro_pause_duration_min'],
                self.settings['micro_pause_duration_max']
            )
            return True, duration
            
        return False, 0
    
    def should_idle(self):
        '''
        判断是否应该进入短暂闲置状态
        
        真实玩家偶尔会停下来查看背包、聊天或发呆
        
        返回：
            tuple: (是否闲置, 闲置时长)
        '''
        if not self.settings['enable_idle_behavior']:
            return False, 0
            
        # 操作次数越多，闲置概率越高（模拟疲劳）
        adjusted_probability = self.settings['idle_probability'] * (1 + self._action_count / 1000)
        
        if random.random() < adjusted_probability:
            duration = random.uniform(
                self.settings['idle_duration_min'],
                self.settings['idle_duration_max']
            )
            self._action_count = 0  # 闲置后重置计数
            return True, duration
            
        return False, 0
    
    def update_fatigue(self):
        '''
        更新疲劳度
        
        长时间游戏会导致反应变慢，这是自然现象
        '''
        current_time = time.time()
        elapsed = current_time - self._last_action_time
        
        # 活跃操作时疲劳度缓慢增加
        if elapsed < 1.0:
            self._fatigue_level = min(1.0, self._fatigue_level + 0.0001)
        else:
            # 休息时疲劳度恢复
            self._fatigue_level = max(0.0, self._fatigue_level - 0.001)
            
        self._last_action_time = current_time
        self._action_count += 1
    
    def add_movement_noise(self, target_x, target_y, noise_level=3):
        '''
        为移动目标添加随机偏移
        
        人类不会点击精确的像素坐标，总会有误差
        
        参数：
            target_x: 目标 X 坐标
            target_y: 目标 Y 坐标
            noise_level: 最大偏移像素
            
        返回：
            tuple: (偏移后的X, 偏移后的Y)
        '''
        noise_x = random.randint(-noise_level, noise_level)
        noise_y = random.randint(-noise_level, noise_level)
        
        return target_x + noise_x, target_y + noise_y
    
    def get_human_like_path(self, start, end, steps=10):
        '''
        生成类似人类的移动路径
        
        人类移动通常有轻微弧度，而非完美直线
        
        参数：
            start: (x, y) 起点
            end: (x, y) 终点
            steps: 中间点数量
            
        返回：
            list: [(x, y), ...] 路径点列表
        '''
        points = []
        
        for i in range(steps + 1):
            t = i / steps
            
            # 线性插值
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            
            # 添加正弦曲线偏移
            curve_amount = 5 * math.sin(t * math.pi)
            
            # 计算垂直于移动方向的偏移
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.sqrt(dx*dx + dy*dy) or 1
            
            perp_x = -dy / length
            perp_y = dx / length
            
            x += perp_x * curve_amount * random.uniform(0.5, 1.5)
            y += perp_y * curve_amount * random.uniform(0.5, 1.5)
            
            points.append((int(x), int(y)))
            
        return points


class TimingRandomizer:
    '''
    时间随机化工具类
    
    提供各种时间相关的随机化方法
    '''
    
    @staticmethod
    def jitter(value, variance_percent=0.15):
        '''
        为数值添加随机抖动
        
        参数：
            value: 基础值
            variance_percent: 变化百分比（0.15 = 15%）
            
        返回：
            float: 抖动后的值
        '''
        variance = value * variance_percent
        return value + random.uniform(-variance, variance)
    
    @staticmethod
    def sleep_with_jitter(base_duration, variance_percent=0.2):
        '''
        带抖动的睡眠
        
        参数：
            base_duration: 基础睡眠时间（秒）
            variance_percent: 变化百分比
        '''
        duration = TimingRandomizer.jitter(base_duration, variance_percent)
        time.sleep(max(0.01, duration))
    
    @staticmethod
    def get_random_interval(min_val, max_val):
        '''
        获取随机间隔（偏向中间值）
        
        使用 Beta 分布，产生更自然的随机分布
        
        参数：
            min_val: 最小值
            max_val: 最大值
            
        返回：
            float: 随机值
        '''
        # Beta(2,2) 分布呈钟形曲线
        beta_value = random.betavariate(2, 2)
        return min_val + (max_val - min_val) * beta_value


# ============================================================
# 全局实例管理
# ============================================================

_human_behavior = None

def get_human_behavior(cfg=None):
    '''
    获取全局 HumanBehavior 实例
    
    参数：
        cfg: 可选的配置字典
        
    返回：
        HumanBehavior: 全局实例
    '''
    global _human_behavior
    if _human_behavior is None:
        _human_behavior = HumanBehavior(cfg)
    return _human_behavior

def init_anti_detect(cfg):
    '''
    使用配置初始化反检测系统
    
    参数：
        cfg: 配置字典
    '''
    global _human_behavior
    _human_behavior = HumanBehavior(cfg)
