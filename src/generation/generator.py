# generate an answer from the retrieved chunks using qwen through langchain's dashscope wrapper

import os
import dashscope
from langchain_community.chat_models import ChatTongyi
from src.generation.prompt_templates import build_prompt

# build the grounded prompt and send it to the llm, then return just the answer text
def generate_answer(query: str, chunks: list[dict], chat_history: list[dict] = None) -> str:
    # point dashscope at the same endpoint used for embeddings
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    dashscope.base_http_api_url = os.getenv("DASHSCOPE_HTTP_BASE_URL")

    # qwen-plus's free quota is exhausted on this account, qwen-plus-character still has quota and works the same for plain q&a
    llm = ChatTongyi(
        model_name="qwen-plus-character"
    )
    prompt = build_prompt(query, chunks, chat_history)

    response = llm.invoke(prompt)
    return response.content