# Evaluation Report

The app searches with **BM25 plus Qwen semantic search, merged by reciprocal rank fusion (RRF)**, and answers with `qwen3.8-flash`. It has no reranker. One Qwen rerank call cost about 7,400 tokens on the evaluation papers (about 135 searches per 1M-token quota), so it was removed. Results from before that are listed at the end.

## Setup

- **Documents:** 9 in a separate evaluation database, so the app's data is never touched: 3 sample documents and 6 arXiv papers (Attention Is All You Need, BERT, RAG, Dense Passage Retrieval, ResNet, LoRA).
- **Development questions (87):** 26 original plus 61 drafted by an LLM from random chunks and reviewed by hand. Each has an exact quote marking where the answer lives, so a retrieved chunk counts as relevant when it contains that quote. This keeps labels valid when chunking changes, and exposed 3 original labels that pointed at chunks without the answer.
- **Held-out questions (19):** written after tuning: 11 paraphrased, 3 cross-document, 5 unanswerable (the right behaviour is to decline).
- **Metrics:** Recall@5 (is the answer chunk in the top 5) and MRR@5 (how high it ranks), each with a 95% bootstrap interval. Answers are graded by an LLM judge as correct, partial or wrong: 30 of the development questions and all 19 held-out ones.
- **Run it:** `build_eval_db.py`, then `evaluation.py`, `ablation.py`, `tuning.py`, `final_comparison.py`, `grounding_eval.py`.

## Results

**Search methods on the development questions** (the app's current setup):

| Method | Recall@5 | MRR@5 |
|---|---|---|
| BM25 | 0.920 (0.86-0.98) | 0.838 (0.77-0.90) |
| Semantic | 0.931 (0.87-0.98) | 0.823 (0.75-0.89) |
| **RRF (the app)** | **0.966 (0.92-1.00)** | **0.883 (0.82-0.93)** |

**Original vs tuned pipeline.** Original: whitespace BM25 tokens, raw text, no source header. Tuned: the current app.

| | Dev (87) original | Dev (87) tuned | Held-out (14 answerable) original | Held-out tuned |
|---|---|---|---|---|
| Recall@5 | 0.908 | **0.966** | 0.679 | **0.821** |
| MRR@5 | 0.788 | **0.883** | 0.589 | **0.673** |
| Answers fully correct | 26 / 30 | **28 / 30** | 16 / 19 | 16 / 19 |

All 5 unanswerable questions were declined correctly by both pipelines, including a trap (BERT's translation score, which lives in a different paper). Per-type verdicts: `final_comparison.md`.

**Grounding check.** 24 correct answers plus LLM-damaged copies; share flagged "not grounded":

| Setting | Good answer (false alarm) | Changed fact | Swapped answer | Added unsupported claim |
|---|---|---|---|---|
| Thinking budget 200 (app) | 0% | 92% | 100% | 96% |
| Thinking off | 0% | 96% | 100% | 96% |

**What each change was worth** (`tuning_report_documents.md`, `ablation_report.md`):

| Change | Result |
|---|---|
| BM25 tokenizer: strip punctuation and drop stop words | BM25 recall 0.770 to 0.920, MRR 0.657 to 0.820 |
| Stemming, other RRF constants (10, 30, 60), down-weighting BM25 | no gain |
| Chunk size | 400 characters was worst (RRF recall 0.885); 600 to 1,500 were within noise (0.943 to 0.966) |
| Cleaned text and a source header on each chunk | small (about +0.02 MRR in a one-off local-model test) |

## Takeaways

1. **The BM25 tokenizer fix was the most valuable change**, and it held on both sets (held-out BM25 recall 0.50 to 0.68).
2. **RRF beats either search alone on the development set** (0.966 vs 0.920 and 0.931). On the held-out questions, semantic search alone ranked the right chunk higher (MRR 0.750 vs 0.673), because keyword search adds noise when a question does not reuse the source's words.
3. **The tuned pipeline beat the original on both sets.** The held-out interval is wide (about 0.3), so read that gain as a direction.
4. **Realistic recall on harder, paraphrased or cross-document questions is about 0.8**, not the 0.97 seen on the development set.
5. **The system declines unanswerable questions reliably** (5 of 5), and **the grounding check catches deliberate damage well** (92% to 100%) with no false alarms.
6. **Removing the reranker cost little**: the earlier comparison below shows about 0.02 recall and 0.05 MRR, and graded answers stayed at 28 of 30.

## Limitations

- **Small samples:** 14 answerable held-out questions, 30 graded development answers, 24 grounding cases. Intervals are wide.
- **The development questions share wording with their sources** (drafted from the chunks), which flatters keyword and semantic search. The held-out set is the fairer test.
- **One model family** writes the held-out questions and damaged answers, answers, judges and grounds. The judge was not checked against human labels. Damaged answers are probably easier to catch than real hallucinations.
- **One gold quote per question:** a fact that appears in two chunks counts as found only if the labeled one is retrieved, so recall is slightly understated.

## Earlier results with the Qwen reranker (record only, not reproducible from the current code)

| Setup (87 questions) | Recall@5 | MRR@5 |
|---|---|---|
| First evaluation, old BM25: fusion only | 0.908 | 0.788 |
| First evaluation, old BM25: fusion + rerank | 0.966 | 0.904 |
| Fixed BM25, 30-chunk lists: fusion only | 0.954 | 0.861 |
| Fixed BM25, 30-chunk lists: fusion + rerank | 0.977 | 0.916 |

Reranking 10 candidates did as well as 20 or 30. That first evaluation also graded 28 of 30 answers correct. A small-local-model test of cleaned text plus a source header gave recall 0.966 to 0.977 and MRR 0.864 to 0.889.
