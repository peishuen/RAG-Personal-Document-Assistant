# turn chunk text into vectors using qwen's embedding model via dashscope

import os
import dashscope
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

def get_dashscope_embedder():
    # point dashscope at the internation endpoint
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    dashscope.base_http_api_url = os.getenv("DASHSCOPE_HTTP_BASE_URL")

    # text-embedding-v3 is not covered by this account's free tier, qwen3.7-text-embedding still has free quota
    return DashScopeEmbeddings(
        model="qwen3.7-text-embedding",
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
    )

def get_local_embedder():
    # runs fully on machine, no api key or cost needed
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# qwen3.7-text-embedding rejects a single request with more than 20 texts
EMBED_BATCH_SIZE = 20

def generate_embeddings(chunks: list[dict]) -> list[dict]:
    # use the main embedding model (dashscope) to embed every chunk's text
    embedder = get_dashscope_embedder()

    texts = [chunk["text"] for chunk in chunks]

    # embed in batches, since the model rejects one big request over the batch limit
    vectors = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i:i + EMBED_BATCH_SIZE]
        vectors.extend(embedder.embed_documents(batch))

    # attach every vector back onto its chunk, keep the text and metadata intact
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector

    return chunks