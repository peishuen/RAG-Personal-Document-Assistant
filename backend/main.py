"""
This file is the starting point of the fastapi backend.
It creates the app, allows requests from the react frontend (cors),
checks the access token on api calls, adds the routers,
and serves the built frontend in production.
"""
import os
import sys
from contextlib import asynccontextmanager

# add the project root to the python path, so imports like "src.xxx" work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# load the secret keys from the .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.routers import documents, sessions, chat
from src.vectorstore.chroma_store import seed_if_empty

# read the access token from the environment (empty means no login is needed)
APP_ACCESS_TOKEN = os.getenv("APP_ACCESS_TOKEN", "").strip()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # copy the prebuilt sample database on startup, because a fresh deploy has an empty chroma_db
    # use a plain file copy instead of running ocr and embedding, which ran out of memory on render
    # ignore errors here, so a failed copy does not stop the server from starting
    try:
        if seed_if_empty():
            print("seeded data/chroma_db from data/seed_chroma_db")
    except Exception as e:
        print(f"sample doc seeding skipped: {e}")

    # let the app run
    yield


app = FastAPI(title="Querio API", lifespan=lifespan)

# allow the frontend to call the api from any address
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def verify_access_token_middleware(request: Request, call_next):
    # protect only the /api/ paths, and leave static files open
    if request.url.path.startswith("/api/"):
        # let cors preflight requests and the verify endpoint through
        if request.method == "OPTIONS" or request.url.path == "/api/auth/verify":
            return await call_next(request)

        # check the token only when one is set
        if APP_ACCESS_TOKEN:
            # look for the token in the header first, then in the url
            token = (
                request.headers.get("X-Access-Token")
                or request.query_params.get("access_token")
                or request.query_params.get("token")
                or request.query_params.get("key")
            )
            # reject the request if the token is wrong or missing
            if token != APP_ACCESS_TOKEN:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized: valid access token required"}
                )

    # pass the request on to the real endpoint
    return await call_next(request)

# let the frontend check if the user's token is valid
@app.get("/api/auth/verify")
def verify_token(request: Request):
    # skip the check when no token is set
    if not APP_ACCESS_TOKEN:
        return {"authenticated": True, "auth_required": False}

    # get the token from the header or the url
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

# add the routers, each one handles a group of api paths
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(chat.router, prefix="/api/sessions", tags=["chat"])

# serve the built react frontend if the dist folder exists (production only)
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
