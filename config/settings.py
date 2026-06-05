# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # LLM配置
    API_KEY = os.getenv("API_KEY", "1NJHGJ7C6C3DL4HKVFQQ655TX0ARTHRUYGTW1TWQ")
    BASE_URL = os.getenv("BASE_URL", "https://ai.gitee.com/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "Qwen2.5-72B-Instruct")
    
    # 数据库配置（可选）
    DB_PATH = os.getenv("DB_PATH", "./data/recipes.db")
    
    # 应用配置
    APP_NAME = "曦曦饮食助手"
    VERSION = "1.0.0"