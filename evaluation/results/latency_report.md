# Latency and Token Report

How long one question takes and how many tokens it uses, before and after the optimizations. All runs used the live app on one document (the chip-types paper), with `qwen3.7-text-embedding` and `qwen3.8-flash`, timed by the app's own logging (`src/metrics/tracker.py`, summarised by `evaluation/latency_report.py`).

## Results

| | Original (3 questions) | Now (15 questions) |
|---|---|---|
| Complete answer, median | 17.9 s | **5.9 s** (p95 8.6 s) |
| First words appear, median | no streaming (same as above) | **5.0 s** (p95 7.5 s) |
| Grounding check, median (runs after the answer is sent) | 146.9 s (range 17.4 to 251.9 s) | **4.0 s** (p95 6.1 s) |
| Chat tokens per question (answer + grounding), mean | 8,568 | **1,534** |
| Grounding output tokens, mean | 6,840 | **215** |
| Rerank tokens per search | 2,325 | **0** (reranker removed) |

**Read it by kind of question**, because the medians above mix different kinds. The original code rewrote every question that had chat history, with unlimited thinking, so even a standalone question paid for a rewrite.

| Kind of question | Original | Now |
|---|---|---|
| No rewrite ran | 5.5 s (1 question) | 5.7 s median (11 questions) |
| A rewrite ran | 17.9 s and 26.5 s (2 questions; the second was not a follow-up) | 8.2 s median (4 questions) |
| The rewrite step itself | 7.8 s on average | 2.7 s median |

**So:** a plain question is about as fast as before (5 to 6 s). The latency gains are on questions that used to trigger a slow rewrite (one took 26.5 s) and on the grounding check, which went from 17 s to over 4 minutes down to a few seconds. The biggest saving is in tokens.

## What changed

- **Thinking budgets** (answer 300, grounding 200, rewrite 100 tokens; `max_tokens` is budget plus reply length): removed runaway hidden reasoning. The grounding check had used 1,029 to 12,969 output tokens for a three-line verdict.
- **Rewrite only for follow-ups** (word-pattern rule): standalone questions skip an LLM call of 2 to 3 s.
- **Streaming:** text appears as it is written. With thinking on, the first words still take about 5 s.
- **Reranker removed:** no rerank tokens. It saved almost no time, because the answer model dominates latency.

| Experiment (3 questions each) | Answer total, median | Answer output tokens | Grounding time, median | Grounding output tokens |
|---|---|---|---|---|
| Original: thinking unlimited | 17.9 s | 679 | 146.9 s | 6,840 |
| Thinking capped by budgets (adopted) | 7.9 s | 294 | 4.6 s | 255 |
| Thinking switched off (not adopted) | 4.5 s | 78 | 1.2 s | 47 |

The capped run's raw records were lost, so its two rows come from the figures printed at the time.

## Method

- **Now:** three fresh chats of five questions (standalone and follow-ups), after one discarded warm-up question so model loading does not skew the numbers. Each question writes one answer record and one grounding record to `data/metrics.jsonl`.
- **Original:** the first three questions of chat 1, before any optimization (thinking unlimited, rewrite on every follow-up, reranker on, no streaming).
- **Times** are measured inside the server (question received to answer saved). **Tokens** are the API's usage counts, thinking included.
- **Reproduce:** start the backend, ask questions, run `python evaluation/latency_report.py`.

## Per-question results

Now (15 questions):

| # | Question | Rewrite | Total (s) | First words (s) | Grounding (s) | Chat tokens |
|---|---|---|---|---|---|---|
| 1 | What types of chips does the paper discuss? | no | 4.3 | 3.9 | 3.2 | 921 |
| 2 | What are their main applications? | yes | 8.1 | 7.4 | 7.7 | 1,526 |
| 3 | Which chip type is used for IoT connections? | no | 4.9 | 3.8 | 5.4 | 1,395 |
| 4 | How are chips classified by manufacturing process? | no | 8.4 | 7.0 | 3.6 | 1,664 |
| 5 | What does the paper say about analog chips? | no | 7.0 | 5.1 | 4.5 | 1,835 |
| 6 | What are digital chips used for? | no | 4.2 | 4.0 | 3.8 | 987 |
| 7 | Can you give examples of them? | yes | 4.5 | 4.2 | 2.6 | 1,344 |
| 8 | What is the role of memory chips? | no | 2.7 | 2.5 | 2.0 | 964 |
| 9 | How does the paper describe chips in the automotive industry? | no | 7.1 | 5.5 | 4.5 | 1,503 |
| 10 | What challenges do chips face in medical rehabilitation? | no | 5.9 | 5.0 | 5.0 | 1,474 |
| 11 | Summarize the key points of the paper. | no | 5.7 | 4.2 | 4.0 | 1,753 |
| 12 | What about its future development trends? | yes | 8.4 | 6.9 | 3.7 | 1,843 |
| 13 | Which chips are used in Wi-Fi devices? | no | 4.4 | 3.5 | 4.2 | 1,423 |
| 14 | What is a DSP chip? | no | 7.4 | 6.2 | 4.7 | 1,765 |
| 15 | How are sensors related to chips in this paper? | yes | 8.9 | 7.8 | 3.5 | 2,610 |

Original (3 questions):

| # | Question | Rewrite | Total (s) | Grounding (s) | Chat tokens |
|---|---|---|---|---|---|
| 1 | What types of chips does the paper discuss? | no | 5.5 | 251.9 | 13,984 |
| 2 | What are their main applications? | yes | 17.9 | 146.9 | 8,254 |
| 3 | Which chip type is used for IoT connections? | yes | 26.5 | 17.4 | 3,466 |

## Limitations

- **Small samples:** the original run is 3 questions, the current run 15, on one document. Quote the figures as "about".
- **The rewrite rule is a word-pattern guess.** It fired on 4 questions: three follow-ups and one standalone question containing "this" (#15), which cost an extra 2 to 3 s.
- **Quality was checked separately** (`evaluation_report.md`). One follow-up on this document gave a weaker answer once after the reranker was removed and a good one on a re-run, so answers can vary.
- **Tokens only:** no money cost is reported.
