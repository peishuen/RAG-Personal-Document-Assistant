# Original vs Tuned Pipeline

Both pipelines use Qwen embeddings and the same chat model, with BM25 and semantic search merged by rank fusion (no reranker), so they can be compared with each other.

## development set (87 questions, used while tuning)

**Retrieval (top 5)**

| Pipeline | Method | Recall@5 | MRR@5 |
|---|---|---|---|
| original | bm25 | 0.770 (0.68-0.86) | 0.657 (0.56-0.75) |
| original | semantic | 0.920 (0.85-0.97) | 0.767 (0.69-0.83) |
| original | rrf | 0.908 (0.84-0.97) | 0.788 (0.71-0.86) |
| tuned (current app) | bm25 | 0.920 (0.86-0.98) | 0.838 (0.77-0.90) |
| tuned (current app) | semantic | 0.931 (0.87-0.98) | 0.823 (0.75-0.89) |
| tuned (current app) | rrf | 0.966 (0.92-1.00) | 0.883 (0.82-0.93) |

**Answers graded by the LLM judge**

| Pipeline | Fully correct | Average score (partial = 0.5) |
|---|---|---|
| original | 26 / 30 | 0.900 (0.80-0.98) |
| tuned (current app) | 28 / 30 | 0.967 (0.92-1.00) |

**Verdicts by question type**

| Pipeline | Type | Correct | Partial | Wrong |
|---|---|---|---|---|
| original | development | 26 | 2 | 2 |
| tuned (current app) | development | 28 | 2 | 0 |

## held-out set (19 questions, written after tuning)

**Retrieval (top 5)**

| Pipeline | Method | Recall@5 | MRR@5 |
|---|---|---|---|
| original | bm25 | 0.500 (0.21-0.79) | 0.321 (0.13-0.52) |
| original | semantic | 0.786 (0.57-0.96) | 0.714 (0.50-0.89) |
| original | rrf | 0.679 (0.43-0.89) | 0.589 (0.36-0.79) |
| tuned (current app) | bm25 | 0.679 (0.43-0.86) | 0.543 (0.31-0.76) |
| tuned (current app) | semantic | 0.821 (0.61-1.00) | 0.750 (0.54-0.93) |
| tuned (current app) | rrf | 0.821 (0.64-0.96) | 0.673 (0.48-0.85) |

**Answers graded by the LLM judge**

| Pipeline | Fully correct | Average score (partial = 0.5) |
|---|---|---|
| original | 16 / 19 | 0.895 (0.76-1.00) |
| tuned (current app) | 16 / 19 | 0.895 (0.76-1.00) |

**Verdicts by question type**

| Pipeline | Type | Correct | Partial | Wrong |
|---|---|---|---|---|
| original | paraphrased | 9 | 1 | 1 |
| original | cross-document | 2 | 1 | 0 |
| original | unanswerable | 5 | 0 | 0 |
| tuned (current app) | paraphrased | 10 | 1 | 0 |
| tuned (current app) | cross-document | 1 | 1 | 1 |
| tuned (current app) | unanswerable | 5 | 0 | 0 |

