# shared qwen client setup, so generator.py, query_rewriter.py and grounding_check.py
# don't each repeat the same dashscope config and model name

import os
from langchain_openai import ChatOpenAI

def get_llm() -> ChatOpenAI:
    # qwen3.8-flash is a dedicated workspace deployment, only reachable through the
    # openai-compatible route (the native dashscope sdk path 400s on this endpoint)
    return ChatOpenAI(
        model="qwen3.8-flash",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_OPENAI_BASE_URL"),
    )
