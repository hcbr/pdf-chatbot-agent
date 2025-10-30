"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: chat.py
@time: 2025/10/29 14:02
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from backend.workflows.retrieval_graph import create_workflow
from backend.utils.schemas import ChatRequest, ChatResponse
from langchain_core.messages import BaseMessage
import json
import asyncio

router = APIRouter()
retrieval_graph = create_workflow()


@router.post("/chat")
async def chat(request: ChatRequest):
    """处理聊天请求并返回流式响应"""
    try:
        # 初始状态
        state = {
            "query": request.query,
            "messages": []  # 可以从thread_id加载历史消息
        }
        result = retrieval_graph.invoke(state)
        answer = result.get("answer")
        return ChatResponse(content=str(answer), sources=[])

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理查询时出错: {str(e)}"
        )
