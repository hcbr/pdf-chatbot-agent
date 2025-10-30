"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: embeddings.py
@time: 2025/10/27 13:53
"""
import requests
from backend.utils.config import settings
from typing import List


def get_embeddings(inputs: List[str]):
    """
    获取向量
    :return:
    """
    embedding_url = settings.text_embedding_url
    model_name = settings.text_embedding_model

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.text_embedding_api_key}"}

    data ={
        "model": model_name,
        "input": inputs
    }
    response = requests.post(embedding_url, json=data, headers=headers)
    results = response.json()['data']
    if len(inputs) == 1:
        return results[0]['embedding']
    else:
        embeddings = [result['embedding'] for result in results]
    return embeddings


if __name__ == '__main__':
    res = get_embeddings(['hello', "good"])