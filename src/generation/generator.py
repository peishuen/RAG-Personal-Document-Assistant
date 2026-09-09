# generate an answer from the retrieved chunks using qwen through langchain's dashscope wrapper

import os
import dashscope
from langchain_community.chat_models import ChatTongyi
from src.generation.prompt_templates import build_prompt

def generate_answer(query: str, chunks: list[dict]) -> str:
    # point dashscope at the same endpoint used for embeddings
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    dashscope.base_http_api_url = os.getenv("DASHSCOPE_HTTP_BASE_URL")

    llm = ChatTongyi(
        model_name="qwen-plus"
    )
    prompt = build_prompt(query, chunks)

    response = llm.invoke(prompt)
    return response.content