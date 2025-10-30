"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: retrieval_graph.py
@time: 2025/10/27 13:53
"""
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

from backend.utils.llm_infer import get_llm
from backend.utils.es_client import EsClient
from backend.utils.embeddings import get_embeddings
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict, Any, Optional, Annotated
from langchain_core.documents import Document


class RetrievalState(BaseModel):
    query: str
    messages: List[BaseMessage] = []
    documents: Optional[List[Document]] = []
    answer: Optional[str] = None
    need_retrieval: bool = False


def generate_answer_directly(state: RetrievalState):
    """
    (节点) 直接生成回答,不需要检索
    :param state:
    :return:
    """
    prompt = ChatPromptTemplate.from_template("""
        回答用户的问题: {input}
    """)
    model = get_llm()
    chain = prompt | model
    result = chain.invoke({"input": state.query})

    # 提取内容字符串
    if hasattr(result, 'content'):
        answer_content = result.content
    else:
        answer_content = str(result)

    # 更新历史消息
    messages =state.messages.copy()
    messages.append(HumanMessage(content=state.query))
    messages.append(AIMessage(content=answer_content))

    return {"messages": messages, "answer": answer_content}


def judge_use_retrieval(state: RetrievalState):
    """
    (节点) 判断是否需要检索
    :param state:
    :return:
    """
    # 让模型根据问题判断是否需要检索
    prompt = ChatPromptTemplate.from_template("""
        你需要判断用户的问题是否需要参考外部文档才能回答。
        如果是关于常识、通用知识的问题，不需要检索，可以直接回答,直接回复"direct_answer"。
        如果涉及到具体的公司或者平台、技术，则需要检索文档进行回答，直接输出"retrieve"。

        用户问题: {query}

        回答格式: 只输出"retrieve"或"direct_answer"
        """)
    model = get_llm()
    chain = prompt | model
    result = chain.invoke({"query": state.query})
    content = result.content.strip()
    if "retrieve" in content:
        return {"need_retrieval": True} # 返回节点名称
    else:
        return {"need_retrieval": False}


def retrieval_documents(state: RetrievalState):
    """
    (节点) 检索文档
    :param state:
    :return:
    """
    query_embedding = get_embeddings([state.query])
    es_client = EsClient()
    docs = es_client.search_similar(query_embedding)
    return {"documents": docs}


def generate_answer_retrieval(state: RetrievalState):
    """
    (节点) 生成回答  基于检索的文档
    :param state:
    :param state:
    :return:
    """
    if not state.documents:
        print("No documents found. use directly answer")
        generate_answer_directly(state)
    else:
        # 构建提示
        prompt = ChatPromptTemplate.from_template("""
            基于以下文档内容，回答用户的问题。
            确保你的回答完全基于提供的文档，不要编造信息。
            如果文档中没有相关信息，直接说明无法回答。

            文档内容:
            {context}

            用户问题: {query}
            """)
        docs_content = [doc.page_content for doc in state.documents]
        docs_content = "\n".join(docs_content)

        # 调用模型
        model = get_llm()
        chain = prompt | model
        result = chain.invoke({"context": docs_content, "query": state.query})
        # 更新消息历史
        # 提取内容字符串
        if hasattr(result, 'content'):
            answer_content = result.content
        else:
            answer_content = str(result)

        # 更新历史消息
        messages = state.messages.copy()
        messages.append(HumanMessage(content=state.query))
        messages.append(AIMessage(content=answer_content))

        return {"messages": messages, "answer": answer_content}


def create_workflow():
    workflow = StateGraph(RetrievalState)
    # 添加节点
    workflow.add_node("generate_answer_directly", generate_answer_directly)
    workflow.add_node("judge_use_retrieval", judge_use_retrieval)
    workflow.add_node("retrieval_documents", retrieval_documents)
    workflow.add_node("generate_answer_retrieval", generate_answer_retrieval)

    # 添加边
    workflow.add_edge(START, "judge_use_retrieval")
    # 添加条件边
    workflow.add_conditional_edges("judge_use_retrieval", lambda state: "retrieval_documents" if state.need_retrieval else "generate_answer_directly")
    # 添加普通边
    workflow.add_edge("generate_answer_directly", END)
    workflow.add_edge("retrieval_documents", "generate_answer_retrieval")
    workflow.add_edge("generate_answer_retrieval", END)

    return workflow.compile(name="retrieval_workflow")


if __name__ == '__main__':
    workflow = create_workflow()
    result = workflow.invoke({"query": "codingplus使用的什么模型？"})
    print(result)