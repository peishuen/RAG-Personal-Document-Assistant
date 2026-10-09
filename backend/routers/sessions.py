# *** sessions router: create, list, resume, and delete saved chat sessions ***
from fastapi import APIRouter

from src.session.session_store import new_session_id, load_session, list_sessions, delete_session

router = APIRouter()


@router.get("")
def get_sessions():
    return list_sessions()


@router.post("")
def create_session():
    return {"id": new_session_id()}


@router.get("/{session_id}")
def get_session(session_id: str):
    return {"id": session_id, "turns": load_session(session_id)}


@router.delete("/{session_id}")
def remove_session(session_id: str):
    delete_session(session_id)
    return {"deleted": session_id}
