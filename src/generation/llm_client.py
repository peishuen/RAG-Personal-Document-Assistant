"""
This file sets up the qwen language model (llm) in one place.
generator.py, query_rewriter.py and grounding_check.py all use it, so they do
not need to repeat the same config and model name.
"""

import os
from langchain_openai import ChatOpenAI

def get_llm() -> ChatOpenAI:
    # connect to qwen3.8-flash through the openai-compatible route
    # use this route because the native dashscope sdk gives a 400 error on this endpoint
    return ChatOpenAI(
        model="qwen3.8-flash",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_OPENAI_BASE_URL"),
    )
