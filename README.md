# Personal Document Assistant (RAG)

A retrieval-augmented generation system that lets a user upload their own documents and ask questions about them in plain language. Instead of scrolling through a PDF or a set of notes, the user gets a direct answer with the exact source cited.

## Overview

This project demonstrates a full RAG pipeline built with LangChain and ChromaDB. It is designed to handle multiple document formats, compare retrieval methods, and reduce hallucination by grounding every answer in the retrieved source text.

The project is intentionally domain agnostic. The same pipeline works whether the uploaded document is a clean PDF, a lecture note, or a scanned report.

## Features

| Feature | Description |
|---|---|
| Multi-format ingestion | Accepts PDFs, plain text notes, and scanned reports as input |
| Adaptive chunking | Splits documents into chunks with a strategy that adjusts to document type and structure |
| Hybrid retrieval with reranking | Retrieves relevant chunks using both BM25 (keyword based) and semantic search (embedding based), combines the two into a single ranked list, and reranks the top results |
| Grounding check | Verifies that a generated answer is actually supported by the retrieved chunks before returning it |
| Retrieval evaluation | Measures retrieval quality using Precision@K and Recall@K for BM25, semantic search, and the combined hybrid ranking |
| Source citation | Every answer points back to the exact chunk or page it came from |
| Batch upload and cross-document Q&A | Supports uploading multiple documents at once and answering questions that draw from across all of them |

## Tech Stack

| Component | Role |
|---|---|
| LangChain | Orchestrates the retrieval and generation pipeline |
| ChromaDB | Local vector store for embedding storage and similarity search |
| BM25 | Sparse keyword based retrieval, used for comparison against semantic search |
| Embedding model | Converts document chunks and queries into vectors for semantic search |
| OCR (e.g. Tesseract) | Extracts text from scanned reports before chunking, used only when the uploaded document has no selectable text |
| LLM | Generates the final answer from the retrieved context |

## Project Structure

```
personal-document-assistant/
├── README.md
├── tasks.md
├── requirements.txt
├── .env.example
├── app.py
│
├── data/
│   └── sample_docs/              # PDF, notes, and scanned reports for testing
│
├── src/
│   ├── ingestion/
│   │   ├── pdf_loader.py
│   │   ├── text_loader.py
│   │   └── ocr_loader.py
│   │
│   ├── chunking/
│   │   └── chunker.py
│   │
│   ├── embeddings/
│   │   └── embedder.py
│   │
│   ├── vectorstore/
│   │   └── chroma_store.py
│   │
│   ├── retrieval/
│   │   ├── bm25_retriever.py
│   │   ├── semantic_retriever.py
│   │   ├── hybrid_ranker.py
│   │   └── cross_document.py     # merges retrieval results across multiple uploaded documents
│   │
│   ├── generation/
│   │   ├── prompt_templates.py
│   │   ├── grounding_check.py
│   │   └── generator.py
│   │
│   └── citation/
│       └── citation_tracker.py
│
├── evaluation/
│   ├── qa_dataset.json           # labeled question and answer pairs, with ground truth chunks
│   ├── run_evaluation.py
│   ├── embedding_comparison.py   # compares two embedding models on the same document set
│   └── results/
│       ├── evaluation_report.md
│       └── embedding_comparison_report.md
│
├── assets/
│   └── workflow-diagram.svg
│
└── tests/
    ├── test_chunking.py
    ├── test_retrieval.py
    └── test_generation.py
```

## Workflow

![RAG Pipeline Workflow](data:image/svg+xml;base64,PHN2ZyB2aWV3Qm94PSIwIDAgMTU1MCA0MDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgZm9udC1mYW1pbHk9IkFyaWFsLCBIZWx2ZXRpY2EsIHNhbnMtc2VyaWYiPgogIDxkZWZzPgogICAgPG1hcmtlciBpZD0iYXJyb3doZWFkIiBtYXJrZXJXaWR0aD0iMTAiIG1hcmtlckhlaWdodD0iMTAiIHJlZlg9IjgiIHJlZlk9IjMiIG9yaWVudD0iYXV0byIgbWFya2VyVW5pdHM9InN0cm9rZVdpZHRoIj4KICAgICAgPHBhdGggZD0iTTAsMCBMMCw2IEw5LDMgeiIgZmlsbD0iIzZiNzI4MCIgLz4KICAgIDwvbWFya2VyPgogIDwvZGVmcz4KCiAgPHJlY3QgeD0iMCIgeT0iMCIgd2lkdGg9IjE1NTAiIGhlaWdodD0iNDAwIiBmaWxsPSIjZmZmZmZmIi8+CgogIDx0ZXh0IHg9Ijc3NSIgeT0iMzAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTgiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSIjMTExODI3Ij5SQUcgUGlwZWxpbmUgV29ya2Zsb3c8L3RleHQ+CgogIDwhLS0gU3RhZ2UgMTogSW5nZXN0IC0tPgogIDxyZWN0IHg9IjIwIiB5PSIxNjUiIHdpZHRoPSIxNzAiIGhlaWdodD0iNzAiIHJ4PSIxMCIgZmlsbD0iI2VlZjRmYiIgc3Ryb2tlPSIjMjU2M2ViIiBzdHJva2Utd2lkdGg9IjIiLz4KICA8dGV4dCB4PSIxMDUiIHk9IjE5NSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxNSIgZm9udC13ZWlnaHQ9ImJvbGQiIGZpbGw9IiMxZjI5MzciPkluZ2VzdDwvdGV4dD4KICA8dGV4dCB4PSIxMDUiIHk9IjIxNSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzM3NDE1MSI+RG9jdW1lbnRzPC90ZXh0PgoKICA8IS0tIFN0YWdlIDI6IENodW5rIC0tPgogIDxyZWN0IHg9IjIzMCIgeT0iMTY1IiB3aWR0aD0iMTcwIiBoZWlnaHQ9IjcwIiByeD0iMTAiIGZpbGw9IiNlZWY0ZmIiIHN0cm9rZT0iIzI1NjNlYiIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPHRleHQgeD0iMzE1IiB5PSIxOTUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTUiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSIjMWYyOTM3Ij5DaHVuazwvdGV4dD4KICA8dGV4dCB4PSIzMTUiIHk9IjIxNSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzM3NDE1MSI+QWRhcHRpdmUgc3BsaXR0aW5nPC90ZXh0PgoKICA8IS0tIFN0YWdlIDM6IEVtYmVkIGFuZCBTdG9yZSAtLT4KICA8cmVjdCB4PSI0NDAiIHk9IjE2NSIgd2lkdGg9IjE3MCIgaGVpZ2h0PSI3MCIgcng9IjEwIiBmaWxsPSIjZWVmNGZiIiBzdHJva2U9IiMyNTYzZWIiIHN0cm9rZS13aWR0aD0iMiIvPgogIDx0ZXh0IHg9IjUyNSIgeT0iMTk1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjE1IiBmb250LXdlaWdodD0iYm9sZCIgZmlsbD0iIzFmMjkzNyI+RW1iZWQgJmFtcDsgU3RvcmU8L3RleHQ+CiAgPHRleHQgeD0iNTI1IiB5PSIyMTUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiMzNzQxNTEiPkNocm9tYURCPC90ZXh0PgoKICA8IS0tIFN0YWdlIDRhOiBCTTI1IC0tPgogIDxyZWN0IHg9IjY1MCIgeT0iNjAiIHdpZHRoPSIxNzAiIGhlaWdodD0iNzAiIHJ4PSIxMCIgZmlsbD0iI2ZlZjNlMiIgc3Ryb2tlPSIjZDk3NzA2IiBzdHJva2Utd2lkdGg9IjIiLz4KICA8dGV4dCB4PSI3MzUiIHk9IjkwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjE1IiBmb250LXdlaWdodD0iYm9sZCIgZmlsbD0iIzFmMjkzNyI+Qk0yNTwvdGV4dD4KICA8dGV4dCB4PSI3MzUiIHk9IjExMCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzM3NDE1MSI+S2V5d29yZCByZXRyaWV2YWw8L3RleHQ+CgogIDwhLS0gU3RhZ2UgNGI6IFNlbWFudGljIC0tPgogIDxyZWN0IHg9IjY1MCIgeT0iMjcwIiB3aWR0aD0iMTcwIiBoZWlnaHQ9IjcwIiByeD0iMTAiIGZpbGw9IiNlYWZhZjEiIHN0cm9rZT0iIzA1OTY2OSIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPHRleHQgeD0iNzM1IiB5PSIzMDAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTUiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSIjMWYyOTM3Ij5TZW1hbnRpYzwvdGV4dD4KICA8dGV4dCB4PSI3MzUiIHk9IjMyMCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzM3NDE1MSI+RW1iZWRkaW5nIHJldHJpZXZhbDwvdGV4dD4KCiAgPCEtLSBTdGFnZSA1OiBIeWJyaWQgUmFuayBhbmQgUmVyYW5rIC0tPgogIDxyZWN0IHg9Ijg4MCIgeT0iMTY1IiB3aWR0aD0iMTcwIiBoZWlnaHQ9IjcwIiByeD0iMTAiIGZpbGw9IiNmM2U4ZmYiIHN0cm9rZT0iIzdjM2FlZCIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPHRleHQgeD0iOTY1IiB5PSIxOTIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTQiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSIjMWYyOTM3Ij5IeWJyaWQgUmFuazwvdGV4dD4KICA8dGV4dCB4PSI5NjUiIHk9IjIxMCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzM3NDE1MSI+KyBSZXJhbms8L3RleHQ+CgogIDwhLS0gU3RhZ2UgNjogR3JvdW5kIGFuZCBHZW5lcmF0ZSAtLT4KICA8cmVjdCB4PSIxMDkwIiB5PSIxNjUiIHdpZHRoPSIxNzAiIGhlaWdodD0iNzAiIHJ4PSIxMCIgZmlsbD0iI2UwZjJmZSIgc3Ryb2tlPSIjMDM2OWExIiBzdHJva2Utd2lkdGg9IjIiLz4KICA8dGV4dCB4PSIxMTc1IiB5PSIxOTIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTQiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSIjMWYyOTM3Ij5Hcm91bmQgJmFtcDsgR2VuZXJhdGU8L3RleHQ+CiAgPHRleHQgeD0iMTE3NSIgeT0iMjEwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjMzc0MTUxIj5MTE0gKyBncm91bmRpbmcgY2hlY2s8L3RleHQ+CgogIDwhLS0gU3RhZ2UgNzogQ2l0ZSAtLT4KICA8cmVjdCB4PSIxMzAwIiB5PSIxNjUiIHdpZHRoPSIxNzAiIGhlaWdodD0iNzAiIHJ4PSIxMCIgZmlsbD0iI2ZkZjJmOCIgc3Ryb2tlPSIjYmUxODVkIiBzdHJva2Utd2lkdGg9IjIiLz4KICA8dGV4dCB4PSIxMzg1IiB5PSIxOTIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTQiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSIjMWYyOTM3Ij5DaXRlIFNvdXJjZXM8L3RleHQ+CiAgPHRleHQgeD0iMTM4NSIgeT0iMjEwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjMzc0MTUxIj5Tb3VyY2UgcmVmZXJlbmNlPC90ZXh0PgoKICA8IS0tIEFycm93cyAtLT4KICA8bGluZSB4MT0iMTkwIiB5MT0iMjAwIiB4Mj0iMjI4IiB5Mj0iMjAwIiBzdHJva2U9IiM2YjcyODAiIHN0cm9rZS13aWR0aD0iMiIgbWFya2VyLWVuZD0idXJsKCNhcnJvd2hlYWQpIi8+CiAgPGxpbmUgeDE9IjQwMCIgeTE9IjIwMCIgeDI9IjQzOCIgeTI9IjIwMCIgc3Ryb2tlPSIjNmI3MjgwIiBzdHJva2Utd2lkdGg9IjIiIG1hcmtlci1lbmQ9InVybCgjYXJyb3doZWFkKSIvPgogIDxsaW5lIHgxPSI2MTAiIHkxPSIyMDAiIHgyPSI2NDgiIHkyPSI5NSIgc3Ryb2tlPSIjNmI3MjgwIiBzdHJva2Utd2lkdGg9IjIiIG1hcmtlci1lbmQ9InVybCgjYXJyb3doZWFkKSIvPgogIDxsaW5lIHgxPSI2MTAiIHkxPSIyMDAiIHgyPSI2NDgiIHkyPSIzMDUiIHN0cm9rZT0iIzZiNzI4MCIgc3Ryb2tlLXdpZHRoPSIyIiBtYXJrZXItZW5kPSJ1cmwoI2Fycm93aGVhZCkiLz4KICA8bGluZSB4MT0iODIwIiB5MT0iOTUiIHgyPSI4NzgiIHkyPSIxOTAiIHN0cm9rZT0iIzZiNzI4MCIgc3Ryb2tlLXdpZHRoPSIyIiBtYXJrZXItZW5kPSJ1cmwoI2Fycm93aGVhZCkiLz4KICA8bGluZSB4MT0iODIwIiB5MT0iMzA1IiB4Mj0iODc4IiB5Mj0iMjEwIiBzdHJva2U9IiM2YjcyODAiIHN0cm9rZS13aWR0aD0iMiIgbWFya2VyLWVuZD0idXJsKCNhcnJvd2hlYWQpIi8+CiAgPGxpbmUgeDE9IjEwNTAiIHkxPSIyMDAiIHgyPSIxMDg4IiB5Mj0iMjAwIiBzdHJva2U9IiM2YjcyODAiIHN0cm9rZS13aWR0aD0iMiIgbWFya2VyLWVuZD0idXJsKCNhcnJvd2hlYWQpIi8+CiAgPGxpbmUgeDE9IjEyNjAiIHkxPSIyMDAiIHgyPSIxMjk4IiB5Mj0iMjAwIiBzdHJva2U9IiM2YjcyODAiIHN0cm9rZS13aWR0aD0iMiIgbWFya2VyLWVuZD0idXJsKCNhcnJvd2hlYWQpIi8+Cjwvc3ZnPgo=)

| Step | Description |
|------|-------------|
| Ingest | The user uploads one or more documents |
| Chunk | Documents are split into smaller pieces, with chunk size and overlap adjusted based on document type |
| Embed & Store | Each chunk is converted into a vector and stored in ChromaDB |
| Retrieve | A user question triggers retrieval using both BM25 and semantic search |
| Hybrid Rank & Rerank | The two result sets are combined into a single ranked list, and the top results are reranked |
| Ground & Generate | The retrieved chunks are passed to the LLM along with the question, and the generated answer is checked against the retrieved text before being returned |
| Cite | The final answer is returned along with the source chunk or page it was grounded in |

## Evaluation

Retrieval quality is measured with a small labeled question and answer set, built as follows:

- 3 to 5 documents are selected, covering the different formats the project supports (a clean PDF, a lecture note, a scanned report)
- For each document, 8 to 10 question and answer pairs are written based on content known to be in that document
- For each question, the chunk or chunks that contain the correct answer are marked as ground truth
- This gives a labeled set of roughly 30 to 50 question and answer pairs across all documents

Using this labeled set, three things are measured:

| What is measured | Description |
|---|---|
| Retrieval accuracy | Precision@K and Recall@K, calculated separately for BM25, semantic search, and the combined hybrid ranking, so the improvement from combining the two methods can be shown with actual numbers |
| Answer correctness | Whether the generated answer actually matches the expected answer, checked separately from retrieval accuracy since a correct retrieval does not always lead to a correct generated answer |
| Embedding model comparison | Two embedding models are run on the same document set, and differences in retrieval results are compared and recorded |

## Setup

```bash
# Clone the repository
git clone <repo-url>
cd personal-document-assistant

# Install dependencies
pip install -r requirements.txt

# Set your API key
export OPENAI_API_KEY=your-key-here

# Run the app
python app.py
```

## Usage

1. Upload one or more documents (PDF, text file, or scanned report)
2. Ask a question about its content, or a question that spans multiple uploaded documents
3. Review the answer along with the cited source
4. Optionally, compare BM25, semantic search, and hybrid ranking results for the same question

## Future Improvements

- Add latency and cost benchmarking for larger document sets

## Author

Pei Shuen
[GitHub](https://github.com/peishuen)
