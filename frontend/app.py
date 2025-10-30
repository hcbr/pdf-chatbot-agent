"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: app.py
@time: 2025/10/30 13:52
"""
import streamlit as st
import requests
import json
import time
from typing import List, Dict, Any

# 配置页面
st.set_page_config(
    page_title="AI PDF Chatbot",
    page_icon="📄",
    layout="wide"
)

# 后端API地址
API_URL = "http://localhost:8000"

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# 标题
st.title("📄 AI PDF Chatbot")
st.write("上传PDF文档并与之对话，获取基于文档内容的回答")

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("查看来源"):
                for i, source in enumerate(message["sources"], 1):
                    st.write(f"来源 {i}:")
                    st.write(source["page_content"][:300] + "...")  # 显示部分内容

# 文件上传
with st.sidebar:
    st.subheader("文档管理")
    uploaded_files = st.file_uploader(
        "上传PDF文件",
        type="pdf",
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("处理文档"):
            with st.spinner("正在处理文档..."):
                files = [("files", (file.name, file.getvalue(), "application/pdf")) for file in uploaded_files]
                response = requests.post(f"{API_URL}/ingest", files=files)

                if response.status_code == 200:
                    result = response.json()
                    st.success(result["message"])
                    st.session_state.uploaded_files.extend(uploaded_files)
                else:
                    st.error(f"处理失败: {response.json().get('detail', '未知错误')}")

    if st.session_state.uploaded_files:
        st.subheader("已上传文档")
        for file in st.session_state.uploaded_files:
            st.write(file.name)

# 聊天输入
if prompt := st.chat_input("请输入你的问题..."):
    # 添加用户消息到会话状态
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(prompt)

    # 获取AI回答
    with st.chat_message("assistant"):
        # 发送请求到API
        try:
            response = requests.post(
                f"{API_URL}/chat",
                json={"query": prompt},
                stream=False
            )

            if response.status_code == 200:
                # 解析响应数据
                response_data = response.json()

                # 检查响应结构
                if isinstance(response_data, dict):
                    # 如果是事件格式
                    if response_data.get('event') == 'answer':
                        data = response_data.get('data', {})
                        content = data.get('content', '')
                        sources = data.get('sources', [])
                    else:
                        # 直接包含内容
                        content = response_data.get('content', '') or response_data.get('answer', '')
                        sources = response_data.get('sources', [])
                else:
                    content = str(response_data)
                    sources = []

                # 显示回答
                st.markdown(content)

                # 显示来源
                if sources:
                    with st.expander("查看来源"):
                        for i, source in enumerate(sources, 1):
                            st.write(f"来源 {i}:")
                            st.write(source.get("page_content", "")[:300] + "...")

                # 添加AI回答到会话状态
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": content,
                    "sources": sources
                })
            else:
                error_msg = f"API请求失败: {response.status_code}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

        except Exception as e:
            error_msg = f"获取回答失败: {str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })

# 添加清空聊天按钮
with st.sidebar:
    st.subheader("聊天管理")
    if st.button("清空聊天记录"):
        st.session_state.messages = []
        st.rerun()