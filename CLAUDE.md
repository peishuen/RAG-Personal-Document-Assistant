# CLAUDE.md

Rules and context for working on Querio, a personal document assistant (RAG).

## Project

Users upload PDFs, text files and scanned reports, then ask questions and get answers with `[Source N]` citations.

- `src/` is the pipeline: ingestion, chunking, embeddings, vectorstore (ChromaDB), retrieval (BM25 + semantic, merged by reciprocal rank fusion), generation (query rewriter, prompt, grounding check), citation, metrics, session
- `backend/` is the FastAPI app (`main.py` + routers for documents, sessions, chat)
- `frontend/` is React + Tailwind + Vite. All api calls go through `frontend/src/api.js`
- `evaluation/` has the labeled QA sets, evaluation scripts and result reports
- `testing/` has the phase test scripts and `build_seed_db.py`
- `data/` holds runtime data (uploads, sessions, chroma_db). Only `sample_docs/` and `seed_chroma_db/` are committed

## Commands

```bash
# backend with docker (main way)
docker compose up --build   # after code or requirements changes
docker compose up -d        # normal start
docker compose down

# backend with conda
conda activate rag-env
uvicorn backend.main:app --reload --port 8000

# frontend
cd frontend && npm run dev     # http://localhost:5173
cd frontend && npm run build   # check the build before pushing frontend changes

# public tunnel for the backend
ngrok http --url=clutch-acre-size.ngrok-free.dev 8000
```

If `docker` is not on PATH in a shell, use `"C:\Program Files\Docker\Docker\resources\bin\docker.exe"`.

## Deployment

- Frontend: Cloudflare, built from `frontend/` on every push to `main` (config in `frontend/wrangler.jsonc`, build variable `VITE_API_BASE_URL`)
- Backend: runs on the user's own computer in Docker, with `data/` mounted from the host
- Tunnel: ngrok static domain. The frontend sends `ngrok-skip-browser-warning` on every api call, so keep that header
- `.env` holds `DASHSCOPE_*`, `APP_ACCESS_TOKEN` and `CORS_ORIGINS`. Never print, commit or paste their values
- Render, Streamlit and `app.py` were removed. Do not add them back

## Decisions to keep

- No reranker. Retrieval is BM25 + Qwen embeddings with rank fusion only. Do not add a reranker or local model fallback unless the user asks
- DashScope quota is 1M tokens per model (embedding and chat). Check usage before big evaluation runs. Answer-grading scripts (`evaluation.py`, `final_comparison.py`, `grounding_eval.py`) use 60k to 330k chat tokens each
- Chat history used for rewriting and answering only includes turns asked with the same file selection (`_same_scope_history` in `backend/routers/chat.py`)

## How to work

- Work phase by phase and task by task. Do not skip ahead
- Edit files directly when the user asks to implement something. State the filenames changed in the summary
- Read the relevant code before suggesting changes, and say what was not tested

## Code style

- Every file starts with a short comment or docstring saying what the file does
- Add inline comments through the code
- Comments use simple English, a human tone, and are short
- Comments start with a lowercase verb, for example `# load the pdf`, `# split pages into chunks`
- Match the naming and style of the surrounding code

## Git

- Commit or push only when the user says so
- Commit messages are short, lowercase and start with a verb, for example `skip the ngrok browser warning on api calls`
- Keep unrelated changes in separate commits

## Writing (README and docs)

- Straight to the point, but explain fully
- Prefer tables and short lists over long paragraphs
- Keep numbers honest, and say when a figure comes from a small sample or the development set
