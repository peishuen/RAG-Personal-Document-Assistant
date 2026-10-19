"""
This file mixes the keyword (bm25) and meaning (semantic) search results.
It merges the two lists by rank position, not by raw score, because the two
scores cannot be compared directly (this is called reciprocal rank fusion).
The best merged chunks are the final search results, so there is no extra reranking model.
"""

from concurrent.futures import ThreadPoolExecutor
from src.retrieval.bm25_retriever import bm25_search
from src.retrieval.semantic_retriever import semantic_search
from src.metrics.tracker import timed

# set a constant that stops the top rank from dominating the score (60 is the usual default)
RRF_K = 60

def build_chunk_id(result: dict) -> str:
    # build the same chunk id used when saving, so chunks in both lists can be matched
    metadata = result["metadata"]
    return f"{metadata['source']}_p{metadata['page']}_c{metadata['chunk_index']}"

def reciprocal_rank_fusion(bm25_results: list[dict], semantic_results: list[dict]) -> list[dict]:
    # give each chunk points based on its rank in each list, then add the points together
    fused_scores = {}
    chunk_lookup = {}

    # add points from the bm25 list (a better rank gives more points)
    for rank, result in enumerate(bm25_results):
        chunk_id = build_chunk_id(result)
        fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)
        chunk_lookup[chunk_id] = result

    # add points from the semantic list in the same way
    for rank, result in enumerate(semantic_results):
        chunk_id = build_chunk_id(result)
        fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)
        chunk_lookup[chunk_id] = result

    # sort chunks by total points, highest first
    ranked_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)

    # build the final list with the new score
    fused_results = []
    for chunk_id in ranked_ids:
        result = chunk_lookup[chunk_id]
        fused_results.append({
            "text": result["text"],
            "metadata": result["metadata"],
            "score": fused_scores[chunk_id]
        })

    return fused_results

def hybrid_search(query: str, collection_name: str = "documents", top_k: int = 5, fusion_k: int = 20, sources: list[str] | None = None) -> list[dict]:
    # run bm25 (local work) and semantic search (network call) at the same time to save time
    # get extra candidates from each, so the merge has enough chunks to choose from
    # time both together, because they run in parallel and only the slower one matters
    with timed("retrieve"):
        with ThreadPoolExecutor(max_workers=2) as executor:
            bm25_future = executor.submit(bm25_search, query, collection_name, fusion_k, sources)
            semantic_future = executor.submit(semantic_search, query, collection_name, fusion_k, sources)
            bm25_results = bm25_future.result()
            semantic_results = semantic_future.result()

    # merge the two lists into one, and keep the best chunks
    return reciprocal_rank_fusion(bm25_results, semantic_results)[:top_k]
