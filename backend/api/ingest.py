"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: ingest.py
@time: 2025/10/29 11:38
"""
import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.workflows.ingestion_graph import create_ingestion_graph
from backend.utils.schemas import IngestResponse

router = APIRouter()
ingestion_graph = create_ingestion_graph()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_pdf(files: list[UploadFile] = File(...)):
    """上传并处理PDF文件"""
    # 验证文件类型
    for file in files:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file.filename}。请上传PDF文件。"
            )

    processed_count = 0

    # 处理每个文件
    for file in files:
        temp_file_path = None
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(await file.read())
                temp_file_path = temp_file.name

            # 运行处理工作流
            result = ingestion_graph.invoke({
                "file_path": temp_file_path
            })

            # 检查结果状态 - 使用字典键访问
            if result.get("status") == "error":
                raise HTTPException(
                    status_code=500,
                    detail=f"处理文件 {file.filename} 失败: {result.get('error', '未知错误')}"
                )

            processed_count += 1

        except HTTPException:
            # 重新抛出 HTTP 异常
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"处理文件 {file.filename} 时出错: {str(e)}"
            )
        finally:
            # 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    return {
        "success": True,
        "message": f"成功处理 {processed_count} 个PDF文件",
        "document_count": processed_count
    }