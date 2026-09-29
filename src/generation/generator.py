# generate an answer from the retrieved chunks using qwen through langchain's dashscope wrapper

from src.generation.prompt_templates import build_prompt
from src.generation.llm_client import get_llm

# build the grounded prompt and send it to the llm, then return just the answer text
def generate_answer(query: str, chunks: list[dict], chat_history: list[dict] = None) -> str:
    llm = get_llm()
    prompt = build_prompt(query, chunks, chat_history)

    response = llm.invoke(prompt)
    return response.content
