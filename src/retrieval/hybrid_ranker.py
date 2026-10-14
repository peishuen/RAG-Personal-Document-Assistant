"""
This file mixes the keyword (bm25) and meaning (semantic) search results.
It merges the two lists by rank position, not by raw score, because the two
scores cannot be compared directly.
Then it reranks the best matches with qwen3-rerank through dashscope,
which reads the question and each chunk again to pick the most relevant ones.
"""

import os
from concurrent.futures import ThreadPoolExecutor
import dashscope
from dashscope import TextReRank
from src.retrieval.bm25_retriever import bm25_search
from src.retrieval.semantic_retriever import semantic_search

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

def rerank(query: str, results: list[dict], top_k: int = 5) -> list[dict]:
    # return nothing if there is nothing to rerank
    if not results:
        return []

    # set the dashscope key and endpoint
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    dashscope.base_http_api_url = os.getenv("DASHSCOPE_HTTP_BASE_URL")

    documents = [r["text"] for r in results]
    try:
        # ask the rerank model to score each chunk against the question
        resp = TextReRank.call(
            model="qwen3-rerank",
            query=query,
            documents=documents,
            top_n=min(top_k, len(documents)),
            return_documents=False
        )

        # use the new order if the call worked
        if resp.status_code == 200 and resp.output and "results" in resp.output:
            reranked = []
            for item in resp.output["results"]:
                # find the original chunk and add the rerank score to a copy
                orig_index = item["index"]
                chunk = dict(results[orig_index])
                chunk["rerank_score"] = float(item["relevance_score"])
                reranked.append(chunk)
            return reranked
        else:
            error_msg = getattr(resp, "message", resp.status_code)
            print(f"Warning: qwen3-rerank call failed ({error_msg}), falling back to fusion order")
    except Exception as e:
        print(f"Warning: qwen3-rerank exception ({e}), falling back to fusion order")

    # keep the fusion order if the api call failed
    for r in results:
        r["rerank_score"] = float(r.get("score", 0.0))
    return results[:top_k]

def hybrid_search(query: str, collection_name: str = "documents", top_k: int = 5, fusion_k: int = 20, sources: list[str] | None = None) -> list[dict]:
    # run bm25 (local work) and semantic search (network call) at the same time to save time
    # get extra candidates from each, so the rerank step has more to choose from
    with ThreadPoolExecutor(max_workers=2) as executor:
        bm25_future = executor.submit(bm25_search, query, collection_name, fusion_k, sources)
        semantic_future = executor.submit(semantic_search, query, collection_name, fusion_k, sources)
        bm25_results = bm25_future.result()
        semantic_results = semantic_future.result()

    # merge the two lists into one
    fused_results = reciprocal_rank_fusion(bm25_results, semantic_results)

    # rerank only the top candidates, because reranking everything would be too slow
    return rerank(query, fused_results[:fusion_k], top_k=top_k)
