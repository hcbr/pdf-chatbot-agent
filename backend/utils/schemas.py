"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: schemas.py
@time: 2025/10/27 17:06
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None

class DocumentSchema(BaseModel):
    page_content: str
    metadata: Dict[str, Any]

class IngestResponse(BaseModel):
    success: bool
    message: str
    document_count: int

class ChatResponse(BaseModel):
    content: str
    sources: List[DocumentSchema] = []