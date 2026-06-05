# debug_test.py
# 用于测试工具调用的调试脚本

def test_tools_manually():
    """手动测试各个工具函数"""
    import sys
    import os
    
    # 添加项目根目录到Python路径
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # 导入所需的模块
    from agents.langchain_food_agent import (
        get_user_preferences,
        collect_user_preferences,
        generate_recipe,
        get_cooking_guide,
        analyze_nutrition,
        user_profile
    )
    from models.user_profile import UserProfile
    
    print("=== 开始测试工具函数 ===\n")
    
    # 测试1: 获取用户偏好（应该显示为空）
    print("测试1: 获取用户偏好（无数据时）")
    result1 = get_user_preferences.func()
    print(f"结果: {result1}\n")
    
    # 测试2: 收集用户偏好
    print("测试2: 收集用户偏好")
    preferences_input = "偏好口味：清淡\n忌口：香菜\n过敏原：芒果\n健康目标：减肥"
    result2 = collect_user_preferences.func(preferences_input)
    print(f"结果: {result2}\n")
    
    # 测试3: 再次获取用户偏好（应该显示刚才保存的数据）
    print("测试3: 获取用户偏好（有数据时）")
    result3 = get_user_preferences.func()
    print(f"结果: {result3}\n")
    
    # 测试4: 生成食谱
    print("测试4: 生成食谱")
    result4 = generate_recipe.func("生成一个食谱")
    print(f"结果: {result4}\n")
    
    # 测试5: 获取烹饪指导（假设当前食谱名称）
    print("测试5: 获取烹饪指导")
    # 注意：这里需要知道当前食谱的名称
    from agents.langchain_food_agent import current_recipe
    if current_recipe:
        result5 = get_cooking_guide.func(current_recipe['name'])
        print(f"结果: {result5}\n")
    else:
        print("无法测试烹饪指导，因为没有当前食谱\n")
    
    # 测试6: 分析营养成分
    print("测试6: 分析营养成分")
    if current_recipe:
        result6 = analyze_nutrition.func(current_recipe['name'])
        print(f"结果: {result6}\n")
    else:
        print("无法测试营养分析，因为没有当前食谱\n")
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_tools_manually()
# debug_test.py
# 用于测试工具调用的调试脚本

def test_tools_manually():
    """手动测试各个工具函数"""
    import sys
    import os
    
    # 添加项目根目录到Python路径
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # 导入所需的模块
    from agents.langchain_food_agent import (
        get_user_preferences,
        collect_user_preferences,
        generate_recipe,
        get_cooking_guide,
        analyze_nutrition,
        user_profile
    )
    from models.user_profile import UserProfile
    
    print("=== 开始测试工具函数 ===\n")
    
    # 测试1: 获取用户偏好（应该显示为空）
    print("测试1: 获取用户偏好（无数据时）")
    result1 = get_user_preferences.func()
    print(f"结果: {result1}\n")
    
    # 测试2: 收集用户偏好
    print("测试2: 收集用户偏好")
    preferences_input = "偏好口味：清淡\n忌口：香菜\n过敏原：芒果\n健康目标：减肥"
    result2 = collect_user_preferences.func(preferences_input)
    print(f"结果: {result2}\n")
    
    # 测试3: 再次获取用户偏好（应该显示刚才保存的数据）
    print("测试3: 获取用户偏好（有数据时）")
    result3 = get_user_preferences.func()
    print(f"结果: {result3}\n")
    
    # 测试4: 生成食谱
    print("测试4: 生成食谱")
    result4 = generate_recipe.func("生成一个食谱")
    print(f"结果: {result4}\n")
    
    # 测试5: 获取烹饪指导（假设当前食谱名称）
    print("测试5: 获取烹饪指导")
    # 注意：这里需要知道当前食谱的名称
    from agents.langchain_food_agent import current_recipe
    if current_recipe:
        result5 = get_cooking_guide.func(current_recipe['name'])
        print(f"结果: {result5}\n")
    else:
        print("无法测试烹饪指导，因为没有当前食谱\n")
    
    # 测试6: 分析营养成分
    print("测试6: 分析营养成分")
    if current_recipe:
        result6 = analyze_nutrition.func(current_recipe['name'])
        print(f"结果: {result6}\n")
    else:
        print("无法测试营养分析，因为没有当前食谱\n")
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_tools_manually()
# debug_test.py
# 用于测试工具调用的调试脚本

def test_tools_manually():
    """手动测试各个工具函数"""
    import sys
    import os
    
    # 添加项目根目录到Python路径
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # 导入所需的模块
    from agents.langchain_food_agent import (
        get_user_preferences,
        collect_user_preferences,
        generate_recipe,
        get_cooking_guide,
        analyze_nutrition,
        user_profile
    )
    from models.user_profile import UserProfile
    
    # 设置全局变量以模拟环境
    from agents.langchain_food_agent import (
        user_profile as up,
        recipe_generator,
        nutrition_analyzer,
        cooking_guide,
        current_recipe,
        temp_daily_preferences
    )
    import agents.langchain_food_agent as agent_module
    
    print("=== 开始测试工具函数 ===\n")
    
    # 测试1: 获取用户偏好（应该显示为空）
    print("测试1: 获取用户偏好（无数据时）")
    result1 = get_user_preferences.func()
    print(f"结果: {result1}\n")
    
    # 测试2: 收集用户偏好
    print("测试2: 收集用户偏好")
    preferences_input = "偏好口味：清淡\n忌口：香菜\n过敏原：芒果\n健康目标：减肥"
    result2 = collect_user_preferences.func(preferences_input)
    print(f"结果: {result2}\n")
    
    # 测试3: 再次获取用户偏好（应该显示刚才保存的数据）
    print("测试3: 获取用户偏好（有数据时）")
    result3 = get_user_preferences.func()
    print(f"结果: {result3}\n")
    
    # 测试4: 生成食谱
    print("测试4: 生成食谱")
    result4 = generate_recipe.func("生成一个食谱")
    print(f"结果: {result4}\n")
    
    # 测试5: 获取烹饪指导（假设当前食谱名称）
    print("测试5: 获取烹饪指导")
    # 注意：这里需要知道当前食谱的名称
    current_recipe_value = getattr(agent_module, 'current_recipe', None)
    if current_recipe_value:
        result5 = get_cooking_guide.func(current_recipe_value['name'])
        print(f"结果: {result5}\n")
    else:
        print("无法测试烹饪指导，因为没有当前食谱\n")
    
    # 测试6: 分析营养成分
    print("测试6: 分析营养成分")
    if current_recipe_value:
        result6 = analyze_nutrition.func(current_recipe_value['name'])
        print(f"结果: {result6}\n")
    else:
        print("无法测试营养分析，因为没有当前食谱\n")
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_tools_manually()