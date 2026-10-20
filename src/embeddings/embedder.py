"""
This file turns chunk text into embeddings (lists of numbers that capture meaning).
Similar text gets similar numbers, which lets us search by meaning.
It uses qwen's embedding model through dashscope, and also has a local
model option that needs no api key.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
import dashscope
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

def get_dashscope_embedder():
    # point dashscope at the international endpoint
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    dashscope.base_http_api_url = os.getenv("DASHSCOPE_HTTP_BASE_URL")

    # use qwen3.7-text-embedding because it still has free quota on this account
    return DashScopeEmbeddings(
        model="qwen3.7-text-embedding",
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
    )

def get_local_embedder():
    # run the model on this machine, so no api key or cost is needed
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# send at most 20 texts per request, because the model rejects bigger requests
EMBED_BATCH_SIZE = 20

# send up to 4 requests at the same time, because most of the time is spent waiting for the network
EMBED_WORKERS = 4

def embed_batch(embedder, batch: list[str]) -> list[list[float]]:
    # try a batch twice, because a busy api can reject a request when several arrive together
    try:
        return embedder.embed_documents(batch)
    except Exception:
        time.sleep(1)
        return embedder.embed_documents(batch)

def generate_embeddings(chunks: list[dict]) -> list[dict]:
    # create the main embedding model (dashscope)
    embedder = get_dashscope_embedder()

    # get the text of every chunk
    texts = [chunk["text"] for chunk in chunks]

    # split the texts into small batches to stay under the limit
    batches = [texts[i:i + EMBED_BATCH_SIZE] for i in range(0, len(texts), EMBED_BATCH_SIZE)]

    # embed the batches at the same time, and keep them in the original order
    with ThreadPoolExecutor(max_workers=EMBED_WORKERS) as executor:
        batch_vectors = list(executor.map(lambda batch: embed_batch(embedder, batch), batches))

    # join the vectors of all batches into one list
    vectors = [vector for batch in batch_vectors for vector in batch]

    # add each vector back to its chunk and keep the text and metadata
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector

    return chunks