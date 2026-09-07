# turn chunk text into vectors using qwen's embedding model via dashscope

import os
import dashscope
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

def get_dashscope_embedder():
    # point dashscope at the internation endpoint
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    dashscope.base_http_api_url = os.getenv("DASHSCOPE_HTTP_BASE_URL")

    return DashScopeEmbeddings(
        model="text-embedding-v3",
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
    )

def get_local_embedder():
    # runs fully on machine, no api key or cost needed
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def generate_embeddings(chunks: list[dict]) -> list[dict]:
    # use the main embedding model (dashscope) to embed every chunk's text
    embedder = get_dashscope_embedder()

    texts = [chunk["text"] for chunk in chunks]
    vectors = embedder.embed_documents(texts)

    # attach every vector back onto its chunk, keep the text and metadata intact
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector

    return chunks