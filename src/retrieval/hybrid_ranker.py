# combine bm25 and semantic results, then rerank the top matches with a cross-encoder
# fuse by rank position, not raw score, since bm25 and semantic scores are not comparable

from sentence_transformers import CrossEncoder
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

def get_reranker():
    # load a small pretrained cross-encoder for scoring query and chunk together
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(query: str, results: list[dict], top_k: int = 5) -> list[dict]:
    reranker = get_reranker()

    # score each chunk against the query directly, slower but more accurate
    pairs = [[query, result["text"]] for result in results]
    scores = reranker.predict(pairs)

    # attach rerank scores and sort, highest first
    for result, score in zip(results, scores):
        result["rerank_score"] = float(score)

    reranked = sorted(results, key=lambda r: r["rerank_score"], reverse=True)
    return reranked[:top_k]

def hybrid_search(query: str, collection_name: str = "documents", top_k: int = 5, fusion_k: int = 20) -> list[dict]:
    # pull extra candidates from each method before the expensive rerank step
    bm25_results = bm25_search(query, collection_name, top_k=fusion_k)
    semantic_results = semantic_search(query, collection_name, top_k=fusion_k)

    fused_results = reciprocal_rank_fusion(bm25_results, semantic_results)

    # rerank only the fused candidates, reranking the whole collection would be too slow
    return rerank(query, fused_results[:fusion_k], top_k=top_k)
