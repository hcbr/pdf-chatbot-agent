"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: ingestion_graph.py
@time: 2025/10/27 13:53
"""
from langgraph.graph import StateGraph, START, END, MessageGraph
from backend.utils.llm_infer import get_llm
from backend.utils.pdf_processor import parse_pdf, split_text_into_chunks
from backend.utils.embeddings import get_embeddings
from backend.utils.config import settings
from backend.utils.es_client import EsClient
import uuid
from langchain_core.documents import Document
from typing import List, Optional, Dict, Tuple, Union, Any
from pydantic import BaseModel


class IngestionState(BaseModel):
    file_path: str
    raw_text: Optional[str] = None
    documents: Optional[List[Document]] = None
    embeddings: Optional[List[List[float]]] = None
    status: str = "started"
    error: Optional[str] = None


# 定义节点
def parse_pdf_node(state: IngestionState) -> Dict[str, Any]:
    """解析PDF文件"""
    try:
        text = parse_pdf(file_path=state.file_path)
        return {"raw_text": text, "status": "pdf_parsed"}
    except Exception as e:
        return {"status": "error", "error": f"解析PDF失败: {str(e)}"}


def split_text_node(state: IngestionState) -> Dict[str, Any]:
    """文本分块"""
    if not state.raw_text:
        return {"status": "error", "error": "没有可分块的文本"}

    try:
        documents = split_text_into_chunks(state.raw_text)
        # 添加源文件信息到metadata
        for doc in documents:
            doc.metadata["source"] = state.file_path
        return {"documents": documents, "status": "text_split"}
    except Exception as e:
        return {"status": "error", "error": f"文本分块失败: {str(e)}"}


def generate_embeddings_node(state: IngestionState) -> Dict[str, Any]:
    """生成嵌入向量"""
    if not state.documents:
        return {"status": "error", "error": "没有可处理的文档"}

    try:
        docs = [doc.page_content for doc in state.documents]
        embeddings = get_embeddings(docs)
        return {"embeddings": embeddings, "status": "embeddings_generated"}
    except Exception as e:
        return {"status": "error", "error": f"生成嵌入失败: {str(e)}"}


def store_in_es_node(state: IngestionState) -> Dict[str, Any]:
    """存储到Elasticsearch"""
    if not state.documents or not state.embeddings:
        return {"status": "error", "error": "没有文档或嵌入可存储"}

    try:
        es_client = EsClient()
        es_client.add_documents(state.documents, state.embeddings)
        return {"status": "completed"}
    except Exception as e:
        return {"status": "error", "error": f"存储到ES失败: {str(e)}"}


# 构建工作流
def create_ingestion_graph():
    workflow = StateGraph(IngestionState)

    # 添加节点
    workflow.add_node("parse_pdf", parse_pdf_node)
    workflow.add_node("split_text", split_text_node)
    workflow.add_node("generate_embeddings", generate_embeddings_node)
    workflow.add_node("store_in_es", store_in_es_node)

    # 定义流程
    workflow.add_edge(START, "parse_pdf")
    workflow.add_edge("parse_pdf", "split_text")
    workflow.add_edge("split_text", "generate_embeddings")
    workflow.add_edge("generate_embeddings", "store_in_es")
    workflow.add_edge("store_in_es", END)


    # 编译图
    return workflow.compile()


if __name__ == '__main__':
    graph = create_ingestion_graph()
    pdf_file = r"D:\重要资料\浩鲸\CodingPLus-代码模型垂直领域微调技术报告.pdf"
    result = graph.invoke({"file_path": pdf_file})
    # print(result)