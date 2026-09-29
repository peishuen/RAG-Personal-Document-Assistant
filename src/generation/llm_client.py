# shared qwen client setup, so generator.py, query_rewriter.py and grounding_check.py
# don't each repeat the same dashscope config and model name

import os
import dashscope
from langchain_community.chat_models import ChatTongyi

def get_llm() -> ChatTongyi:
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    dashscope.base_http_api_url = os.getenv("DASHSCOPE_HTTP_BASE_URL")

    # qwen-plus's free quota is exhausted on this account, qwen-plus-character still has quota and works the same for plain q&a
    return ChatTongyi(model_name="qwen-plus-character")
