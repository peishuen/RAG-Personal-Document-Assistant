# Evaluation Report

## Setup

- **Documents evaluated:** 3 (`OPV2V.pdf`, `Coop-Percep.txt`, `Final-Presentation-Slide.pdf`), covering a dense academic PDF, a plain text summary, and a slide deck with one OCR'd page.
- **Labeled questions:** 26 total (9 from OPV2V.pdf, 8 from Coop-Percep.txt, 9 from Final-Presentation-Slide.pdf), each with one manually verified ground truth chunk. See `evaluation/qa_dataset.json`.
- **Retrieval settings:** Top@5 for all three methods (BM25, semantic search, hybrid fusion + rerank).
- **Answer correctness:** generated answer embedded and compared to the expected answer by cosine similarity, threshold 0.75.

**Note on this version of the report:** the PDF text extraction pipeline was rebuilt (see the ingestion phase notes) to correctly read two-column research paper layouts, which changes chunk boundaries for `OPV2V.pdf`. Re-running this evaluation surfaced a real methodology gap: `qa_dataset.json`'s ground truth is a positional chunk id (`source_page_chunkindex`), not tied to chunk content, so when chunk boundaries shift, an old id can silently point at the wrong text without erroring. 4 of 9 `OPV2V.pdf` ground truth ids were found stale this way and have been corrected to the chunk that actually contains the expected answer (verified by hand, not just keyword matching). The numbers below reflect the corrected dataset and the current pipeline, and are not directly comparable to the previous version of this report, which measured a different (bugged) extraction against different ground truth.

## Retrieval Results

| Method | Precision@5 | Recall@5 |
|---|---|---|
| BM25 | 0.115 | 0.577 |
| Semantic search | 0.154 | 0.769 |
| Hybrid (fusion + rerank) | 0.177 | 0.885 |

**Note on precision:** every question has exactly one ground truth chunk, so the maximum possible Precision@5 is 1/5 = 0.20. Hybrid's 0.177 sits close to that ceiling.

**Hybrid still clearly beats either individual method**, consistent with the prior version of this report: BM25 alone misses the correct chunk on nearly half the questions (57.7% recall), semantic search improves that to 76.9%, and combining both with a reranking step reaches 88.5%.

## Answer Correctness

Answer correctness was measured on a single run this time (the prior version of this report ran 3 times and found generation non-determinism causes the score to vary by several points run to run — that finding still stands and should be kept in mind when reading a single percentage below).

**73.1% (19/26)** of generated answers matched the expected answer at the 0.75 similarity threshold. Breaking down the 7 failures:

| Question | Similarity | Category |
|---|---|---|
| Fusion strategy per Table IV | 0.731 | Threshold bluntness — answer is substantively correct, just paraphrased differently, scored just under the cutoff |
| Why compression/sync/security matter | 0.674 | Threshold bluntness — answer nearly restates the expected answer verbatim |
| Three collaboration levels | 0.742 | Threshold bluntness — answer lists the same three items, different wording |
| Presentation title and presenter | 0.234 | **Pre-existing retrieval gap** — the title-slide chunk is not retrieved in the top 5 at all. Same gap documented in the prior version of this report, reproduced again here, unrelated to this round's fixes |
| What is out of scope | 0.567 | **Pre-existing layout issue** — this question's source is a 3-column grid slide (not a 2-column layout), a different and still-unsolved problem from the two-column fix made this session |
| Confidence threshold ≤0.30 behavior | 0.614 | Generation gave a partial answer (mentioned RSU activation, omitted the RSU Pi/YOLOv8n/JSON transfer detail) despite the correct chunk being retrieved |
| Two deficiencies identified | 0.283 | Generation refusal — the correct chunk was retrieved in rank 1, but the model answered "I don't know" anyway. Same non-deterministic refusal pattern noted in the prior version of this report |

**3 of the 7 failures are the answer-correctness threshold being too blunt**, not real errors — this reinforces the earlier finding that a fixed 0.75 cosine cutoff is not a reliable pass/fail signal for this kind of paraphrase-heavy answer.

**2 of the 7 failures are pre-existing, already-documented issues** (the title-slide retrieval gap, and the 3-column grid slide's scrambled layout) that this session's PDF-extraction fix did not touch, because they have different root causes than the two-column interleaving bug that fix targeted.

## Key Takeaways

1. **Hybrid ranking still measurably beats either individual method** on this corrected dataset, confirming the earlier conclusion holds after the extraction pipeline changed.
2. **Ground truth datasets need to be re-verified whenever ingestion changes**, not just re-run. A positional chunk id is not a durable reference — 4 of 9 OPV2V ground truth entries had silently drifted to point at different content after the loader change, with no error raised anywhere in the pipeline.
3. **The answer-correctness threshold remains the biggest source of misleading "failures"** — 3 of 7 failures this run were near-correct paraphrases scored just under 0.75, not real mistakes.
4. **Two specific failure modes are known, pre-existing, and unrelated to this session's fixes**: the title-slide retrieval gap, and the 3-column grid slide's layout, which a simple two-column detector correctly declines to touch since splitting it in half would be equally wrong.
