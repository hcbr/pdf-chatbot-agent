"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: pdf_loader.py
@time: 2025/10/27 13:53
"""
from idlelib.outwin import file_line_pats

import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from backend.utils.config import settings
import os
import json
import requests


def process_pdf_server(file_path, prompt=None, skip_repeat=None):
    """
    处理PDF文件的客户端示例

    Args:
        file_path: 本地PDF文件路径
        prompt: 可选的提示词，如为None则使用默认提示词
        skip_repeat: 是否跳过重复内容

    Returns:
        dict: 处理结果，包含任务ID等信息
        None: 处理失败时返回None
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return None

    # API端点
    url = "http://10.10.185.1:32806/process_pdf"

    # 准备文件和数据
    try:
        files = {
            'file': ('input.pdf', open(file_path, 'rb'), 'application/pdf')
        }

        data = {}
        if prompt is not None:
            data['prompt'] = prompt
        if skip_repeat is not None:
            data['skip_repeat'] = str(skip_repeat).lower()

        print(f"正在处理PDF文件: {file_path}")

        # 发送请求
        response = requests.post(url, files=files, data=data, timeout=60)

        if response.status_code == 200:
            result = response.json()
            print(f"处理完成!")
            print(f"返回结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

            # 确保返回结果
            return result
        else:
            print(f"处理失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None

    except requests.exceptions.Timeout:
        print("请求超时，请检查服务是否正常")
        return None
    except requests.exceptions.ConnectionError:
        print("连接失败，请检查网络和服务地址")
        return None
    except Exception as e:
        print(f"请求出错: {e}")
        return None
    finally:
        # 确保文件被关闭
        if 'files' in locals() and 'file' in files:
            files['file'][1].close()


def parse_pdf(parse_type="", file_path=None):
    """
    pdf解析
    :param parse_type: 解析类型，默认使用第三方包
    :return:
    """
    print(f"开始解析PDF文件: {file_path}, 解析类型: {parse_type}")
    if parse_type == "server":
        # 调用pdf服务解析pdf  我部署的是deepseek-ocr
        parse_result = process_pdf_server(file_path)
        if parse_result and parse_result.get("files"):
            text = parse_result.get("files").get("mmd")  # 部署deepseek-ocr自己定义的返回结构
            return text
        else:
            print("pdf解析存在问题！")
            return None
    else:
        # 默认使用第三方包解析pdf
        with open(file_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text


def split_text_into_chunks(text, chunk_size=1000, chunk_overlap=100):
    """
    将文本分割成多个子字符串
    :param text:
    :param chunk_size:
    :param chunk_overlap:
    :return:
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    chunks = text_splitter.split_text(text)

    # 创建Document对象列表
    documents = [
        Document(
            page_content=chunk,
            metadata={"chunk_id": i}
        ) for i, chunk in enumerate(chunks)
    ]

    return documents


if __name__ == '__main__':
    file_path = r"D:\重要资料\浩鲸\CodingPLus-代码模型垂直领域微调技术报告.pdf"
    text = parse_pdf(parse_type="server", file_path=file_path)