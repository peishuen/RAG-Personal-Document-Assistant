"""
This file handles the sessions api.
It lets the user create, list, open and delete saved chat sessions.
"""
from fastapi import APIRouter

from src.session.session_store import new_session_id, load_session, list_sessions, delete_session

router = APIRouter()


# return all saved sessions
@router.get("")
def get_sessions():
    return list_sessions()


# create a new session and return its id
@router.post("")
def create_session():
    return {"id": new_session_id()}


# return one session with all its turns
@router.get("/{session_id}")
def get_session(session_id: str):
    return {"id": session_id, "turns": load_session(session_id)}


# delete one session
@router.delete("/{session_id}")
def remove_session(session_id: str):
    delete_session(session_id)
    return {"deleted": session_id}
