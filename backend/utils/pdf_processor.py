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


def parse_pdf(parse_type="", file_path=None):
    """
    pdf解析
    :param parse_type: 解析类型，默认使用第三方包
    :return:
    """
    if parse_type == "local":
        # 使用第三方包解析pdf
        pass
    elif parse_type == "server":
        # 使用langchain解析pdf
        pass
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
    text = parse_pdf(parse_type="local", file_path=file_path)