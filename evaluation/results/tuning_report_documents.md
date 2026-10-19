# Tuning Report

87 questions, collection `documents`, top 5. Mean with 95% confidence interval.

## Part 1: bm25 tokenizer

| Tokenizer | bm25 Recall@5 | bm25 MRR@5 |
|---|---|---|
| whitespace (old app setting) | 0.770 (0.68-0.86) | 0.657 (0.56-0.75) |
| punctuation stripped | 0.908 (0.84-0.97) | 0.775 (0.69-0.85) |
| stripped + stop words (now in the app) | 0.920 (0.86-0.98) | 0.820 (0.75-0.89) |
| stripped + stop words + stemming | 0.908 (0.84-0.97) | 0.819 (0.74-0.88) |

## Part 2: merging bm25 and semantic results (with the app's tokenizer)

| rrf constant | bm25 weight | Recall@5 | MRR@5 |
|---|---|---|---|
| 60 (current) | 1.0 | 0.943 (0.89-0.99) | 0.855 (0.79-0.91) |
| 60 | 0.5 | 0.931 (0.87-0.98) | 0.814 (0.74-0.87) |
| 60 | 0.3 | 0.931 (0.87-0.98) | 0.805 (0.73-0.87) |
| 30 | 1.0 | 0.943 (0.89-0.99) | 0.855 (0.79-0.91) |
| 30 | 0.5 | 0.931 (0.87-0.98) | 0.813 (0.74-0.87) |
| 10 | 1.0 | 0.943 (0.89-0.99) | 0.856 (0.79-0.92) |
| 10 | 0.5 | 0.943 (0.89-0.99) | 0.816 (0.75-0.88) |
