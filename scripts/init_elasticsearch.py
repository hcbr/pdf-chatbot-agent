"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: init_elasticsearch.py
@time: 2025/10/27 15:49
"""
from backend.utils.config import settings
from elasticsearch import Elasticsearch
import traceback


def init_es():
    es = Elasticsearch(
        hosts=settings.es_host,
        http_auth=(settings.es_user, settings.es_password),
    )
    index_name = settings.es_index

    # 定义索引映射 - 支持向量存储
    mapping = {
        "mappings": {
            "properties": {
                "content": {"type": "text"},
                "metadata": {"type": "object"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": 1536,  # OpenAI嵌入维度
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    }

    try:
        # 创建索引
        if not es.indices.exists(index=index_name):
            es.indices.create(index=index_name, body=mapping)
            print(f"索引 '{index_name}' 创建成功")
        else:
            print(f"索引 '{index_name}' 已存在")

        # 验证连接
        if es.ping():
            print("成功连接到Elasticsearch")
        else:
            print("无法连接到Elasticsearch")

    except Exception as e:
        print(f"发生错误: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    init_es()