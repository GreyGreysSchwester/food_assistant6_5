# utils/helpers.py
import re
from typing import Dict, List

def extract_keywords(text: str, keywords: List[str]) -> Dict[str, str]:
    """从文本中提取关键词对应的内容"""
    result = {}
    
    for keyword in keywords:
        # 使用正则表达式查找关键词后的值
        pattern = rf"{keyword}[：:]\s*([^\n\r]+)"
        match = re.search(pattern, text)
        if match:
            result[keyword] = match.group(1).strip()
        else:
            result[keyword] = ""
    
    return result

def validate_ingredients(ingredients: List[str], restrictions: str, allergies: str) -> List[str]:
    """验证食材是否符合限制条件"""
    filtered_ingredients = []
    
    restrictions_list = [item.strip() for item in restrictions.split("，") if item.strip()]
    allergies_list = [item.strip() for item in allergies.split("，") if item.strip()]
    
    all_forbidden = restrictions_list + allergies_list
    
    for ingredient in ingredients:
        is_forbidden = False
        for forbidden in all_forbidden:
            if forbidden.lower() in ingredient.lower():
                is_forbidden = True
                break
        
        if not is_forbidden:
            filtered_ingredients.append(ingredient)
    
    return filtered_ingredients

def format_time(minutes: int) -> str:
    """格式化时间显示"""
    if minutes < 60:
        return f"{minutes}分钟"
    else:
        hours = minutes // 60
        mins = minutes % 60
        if mins > 0:
            return f"{hours}小时{mins}分钟"
        else:
            return f"{hours}小时"
