# persist chat sessions to disk, one json file per session, so a user can reload the
# page and pick up a past conversation as streamlit's own session_state doesn't survive
# a reload, it's recreated empty on every new browser connection

import json
import os
import time
import uuid

SESSIONS_DIR = "data/sessions"

def new_session_id() -> str:
    return uuid.uuid4().hex

def _session_path(session_id: str) -> str:
    return os.path.join(SESSIONS_DIR, f"{session_id}.json")

def _read_session_file(session_id: str) -> dict | None:
    path = _session_path(session_id)
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_session(session_id: str, turns: list[dict]) -> None:
    # only persist once there's at least one finished turn, so reloading before ever
    # asking a question doesn't litter the sessions folder with empty files
    if not turns:
        return

    os.makedirs(SESSIONS_DIR, exist_ok=True)

    existing = _read_session_file(session_id)
    created_at = existing["created_at"] if existing else time.time()

    # title the session after its first question, trimmed to keep the picker tidy
    first_question = turns[0]["question"]
    title = first_question if len(first_question) <= 60 else first_question[:60] + "..."

    data = {
        "id": session_id,
        "title": title,
        "created_at": created_at,
        "updated_at": time.time(),
        "turns": turns
    }

    with open(_session_path(session_id), "w", encoding="utf-8") as f:
        json.dump(data, f)

def load_session(session_id: str) -> list[dict]:
    data = _read_session_file(session_id)
    return data["turns"] if data else []

def list_sessions() -> list[dict]:
    # newest first, so the most recently active conversation sits at the top of the picker
    if not os.path.exists(SESSIONS_DIR):
        return []

    sessions = []
    for filename in os.listdir(SESSIONS_DIR):
        if not filename.endswith(".json"):
            continue

        data = _read_session_file(filename[:-len(".json")])
        if data:
            sessions.append({
                "id": data["id"],
                "title": data["title"],
                "updated_at": data["updated_at"],
                "turn_count": len(data["turns"])
            })

    sessions.sort(key=lambda s: s["updated_at"], reverse=True)
    return sessions

def delete_session(session_id: str) -> None:
    path = _session_path(session_id)
    if os.path.exists(path):
        os.remove(path)

def format_relative_time(timestamp: float) -> str:
    # short "x ago" label for the session picker, falls back to a date once it's old
    seconds = time.time() - timestamp

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    if seconds < 86400 * 7:
        return f"{int(seconds // 86400)}d ago"

    return time.strftime("%Y-%m-%d", time.localtime(timestamp))
