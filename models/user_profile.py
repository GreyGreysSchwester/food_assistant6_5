# models/user_profile.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class UserProfile:
    """用户饮食偏好模型"""
    preferences: str = ""  # 偏好口味
    dietary_restrictions: str = ""  # 忌口
    allergies: str = ""  # 过敏原
    health_goals: str = ""  # 健康目标
    available_ingredients: List[str] = None  # 可用食材
    
    def __post_init__(self):
        if self.available_ingredients is None:
            self.available_ingredients = []
    
    def to_dict(self):
        return {
            "preferences": self.preferences,
            "dietary_restrictions": self.dietary_restrictions,
            "allergies": self.allergies,
            "health_goals": self.health_goals,
            "available_ingredients": self.available_ingredients
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            preferences=data.get("preferences", ""),
            dietary_restrictions=data.get("dietary_restrictions", ""),
            allergies=data.get("allergies", ""),
            health_goals=data.get("health_goals", ""),
            available_ingredients=data.get("available_ingredients", [])
        )
