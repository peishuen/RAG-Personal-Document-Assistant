# confirm that all key packages load and the dashscope api key works

import os
import sys
import dashscope
from dotenv import load_dotenv
import chromadb
import langchain
from langchain_community.chat_models import ChatTongyi

# load api key and endpoint from .env
load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

# confirm values are loading correctly
api_key = os.getenv("DASHSCOPE_API_KEY")
base_url = os.getenv("DASHSCOPE_HTTP_BASE_URL")
print("api key loaded:", api_key[:15] + "..." if api_key else "NOT FOUND")
print("api key length:", len(api_key) if api_key else 0)
print("base url:", base_url if base_url else "NOT FOUND")

# explicitly point dashscope sdk to the international endpoint
dashscope.api_key = api_key
dashscope.base_http_api_url = base_url

# check all imports loaded
print("langchain:", langchain.__version__)
print("chromadb:", chromadb.__version__)
print("all packages imported successfully")

# test qwen connection via chattongyi, pass key directly to avoid env lookup issues
llm = ChatTongyi(
    model="qwen-turbo",
    dashscope_api_key=api_key,
)
response = llm.invoke("say hello in one word")
print("qwen response:", response.content)
