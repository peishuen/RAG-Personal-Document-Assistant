# CLAUDE.md

Rules and context for working on Querio, a personal document assistant (RAG).

## Project

Users upload PDFs, text files and scanned reports, then ask questions and get answers with `[Source N]` citations.

- `src/` is the pipeline: ingestion, chunking, embeddings, vectorstore (ChromaDB), retrieval (BM25 + semantic, merged by reciprocal rank fusion), generation (query rewriter, prompt, grounding check), citation, metrics, session
- `backend/` is the FastAPI app (`main.py` + routers for documents, sessions, chat)
- `frontend/` is React + Tailwind + Vite. All api calls go through `frontend/src/api.js`
- `evaluation/` has the labeled QA sets, evaluation scripts and result reports
- `testing/` has the phase test scripts and `build_seed_db.py`
- `tests/` has the key-free unit tests that run in CI (chunker, text cleaner, rank fusion, citations). Test tools are in `requirements-dev.txt`
- `.github/workflows/ci.yml` is the CI/CD pipeline. `docker-compose.prod.yml` runs the backend and ngrok on the server
- `data/` holds runtime data (uploads, sessions, chroma_db). Only `sample_docs/` and `seed_chroma_db/` are committed

## Commands

```bash
# local backend with docker
docker compose up --build   # after code or requirements changes
docker compose up -d        # normal start
docker compose down

# local backend with conda
conda activate rag-env
uvicorn backend.main:app --reload --port 8000

# unit tests (no api keys needed)
python -m pytest tests -q

# frontend
cd frontend && npm run dev     # http://localhost:5173
cd frontend && npm run build   # check the build before pushing frontend changes

# public tunnel for a local backend (stop the server's tunnel first, the domain allows one tunnel at a time)
ngrok http --url=clutch-acre-size.ngrok-free.dev 8000
```

If `docker` is not on PATH in a shell, use `"C:\Program Files\Docker\Docker\resources\bin\docker.exe"`.

## Deployment

- Frontend: Cloudflare, built from `frontend/` on every push to `main` (config in `frontend/wrangler.jsonc`, build variable `VITE_API_BASE_URL`)
- Backend: runs on an AWS EC2 server (Ubuntu, x86) in Docker, from `docker-compose.prod.yml`. `data/` lives in the repo clone at `~/querio` on the server and is mounted into the container
- Pipeline: every push to `main` runs CI (`.github/workflows/ci.yml`): build frontend, build and test the backend image, publish it to `ghcr.io/peishuen/querio-backend` (tags `latest` and the commit sha), then deploy over SSH. The deploy job runs `git pull`, pulls the image, restarts the containers, waits for the health check, then calls `/health` through the public ngrok address. It fails if any of that fails
- GitHub secrets for the deploy: `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`. The server's SSH port must accept GitHub runner addresses, because they change
- Server setup, done once: install Docker, clone the repo to `~/querio`, run `docker login ghcr.io` with a token that has only `read:packages` (the image is private), and create `~/querio/.env`
- Tunnel: ngrok runs as a second container on the server, on the static domain. Only one tunnel can use the domain at a time, so stop any local ngrok first. The frontend sends `ngrok-skip-browser-warning` on every api call, so keep that header
- The server's public IP changes if the instance is stopped and started, unless an Elastic IP is attached. If it changes, update `EC2_HOST`
- `.env` holds `DASHSCOPE_*`, `VOYAGE_API_KEY`, `INVITE_CODE` and `CORS_ORIGINS`, plus `NGROK_AUTHTOKEN` on the server. Never print, commit or paste their values
- Access is by invitation link only (`?invite=<INVITE_CODE>`, sent as the `X-Invite-Code` header). There is no login form or typed access key. Do not add one back
- Render, Streamlit and `app.py` were removed. Do not add them back

## Decisions to keep

- No reranker. Retrieval is BM25 + Voyage `voyage-4` embeddings with rank fusion only. Do not add a reranker or local model fallback unless the user asks
- Embeddings use Voyage AI (`VOYAGE_API_KEY`), because the DashScope embedding free quota ran out. Without a payment method Voyage allows about 3 requests and 10k tokens a minute, so `embedder.py` batches 24 chunks per request and waits on rate limits. After changing the embedding model, re-embed with `testing/reembed_db.py`
- DashScope (chat model only now) quota is 1M tokens per model. Check usage before big evaluation runs. Answer-grading scripts (`evaluation.py`, `final_comparison.py`, `grounding_eval.py`) use 60k to 330k chat tokens each
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
