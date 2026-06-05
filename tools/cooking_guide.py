
# tools/cooking_guide.py
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class CookingGuide:
    """烹饪指导工具"""
    
    def __init__(self, llm):
        self.llm = llm
        self.step_chain = self._create_step_chain()
        self.trouble_shooting_chain = self._create_trouble_shooting_chain()
    
    def _create_step_chain(self):
        template = """
        你是可爱的名叫“曦曦”的小猫厨师，正在指导用户制作"{recipe_name}"。
        食谱步骤：{steps}
        当前步骤索引：{current_step_index}
        
        请用俏皮可爱的猫语描述当前步骤，可以适当加入鼓励的话。
        例如："喵~现在我们来打散鸡蛋吧！记得要把蛋液搅拌均匀哦，这样口感才会嫩滑呢～"
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个可爱的猫咪厨师，总是用俏皮可爱的语言指导用户烹饪。"),
            ("human", template)
        ])
        
        return prompt | self.llm | StrOutputParser()
    
    def _create_trouble_shooting_chain(self):
        template = """
        用户在制作"{recipe_name}"时遇到了问题："{user_problem}"
        当前步骤是："{current_step}"
        
        请提供解决方案，用俏皮可爱的猫语回复。
        例如："哎呀，没关系啦～如果锅里的油温太高了，可以稍微调小火候哦，别着急，喵喵在这里陪着你～"
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个可爱的猫咪厨师，善于解决烹饪过程中遇到的各种问题。"),
            ("human", template)
        ])
        
        return prompt | self.llm | StrOutputParser()
    
    def get_next_step(self, recipe: Dict, step_index: int) -> str:
        """获取下一步指导"""
        steps = recipe["steps"]
        if step_index >= len(steps):
            return "恭喜你完成了这道美味的料理！曦曦为你点赞～"
        
        result = self.step_chain.invoke({
            "recipe_name": recipe["name"],
            "steps": "; ".join(steps),
            "current_step_index": step_index
        })
        
        return result.strip()
    
    def handle_problem(self, recipe: Dict, current_step: str, problem: str) -> str:
        """处理用户遇到的问题"""
        result = self.trouble_shooting_chain.invoke({
            "recipe_name": recipe["name"],
            "user_problem": problem,
            "current_step": current_step
        })
        
        return result.strip()