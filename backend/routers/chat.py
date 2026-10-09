# *** chat router: runs the retrieval + generation pipeline for one question and saves the turn ***
import re

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from src.retrieval.cross_document import cross_document_search
from src.generation.query_rewriter import rewrite_query
from src.generation.generator import generate_answer
from src.generation.grounding_check import check_grounding
from src.citation.citation_tracker import build_cited_answer
from src.session.session_store import load_session, save_session

router = APIRouter()

# matches the same "[Source 1]" / "[1]" markers citation_tracker looks for, just to decide
# up front whether the answer cited anything at all worth fact-checking
CITATION_MARKER = re.compile(r"\[(?:Source )?\d+\]")


class Question(BaseModel):
    question: str
    sources: list[str] = []


def _run_grounding_check(session_id: str, turn_index: int, answer: str, chunks: list[dict]):
    # runs after the response has already gone out, so grounding never blocks the answer
    grounding = check_grounding(answer, chunks)

    turns = load_session(session_id)
    turns[turn_index]["grounded"] = grounding["grounded"]
    turns[turn_index]["grounding_reason"] = grounding["reason"]
    save_session(session_id, turns)


@router.post("/{session_id}/messages")
def ask_question(session_id: str, body: Question, background_tasks: BackgroundTasks):
    # same pipeline app.py ran inline: rewrite -> retrieve -> generate -> cite -> persist
    # grounding now happens after, in the background, instead of blocking the reply
    prior_turns = load_session(session_id)

    standalone_query = rewrite_query(body.question, prior_turns)
    chunks = cross_document_search(standalone_query, top_k=5, sources=body.sources)
    answer = generate_answer(standalone_query, chunks, prior_turns)
    cited = build_cited_answer(answer, chunks)

    # structured, not a pre-joined string, so the frontend can turn each [Source N] into a link
    citations = [
        {
            "number": chunks.index(chunk) + 1,
            "source": chunk["metadata"]["source"],
            "page": chunk["metadata"]["page"],
            "chunk_index": chunk["metadata"]["chunk_index"],
        }
        for chunk in cited["cited_chunks"]
    ]

    turn = {
        "question": body.question,
        "answer": cited["answer"],
        "grounded": None,
        "grounding_reason": None,
        "citations": citations,
    }

    turns = prior_turns + [turn]
    save_session(session_id, turns)

    # nothing to fact-check when the answer cites no source (eg. "I don't know") or
    # retrieval came back empty, skip the grounding call entirely instead of running it anyway
    if chunks and CITATION_MARKER.search(answer):
        background_tasks.add_task(_run_grounding_check, session_id, len(turns) - 1, answer, chunks)
    else:
        turn["grounded"] = False
        turn["grounding_reason"] = "no chunks were retrieved" if not chunks else "answer did not cite any source"
        save_session(session_id, turns)

    return turn
