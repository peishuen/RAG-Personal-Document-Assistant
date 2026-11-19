"""
This file tests reciprocal rank fusion without any api key.
It only calls the merge function, so no search or embedding runs.
"""

import pytest

from src.retrieval.hybrid_ranker import reciprocal_rank_fusion, build_chunk_id, RRF_K


def make_result(name, page=1, index=0):
    # build a search result in the same shape the retrievers return
    return {"text": f"text of {name}", "metadata": {"source": name, "page": page, "chunk_index": index}}


def test_chunk_id_includes_source_page_and_chunk():
    assert build_chunk_id(make_result("a.pdf", page=2, index=5)) == "a.pdf_p2_c5"


def test_chunk_in_both_lists_beats_chunks_in_one_list():
    shared = make_result("shared.pdf")
    fused = reciprocal_rank_fusion(
        [make_result("bm25-only.pdf"), shared],
        [make_result("semantic-only.pdf"), shared],
    )
    # the shared chunk is second in both lists, but adds points twice
    assert fused[0]["metadata"]["source"] == "shared.pdf"
    assert len(fused) == 3


def test_score_is_the_sum_of_rank_points():
    shared = make_result("shared.pdf")
    fused = reciprocal_rank_fusion([shared], [make_result("other.pdf"), shared])
    # rank 0 in bm25 and rank 1 in semantic
    expected = 1 / (RRF_K + 1) + 1 / (RRF_K + 2)
    assert fused[0]["score"] == pytest.approx(expected)


def test_results_are_sorted_from_best_to_worst():
    fused = reciprocal_rank_fusion(
        [make_result("a.pdf"), make_result("b.pdf"), make_result("c.pdf")],
        [],
    )
    scores = [r["score"] for r in fused]
    assert scores == sorted(scores, reverse=True)
    assert [r["metadata"]["source"] for r in fused] == ["a.pdf", "b.pdf", "c.pdf"]


def test_empty_lists_give_empty_result():
    assert reciprocal_rank_fusion([], []) == []
