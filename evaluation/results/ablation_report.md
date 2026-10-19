# Ablation Study

Retrieval only, 87 labeled questions, top 5 results, Qwen embeddings. Each cell is the mean with a 95% bootstrap confidence interval.

## Part 1: pipeline components (the app's current setup)

| Method | Recall@5 | MRR@5 | Precision@5 |
|---|---|---|---|
| bm25 | 0.920 (0.86-0.98) | 0.838 (0.77-0.90) | 0.232 (0.21-0.26) |
| semantic | 0.931 (0.87-0.98) | 0.823 (0.75-0.89) | 0.239 (0.21-0.27) |
| rrf | 0.966 (0.92-1.00) | 0.883 (0.82-0.93) | 0.241 (0.22-0.27) |

## Part 2: chunk size, overlap and text preparation

Recall@5 for each method.

| Setup | bm25 | semantic | rrf |
|---|---|---|---|
| 400 / 60 | 0.885 (0.82-0.94) | 0.920 (0.86-0.98) | 0.885 (0.82-0.94) |
| 600 / 200 pdf, 800 / 100 text (raw text) | 0.920 (0.86-0.98) | 0.920 (0.85-0.97) | 0.943 (0.89-0.99) |
| 1000 / 150 | 0.920 (0.85-0.97) | 0.931 (0.87-0.98) | 0.954 (0.91-0.99) |
| 1500 / 200 | 0.954 (0.91-0.99) | 0.908 (0.84-0.97) | 0.966 (0.92-1.00) |
| current app (600 / 200 pdf, 800 / 100 text, cleaned text + header) | 0.920 (0.86-0.98) | 0.931 (0.87-0.98) | 0.966 (0.92-1.00) |
