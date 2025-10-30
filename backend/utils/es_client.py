"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: es_client.py
@time: 2025/10/27 16:02
"""
import os
from backend.utils.config import settings
from elasticsearch import Elasticsearch
from typing import List
from langchain_core.documents import Document  # 可能存在问题


class EsClient:
    def __init__(self):
        self.es = Elasticsearch(
            hosts=settings.es_host,
            http_auth=(settings.es_user, settings.es_password),
        )

        self.index_name = settings.es_index

        # 验证连接
        if not self.es.ping():
            raise Exception("Elasticsearch连接失败")

    def add_documents(self, documents:List[Document], embeddings:List[List[float]]):
        """
        向ES中添加文档及其嵌入向量
        :param documents:
        :param embeddings:
        :return:
        """
        if len(documents) != len(embeddings):
            raise Exception("文档和嵌入向量数量不匹配")

        actions = []
        for doc, embedding in zip(documents, embeddings):
            # 1. 新增：操作行（指定操作类型为 index，以及索引 _index）
            action_line = {
                "index": {  # 操作类型：index（插入或更新）
                    "_index": self.index_name  # 目标索引
                }
            }
            # 2. 数据行（原有的 _source 内容，去掉外层 _index）
            data_line = {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "embedding": embedding,
            }
            # 3. 交替添加操作行和数据行（Bulk API 要求）
            actions.append(action_line)
            actions.append(data_line)

        # 批量插入（保持 body=actions 关键字参数）
        response = self.es.bulk(body=actions)
        # 新增：检查批量操作是否有错误（可选但推荐）
        if response.get("errors", False):
            # 提取错误信息（方便调试）
            errors = [item for item in response["items"] if item["index"].get("error")]
            raise Exception(f"批量插入失败，错误信息：{errors}")

    def search_similar(self, query_embedding: List[float], k: int = settings.top_k):
        """
        查询相似的文档 - 使用正确的KNN语法
        """
        query = {
            "knn": {
                "field": "embedding",  # 指定向量字段名
                "query_vector": query_embedding,  # 查询向量
                "k": k,  # 返回最相似的k个文档
                # "num_candidates": k * 10  # 候选数量，放在knn的顶层
            },
            "_source": {
                "includes": ["content", "metadata"]
            }
        }

        try:
            print(f"执行KNN搜索，k={k}")
            response = self.es.search(index=self.index_name, body=query)
            print(f"搜索到 {len(response['hits']['hits'])} 个文档")

        except Exception as e:
            print(f"KNN搜索失败: {e}")
            # 尝试备选方案
            raise Exception(f"KNN搜索失败: {e}")

        # 转换为langchain的document对象
        documents = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            documents.append(Document(
                page_content=source['content'],
                metadata=source['metadata']
            ))
        return documents
