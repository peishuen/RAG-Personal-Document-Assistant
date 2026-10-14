# *** fastapi entrypoint: creates the app, enables cors for the react dev server, and mounts the routers ***
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.routers import documents, sessions, chat
from src.ingestion.sample_docs import ingest_sample_docs

APP_ACCESS_TOKEN = os.getenv("APP_ACCESS_TOKEN", "").strip()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # every fresh deploy starts with an empty chroma_db (it's gitignored, regenerated
    # data) so seed the sample docs here if they aren't already stored. best-effort:
    # a failure here (eg. missing api key) shouldn't stop the server from starting
    try:
        ingest_sample_docs()
    except Exception as e:
        print(f"sample doc ingestion skipped: {e}")

    yield


app = FastAPI(title="Querio API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def verify_access_token_middleware(request: Request, call_next):
    # Only protect /api/ endpoints, leaving static files and CORS preflights accessible
    if request.url.path.startswith("/api/"):
        if request.method == "OPTIONS" or request.url.path == "/api/auth/verify":
            return await call_next(request)

        if APP_ACCESS_TOKEN:
            token = (
                request.headers.get("X-Access-Token")
                or request.query_params.get("access_token")
                or request.query_params.get("token")
                or request.query_params.get("key")
            )
            if token != APP_ACCESS_TOKEN:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized: valid access token required"}
                )

    return await call_next(request)

@app.get("/api/auth/verify")
def verify_token(request: Request):
    if not APP_ACCESS_TOKEN:
        return {"authenticated": True, "auth_required": False}

    token = (
        request.headers.get("X-Access-Token")
        or request.query_params.get("access_token")
        or request.query_params.get("token")
        or request.query_params.get("key")
    )
    if token == APP_ACCESS_TOKEN:
        return {"authenticated": True, "auth_required": True}
    return JSONResponse(
        status_code=401,
        content={"authenticated": False, "auth_required": True, "detail": "Invalid or missing access token"}
    )

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(chat.router, prefix="/api/sessions", tags=["chat"])

# Serve compiled React frontend in production if dist exists
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
