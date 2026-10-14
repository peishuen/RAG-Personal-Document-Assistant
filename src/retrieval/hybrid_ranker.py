# combine bm25 and semantic results, then rerank the top matches with qwen3-rerank via dashscope
# fuse by rank position, not raw score, since bm25 and semantic scores are not comparable

import os
from concurrent.futures import ThreadPoolExecutor
import dashscope
from dashscope import TextReRank
from src.retrieval.bm25_retriever import bm25_search
from src.retrieval.semantic_retriever import semantic_search

# dampens rank 1's weight in the fusion score, 60 is the standard rrf default
RRF_K = 60

def build_chunk_id(result: dict) -> str:
    # rebuild the chunk id used at storage time, so both result lists can be matched
    metadata = result["metadata"]
    return f"{metadata['source']}_p{metadata['page']}_c{metadata['chunk_index']}"

def reciprocal_rank_fusion(bm25_results: list[dict], semantic_results: list[dict]) -> list[dict]:
    # score each chunk by its rank in both lists, then merge into one fusion score
    fused_scores = {}
    chunk_lookup = {}

    for rank, result in enumerate(bm25_results):
        chunk_id = build_chunk_id(result)
        fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)
        chunk_lookup[chunk_id] = result

    for rank, result in enumerate(semantic_results):
        chunk_id = build_chunk_id(result)
        fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)
        chunk_lookup[chunk_id] = result

    # sort chunks by fusion score, highest first
    ranked_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)

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
    if not results:
        return []

    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    dashscope.base_http_api_url = os.getenv("DASHSCOPE_HTTP_BASE_URL")

    documents = [r["text"] for r in results]
    try:
        resp = TextReRank.call(
            model="qwen3-rerank",
            query=query,
            documents=documents,
            top_n=min(top_k, len(documents)),
            return_documents=False
        )

        if resp.status_code == 200 and resp.output and "results" in resp.output:
            reranked = []
            for item in resp.output["results"]:
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

    # fallback to reciprocal rank fusion ordering if API call fails
    for r in results:
        r["rerank_score"] = float(r.get("score", 0.0))
    return results[:top_k]

def hybrid_search(query: str, collection_name: str = "documents", top_k: int = 5, fusion_k: int = 20, sources: list[str] | None = None) -> list[dict]:
    # bm25 is local cpu work and semantic search is a network call, run them side by side
    # instead of one after the other, pull extra candidates from each before the rerank step
    with ThreadPoolExecutor(max_workers=2) as executor:
        bm25_future = executor.submit(bm25_search, query, collection_name, fusion_k, sources)
        semantic_future = executor.submit(semantic_search, query, collection_name, fusion_k, sources)
        bm25_results = bm25_future.result()
        semantic_results = semantic_future.result()

    fused_results = reciprocal_rank_fusion(bm25_results, semantic_results)

    # rerank only the fused candidates, reranking the whole collection would be too slow
    return rerank(query, fused_results[:fusion_k], top_k=top_k)
