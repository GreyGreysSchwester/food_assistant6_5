# agents/food_agent.py
from enum import Enum
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
import re

class AgentState(Enum):
    """智能体状态枚举"""
    COLLECTING_REQUIREMENTS = "collecting_requirements"
    GENERATING_RECIPE = "generating_recipe"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COOKING_GUIDE = "cooking_guide"
    NUTRITION_ANALYSIS = "nutrition_analysis"
    COMPLETED = "completed"

# ===================== 配置 =========================
API_KEY = Settings.API_KEY
BASE_URL = Settings.BASE_URL
MODEL_NAME = Settings.MODEL_NAME
# ========================================================

# 定义系统提示
SYSTEM_PROMPT = """你是一个名叫"曦曦"的小猫，是一个饮食助手，一位专业的饮食顾问。你的性格活泼，有耐心，口头禅是"喵"。你的任务是帮助用户制定符合他们偏好的饮食计划。

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


@tool
def generate_recipe(user_input: str) -> str:
    """根据用户偏好生成食谱。"""
    print("[DEBUG] 调用了 generate_recipe 工具")
    print(f"[DEBUG] 用户输入: {user_input}")
    print(recipe['steps'])
    global user_profile, current_recipe
    
    if not user_profile:
        result = "请先提供您的饮食偏好信息，这样我可以为您生成合适的食谱。"
        print(f"[DEBUG] 返回: {result}")
        return result
    
    # 生成食谱
    recipe = recipe_generator.generate_recipe(user_profile)
    current_recipe = recipe  # 保存当前食谱供后续使用
    
    result = f"为您生成的食谱：\n名称：{recipe['name']}\n食材：{', '.join(recipe['ingredients'])}\n烹饪时间：{recipe['cooking_time']}分钟\n难度：{recipe['difficulty']}\n营养信息：{recipe['nutrition_info']}"
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

#
#@tool
#def analyze_nutrition(recipe_name: str) -> str:
 #   """分析食谱的营养成分。"""
  #  print("[DEBUG] 调用了 analyze_nutrition 工具")
   # print(f"[DEBUG] 请求分析的食谱名称: {recipe_name}")
    #global current_recipe
    #global user_profile
    #if current_recipe and current_recipe['name'] == recipe_name:
        # 使用用户档案中的健康目标
     #   health_goals = user_profile.health_goals if user_profile else ""
      #  result = nutrition_analyzer.analyze_nutrition(current_recipe, health_goals)
       # print(f"[DEBUG] 返回营养分析")
      #  return result
   # else:
    #    result = "请先生成食谱，然后我可以为您分析营养成分。"
     #   print(f"[DEBUG] 返回: {result}")
    #    return result
#
@tool
def analyze_nutrition(recipe_name: str) -> str:
    """分析食谱的营养成分。"""

    global current_recipe
    global user_profile

    if not current_recipe:
        return "请先生成食谱，然后我可以为您分析营养成分。"

    health_goals = (user_profile.health_goals if user_profile else "" )
    nutrition = nutrition_analyzer.analyze_nutrition(
         current_recipe,
         health_goals
    )
    result = f"""

### 🔥 **热量：** {nutrition.get('calories', '-')} kcal
### 💪 **蛋白质：** {nutrition.get('protein', '-')} g
### 🌾 **碳水化合物：** {nutrition.get('carbs', '-')} g
### 🥑 **脂肪：** {nutrition.get('fat', '-')} g
### ⭐ **健康评分：** {nutrition.get('health_score', '-')} /10
### 🍊 维生素
{nutrition.get('vitamins', '暂无数据')}
### 🦴 矿物质
{nutrition.get('minerals', '暂无数据')}
### 💡 曦曦的小建议
{nutrition.get('recommendations', '暂无建议')}
### 📖 膳食指南参考
{nutrition.get('reference_guide', '暂无参考')}
"""
    return result
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


# 创建代理
agent = create_react_agent(
    model=model,
    tools=[get_user_preferences, collect_user_preferences, generate_recipe, get_cooking_guide, analyze_nutrition],
    checkpointer=checkpointer,
)


class FoodAssistantAgent:
    """基于LangChain的饮食助手智能体"""
    
    def __init__(self, initial_user_profile=None):
        global user_profile
        # 如果提供了初始用户档案，则使用它，否则重置为None
        if initial_user_profile is not None:
            user_profile = initial_user_profile
        else:
            user_profile = None  # 重置用户偏好
        self.state = AgentState.COLLECTING_REQUIREMENTS
        self.user_profile = user_profile if user_profile is not None else UserProfile()  # 确保是UserProfile对象
        self.current_recipe = current_recipe  # 添加实例属性
        self.current_step_index = current_step_index  # 添加实例属性
        self.config = {"configurable": {"thread_id": "food-assistant-thread-1"}}
        self.conversation_history = []
    
    def process_user_input(self, user_input: str) -> str:
        """处理用户输入"""
        global current_recipe, user_profile

        self.conversation_history.append({"role": "user", "content": user_input})

        has_pref = any(k in user_input for k in ["偏好口味", "忌口", "过敏原", "健康目标"])

        if has_pref:
            collect_user_preferences.invoke(user_input)
            recipe = recipe_generator.generate_recipe(user_profile)
            current_recipe = recipe
            
            result = (
                "✅ 已保存您的饮食习惯" +
                self._format_recipe_markdown(recipe)
            )
        else:
            response = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=self.config
            )
            result = response["messages"][-1].content

        self.current_recipe = current_recipe
        self.conversation_history.append({"role": "assistant", "content": result})
        return result
    

    def _format_recipe_markdown(self, recipe):
        ingredients = "\n".join([f"- {x}" for x in recipe.get("ingredients", [])])
        steps_list = []

        for i, s in enumerate(recipe.get("steps", [])):
            clean_step = re.sub(r'^\d+[\.、]\s*', '', s)
            steps_list.append(f"{i+1}. {clean_step}")

        steps = "\n".join(steps_list)
        #steps = "\n".join(recipe.get("steps", []))
        return f"""# 🍽️ 今日专属推荐

## 📌 菜谱名称
**{recipe.get('name','')}**

## 🥬 所需食材
{ingredients}

## ⏱️ 预计时间
**{recipe.get('cooking_time','')} 分钟**

## ⭐ 做饭难度
**{recipe.get('difficulty','')}**

## 👩‍🍳 制作步骤
{steps}

💡 继续点击进行营养分析
"""

    def reset_conversation(self):
        """重置对话"""
        global user_profile, current_recipe, current_step_index
        # 重置全局变量
        user_profile = None
        current_recipe = None
        current_step_index = 0
        
        # 更新实例属性，确保是UserProfile对象
        self.user_profile = UserProfile()
        self.current_recipe = None
        self.current_step_index = 0
        
        # 清空对话历史
        self.conversation_history = []
        
        welcome_msg = (
            "🐱 喵～欢迎来到曦曦饮食助手！\n\n"
            "把你手头的食材或者一句话告诉我，我来帮你决定今天吃什么～\n\n"
            "你可以这样告诉我你的需求，请填写饮食偏好：\n"
            "偏好口味：\n"
            "忌口：\n"
            "过敏原：\n"
            "健康目标：\n\n"
            "示例：\n"
            "偏好口味：清淡\n"
            "忌口：香菜\n"
            "过敏原：芒果\n"
            "健康目标：减肥\n\n"
            "或者直接说你想吃什么也可以喵～"
        )
        
        self.conversation_history.append({"role": "assistant", "content": welcome_msg})
        return welcome_msg