# agents/langchain_food_agent.py
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from models.user_profile import UserProfile
from config.settings import Settings
from tools.recipe_generator import RecipeGenerator
from tools.nutrition_analyzer import NutritionAnalyzer
from tools.cooking_guide import CookingGuide
from dataclasses import dataclass
from typing import Optional

# ===================== 配置 =========================
API_KEY = Settings.API_KEY
BASE_URL = Settings.BASE_URL
MODEL_NAME = Settings.MODEL_NAME
# ========================================================

# 定义系统提示
SYSTEM_PROMPT = """你是一个名叫“曦曦”的小猫，是一个饮食助手，一位专业的饮食顾问。你的性格活泼，有耐心，口头禅是“喵”。你的任务是帮助用户制定符合他们偏好的饮食计划。

你可以使用以下工具：
- get_user_preferences：获取用户的饮食偏好
- collect_user_preferences：收集并保存用户的饮食偏好
- generate_recipe：根据用户偏好生成食谱
- get_cooking_guide：获取烹饪指导
- analyze_nutrition：分析食谱营养成分

首先，你需要引导用户按照以下模板提供饮食偏好信息：
偏好口味：
忌口：
过敏原：
健康目标：

然后根据用户的信息提供合适的建议和服务。"""

@tool
def get_user_preferences() -> str:
    """获取用户的饮食偏好信息。"""
    print("[DEBUG] 调用了 get_user_preferences 工具")
    global user_profile
    if user_profile:
        result = f"偏好口味：{user_profile.preferences}\n忌口：{user_profile.dietary_restrictions}\n过敏原：{user_profile.allergies}\n健康目标：{user_profile.health_goals}"
        print(f"[DEBUG] 返回用户偏好信息: {result}")
        return result
    else:
        result = "用户尚未提供饮食偏好信息。"
        print(f"[DEBUG] 返回: {result}")
    return result


@tool
def get_user_preferences_for_display() -> str:
    """获取用户的饮食偏好信息，用于显示。"""
    global user_profile
    if user_profile:
        # 检查各项是否为空，如为空则显示相应提示
        preferences = user_profile.preferences if user_profile.preferences else "未记录"
        dietary_restrictions = user_profile.dietary_restrictions if user_profile.dietary_restrictions else "未记录"
        allergies = user_profile.allergies if user_profile.allergies else "未记录"
        health_goals = user_profile.health_goals if user_profile.health_goals else "未记录"
        
        result = f"目前记录的您的饮食习惯如下：\n\n- 偏好口味：{preferences}\n- 忌口：{dietary_restrictions}\n- 过敏原：{allergies}\n- 健康目标：{health_goals}\n\n如果您有任何其他饮食偏好、忌口、过敏原或健康目标，请告诉我，我会为您更新记录。"
        return result
    else:
        result = "目前还没有记录您的任何饮食偏好信息。请告诉我：\n- 您的偏好口味\n- 忌口\n- 过敏原\n- 健康目标\n\n例如：\n偏好口味：清淡\n忌口：香菜\n过敏原：芒果\n健康目标：减肥"
    return result


@tool
def update_dietary_restrictions(restriction_type: str, items: str) -> str:
    """更新饮食限制，包括忌口和过敏原。"""
    global user_profile
    if not user_profile:
        return "请先设置您的基本饮食偏好信息，然后再更新饮食限制。"
    
    if restriction_type == "restriction":  # 忌口
        if user_profile.dietary_restrictions:
            # 分割现有的忌口项，避免重复添加
            existing_restrictions = [r.strip() for r in user_profile.dietary_restrictions.split(",") if r.strip()]
            # 检查新项是否已经在列表中
            new_items = [item.strip() for item in items.split(",") if item.strip()]
            for item in new_items:
                if item not in existing_restrictions:
                    existing_restrictions.append(item)
            user_profile.dietary_restrictions = ", ".join(existing_restrictions)
        else:
            user_profile.dietary_restrictions = items
        return f"已更新您的忌口信息：{user_profile.dietary_restrictions}"
    elif restriction_type == "allergy":  # 过敏原
        if user_profile.allergies:
            # 分割现有的过敏原，避免重复添加
            existing_allergies = [a.strip() for a in user_profile.allergies.split(",") if a.strip()]
            # 检查新项是否已经在列表中
            new_items = [item.strip() for item in items.split(",") if item.strip()]
            for item in new_items:
                if item not in existing_allergies:
                    existing_allergies.append(item)
            user_profile.allergies = ", ".join(existing_allergies)
        else:
            user_profile.allergies = items
        return f"已更新您的过敏原信息：{user_profile.allergies}"
    else:
        return "无效的限制类型，请使用 'restriction' 或 'allergy'。"


# 内部函数用于意图检测，避免直接调用工具
def _internal_detect_user_intent(user_input: str) -> str:
    """内部函数：检测用户输入意图：profile_setup（个人资料设置）, dietary_update（饮食规则更新）, daily_preference（每日临时偏好）, recipe_request（食谱请求）, recipe_confirmation（菜谱确认）, cooking_step（烹饪步骤控制）, previous_step（上一步）, nutrition_summary（营养总结）, or general（一般对话）"""
    user_input_lower = user_input.lower().strip()
    
    # 优先检查：换一道、换一个、重新生成等明确的换菜请求
    change_keywords = ["换一道", "换一个", "换一", "换别的", "重新生成", "重新来", "换一道菜", "换菜", "换别的菜", "换其他"]
    if any(keyword in user_input_lower for keyword in change_keywords):
        return "recipe_request"
    
    # 检查"不想吃"后面跟食材或食物类型的情况 - 这是菜谱请求（排除特定食物）
    if "不想吃" in user_input:
        food_types = ["素", "肉", "鱼", "鸡", "牛", "猪", "沙拉", "火锅", "烧烤", "炒菜", "汤", "面", "饭", "点心", "甜点", "海鲜", "蛋"]
        if any(food in user_input for food in food_types):
            return "recipe_request"
    
    # 检查是否是完整的偏好信息输入 - 更宽松的检测
    # 检查是否包含多个偏好字段
    preference_fields = ['偏好口味', '口味', '忌口', '过敏原', '过敏', '健康目标', '目标']
    found_fields = [field for field in preference_fields if field in user_input]
    
    # 如果包含至少3个偏好字段，视为偏好设置
    if len(found_fields) >= 3:
        return "profile_setup"
    
    # 检查是否明确包含偏好设置的关键词组合
    has_flavor = any(kw in user_input for kw in ["偏好口味", "口味", "偏好"])
    has_restriction = any(kw in user_input for kw in ["忌口", "不能吃", "不吃"])
    has_allergy = any(kw in user_input for kw in ["过敏原", "过敏"])
    has_goal = any(kw in user_input for kw in ["健康目标", "目标"])
    
    if (has_flavor or has_restriction or has_allergy or has_goal) and len(user_input) > 20:
        # 如果包含偏好关键词且长度足够，可能是偏好设置
        field_count = sum([has_flavor, has_restriction, has_allergy, has_goal])
        if field_count >= 2:
            return "profile_setup"
    
    # 检测是否为饮食规则更新（只有在不是完整设置时才判断为更新）
    # 注意：这里只检测明确的"不能吃"、"过敏"等长期限制
    # 排除"换一道"等换菜请求，因为这些是recipe_request
    change_keywords = ["换一道", "换一个", "换一", "换别的", "重新生成", "重新来", "换一道菜", "换菜"]
    is_change_request = any(keyword in user_input_lower for keyword in change_keywords)
    
    # 只有在不是换菜请求时才检查dietary_update
    if not is_change_request:
        dietary_keywords = ["过敏", "过敏原", "不能吃", "不能", "不可以", "禁忌", "忌口", "不耐受", "禁食"]
        dietary_indicators = [keyword for keyword in dietary_keywords if keyword in user_input_lower]
        
        # 检查是否包含"我不吃"表达
        has_not_eat = "我不吃" in user_input_lower
        
        # 排除那些看起来像是完整设置的情况
        if dietary_indicators and not (has_flavor and has_restriction and (has_allergy or has_goal)):
            return "dietary_update"
        elif has_not_eat:
            # 检查"我不吃"后面是否有具体的食材
            food_items = ["鱼", "肉", "鸡", "牛", "猪", "蛋", "奶", "豆", "花生", "海鲜", "虾", "蟹", "贝类", "葱", "姜", "蒜", "柠檬", "苹果", "香蕉", "橘子", "草莓", "葡萄", "西瓜", "梨", "桃", "杏", "李", "橙", "柚", "猕猴桃", "芒果", "菠萝", "火龙果", "蓝莓", "覆盆子", "黑莓", "桑葚", "石榴", "柿子", "枣", "栗子", "核桃", "杏仁", "腰果", "开心果", "榛子", "夏威夷果", "松子", "葵花籽", "南瓜籽", "芝麻", "大豆", "小麦", "玉米", "大米", "小米", "燕麦", "荞麦", "薏米", "绿豆", "红豆", "黑豆", "黄豆", "豆腐", "豆浆", "腐竹", "豆皮", "豆芽", "韭菜", "香菜", "芹菜", "菠菜", "小白菜", "油菜", "生菜", "白菜", "卷心菜", "紫甘蓝", "胡萝卜", "白萝卜", "青萝卜", "土豆", "红薯", "山药", "芋头", "莲藕", "竹笋", "冬瓜", "黄瓜", "丝瓜", "苦瓜", "南瓜", "茄子", "西红柿", "辣椒", "青椒", "红椒", "黄椒", "洋葱", "大蒜", "生姜", "香葱", "大葱", "蘑菇", "香菇", "平菇", "金针菇", "杏鲍菇", "木耳", "银耳", "海带", "紫菜", "裙带菜"]
            if any(item in user_input_lower for item in food_items):
                return "dietary_update"
    
    # 检测是否为每日偏好（临时性）- "今天不想吃"、"今天不要"等表达
    # 只有在明确的临时表达时才判断为每日偏好
    daily_keywords = ["今天不想", "今天不要", "暂时不想", "暂时不要"]
    has_specific_daily = any(keyword in user_input_lower for keyword in daily_keywords)
    
    # 检测是否有食材提及（食物名称）
    ingredient_indicators = ["鸡肉", "牛肉", "猪肉", "鱼", "虾", "花生", "鸡蛋", "牛奶", "大豆", "坚果", "海鲜", "胡萝卜", "洋葱", "西兰花", "白菜", "米饭", "面条", "沙拉"]
    has_ingredient = any(ingredient in user_input for ingredient in ingredient_indicators)
    
    # 如果有"今天不想"或"今天不要"且提到食材，则是每日临时偏好
    if has_specific_daily and has_ingredient:
        return "daily_preference"
    
    # 检查是否是食谱请求的核心关键词组合 - 优先检查明确的请求
    if "生成" in user_input_lower and any(keyword in user_input_lower for keyword in ["食谱", "菜谱", "菜"]):
        return "recipe_request"
    
    # 检查是否包含食谱相关词汇 - 这是最直接的检测
    if any(keyword in user_input_lower for keyword in ["食谱", "菜谱"]):
        return "recipe_request"
    
    # 检查包含"菜谱"的表达
    if "菜谱" in user_input_lower:
        # 检查是否是要求生成或获取菜谱
        if any(action in user_input_lower for action in ["生成", "推荐", "来", "给", "做", "弄", "要", "想要", "求", "给我", "确定"]):
            return "recipe_request"
        # 如果只是提及菜谱，也可能是在请求
        return "recipe_request"
    
    # 检查"换一道"、"重新生成"、"换一个"等表达
    change_keywords = ["换一道", "换一个", "换一", "换别的", "重新生成", "重新来", "换一道菜", "换菜"]
    if any(keyword in user_input_lower for keyword in change_keywords):
        return "recipe_request"
    
    # 检查"不想吃"后面跟食材或食物类型的情况 - 这是菜谱请求
    if "不想吃" in user_input_lower or "不想吃全" in user_input_lower:
        # 检查是否跟着具体的食物类型
        food_types = ["素", "肉", "鱼", "鸡", "牛", "猪", "沙拉", "火锅", "烧烤", "炒菜", "汤", "面", "饭", "点心", "甜点"]
        if any(food in user_input for food in food_types):
            return "recipe_request"
    
    # 检查其他常见的食谱请求表达
    if "做" in user_input_lower and any(keyword in user_input_lower for keyword in ["食谱", "菜谱", "菜", "饭", "餐"]):
        return "recipe_request"
    
    # 检查"一道菜"这类表达
    if "一道菜" in user_input_lower or "换一道" in user_input_lower:
        return "recipe_request"
    
    # 检查其他食谱相关动作词
    if any(keyword in user_input_lower for keyword in ["想吃", "做", "弄", "推荐", "来", "生成", "要", "给我"]):
        # 如果同时包含食物相关词汇，则认为是食谱请求
        food_related = ["轻食", "中餐", "西餐", "日料", "韩料", "素食", "汤", "主食", "甜点", "沙拉", "烤肉", "火锅", "面条", "米饭", "菜", "饭", "餐"]
        if any(food in user_input_lower for food in food_related):
            return "recipe_request"
        # 如果是"想吃"，则直接认为是食谱请求
        if "想吃" in user_input_lower:
            return "recipe_request"
        # 如果是"生成"、"推荐"等，也倾向于认为是食谱请求
        if any(action in user_input_lower for action in ["生成", "推荐", "来", "要", "给我"]):
            return "recipe_request"
    
    # 检查模糊的食谱请求，如"做"、"弄"等词配合食物相关词汇
    if ("做" in user_input_lower or "弄" in user_input_lower) and (
        any(food in user_input_lower for food in ["菜", "饭", "餐", "汤", "点心"])
    ):
        return "recipe_request"
    
    # 检查"吃什么"这类表达
    if "吃什么" in user_input_lower:
        return "recipe_request"
    
    # 检查"做法"
    if "做法" in user_input_lower:
        return "recipe_request"
    
    # 检查是否只是想获取食谱（没有具体食材信息，但表达了想获取食谱的意愿）
    if any(keyword in user_input_lower for keyword in ["食谱", "菜谱", "推荐", "推荐一个", "给我一个", "做一个", "弄一个"]):
        return "recipe_request"
    
    # 检测菜谱确认意图
    # 只有在已经有食谱的情况下才识别为菜谱确认
    if any(keyword in user_input_lower for keyword in ["确定菜谱", "确认菜谱", "开始烹饪", "开始做", "就这样", "好的", "可以"]) and current_recipe:
        return "recipe_confirmation"
    
    # 如果用户说"确定菜谱"但没有现成的菜谱，可能是想生成菜谱
    if "确定菜谱" in user_input_lower:
        return "recipe_request"
    
    # 检测烹饪步骤控制
    if any(keyword in user_input_lower for keyword in ["好了", "完成", "下一步", "继续", "继续做", "做下一步", "下一部"]):
        return "cooking_step"
    
    # 检测上一步意图
    if any(keyword in user_input_lower for keyword in ["上一步", "上一部", "回去", "返回", "重做"]):
        return "previous_step"
    
    # 检测是否询问营养信息或完成烹饪
    if any(keyword in user_input_lower for keyword in ["营养", "分析", "完成", "做好了", "结束了", "做完", "小结", "总结", "营养成分"]):
        return "nutrition_summary"
    
    # 默认为一般性对话
    # 检查是否是对确认更新的回复
    if "__CONFIRM_UPDATE__" in user_input or "__END_CONFIRM__" in user_input:
        return "confirm_update"
    
    # 检查是否是确认按钮点击
    if "确认" in user_input and ("过敏" in user_input or "忌口" in user_input or "更新" in user_input):
        return "confirm_update"
    
    return "general"

@tool
def collect_user_preferences(preferences: str) -> str:
    """收集并保存用户的饮食偏好信息。"""
    print("[DEBUG] 调用了 collect_user_preferences 工具")
    print(f"[DEBUG] 输入的偏好信息: {preferences}")
    global user_profile
    # 解析偏好信息 - 支持多种格式（换行分隔或空格分隔）
    # 首先尝试按换行符分割
    lines = preferences.split('\n')
    
    # 如果只有一行，尝试按中文冒号和空格分割
    if len(lines) == 1 and ('偏好口味：' in preferences or '偏好口味:' in preferences):
        # 更精确的解析策略：查找每个类别及其内容
        import re
        
        # 按顺序查找每个类别
        categories = ['偏好口味', '忌口', '过敏原', '健康目标']
        pref_dict = {}
        
        for category in categories:
            # 查找 "类别：内容" 或 "类别:内容" 模式
            pattern = f'{category}[：:]([^\\s\\n]*)'
            match = re.search(pattern, preferences)
            if match:
                # 提取内容直到下一个类别开始或字符串结束
                content = match.group(1).strip()
                # 确保内容不会延伸到下一个类别
                next_categories = [cat for cat in categories if cat != category]
                for next_cat in next_categories:
                    # 找到下一个类别的位置
                    next_match = re.search(f'{next_cat}[：:]', content)
                    if next_match:
                        # 截取到下一个类别之前的内容
                        content = content[:next_match.start()].rstrip()
                        break
                pref_dict[category] = content
        
        # 重新构建带换行符的字符串以保持后续代码兼容
        processed_prefs = '\n'.join([f'{key}：{value}' for key, value in pref_dict.items()])
        lines = processed_prefs.split('\n')
    
    pref_dict = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '：' in line:
            key, value = line.split('：', 1)
            pref_dict[key.strip()] = value.strip()
        elif ':' in line:
            key, value = line.split(':', 1)
            pref_dict[key.strip()] = value.strip()
    
    # 创建或更新用户档案 - 保留现有信息并更新指定字段
    if user_profile:
        # 更新现有档案，只更新提供的字段
        if '偏好口味' in pref_dict:
            user_profile.preferences = pref_dict['偏好口味']
        if '忌口' in pref_dict:
            user_profile.dietary_restrictions = pref_dict['忌口']
        if '过敏原' in pref_dict:
            user_profile.allergies = pref_dict['过敏原']
        if '健康目标' in pref_dict:
            user_profile.health_goals = pref_dict['健康目标']
    else:
        # 如果没有现有档案，创建新档案
        user_profile = UserProfile(
            preferences=pref_dict.get('偏好口味', ''),
            dietary_restrictions=pref_dict.get('忌口', ''),
            allergies=pref_dict.get('过敏原', ''),
            health_goals=pref_dict.get('健康目标', '')
        )
    
    result = f"已保存您的饮食偏好信息：\n偏好口味：{user_profile.preferences}\n忌口：{user_profile.dietary_restrictions}\n过敏原：{user_profile.allergies}\n健康目标：{user_profile.health_goals}"
    print(f"[DEBUG] 返回结果: {result}")
    return result


# 内部函数用于直接处理偏好设置，避免工具调用问题
def _internal_collect_user_preferences(preferences: str) -> str:
    """内部函数：收集并保存用户的饮食偏好信息。"""
    print("[DEBUG] 调用了 _internal_collect_user_preferences 函数")
    print(f"[DEBUG] 输入的偏好信息: {preferences}")
    global user_profile
    
    # 解析偏好信息 - 使用更灵活的正则表达式
    import re
    
    # 定义可能的关键词
    keywords = ['偏好口味', '忌口', '过敏原', '健康目标', '口味', '过敏', '目标']
    
    # 构建更灵活的正则表达式
    pref_dict = {}
    
    for keyword in keywords:
        # 匹配 "关键字:内容" 或 "关键字：内容" 格式
        # 但要确保内容不跨越到下一个关键字
        if keyword == '偏好口味' or keyword == '口味':
            # 匹配偏好口味
            pattern = r'(?:偏好口味|口味)[：:](.*?)(?=(?:\n|$|忌口|过敏原|健康目标|过敏|目标))'
            match = re.search(pattern, preferences, re.DOTALL)
            if match:
                pref_dict['偏好口味'] = match.group(1).strip().strip(';，,。')
        elif keyword == '忌口':
            pattern = r'忌口[：:](.*?)(?=(?:\n|$|偏好口味|过敏原|健康目标|口味|过敏|目标))'
            match = re.search(pattern, preferences, re.DOTALL)
            if match:
                pref_dict['忌口'] = match.group(1).strip().strip(';，,。')
        elif keyword == '过敏原' or keyword == '过敏':
            pattern = r'(?:过敏原|过敏)[：:](.*?)(?=(?:\n|$|偏好口味|忌口|健康目标|口味|目标))'
            match = re.search(pattern, preferences, re.DOTALL)
            if match:
                pref_dict['过敏原'] = match.group(1).strip().strip(';，,。')
        elif keyword == '健康目标' or keyword == '目标':
            pattern = r'(?:健康目标|目标)[：:](.*?)(?=(?:\n|$|偏好口味|忌口|过敏原|口味|过敏))'
            match = re.search(pattern, preferences, re.DOTALL)
            if match:
                pref_dict['健康目标'] = match.group(1).strip().strip(';，,。')
    
    # 创建或更新用户档案
    if user_profile:
        # 更新现有档案
        if '偏好口味' in pref_dict:
            user_profile.preferences = pref_dict['偏好口味']
        if '忌口' in pref_dict:
            user_profile.dietary_restrictions = pref_dict['忌口']
        if '过敏原' in pref_dict:
            user_profile.allergies = pref_dict['过敏原']
        if '健康目标' in pref_dict:
            user_profile.health_goals = pref_dict['健康目标']
    else:
        # 创建新档案
        user_profile = UserProfile(
            preferences=pref_dict.get('偏好口味', ''),
            dietary_restrictions=pref_dict.get('忌口', ''),
            allergies=pref_dict.get('过敏原', ''),
            health_goals=pref_dict.get('健康目标', '')
        )
    
    result = f"已保存您的饮食偏好信息：\n偏好口味：{user_profile.preferences}\n忌口：{user_profile.dietary_restrictions}\n过敏原：{user_profile.allergies}\n健康目标：{user_profile.health_goals}"
    print(f"[DEBUG] 返回结果: {result}")
    return result

@tool
def generate_recipe(user_input: str) -> str:
    """根据用户偏好生成食谱。"""
    print("[DEBUG] 调用了 generate_recipe 工具")
    print(f"[DEBUG] 用户输入: {user_input}")
    global user_profile, current_recipe
    # 如果尚未有用户档案，尝试从本次输入中解析并保存偏好信息
    if not user_profile:
        pref_keys = ['偏好口味', '忌口', '过敏原', '健康目标', '偏好']
        if any(key in user_input for key in pref_keys):
            print("[DEBUG] generate_recipe: 在输入中检测到偏好字段，尝试保存偏好信息")
            try:
                pref_msg = collect_user_preferences.func(user_input)
            except Exception as e:
                print(f"[DEBUG] 保存偏好信息失败: {e}")

    if not user_profile:
        # 尝试从模块重新导入user_profile，以防在某些环境下全局变量未正确设置
        import importlib
        import agents.langchain_food_agent
        importlib.reload(agents.langchain_food_agent)
        user_profile = agents.langchain_food_agent.user_profile
        
        if not user_profile:
            result = "请先提供您的饮食偏好信息，这样我可以为您生成合适的食谱。"
            print(f"[DEBUG] 返回: {result}")
            return result
    
    # 创建临时档案以合并永久偏好和临时偏好
    temp_profile = UserProfile(
        preferences=user_profile.preferences,
        dietary_restrictions=user_profile.dietary_restrictions,
        allergies=user_profile.allergies,
        health_goals=user_profile.health_goals
    )
    
    # 合并临时偏好
    global temp_daily_preferences
    if temp_daily_preferences["exclude_ingredients"]:
        excluded_str = ", ".join(temp_daily_preferences["exclude_ingredients"])
        if temp_profile.dietary_restrictions:
            temp_profile.dietary_restrictions += ", " + excluded_str
        else:
            temp_profile.dietary_restrictions = excluded_str
    
    print(f"[DEBUG] 使用的用户档案: {temp_profile.to_dict()}")
    
    # 生成食谱
    recipe = recipe_generator.generate_recipe(temp_profile)
    current_recipe = recipe  # 保存当前食谱供后续使用
    
    # 清除临时偏好
    temp_daily_preferences = {
        "exclude_ingredients": [],
        "include_ingredients": [],
        "dish_type": "",
        "cooking_method": ""
    }
    steps_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(recipe.get('steps', []))])
    recipe_text = (
        f"为您生成的食谱：\n名称：{recipe['name']}\n食材：{', '.join(recipe['ingredients'])}\n烹饪时间：{recipe['cooking_time']}分钟\n难度：{recipe['difficulty']}\n营养信息：{recipe['nutrition_info']}\n\n做法：\n{steps_text}"
    )

    if pref_msg:
        result = pref_msg + "\n\n" + recipe_text
    else:
        result = recipe_text

    print(f"[DEBUG] 生成的食谱: {recipe}")
    print(f"[DEBUG] 返回结果: {result}")
    return result

@tool
def get_cooking_guide(recipe_name: str) -> str:
    """获取食谱的烹饪指导。"""
    print("[DEBUG] 调用了 get_cooking_guide 工具")
    print(f"[DEBUG] 请求的食谱名称: {recipe_name}")
    global current_recipe
    if current_recipe and current_recipe['name'] == recipe_name:
        # 返回完整的烹饪步骤列表
        steps_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(current_recipe['steps'])])
        result = f"喵~ 这是{recipe_name}的详细烹饪步骤：\n\n{steps_text}\n\n您可以告诉我'下一步'或'好了'，我会逐步指导您完成这道美味的料理喵～"
        print(f"[DEBUG] 返回烹饪指导")
        return result
    else:
        result = "请先生成食谱，然后我可以为您提供详细的烹饪指导。"
        print(f"[DEBUG] 返回: {result}")
    return result

@tool
def analyze_nutrition(recipe_name: str) -> str:
    """分析食谱的营养成分。"""
    print("[DEBUG] 调用了 analyze_nutrition 工具")
    print(f"[DEBUG] 请求分析的食谱名称: {recipe_name}")
    global current_recipe
    global user_profile
    if current_recipe and current_recipe['name'] == recipe_name:
        # 使用用户档案中的健康目标
        health_goals = user_profile.health_goals if user_profile else ""
        result = nutrition_analyzer.analyze_nutrition(current_recipe, health_goals)
        print(f"[DEBUG] 返回营养分析")
        return result
    else:
        result = "请先生成食谱，然后我可以为您分析营养成分。"
        print(f"[DEBUG] 返回: {result}")
        return result

@tool
def get_next_cooking_step(recipe_name: str) -> str:
    """获取下一步烹饪指导。"""
    print("[DEBUG] 调用了 get_next_cooking_step 工具")
    print(f"[DEBUG] 请求的食谱名称: {recipe_name}")
    global current_recipe, current_step_index
    
    if current_recipe and current_recipe['name'] == recipe_name:
        # 获取下一步指导
        step_response = cooking_guide.get_next_step(current_recipe, current_step_index)
        
        # 更新步骤索引
        current_step_index += 1
        
        print(f"[DEBUG] 返回下一步烹饪指导")
        return step_response
    else:
        result = "请先生成食谱，然后我可以为您提供烹饪指导。"
        print(f"[DEBUG] 返回: {result}")
        return result

@tool
def get_previous_cooking_step(recipe_name: str) -> str:
    """获取上一步烹饪指导。"""
    print("[DEBUG] 调用了 get_previous_cooking_step 工具")
    print(f"[DEBUG] 请求的食谱名称: {recipe_name}")
    global current_recipe, current_step_index
    
    if current_recipe and current_recipe['name'] == recipe_name:
        # 确保步骤索引不会小于0
        if current_step_index > 0:
            current_step_index -= 1  # 回退到上一步
            
        # 获取当前步骤指导（回退后的步骤）
        step_response = cooking_guide.get_next_step(current_recipe, current_step_index)
        
        print(f"[DEBUG] 返回上一步烹饪指导")
        return step_response
    else:
        result = "请先生成食谱，然后我可以为您提供烹饪指导。"
        print(f"[DEBUG] 返回: {result}")
        return result

@tool
def complete_cooking_and_get_nutrition(recipe_name: str) -> str:
    """完成烹饪并获取营养分析。"""
    print("[DEBUG] 调用了 complete_cooking_and_get_nutrition 工具")
    print(f"[DEBUG] 请求分析的食谱名称: {recipe_name}")
    global current_recipe, current_step_index
    global user_profile
    
    if current_recipe and current_recipe['name'] == recipe_name:
        # 重置步骤索引
        current_step_index = 0
        
        # 获取营养分析
        health_goals = user_profile.health_goals if user_profile else ""
        result = nutrition_analyzer.analyze_nutrition(current_recipe, health_goals)
        
        # 格式化为营养小结卡片
        nutrition_card = f"🎉 恭喜完成料理制作！让我来为你分析一下营养情况：\n\n"
        nutrition_card += f"📊 营养分析报告：\n"
        nutrition_card += f"• 总热量：{result['calories']} 千卡\n"
        nutrition_card += f"• 蛋白质：{result['protein']} 克\n"
        nutrition_card += f"• 碳水化合物：{result['carbs']} 克\n"
        nutrition_card += f"• 脂肪：{result['fat']} 克\n"
        nutrition_card += f"• 维生素：{result['vitamins']}\n"
        nutrition_card += f"• 矿物质：{result['minerals']}\n"
        nutrition_card += f"• 健康评分：{result['health_score']}/10\n\n"
        nutrition_card += f"💡 {result['recommendations']}\n\n"
        nutrition_card += f"📋 {result['reference_guide']}\n\n"
        nutrition_card += f"曦曦觉得这顿饭很健康呢～记得按时吃饭哦！"
        
        print(f"[DEBUG] 返回营养小结卡片")
        return nutrition_card
    else:
        result = "请生成食谱，然后我可以为您分析营养成分。"
        print(f"[DEBUG] 返回: {result}")
        return result

@tool
def detect_user_intent(user_input: str) -> str:
    """检测用户输入意图：profile_setup（个人资料设置）, dietary_update（饮食规则更新）, daily_preference（每日临时偏好）, recipe_request（食谱请求）, cooking_step（烹饪步骤控制）, previous_step（上一步）, nutrition_summary（营养总结）, or general（一般对话）"""
    user_input_lower = user_input.lower().strip()
    
    # 检查是否是完整的偏好信息输入 - 更宽松的检测
    # 检查是否包含多个偏好字段
    preference_fields = ['偏好口味', '口味', '忌口', '过敏原', '过敏', '健康目标', '目标']
    found_fields = [field for field in preference_fields if field in user_input]
    
    # 如果包含至少3个偏好字段，视为偏好设置
    if len(found_fields) >= 3:
        return "profile_setup"
    
    # 检查是否明确包含偏好设置的关键词组合
    has_flavor = any(kw in user_input for kw in ["偏好口味", "口味", "偏好"])
    has_restriction = any(kw in user_input for kw in ["忌口", "不能吃", "不吃"])
    has_allergy = any(kw in user_input for kw in ["过敏原", "过敏"])
    has_goal = any(kw in user_input for kw in ["健康目标", "目标"])
    
    if (has_flavor or has_restriction or has_allergy or has_goal) and len(user_input) > 20:
        # 如果包含偏好关键词且长度足够，可能是偏好设置
        field_count = sum([has_flavor, has_restriction, has_allergy, has_goal])
        if field_count >= 2:
            return "profile_setup"
    
    # 检测是否为饮食规则更新（只有在不是完整设置时才判断为更新）
    dietary_keywords = ["过敏", "过敏原", "不能吃", "不能", "不可以", "禁忌", "忌口", "不耐受", "禁食"]
    dietary_indicators = [keyword for keyword in dietary_keywords if keyword in user_input_lower]
    
    # 排除那些看起来像是完整设置的情况
    if dietary_indicators and not (has_flavor and has_restriction and (has_allergy or has_goal)):
        return "dietary_update"
    
    # 检测是否为每日偏好（临时性）
    daily_keywords = ["今天", "今天不想", "今天不要", "现在", "暂时", "不想吃", "不吃", "不要"]
    daily_indicators = [keyword for keyword in daily_keywords if keyword in user_input_lower]
    
    # 检测是否有特定食材
    ingredient_indicators = ["鸡肉", "牛肉", "猪肉", "鱼", "虾", "花生", "鸡蛋", "牛奶", "大豆", "坚果", "海鲜"]
    has_ingredient = any(ingredient in user_input for ingredient in ingredient_indicators)
    
    if daily_indicators and has_ingredient:
        return "daily_preference"
    
    # 检查是否是食谱请求的核心关键词组合 - 优先检查明确的请求
    if "生成" in user_input_lower and any(keyword in user_input_lower for keyword in ["食谱", "菜谱", "菜"]):
        return "recipe_request"
    
    # 检查是否包含食谱相关词汇 - 这是最直接的检测
    if any(keyword in user_input_lower for keyword in ["食谱", "菜谱"]):
        return "recipe_request"
    
    # 检查其他常见的食谱请求表达
    if "做" in user_input_lower and any(keyword in user_input_lower for keyword in ["食谱", "菜谱", "菜", "饭", "餐"]):
        return "recipe_request"
    
    # 检查其他食谱相关动作词
    if any(keyword in user_input_lower for keyword in ["想吃", "做", "弄", "推荐", "来", "生成", "要", "给我"]):
        # 如果同时包含食物相关词汇，则认为是食谱请求
        food_related = ["轻食", "中餐", "西餐", "日料", "韩料", "素食", "汤", "主食", "甜点", "沙拉", "烤肉", "火锅", "面条", "米饭", "菜", "饭", "餐"]
        if any(food in user_input_lower for food in food_related):
            return "recipe_request"
        # 如果是"想吃"，则直接认为是食谱请求
        if "想吃" in user_input_lower:
            return "recipe_request"
        # 如果是"生成"、"推荐"等，也倾向于认为是食谱请求
        if any(action in user_input_lower for action in ["生成", "推荐", "来", "要", "给我"]):
            return "recipe_request"
    
    # 检查模糊的食谱请求，如"做"、"弄"等词配合食物相关词汇
    if ("做" in user_input_lower or "弄" in user_input_lower) and (
        any(food in user_input_lower for food in ["菜", "饭", "餐", "汤", "点心"])
    ):
        return "recipe_request"
    
    # 检查"吃什么"这类表达
    if "吃什么" in user_input_lower:
        return "recipe_request"
    
    # 检查"做法"
    if "做法" in user_input_lower:
        return "recipe_request"
    
    # 检查是否只是想获取食谱（没有具体食材信息，但表达了想获取食谱的意愿）
    if any(keyword in user_input_lower for keyword in ["食谱", "菜谱", "推荐", "推荐一个", "给我一个", "做一个", "弄一个"]):
        return "recipe_request"
    
    # 检测烹饪步骤控制
    if any(keyword in user_input_lower for keyword in ["好了", "完成", "下一步", "继续", "继续做", "做下一步", "下一部"]):
        return "cooking_step"
    
    # 检测上一步意图
    if any(keyword in user_input_lower for keyword in ["上一步", "上一部", "回去", "返回", "重做"]):
        return "previous_step"
    
    # 检测是否询问营养信息或完成烹饪
    if any(keyword in user_input_lower for keyword in ["营养", "分析", "完成", "做好了", "结束了", "做完", "小结", "总结", "营养成分"]):
        return "nutrition_summary"
    
    # 默认为一般性对话
    return "general"

# 模型配置和参数设置
model = ChatOpenAI(
    model=MODEL_NAME,
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.7,
)

# 记忆
checkpointer = InMemorySaver()

# 全局变量
user_profile = None
recipe_generator = RecipeGenerator(model)
nutrition_analyzer = NutritionAnalyzer(model)
cooking_guide = CookingGuide(model)
current_recipe = None
current_step_index = 0  # 当前烹饪步骤索引

# 用于存储临时的每日偏好
temp_daily_preferences = {
    "exclude_ingredients": [],
    "include_ingredients": [],
    "dish_type": "",
    "cooking_method": ""
}

# 创建代理
agent = create_react_agent(
    model=model,
    tools=[get_user_preferences, get_user_preferences_for_display, collect_user_preferences, update_dietary_restrictions, generate_recipe, get_cooking_guide, analyze_nutrition, get_next_cooking_step, get_previous_cooking_step, complete_cooking_and_get_nutrition, detect_user_intent],
    checkpointer=checkpointer,
)

class LangChainFoodAgent:
    """基于LangChain的饮食助手智能体"""
    
    def __init__(self, initial_user_profile=None):
        global user_profile
        # 如果提供了初始用户档案，则使用它，否则重置为None
        if initial_user_profile is not None:
            user_profile = initial_user_profile
            self.profile_completed = True  # 如果有初始档案，表示已完成初始设置
        else:
            user_profile = None  # 重置用户偏好
            self.profile_completed = False
        self.config = {"configurable": {"thread_id": "food-assistant-thread-1"}}
        self.conversation_history = []
    
    def process_user_input(self, user_input: str) -> str:
        """处理用户输入"""
        global current_recipe
        
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # 检查是否已完成初始偏好设置
        if not self.profile_completed:
            # 还未完成初始设置，检查是否是偏好信息输入
            intent_result = _internal_detect_user_intent(user_input)
            
            if intent_result == "profile_setup":
                # 使用内部函数处理偏好信息，避免工具调用错误
                try:
                    profile_response = _internal_collect_user_preferences(user_input)
                    # 标记为已完成初始设置
                    self.profile_completed = True
                    
                    # 获取更新后的user_profile
                    import agents.langchain_food_agent as agent_module
                    current_profile = agent_module.user_profile
                    
                    # 自动生成食谱
                    try:
                        # 创建临时档案
                        temp_profile = UserProfile(
                            preferences=current_profile.preferences if current_profile else "",
                            dietary_restrictions=current_profile.dietary_restrictions if current_profile else "",
                            allergies=current_profile.allergies if current_profile else "",
                            health_goals=current_profile.health_goals if current_profile else ""
                        )
                        recipe = recipe_generator.generate_recipe(temp_profile)
                        agent_module.current_recipe = recipe
                        
                        # 格式化食谱输出
                        recipe_response = f"🐱 已为您生成符合偏好的食谱喵～\n\n"
                        recipe_response += f"📝 菜谱名称：{recipe['name']}\n\n"
                        recipe_response += f"🥗 材料：\n"
                        for i, ingredient in enumerate(recipe['ingredients'], 1):
                            recipe_response += f"   {i}. {ingredient}\n"
                        recipe_response += f"\n⏱️ 烹饪时间：{recipe['cooking_time']}分钟\n"
                        recipe_response += f"\n📊 难度：{recipe['difficulty']}\n"
                        recipe_response += f"\n💪 营养信息：{recipe['nutrition_info']}\n"
                        recipe_response += f"\n📋 简要步骤：\n"
                        for i, step in enumerate(recipe['steps'][:3], 1):
                            recipe_response += f"   {i}. {step}\n"
                        if len(recipe['steps']) > 3:
                            recipe_response += f"   ...共{len(recipe['steps'])}步\n"
                        recipe_response += f"\n🌟 告诉曦曦'确定菜谱'开始烹饪，或'换一道菜'重新推荐喵～"
                        
                        final_response = profile_response + "\n\n" + recipe_response
                    except Exception as e:
                        print(f"[DEBUG] 生成食谱出错: {e}")
                        final_response = profile_response + f"\n\n🐱 已保存您的偏好，但由于技术问题暂时无法生成食谱，请稍后再试喵～"
                    
                    self.conversation_history.append({"role": "assistant", "content": final_response})
                    return final_response
                except Exception as e:
                    response = f"保存偏好信息时遇到问题：{str(e)}\n\n请按照以下格式提供信息：\n偏好口味：\n忌口：\n过敏原：\n健康目标："
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
            else:
                # 如果用户还未提供完整偏好信息就开始其他对话，引导其先完成设置
                response = f"🐱 为了更好地为您服务，请先提供您的饮食偏好信息：\n\n请按以下模板提供信息：\n偏好口味：\n忌口：\n过敏原：\n健康目标：\n\n例如：\n偏好口味：清淡\n忌口：香菜\n过敏原：芒果\n健康目标：减肥"
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
        else:
            # 已完成初始设置，使用内部意图识别函数检测用户意图
            intent_result = _internal_detect_user_intent(user_input)
            
            if intent_result == "dietary_update":
                # 处理饮食规则更新
                response = self._handle_dietary_update(user_input)
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            elif intent_result == "daily_preference":
                # 处理每日偏好
                response = self._handle_daily_preference(user_input)
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            elif intent_result == "recipe_request":
                # 获取当前用户档案
                import agents.langchain_food_agent as agent_module
                current_profile = agent_module.user_profile
                
                if not current_profile:
                    # 如果没有用户档案，引导用户设置
                    response = "🐱 为了更好地为您服务，请先提供您的饮食偏好信息喵～\n\n请按以下格式：\n偏好口味：\n忌口：\n过敏原：\n健康目标："
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
                
                # 解析用户输入中的偏好/限制
                user_input_lower = user_input.lower()
                extra_exclude = []
                
                # 检查"不想吃"后面跟的内容
                if "不想吃" in user_input:
                    start_pos = user_input.find("不想吃")
                    remaining = user_input[start_pos + 4:].strip()
                    # 常见食物类型
                    food_types = {
                        "素": "素食",
                        "全素": "素食",
                        "肉": "肉类",
                        "鸡肉": "鸡肉",
                        "牛肉": "牛肉",
                        "猪肉": "猪肉",
                        "鱼": "鱼类"
                    }
                    for food, food_type in food_types.items():
                        if food in remaining:
                            if "素" in food_type:
                                extra_exclude.append("素食")
                            break
                
                # 生成新食谱
                try:
                    if extra_exclude:
                        # 临时添加排除项
                        temp_profile = UserProfile(
                            preferences=current_profile.preferences,
                            dietary_restrictions=current_profile.dietary_restrictions + ", " + ", ".join(extra_exclude),
                            allergies=current_profile.allergies,
                            health_goals=current_profile.health_goals
                        )
                        recipe = recipe_generator.generate_recipe(temp_profile)
                    else:
                        recipe = recipe_generator.generate_recipe(current_profile)
                    
                    agent_module.current_recipe = recipe
                    
                    # 格式化输出
                    response = f"🐱 好的喵～已为您重新生成食谱喵～\n\n"
                    response += f"📝 菜谱名称：{recipe['name']}\n\n"
                    response += f"🥗 材料：\n"
                    for i, ingredient in enumerate(recipe['ingredients'], 1):
                        response += f"   {i}. {ingredient}\n"
                    response += f"\n⏱️ 烹饪时间：{recipe['cooking_time']}分钟\n"
                    response += f"📊 难度：{recipe['difficulty']}\n\n"
                    response += f"💪 营养信息：{recipe['nutrition_info']}\n\n"
                    response += f"📋 简要步骤：\n"
                    for i, step in enumerate(recipe['steps'][:3], 1):
                        response += f"   {i}. {step}\n"
                    if len(recipe['steps']) > 3:
                        response += f"   ...共{len(recipe['steps'])}步\n"
                    response += f"\n🌟 告诉曦曦'确定菜谱'开始烹饪喵～"
                except Exception as e:
                    response = f"🐱 抱歉喵，生成食谱时遇到问题：{str(e)}\n\n请稍后再试喵～"
                
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            elif intent_result == "cooking_step":
                # 处理烹饪步骤控制
                if current_recipe:
                    response = get_next_cooking_step(current_recipe['name'])
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
                else:
                    response = "请先生成食谱，然后我们可以开始烹饪步骤喵～"
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
            elif intent_result == "previous_step":
                # 处理上一步意图
                if current_recipe:
                    response = get_previous_cooking_step(current_recipe['name'])
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
                else:
                    response = "请先生成食谱，然后我们可以开始烹饪步骤喵～"
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
            elif intent_result == "recipe_confirmation":
                # 处理菜谱确认，开始烹饪指导
                if current_recipe:
                    # 开始烹饪指导
                    try:
                        response = get_cooking_guide(current_recipe['name'])
                        # 添加提示信息
                        response += "\n\n当你完成这一步后，告诉我'好了'或'下一步'，我会继续指导你喵～"
                        self.conversation_history.append({"role": "assistant", "content": response})
                        return response
                    except Exception as e:
                        response = f"开始烹饪指导时遇到问题：{str(e)}\n\n让我为您提供烹饪指导：\n{current_recipe['name']}\n\n材料：{', '.join(current_recipe['ingredients'])}\n\n步骤：{'; '.join(current_recipe['steps'])}"
                        self.conversation_history.append({"role": "assistant", "content": response})
                        return response
                else:
                    response = "请生成食谱，然后告诉我'确定菜谱'开始烹饪喵～"
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
            elif intent_result == "nutrition_summary":
                # 处理营养总结
                if current_recipe:
                    response = complete_cooking_and_get_nutrition(current_recipe['name'])
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
                else:
                    response = "请生成食谱，然后我们可以分析营养成分喵～"
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
            
        # 运行代理
        response = agent.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=self.config
        )
        
        # 提取响应内容
        result = response["messages"][-1].content
        self.conversation_history.append({"role": "assistant", "content": result})
        return result
    
    def _is_preference_input(self, user_input: str) -> bool:
        """检查用户输入是否为偏好信息"""
        return "偏好口味:" in user_input or "忌口:" in user_input or "过敏原:" in user_input or "健康目标:" in user_input
    
    def _parse_preferences_from_input(self, user_input: str):
        """从用户输入中解析偏好信息"""
        global user_profile
        
        # 分割输入为行
        lines = user_input.split('\n')
        
        preferences = ""
        dietary_restrictions = ""
        allergies = ""
        health_goals = ""
        
        for line in lines:
            if "偏好口味:" in line:
                preferences = line.split("偏好口味:")[1].strip()
            elif "忌口:" in line:
                dietary_restrictions = line.split("忌口:")[1].strip()
            elif "过敏原:" in line:
                allergies = line.split("过敏原:")[1].strip()
            elif "健康目标:" in line:
                health_goals = line.split("健康目标:")[1].strip()
        
        # 如果还没有用户档案，则创建
        if not user_profile:
            user_profile = UserProfile(
                preferences=preferences,
                dietary_restrictions=dietary_restrictions,
                allergies=allergies,
                health_goals=health_goals
            )
        else:
            # 更新现有档案
            if preferences:
                user_profile.preferences = preferences
            if dietary_restrictions:
                user_profile.dietary_restrictions = dietary_restrictions
            if allergies:
                user_profile.allergies = allergies
            if health_goals:
                user_profile.health_goals = health_goals
    
    def _handle_dietary_update(self, user_input: str):
        """处理饮食规则更新，返回确认提示"""
        # 获取当前用户档案
        import agents.langchain_food_agent as agent_module
        current_profile = agent_module.user_profile
        
        # 检查是否已有用户档案
        if not current_profile:
            # 如果没有用户档案，需要引导用户提供完整信息
            return "请先提供您的完整饮食偏好信息（包括偏好口味、忌口、过敏原和健康目标），然后再单独告诉我您有过敏或其他饮食限制喵～"
        
        # 解析输入中的过敏原或忌口
        new_allergy = ""
        new_restriction = ""
        
        # 解析并提取过敏原
        if "过敏" in user_input or "过敏原" in user_input:
            allergy_keywords = ["过敏", "过敏原"]
            for keyword in allergy_keywords:
                if keyword in user_input:
                    start_pos = user_input.find(keyword)
                    if start_pos != -1:
                        remaining = user_input[start_pos + len(keyword):].strip()
                        if remaining.startswith("：") or remaining.startswith(":"):
                            remaining = remaining[1:].strip()
                        # 提取食物名称（去掉"对...过敏"等句式）
                        new_allergy = remaining.replace("对", "").replace("了", "").strip()
                        break
        
        # 解析并提取忌口 - 包括"我不吃"这样的表达
        if "忌口" in user_input or "不能吃" in user_input or "我不吃" in user_input:
            restriction_keywords = ["忌口", "不能吃", "我不吃"]
            for keyword in restriction_keywords:
                if keyword in user_input:
                    start_pos = user_input.find(keyword)
                    if start_pos != -1:
                        remaining = user_input[start_pos + len(keyword):].strip()
                        if remaining.startswith("：") or remaining.startswith(":") or remaining.startswith(" "):
                            remaining = remaining.lstrip(': ')
                        # 处理多个食材的情况，例如 "我不吃鱼，虾，蟹"
                        if "," in remaining or "，" in remaining:
                            # 按逗号分割食材
                            items = [item.strip() for item in remaining.replace("，", ",").split(",")]
                            new_restriction = ", ".join(items)
                        else:
                            new_restriction = remaining
                        break
        
        # 解析"不过敏了"等移除过敏原的表达
        remove_allergy = False
        if "不过敏" in user_input or "不再过敏" in user_input:
            # 提取要移除的过敏原
            for keyword in allergy_keywords:
                if keyword in user_input:
                    start_pos = user_input.find(keyword)
                    if start_pos != -1:
                        remaining = user_input[start_pos + len(keyword):].strip()
                        if remaining.startswith("：") or remaining.startswith(":"):
                            remaining = remaining[1:].strip()
                        new_allergy = remaining
                        remove_allergy = True
                        break
        
        # 构建确认提示
        current_allergies = current_profile.allergies or "无"
        current_restrictions = current_profile.dietary_restrictions or "无"
        
        if new_allergy:
            if remove_allergy:
                action_text = f"移除过敏原【{new_allergy}】"
            else:
                action_text = f"添加过敏原【{new_allergy}】"
        elif new_restriction:
            action_text = f"添加忌口【{new_restriction}】"
        else:
            return "🐱曦曦没有理解您的意思，请告诉曦曦您想要更新什么饮食限制喵～"
        
        # 返回确认提示，使用特殊标记让前端显示确认按钮
        confirm_prompt = f"__CONFIRM_UPDATE__{action_text}__CURRENT_ALLERGY__{current_allergies}__CURRENT_RESTRICTION__{current_restrictions}__NEW_ALLERGY__{new_allergy}__NEW_RESTRICTION__{new_restriction}__REMOVE__{str(remove_allergy)}__END_CONFIRM__"
        
        return confirm_prompt
    
    def _confirm_dietary_update(self, action_type: str, new_item: str, remove: bool = False):
        """确认更新饮食习惯"""
        import agents.langchain_food_agent as agent_module
        current_profile = agent_module.user_profile
        
        if not current_profile:
            return "曦曦没有找到您的饮食偏好信息，请重新设置喵～"
        
        if action_type == "allergy":
            if remove:
                # 移除过敏原
                allergies_list = [a.strip() for a in current_profile.allergies.split(",") if a.strip()]
                if new_item in allergies_list:
                    allergies_list.remove(new_item)
                    current_profile.allergies = ", ".join(allergies_list)
                return f"🐱 已为您移除过敏原【{new_item}】喵～\n\n当前过敏原：{current_profile.allergies or '无'}"
            else:
                # 添加过敏原
                if current_profile.allergies:
                    if new_item not in current_profile.allergies:
                        current_profile.allergies += f", {new_item}"
                else:
                    current_profile.allergies = new_item
                return f"🐱 已为您添加过敏原【{new_item}】喵～\n\n当前过敏原：{current_profile.allergies}"
        elif action_type == "restriction":
            # 添加忌口
            if current_profile.dietary_restrictions:
                # 分割现有的忌口项，避免重复添加
                existing_restrictions = [r.strip() for r in current_profile.dietary_restrictions.split(",") if r.strip()]
                # 检查新项是否已经在列表中
                new_items = [item.strip() for item in new_item.split(",") if item.strip()]
                for item in new_items:
                    if item not in existing_restrictions:
                        existing_restrictions.append(item)
                current_profile.dietary_restrictions = ", ".join(existing_restrictions)
            else:
                current_profile.dietary_restrictions = new_item
            return f"🐱 已为您添加忌口【{new_item}】喵～\n\n当前忌口：{current_profile.dietary_restrictions}"
        
        return "🐱 更新失败，请稍后再试喵～"
    
    def _handle_daily_preference(self, user_input: str):
        """处理每日临时偏好"""
        global temp_daily_preferences
        
        # 清除之前的临时偏好
        temp_daily_preferences = {
            "exclude_ingredients": [],
            "include_ingredients": [],
            "dish_type": "",
            "cooking_method": ""
        }
        
        # 检测用户不想吃的食材
        exclude_keywords = ["不想吃", "不吃", "不要", "不想", "不想要"]
        for keyword in exclude_keywords:
            if keyword in user_input:
                # 找出食材
                start_pos = user_input.find(keyword)
                remaining = user_input[start_pos + len(keyword):].strip()
                if remaining.startswith("：") or remaining.startswith(":"):
                    remaining = remaining[1:].strip()
                
                # 常见食材列表
                ingredients = ["鸡肉", "牛肉", "猪肉", "羊肉", "鱼", "虾", "蟹", "鸡蛋", "牛奶", "花生", "大豆", "坚果", "海鲜", "辣椒", "香菜"]
                for ingredient in ingredients:
                    if ingredient in remaining or ingredient in user_input:
                        temp_daily_preferences["exclude_ingredients"].append(ingredient)
        
        # 检测用户想吃的食材或菜系
        include_keywords = ["想吃", "要吃", "想", "需要"]
        for keyword in include_keywords:
            if keyword in user_input:
                start_pos = user_input.find(keyword)
                remaining = user_input[start_pos + len(keyword):].strip()
                if remaining.startswith("：") or remaining.startswith(":"):
                    remaining = remaining[1:].strip()
                
                # 检测菜系或类型
                dish_types = ["轻食", "中餐", "西餐", "日料", "韩料", "素食", "汤", "主食", "甜点", "沙拉", "烤肉", "火锅", "面条", "米饭"]
                for dish_type in dish_types:
                    if dish_type in remaining or dish_type in user_input:
                        temp_daily_preferences["dish_type"] = dish_type
                        break
        
        # 检测烹饪方式
        cooking_methods = ["蒸", "煮", "炒", "烤", "炸", "炖", "凉拌", "生食"]
        for method in cooking_methods:
            if method in user_input:
                temp_daily_preferences["cooking_method"] = method
                break
        
        # 获取当前用户档案
        import agents.langchain_food_agent as agent_module
        current_profile = agent_module.user_profile
        
        # 获取当前食谱（如果有）
        current_recipe = agent_module.current_recipe
        
        # 提取用户不想吃的食材
        excluded_ingredients = temp_daily_preferences["exclude_ingredients"]
        
        if current_profile:
            # 创建临时档案，合并全局偏好和临时偏好
            # 注意：这里只是临时排除食材，不修改全局偏好
            excluded_str = "，".join(excluded_ingredients) if excluded_ingredients else ""
            
            # 直接调用recipe_generator生成新食谱
            try:
                recipe = recipe_generator.generate_recipe(current_profile)
                
                # 如果有要排除的食材，尝试生成新食谱或过滤结果
                if excluded_ingredients:
                    # 检查生成的食谱是否包含要排除的食材
                    recipe_text = str(recipe).lower()
                    should_regenerate = False
                    for excluded in excluded_ingredients:
                        if excluded in recipe_text:
                            should_regenerate = True
                            break
                    
                    # 如果包含，排除后重新生成
                    if should_regenerate:
                        temp_profile = UserProfile(
                            preferences=current_profile.preferences,
                            dietary_restrictions=current_profile.dietary_restrictions + ", " + excluded_str if current_profile.dietary_restrictions else excluded_str,
                            allergies=current_profile.allergies,
                            health_goals=current_profile.health_goals
                        )
                        recipe = recipe_generator.generate_recipe(temp_profile)
                
                # 更新当前食谱
                agent_module.current_recipe = recipe
                
                # 格式化输出
                response = f"🐱 好的喵～已根据您的临时需求重新生成食谱喵～\n\n"
                response += f"📝 菜谱名称：{recipe['name']}\n\n"
                response += f"🥗 材料：\n"
                for i, ingredient in enumerate(recipe['ingredients'], 1):
                    response += f"   {i}. {ingredient}\n"
                response += f"\n⏱️ 烹饪时间：{recipe['cooking_time']}分钟\n"
                response += f"📊 难度：{recipe['difficulty']}\n\n"
                response += f"💪 营养信息：{recipe['nutrition_info']}\n\n"
                response += f"📋 简要步骤：\n"
                for i, step in enumerate(recipe['steps'][:3], 1):
                    response += f"   {i}. {step}\n"
                if len(recipe['steps']) > 3:
                    response += f"   ...共{len(recipe['steps'])}步\n"
                response += f"\n🌟 告诉曦曦'确定菜谱'开始烹饪喵～"
                
                return response
            except Exception as e:
                return f"🐱 抱歉喵，生成新食谱时遇到了一点问题：{str(e)}\n\n请告诉曦曦'确定菜谱'继续使用之前的食谱，或重新描述您的需求喵～"
        else:
            return "请先提供您的饮食偏好信息，这样我才能根据您的临时需求为您推荐食谱喵～"
    
    def reset_conversation(self):
        """重置对话"""
        global user_profile
        user_profile = None  # 重置用户偏好
        self.conversation_history = []
        
        welcome_msg = (
            "🐱喵～欢迎来到曦曦饮食助手！\n\n"
            "在开始之前，请告诉我你的饮食偏好信息：\n\n"
            "请按以下模板提供信息：\n"
            "偏好口味：\n"
            "忌口：\n"
            "过敏原：\n"
            "健康目标：\n\n"
            "例如：\n"
            "偏好口味：清淡\n"
            "忌口：香菜\n"
            "过敏原：芒果\n"
            "健康目标：减肥\n\n"
            "如果你有现有食材，也可以告诉我，我会优先使用它们喵～"
        )
        
        self.conversation_history.append({"role": "assistant", "content": welcome_msg})
        return welcome_msg