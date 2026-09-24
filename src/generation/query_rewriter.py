# condense chat history and a new follow-up question into one standalone query
# lets retrieval work on follow-ups like "what about its accuracy" by resolving what "its" refers to

import os
import dashscope
from langchain_community.chat_models import ChatTongyi

# skip rewriting when there is no prior turn, the ques is already standalone
def rewrite_query(question: str, chat_history: list[dict]) -> str:
    if not chat_history:
        return question

    # point dashscope at the same endpoint used for embeddings and generation
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    dashscope.base_http_api_url = os.getenv("DASHSCOPE_HTTP_BASE_URL")

    llm = ChatTongyi(
        model_name="qwen-plus-character"
    )

    # only the question and answer text matter here, not grounding or citation details
    history_text = "\n".join(
        f"User: {turn['question']}\nAssistant: {turn['answer']}" for turn in chat_history
    )

    prompt = f"""
    Given the conversation history and a follow-up question, rewrite the follow-up question
    into a standalone question that makes sense without the history. \n
    
    If the follow-up question is already standalone, return it unchanged. 
    Only output the rewritten question, nothing else. \n

    Conversation history: {history_text} \n

    Follow-up question: {question} \n

    Standalone question: 
    """

    response = llm.invoke(prompt)
    return response.content.strip()