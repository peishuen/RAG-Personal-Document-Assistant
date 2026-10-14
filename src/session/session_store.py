"""
This file saves chat sessions to disk, with one json file for each session.
This lets a user reload the page and continue an old conversation.
Streamlit's own session_state cannot do this, because it is empty again
on every new browser connection.
"""

import json
import os
import time
import uuid

# set the folder where session files are saved
SESSIONS_DIR = "data/sessions"

def new_session_id() -> str:
    # create a random unique id
    return uuid.uuid4().hex

def _session_path(session_id: str) -> str:
    # build the file path for a session
    return os.path.join(SESSIONS_DIR, f"{session_id}.json")

def _read_session_file(session_id: str) -> dict | None:
    path = _session_path(session_id)
    # return nothing if the file does not exist
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_session(session_id: str, turns: list[dict]) -> None:
    # save only after at least one finished turn, to avoid creating empty files
    if not turns:
        return

    os.makedirs(SESSIONS_DIR, exist_ok=True)

    # keep the original created time if the session was saved before
    existing = _read_session_file(session_id)
    created_at = existing["created_at"] if existing else time.time()

    # use the first question as the title, and cut it at 60 characters to keep the list tidy
    first_question = turns[0]["question"]
    title = first_question if len(first_question) <= 60 else first_question[:60] + "..."

    # collect everything we want to save
    data = {
        "id": session_id,
        "title": title,
        "created_at": created_at,
        "updated_at": time.time(),
        "turns": turns
    }

    # write the data to the session file
    with open(_session_path(session_id), "w", encoding="utf-8") as f:
        json.dump(data, f)

def load_session(session_id: str) -> list[dict]:
    # return the saved turns, or an empty list if the session does not exist
    data = _read_session_file(session_id)
    return data["turns"] if data else []

def list_sessions() -> list[dict]:
    # return nothing if no session was ever saved
    if not os.path.exists(SESSIONS_DIR):
        return []

    sessions = []
    for filename in os.listdir(SESSIONS_DIR):
        # skip files that are not session files
        if not filename.endswith(".json"):
            continue

        # read the file, using the name without ".json" as the session id
        data = _read_session_file(filename[:-len(".json")])
        if data:
            sessions.append({
                "id": data["id"],
                "title": data["title"],
                "updated_at": data["updated_at"],
                "turn_count": len(data["turns"])
            })

    # sort with the newest first, so the latest conversation is at the top
    sessions.sort(key=lambda s: s["updated_at"], reverse=True)
    return sessions

def delete_session(session_id: str) -> None:
    path = _session_path(session_id)
    # delete the file only if it exists
    if os.path.exists(path):
        os.remove(path)

def format_relative_time(timestamp: float) -> str:
    # make a short label like "5m ago", and show the date when it is more than a week old
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
