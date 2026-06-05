# test_debug.py
# 用于测试langchain_food_agent中的用户偏好保存和更新问题

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_user_profile_persistence():
    """测试用户档案的持久性和更新功能"""
    print("=== 开始测试用户档案持久性 ===\n")
    
    # 导入所需模块
    from agents.langchain_food_agent import (
        user_profile as global_user_profile,
        get_user_preferences,
        collect_user_preferences,
        _internal_detect_user_intent,
        LangChainFoodAgent
    )
    from models.user_profile import UserProfile
    
    # 1. 检查初始状态
    print("1. 初始状态测试:")
    print(f"   全局 user_profile: {global_user_profile}")
    result = get_user_preferences.func()
    print(f"   get_user_preferences结果: {result}\n")
    
    # 2. 设置初始偏好
    print("2. 设置初始偏好:")
    initial_prefs = "偏好口味：清淡\n忌口：香菜\n过敏原：芒果\n健康目标：减肥"
    collect_result = collect_user_preferences.func(initial_prefs)
    print(f"   设置初始偏好结果: {collect_result}")
    
    # 检查全局变量是否已更新
    print(f"   更新后全局 user_profile: {global_user_profile}")
    if global_user_profile:
        print(f"   详细信息 - 口味: {global_user_profile.preferences}, 忌口: {global_user_profile.dietary_restrictions}, 过敏原: {global_user_profile.allergies}, 目标: {global_user_profile.health_goals}")
    
    result_after_set = get_user_preferences.func()
    print(f"   设置后get_user_preferences结果: {result_after_set}\n")
    
    # 3. 测试意图检测
    print("3. 意图检测测试:")
    test_inputs = [
        "我不吃鱼",
        "我不吃柠檬",
        "输出我的饮食习惯",
        "生成食谱"
    ]
    
    for test_input in test_inputs:
        intent = _internal_detect_user_intent(test_input)
        print(f"   输入: '{test_input}' -> 意图: {intent}")
    
    # 4. 测试LangChainFoodAgent
    print("\n4. LangChainFoodAgent测试:")
    agent = LangChainFoodAgent()
    
    # 处理初始偏好设置
    print("   处理初始偏好设置...")
    response1 = agent.process_user_input("偏好口味：麻辣\n忌口：葱，姜，蒜\n过敏原：花生，大豆\n健康目标：减肥")
    print(f"   偏好设置响应: {response1}")
    
    # 检查当前用户档案 - 修正属性访问
    print(f"   agent.agent.user_profile: 不存在此属性")
    print(f"   agent.profile_completed: {agent.profile_completed}")
    from agents.langchain_food_agent import user_profile as langchain_food_agent
    print(f"   全局 user_profile: {langchain_food_agent.user_profile}")
    if langchain_food_agent.user_profile:
        print(f"   详细信息 - 口味: {langchain_food_agent.user_profile.preferences}, 忌口: {langchain_food_agent.user_profile.dietary_restrictions}, 过敏原: {langchain_food_agent.user_profile.allergies}, 目标: {langchain_food_agent.user_profile.health_goals}")
    
    # 尝试更新饮食限制
    print("\n   尝试更新饮食限制...")
    response2 = agent.process_user_input("我不吃鱼")
    print(f"   更新饮食限制响应: {response2}")
    
    # 再次检查用户档案
    print(f"   更新后agent.user_profile: {agent.agent.user_profile}")
    if agent.agent.user_profile:
        print(f"   详细信息 - 口味: {agent.agent.user_profile.preferences}, 忌口: {agent.agent.user_profile.dietary_restrictions}, 过敏原: {agent.agent.user_profile.allergies}, 目标: {agent.agent.user_profile.health_goals}")
    
    # 查询当前偏好
    print("\n   查询当前偏好...")
    response3 = agent.process_user_input("输出我的饮食习惯")
    print(f"   查询偏好响应: {response3}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_user_profile_persistence()