# tools/nutrition_analyzer.py
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class NutritionAnalyzer:
    """营养分析工具"""
    
    def __init__(self, llm):
        self.llm = llm
        self.analysis_chain = self._create_analysis_chain()
    
    def _create_analysis_chain(self):
        template = """
        请对以下食谱进行营养分析：
        
        食谱名称：{recipe_name}
        食材列表：{ingredients}
        制作步骤：{steps}
        健康目标：{health_goals}
        
        请返回一个JSON格式的营养分析报告，包含以下字段：
        - calories: 总热量（千卡）
        - protein: 蛋白质含量（克）
        - carbs: 碳水化合物含量（克）
        - fat: 脂肪含量（克）
        - vitamins: 维生素含量摘要
        - minerals: 矿物质含量摘要
        - health_score: 健康评分（1-10分）
        - recommendations: 改进建议
        - reference_guide: 参考膳食指南说明
        
        请注意保护用户隐私，不要存储或记录任何个人健康信息。
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的营养师，善于分析食物的营养价值。"),
            ("human", template)
        ])
        
        return prompt | self.llm | StrOutputParser()
    
    def analyze_nutrition(self, recipe: Dict, health_goals: str) -> Dict:
        """分析食谱营养"""
        result = self.analysis_chain.invoke({
            "recipe_name": recipe["name"],
            "ingredients": ", ".join(recipe["ingredients"]),
            "steps": "; ".join(recipe["steps"]),
            "health_goals": health_goals
        })
        
        try:
            response_text = result
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            json_str = response_text[start_idx:end_idx]
            import json
            analysis_data = json.loads(json_str)
            return analysis_data
        except Exception as e:
            print(f"JSON解析失败: {e}")
            return {
                "calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0,
                "vitamins": "待分析",
                "minerals": "待分析",
                "health_score": 0,
                "recommendations": "无建议",
                "reference_guide": "参考中国居民膳食指南"
            }