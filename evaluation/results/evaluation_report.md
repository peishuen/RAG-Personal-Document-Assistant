# Evaluation Report

## Setup

- **Documents evaluated:** 3 (`OPV2V.pdf`, `Coop-Percep.txt`, `Final-Presentation-Slide.pdf`), covering a dense academic PDF, a plain text summary, and a slide deck with one OCR'd page.
- **Labeled questions:** 26 total (9 from OPV2V.pdf, 8 from Coop-Percep.txt, 9 from Final-Presentation-Slide.pdf), each with one manually verified ground truth chunk. See `evaluation/qa_dataset.json`.
- **Retrieval settings:** Top@5 for all three methods (BM25, semantic search, hybrid fusion + rerank).
- **Answer correctness:** generated answer embedded and compared to the expected answer by cosine similarity, threshold 0.75.

## Retrieval Results

| Method | Precision@5 | Recall@5 |
|---|---|---|
| BM25 | 0.131 | 0.654 |
| Semantic search | 0.177 | 0.885 |
| Hybrid (fusion + rerank) | 0.192 | 0.962 |

**Note on precision:** every question has exactly one ground truth chunk, so the maximum possible Precision@5 is 1/5 = 0.20 (one relevant chunk out of five retrieved). Hybrid's 0.192 sits right at that ceiling, meaning it isn't just retrieving well, it's retrieving almost as well as this metric allows.

**Recall@5 is the clearest result.** BM25 found the correct chunk only 65.4% of the time, relying purely on keyword overlap. Semantic search improved that to 88.5% by matching meaning instead of exact words. Hybrid combined both signals and reranked the result with a cross-encoder, reaching 96.2%, missing only 1 of 26 questions. This is a direct, measured payoff from the work in Phase 6: combining retrieval methods recovers cases that either method misses on its own.

## Answer Correctness

Answer correctness was measured across 3 separate runs of `evaluation.py`, and the result was different every time:

| Run | Correct | Accuracy |
|---|---|---|
| Run 1 | 22/26 | 84.6% |
| Run 2 | 20/26 | 76.9% |
| Run 3 | 21/26 | 80.8% |

This variance comes entirely from generation, not retrieval — BM25, semantic, and hybrid precision/recall were identical across every run (retrieval is deterministic), while `qwen-plus-character` produces different wording, and occasionally a different decision to answer at all, for the exact same prompt each time. This is expected LLM sampling non-determinism, and it means a single accuracy percentage from one run should not be treated as a fixed score for this system.

**Two failures reproduced in every single run**, which makes them the most reliable findings in this report, not the raw accuracy percentage:

| Question | Similarity (typical) | What actually happened |
|---|---|---|
| What is explicitly listed as out of scope for this project? | 0.22-0.27 | The model swaps in content from the adjacent "Research Basis" section instead of the actual "Out of scope" bullets, every time. Reproduced across 5 separate test runs total (Phase 7, Phase 8 twice, and 3 evaluation runs). This is a genuine, repeatable comprehension limitation, not noise. |
| What is the title of this project's presentation, and who presented it? | 0.23 | The model answers "I don't know" every time, meaning the title slide's chunk (page 1) is consistently not being retrieved for this specific question, despite hybrid search's strong 96.2% recall overall. A genuine, repeatable retrieval gap for this one question. |

**Other failures did not reproduce.** For example, "what happens when detection confidence is <=0.30?" was answered correctly in Run 1 (similarity 0.725) but became "I don't know" in Run 3, using the exact same retrieved context both times. This points to generation occasionally refusing to answer despite having the right chunk in hand, rather than a fixed knowledge or retrieval gap. Several other "failures" across the 3 runs were phrasing differences that scored just under the 0.75 threshold (e.g. 0.673, 0.749) while being substantively correct, suggesting the threshold itself is a blunt instrument for this check.

## Key Takeaways

1. **Hybrid ranking measurably beats either individual method**, especially on recall (96.2% vs 88.5% semantic vs 65.4% BM25). This validates combining sparse and dense retrieval rather than picking one. Retrieval was also confirmed stable across all 3 runs, unlike generation.
2. **A correct citation does not guarantee a correct answer.** The "out of scope" question's chunk citation was accurate every run, but the model still misread which bullet list its content belonged to. Grounding checks based on embedding similarity to the source chunk cannot catch this class of error, since the answer is topically close to the right chunk even when it's factually wrong within it.
3. **Answer correctness is not a single number for this system.** Running the same 26 questions 3 times produced 3 different accuracy scores (76.9%-84.6%) with a different failure set each time, purely from generation non-determinism. Only the 2 failures that reproduced in every run should be treated as real, fixable limitations.
4. **A 0.75 similarity threshold for answer correctness is a blunt instrument.** Several "failures" across the 3 runs were phrasing differences rather than wrong answers, suggesting either a lower threshold or a different correctness method (e.g. LLM-as-judge) would give a more accurate picture.
5. **The model's willingness to say "I don't know" is a good sign for the grounding work in Phase 7**, but it cuts both ways: it correctly avoids hallucinating on a genuine retrieval miss (the title question), but it also sometimes refuses to answer questions it has already answered correctly before, using identical retrieved context.
