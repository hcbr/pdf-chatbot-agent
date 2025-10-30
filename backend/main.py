"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: main.py
@time: 2025/10/27 13:54
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.ingest import router as ingest_router
from backend.api.chat import router as chat_router
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI(title="AI PDF Chatbot API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(ingest_router)
app.include_router(chat_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)