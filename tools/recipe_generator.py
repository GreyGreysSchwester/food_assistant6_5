# tools/recipe_generator.py
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.output_parsers import StrOutputParser

# 定义一个兼容的LLMChain替代品
class LLMChain:
    def __init__(self, llm, prompt):
        self.chain = prompt | llm | StrOutputParser()
    
    def invoke(self, inputs):
        result = self.chain.invoke(inputs)
        return {'text': result}
import json

class RecipeGenerator:
    """食谱生成工具"""
    
    def __init__(self, llm):
        self.llm = llm
        self.recipe_chain = self._create_recipe_chain()
    
    def _create_recipe_chain(self):
        template = """
        根据以下用户饮食要求生成一道适合的食谱：
        
        偏好口味：{preferences}
        忌口：{dietary_restrictions}
        过敏原：{allergies}
        健康目标：{health_goals}
        可用食材：{available_ingredients}
        
        请返回一个JSON格式的食谱，包含以下字段：
        - name: 食谱名称（以猫咪的口吻起个俏皮的名字）
        - ingredients: 食材列表
        - steps: 制作步骤列表
        - cooking_time: 预计烹饪时间（分钟）
        - difficulty: 难度等级（简单/中等/困难）
        - nutrition_info: 营养信息摘要
        
        请确保食谱符合用户的忌口和过敏要求。
        """
        
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是一个专业的饮食顾问，善于根据用户的需求生成个性化的食谱。"),
                ("human", template)
            ])
        except:
            # 如果ChatPromptTemplate不可用，使用PromptTemplate作为备选方案
            prompt = PromptTemplate(template=template)
            return LLMChain(llm=self.llm, prompt=prompt)
        
        return prompt | self.llm | StrOutputParser()
    
    def generate_recipe(self, user_profile) -> Dict:
        """生成食谱"""
        result = self.recipe_chain.invoke({
            "preferences": user_profile.preferences,
            "dietary_restrictions": user_profile.dietary_restrictions,
            "allergies": user_profile.allergies,
            "health_goals": user_profile.health_goals,
            "available_ingredients": ", ".join(user_profile.available_ingredients)
        })
        
        try:
            # 尝试解析JSON响应
            response_text = result
            # 提取JSON部分
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            json_str = response_text[start_idx:end_idx]
            recipe_data = json.loads(json_str)
            return recipe_data
        except Exception as e:
            # 如果解析失败，返回默认值
            print(f"JSON解析失败: {e}")
            return {
                "name": "喵喵特制料理",
                "ingredients": ["食材待定"],
                "steps": ["烹饪步骤待定"],
                "cooking_time": 30,
                "difficulty": "简单",
                "nutrition_info": "营养信息待定"
            }
    
    def get_alternative_recipe(self, user_request: str, current_recipe: Dict) -> Dict:
        """根据用户的新请求生成替代食谱"""
        template = f"""
        用户不喜欢当前的食谱"{current_recipe['name']}"，他们希望{user_request}。
        
        请根据以下用户饮食要求生成一道新的食谱：
        
        偏好口味：{current_recipe.get('preferences', '')}
        忌口：{current_recipe.get('dietary_restrictions', '')}
        过敏原：{current_recipe.get('allergies', '')}
        健康目标：{current_recipe.get('health_goals', '')}
        
        请返回一个JSON格式的食谱，包含以下字段：
        - name: 食谱名称（以猫咪的口吻起个俏皮的名字）
        - ingredients: 食材列表
        - steps: 制作步骤列表
        - cooking_time: 预计烹饪时间（分钟）
        - difficulty: 难度等级（简单/中等/困难）
        - nutrition_info: 营养信息摘要
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的饮食顾问，善于根据用户的需求生成个性化的食谱。"),
            ("human", template)
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        result = chain.invoke({})
        
        try:
            response_text = result
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            json_str = response_text[start_idx:end_idx]
            recipe_data = json.loads(json_str)
            return recipe_data
        except Exception as e:
            print(f"JSON解析失败: {e}")
            return {
                "name": "喵喵特制料理",
                "ingredients": ["食材待定"],
                "steps": ["烹饪步骤待定"],
                "cooking_time": 30,
                "difficulty": "简单",
                "nutrition_info": "营养信息待定"
            }