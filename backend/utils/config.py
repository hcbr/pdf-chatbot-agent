"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: config.py
@time: 2025/10/27 13:52
"""
import os
from pathlib import Path
from dotenv import load_dotenv


root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env.dev"
load_dotenv(dotenv_path=env_path)


class Config():
    # 根目录
    root_path = root_dir

    # es数据库配置
    es_host: str = os.getenv("ES_HOST")
    es_user: str = os.getenv("ES_USER")
    es_password: str = os.getenv("ES_PASSWORD")
    es_index: str = os.getenv("ES_INDEX")

    # LLM配置
    llm_api_url: str = os.getenv("LLM_API_URL")
    llm_api_key: str = os.getenv("LLM_API_KEY")
    llm_api_model: str = os.getenv("LLM_API_MODEL")

    # 向量模型配置
    text_embedding_url: str = os.getenv("TEXT_EMBEDDING_URL")
    text_embedding_api_key: str = os.getenv("TEXT_EMBEDDING_API_KEY")
    text_embedding_model: str = os.getenv("TEXT_EMBEDDING_MODEL")

    # 搜索配置
    top_k: int = os.getenv("TOP_K")


settings = Config()