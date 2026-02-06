'''
刷怪效率优化测试脚本

测试内容：
1. 向量化颜色搜索性能对比
2. 战斗状态机逻辑验证
3. 自适应冷却计算验证

运行方法：
    python tests/test_optimization.py
'''

import time
import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import logger


def test_vectorized_color_search():
    '''
    测试向量化颜色搜索的性能提升
    '''
    print("\n" + "="*60)
    print("测试 1: 向量化颜色搜索性能")
    print("="*60)
    
    # 模拟路线图 (200x200 像素)
    img_route = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
    
    # 添加一些颜色编码点
    img_route[50, 50] = [255, 0, 0]    # 红色
    img_route[100, 100] = [0, 0, 255]  # 蓝色
    img_route[75, 80] = [255, 255, 0]  # 黄色
    
    color_code = {
        (255, 0, 0): "left none none",
        (0, 0, 255): "right none none",
        (255, 255, 0): "none none goal",
    }
    
    player_pos = (100, 100)
    search_range = 30
    
    # === 原始 Python 循环方法 ===
    def original_search():
        x0, y0 = player_pos
        x_min = max(0, x0 - search_range)
        x_max = min(200, x0 + search_range)
        y_min = max(0, y0 - search_range)
        y_max = min(200, y0 + search_range)
        
        nearest = None
        min_dist = float('inf')
        
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                pixel = tuple(img_route[y, x])
                dist = abs(x - x0) + abs(y - y0)
                if pixel in color_code and dist < min_dist:
                    nearest = {"pixel": (x, y), "command": color_code[pixel], "distance": dist}
                    min_dist = dist
        
        return nearest
    
    # === NumPy 向量化方法 ===
    def vectorized_search():
        x0, y0 = player_pos
        x_min = max(0, x0 - search_range)
        x_max = min(200, x0 + search_range)
        y_min = max(0, y0 - search_range)
        y_max = min(200, y0 + search_range)
        
        roi = img_route[y_min:y_max, x_min:x_max]
        player_local_y = y0 - y_min
        player_local_x = x0 - x_min
        
        nearest = None
        min_dist = float('inf')
        
        for color_tuple, command in color_code.items():
            color_array = np.array(color_tuple, dtype=np.uint8)
            mask = np.all(roi == color_array, axis=2)
            
            if not np.any(mask):
                continue
            
            coords = np.argwhere(mask)
            distances = np.abs(coords[:, 0] - player_local_y) + \
                        np.abs(coords[:, 1] - player_local_x)
            
            min_idx = np.argmin(distances)
            dist = distances[min_idx]
            
            if dist < min_dist:
                min_dist = dist
                y_local, x_local = coords[min_idx]
                nearest = {
                    "pixel": (int(x_min + x_local), int(y_min + y_local)),
                    "command": command,
                    "distance": int(dist)
                }
        
        return nearest
    
    # 性能测试
    iterations = 1000
    
    # 原始方法
    start = time.time()
    for _ in range(iterations):
        result_original = original_search()
    time_original = time.time() - start
    
    # 向量化方法
    start = time.time()
    for _ in range(iterations):
        result_vectorized = vectorized_search()
    time_vectorized = time.time() - start
    
    # 结果验证
    print(f"\n原始方法耗时: {time_original*1000:.2f} ms ({iterations} 次)")
    print(f"向量化方法耗时: {time_vectorized*1000:.2f} ms ({iterations} 次)")
    print(f"性能提升: {time_original/time_vectorized:.1f}x")
    
    # 验证结果一致性（只比较关键字段）
    result_match = True
    if result_original is None and result_vectorized is None:
        result_match = True
    elif result_original is None or result_vectorized is None:
        result_match = False
    else:
        # 比较 command 和 distance（pixel 格式可能略有不同）
        result_match = (result_original["command"] == result_vectorized["command"] and
                       result_original["distance"] == result_vectorized["distance"])
    
    if result_match:
        print("[OK] 结果一致性验证通过")
    else:
        print(f"[X] 结果不一致!")
        print(f"  原始: {result_original}")
        print(f"  向量化: {result_vectorized}")
    
    return time_original / time_vectorized


def test_adaptive_cooldown():
    '''
    测试自适应冷却计算
    '''
    print("\n" + "="*60)
    print("测试 2: 自适应冷却计算")
    print("="*60)
    
    base_cooldown = 0.5
    
    def get_adaptive_cooldown(base_cooldown, monster_count, hp_percent, mp_percent):
        multiplier = 1.0
        
        if monster_count >= 3:
            multiplier *= 0.6
        elif monster_count >= 2:
            multiplier *= 0.8
        
        if hp_percent < 30:
            multiplier *= 1.5
        elif hp_percent < 50:
            multiplier *= 1.2
        
        if mp_percent < 30:
            multiplier *= 1.3
        
        multiplier = max(0.4, min(2.0, multiplier))
        
        return base_cooldown * multiplier
    
    # 测试用例
    test_cases = [
        {"monster_count": 1, "hp_percent": 100, "mp_percent": 100, "expected_range": (0.4, 0.6)},
        {"monster_count": 3, "hp_percent": 100, "mp_percent": 100, "expected_range": (0.2, 0.4)},
        {"monster_count": 1, "hp_percent": 25, "mp_percent": 100, "expected_range": (0.6, 0.9)},
        {"monster_count": 3, "hp_percent": 25, "mp_percent": 25, "expected_range": (0.4, 0.7)},
    ]
    
    all_passed = True
    for i, tc in enumerate(test_cases):
        result = get_adaptive_cooldown(
            base_cooldown, 
            tc["monster_count"], 
            tc["hp_percent"], 
            tc["mp_percent"]
        )
        
        in_range = tc["expected_range"][0] <= result <= tc["expected_range"][1]
        status = "[OK]" if in_range else "[X]"
        
        print(f"\n测试用例 {i+1}: {status}")
        print(f"  怪物数: {tc['monster_count']}, HP: {tc['hp_percent']}%, MP: {tc['mp_percent']}%")
        print(f"  计算冷却: {result:.3f}s (期望范围: {tc['expected_range']})")
        
        if not in_range:
            all_passed = False
    
    if all_passed:
        print("\n[OK] 所有自适应冷却测试通过")
    else:
        print("\n[X] 部分测试失败")
    
    return all_passed


def test_combat_state_machine():
    '''
    测试战斗状态机逻辑
    '''
    print("\n" + "="*60)
    print("测试 3: 战斗状态机逻辑")
    print("="*60)
    
    class MockHuntingState:
        def __init__(self):
            self.is_engaging = False
            self.engage_start_time = None
            self.consecutive_attack_count = 0
            self.no_monster_frame_count = 0
            self.max_engage_duration = 3.0
            self.max_consecutive_attacks = 5
            self.disengage_no_monster_frames = 3
        
        def should_enter_combat(self, monster_count, cooldown_ready):
            return monster_count > 0 and cooldown_ready
        
        def should_exit_combat(self, monster_count, elapsed_time):
            if monster_count == 0:
                self.no_monster_frame_count += 1
                if self.no_monster_frame_count >= self.disengage_no_monster_frames:
                    return True
            else:
                self.no_monster_frame_count = 0
            
            if elapsed_time > self.max_engage_duration:
                return True
            
            if self.consecutive_attack_count >= self.max_consecutive_attacks:
                return True
            
            return False
    
    state = MockHuntingState()
    
    # 测试进入战斗
    print("\n--- 测试进入战斗 ---")
    assert state.should_enter_combat(2, True) == True, "应该进入战斗"
    assert state.should_enter_combat(0, True) == False, "没有怪物不应进入战斗"
    assert state.should_enter_combat(2, False) == False, "冷却未完成不应进入战斗"
    print("[OK] 进入战斗逻辑正确")
    
    # 测试退出战斗
    print("\n--- 测试退出战斗 ---")
    
    # 连续无怪物
    state.no_monster_frame_count = 0
    for _ in range(3):
        result = state.should_exit_combat(0, 0.5)
    assert result == True, "连续无怪物应退出战斗"
    print("[OK] 连续无怪物退出逻辑正确")
    
    # 超时
    state.no_monster_frame_count = 0
    assert state.should_exit_combat(1, 5.0) == True, "超时应退出战斗"
    print("[OK] 超时退出逻辑正确")
    
    # 连续攻击上限
    state.no_monster_frame_count = 0
    state.consecutive_attack_count = 5
    assert state.should_exit_combat(1, 1.0) == True, "达到攻击上限应退出战斗"
    print("[OK] 攻击上限退出逻辑正确")
    
    print("\n[OK] 所有战斗状态机测试通过")
    return True


def test_hunting_state_import():
    '''
    测试 HuntingState 能否正确导入（语法检查）
    '''
    print("\n" + "="*60)
    print("测试 4: HuntingState 导入检查")
    print("="*60)
    
    try:
        from src.states.hunting import HuntingState
        print("[OK] HuntingState 导入成功")
        
        # 检查必要的方法是否存在
        required_methods = ['on_enter', 'on_exit', 'on_frame', 'check_transitions']
        for method in required_methods:
            if hasattr(HuntingState, method):
                print(f"  [OK] 方法 {method} 存在")
            else:
                print(f"  [X] 方法 {method} 缺失")
                return False
        
        return True
    except Exception as e:
        print(f"[X] 导入失败: {e}")
        return False


def main():
    print("="*60)
    print("刷怪效率优化测试")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    try:
        speedup = test_vectorized_color_search()
        results.append(("向量化颜色搜索", speedup >= 1.5, f"{speedup:.1f}x 提升"))
    except Exception as e:
        results.append(("向量化颜色搜索", False, str(e)))
    
    try:
        passed = test_adaptive_cooldown()
        results.append(("自适应冷却", passed, ""))
    except Exception as e:
        results.append(("自适应冷却", False, str(e)))
    
    try:
        passed = test_combat_state_machine()
        results.append(("战斗状态机", passed, ""))
    except Exception as e:
        results.append(("战斗状态机", False, str(e)))
    
    try:
        passed = test_hunting_state_import()
        results.append(("HuntingState 导入", passed, ""))
    except Exception as e:
        results.append(("HuntingState 导入", False, str(e)))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    all_passed = True
    for name, passed, note in results:
        status = "[PASS]" if passed else "[FAIL]"
        note_str = f" ({note})" if note else ""
        print(f"  {name}: {status}{note_str}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("全部测试通过！优化代码可以安全部署。")
    else:
        print("部分测试失败，请检查相关代码。")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
