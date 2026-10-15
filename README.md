# Personal Document Assistant (RAG)

Upload your own documents and ask questions in plain language. You get a direct answer with the exact source cited.

**Live demo:** [rag-personal-document-assistant.onrender.com](https://rag-personal-document-assistant.onrender.com/) (FastAPI + React, hosted on Render)
**Original Streamlit version:** [streamlit.app](https://peishuen-rag-personal-document-assistant-app-h78qzs.streamlit.app/)

## Features

- **Multi-format ingestion:** PDFs, text files, and scanned reports (OCR is used only when a page has no selectable text)
- **Adaptive chunking:** chunk size and overlap change with the document type
- **Hybrid retrieval:** BM25 (keywords) plus semantic search (embeddings), merged by rank, then reranked with `qwen3-rerank`
- **Cross-document Q&A:** upload many files at once, and optionally limit a question to chosen files
- **Grounding check:** an LLM fact-checks each answer against the retrieved chunks
- **Source citation:** every `[Source N]` in an answer links to the file, page and chunk it came from
- **Chat sessions:** conversations are saved and can be resumed, and follow-up questions are rewritten to stand alone
- **Optional access key:** protect the API with a token, or sign in with a magic link
- **Evaluation:** Precision@K, Recall@K and answer correctness for BM25, semantic and hybrid search

## Tech stack

| Part | Tool | Model or note |
|---|---|---|
| Pipeline | LangChain | |
| Vector store | ChromaDB | cosine similarity |
| Keyword search | BM25 (`rank_bm25`) | |
| Embeddings | Qwen via Alibaba DashScope | `qwen3.7-text-embedding` |
| Reranker | Qwen via DashScope | `qwen3-rerank` |
| LLM | Qwen via DashScope | `qwen3.8-flash` |
| OCR | Tesseract | used only for pages with no text |
| Backend | FastAPI | |
| Frontend | React, Tailwind CSS, Vite | |
| Deployment | Docker on Render | |
| Original UI | Streamlit (`app.py`) | |

## Workflow

![RAG Pipeline Workflow](assets/workflow-diagram.svg)

1. **Ingest:** load and read the uploaded files
2. **Chunk:** split pages into smaller pieces
3. **Embed and store:** turn chunks into vectors and save them in ChromaDB
4. **Retrieve:** run BM25 and semantic search on the question
5. **Rank:** merge the two lists and rerank the top results
6. **Generate and ground:** the LLM answers from the chunks, then the answer is fact-checked
7. **Cite:** return the answer with its sources

## Project structure

```
├── backend/            # fastapi app: main.py + routers (documents, sessions, chat)
├── frontend/           # react app: App.jsx, api.js, components (Document, Session, Chat panels)
├── src/                # the rag pipeline
│   ├── ingestion/      # pdf, text and ocr loaders, batch loader, sample docs
│   ├── chunking/
│   ├── embeddings/
│   ├── vectorstore/    # chromadb helpers and seeding
│   ├── retrieval/      # bm25, semantic, hybrid ranker, cross-document search
│   ├── generation/     # llm client, prompts, query rewriter, grounding check, generator
│   ├── citation/
│   └── session/        # saves chats as json files
├── data/
│   ├── sample_docs/    # 3 sample files
│   ├── seed_chroma_db/ # prebuilt db with only the sample docs (shipped in the image)
│   ├── chroma_db/      # live db (created at runtime)
│   ├── uploads/        # uploaded files
│   └── sessions/       # saved chats
├── evaluation/         # labeled qa set, evaluation scripts, results
├── testing/            # phase test scripts, build_seed_db.py, ingest_sample_docs.py
├── app.py              # original streamlit app
├── Dockerfile          # builds the react app, then runs fastapi
└── requirements.txt
```

## Setup

Easiest: use the [live demo](https://rag-personal-document-assistant.onrender.com/). To run locally, you need:

| Requirement | Needed for |
|---|---|
| Python 3.11 | backend and pipeline |
| Node.js | React frontend |
| DashScope API key | embeddings, reranking and answers |
| Tesseract (on PATH, or at the default Windows install path) | scanned PDFs only |

```bash
git clone https://github.com/peishuen/RAG-Personal-Document-Assistant.git
cd RAG-Personal-Document-Assistant
conda create -n rag-env python=3.11
conda activate rag-env
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
DASHSCOPE_API_KEY=your-key-here
DASHSCOPE_HTTP_BASE_URL=https://dashscope-intl.aliyuncs.com/api/v1
DASHSCOPE_OPENAI_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
APP_ACCESS_TOKEN=
```

| Variable | Purpose |
|---|---|
| `DASHSCOPE_API_KEY` | your DashScope key (required) |
| `DASHSCOPE_HTTP_BASE_URL` | endpoint for embeddings and reranking |
| `DASHSCOPE_OPENAI_BASE_URL` | endpoint for the language model |
| `APP_ACCESS_TOKEN` | optional, leave empty for no login |

Run the app:

```bash
# backend, from the project root
uvicorn backend.main:app --reload --port 8000

# frontend, in a second terminal
cd frontend
npm install
npm run dev
```

| Interface | Command | Address |
|---|---|---|
| Backend (FastAPI) | `uvicorn backend.main:app --reload --port 8000` | `http://localhost:8000` |
| Frontend (React) | `npm run dev` in `frontend/` | `http://localhost:5173` (open this one) |
| Original Streamlit app | `streamlit run app.py` | `http://localhost:8501` (also needs `.env`) |

On first start, the backend copies `data/seed_chroma_db` into `data/chroma_db`, so the sample docs are ready to query. If you change the sample docs, run `python testing/build_seed_db.py` and commit the new folder.

## Deployment (Render)

| Topic | Detail |
|---|---|
| Type | Docker web service, built from the `Dockerfile` |
| Env vars | the same four variables as the `.env` table above |
| Port | uses Render's `$PORT`, default 10000 |
| Seeding | a fresh deploy copies the prebuilt sample db instead of running OCR and embedding, which ran out of memory on the 512 MB free tier |
| Storage | uploads, sessions and new embeddings are lost on redeploy unless you attach a persistent disk |
| Private access | if `APP_ACCESS_TOKEN` is set, open `https://rag-personal-document-assistant.onrender.com/?access_token=YOUR_KEY`, or type the key on the login screen |
| Cold starts | the free tier sleeps when idle, so the first request can be slow |

## Usage

1. Upload one or more documents (PDF or text)
2. Optionally tick files to limit the search to them
3. Ask a question, or start from a suggestion
4. Read the answer, check the grounding badge, and click a `[Source N]` badge to see where it came from

## Evaluation

A labeled question set (`evaluation/qa_dataset.json`) marks the chunks that contain each correct answer. Run `python evaluation/evaluation.py` to measure:

- **Retrieval:** Precision@K and Recall@K for BM25, semantic and hybrid search
- **Answers:** whether the generated answer is close in meaning to the expected one
- **Embeddings:** `evaluation/embedding_comparison.py` compares DashScope with a local model

Results are saved in `evaluation/results/`.

## Future improvements

- Benchmark latency and cost on larger document sets
- Keep uploads and sessions after a redeploy, for example with a persistent disk or a hosted database

## Author

Pei Shuen · [GitHub](https://github.com/peishuen)
