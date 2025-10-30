"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: llm_infer.py
@time: 2025/10/27 16:53
"""
from langchain_openai.chat_models import ChatOpenAI
from backend.utils.config import settings


def get_llm():
    """
    获取llm模型
    :return:
    """
    model = ChatOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_url,
        model=settings.llm_api_model,
        temperature=0.1,

    )
    return model


if __name__ == '__main__':
    model = get_llm()
    print(model)