# compare dashscope embedding model against a local sentence-transformers model
# embeds the same chunks and test queries with both, then compares which chunks come back closest

import sys
import os

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
from src.embeddings.embedder import get_dashscope_embedder, get_local_embedder

def cosine_similarity(vec_a, vec_b):
    # measures how close two vectors point in the same direction (1 = identical, 0 = unrelated)
    vec_a, vec_b = np.array(vec_a), np.array(vec_b)
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))

def compare_models(chunks: list[str], query: str):
    dashscope_embedder = get_dashscope_embedder()
    local_embedder = get_local_embedder()

    # embed the query with both models
    dashscope_query_vec = dashscope_embedder.embed_query(query)
    local_query_vec = local_embedder.embed_query(query)

    # embed all chunks with both models
    dashscope_chunk_vecs = dashscope_embedder.embed_documents(chunks)
    local_chunk_vecs = local_embedder.embed_documents(chunks)

    # score every chunk against the query for each model
    dashscope_scores = [cosine_similarity(dashscope_query_vec, v) for v in dashscope_chunk_vecs]
    local_scores = [cosine_similarity(local_query_vec, v) for v in local_chunk_vecs]

    # rank chunks by score, highest first
    dashscope_ranked = sorted(zip(chunks, dashscope_scores), key = lambda x: x[1], reverse=True)
    local_ranked = sorted(zip(chunks, local_scores), key=lambda x: x[1], reverse=True)

    return dashscope_ranked, local_ranked