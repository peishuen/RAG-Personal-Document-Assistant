"""
This file downloads the six open-access arXiv papers used by the evaluation.
The pdfs are saved in data/eval_docs, which is not committed to git, so run this
once before build_eval_db.py on a fresh checkout.
Run it like this: python evaluation/download_eval_docs.py
"""

import os
import urllib.request

EVAL_DOCS_DIR = "data/eval_docs"

# list each paper as: file name, arxiv id
PAPERS = {
    "attention_is_all_you_need.pdf": "1706.03762",
    "bert.pdf": "1810.04805",
    "rag_knowledge_intensive_nlp.pdf": "2005.11401",
    "dense_passage_retrieval.pdf": "2004.04906",
    "deep_residual_learning.pdf": "1512.03385",
    "lora.pdf": "2106.09685",
}

if __name__ == "__main__":
    os.makedirs(EVAL_DOCS_DIR, exist_ok=True)

    for file_name, arxiv_id in PAPERS.items():
        path = os.path.join(EVAL_DOCS_DIR, file_name)

        # skip files that are already downloaded
        if os.path.exists(path):
            print(f"{file_name}: already there, skipped")
            continue

        # download the pdf from arxiv
        request = urllib.request.Request(f"https://arxiv.org/pdf/{arxiv_id}", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=120) as response, open(path, "wb") as f:
            f.write(response.read())
        print(f"{file_name}: downloaded")
