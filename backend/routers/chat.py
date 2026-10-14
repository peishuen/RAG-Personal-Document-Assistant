"""
This file handles the chat api.
For one question, it rewrites the question, searches the documents,
generates an answer, adds citations, and saves the turn to the session.
The grounding check runs later in the background, so the answer is not delayed.
"""
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

# match markers like "[Source 1]" or "[1]" to check if the answer cited anything
CITATION_MARKER = re.compile(r"\[(?:Source )?\d+\]")


# describe the data the frontend sends: the question and the files to search in
class Question(BaseModel):
    question: str
    sources: list[str] = []


def _run_grounding_check(session_id: str, turn_index: int, answer: str, chunks: list[dict]):
    # run after the answer is already sent, so the user does not wait for it
    grounding = check_grounding(answer, chunks)

    # add the result to the saved turn
    turns = load_session(session_id)
    turns[turn_index]["grounded"] = grounding["grounded"]
    turns[turn_index]["grounding_reason"] = grounding["reason"]
    save_session(session_id, turns)


@router.post("/{session_id}/messages")
def ask_question(session_id: str, body: Question, background_tasks: BackgroundTasks):
    # follow these steps: rewrite, search, generate, cite, save
    # run the grounding check afterwards in the background
    prior_turns = load_session(session_id)

    # rewrite the question so it makes sense alone
    standalone_query = rewrite_query(body.question, prior_turns)
    # find the best 5 chunks
    chunks = cross_document_search(standalone_query, top_k=5, sources=body.sources)
    # write the answer from those chunks
    answer = generate_answer(standalone_query, chunks, prior_turns)
    # find which chunks the answer cited
    cited = build_cited_answer(answer, chunks)

    # keep citations as a list of fields, so the frontend can turn each [Source N] into a link
    citations = [
        {
            "number": chunks.index(chunk) + 1,
            "source": chunk["metadata"]["source"],
            "page": chunk["metadata"]["page"],
            "chunk_index": chunk["metadata"]["chunk_index"],
        }
        for chunk in cited["cited_chunks"]
    ]

    # build this turn, and fill the grounding fields later
    turn = {
        "question": body.question,
        "answer": cited["answer"],
        "grounded": None,
        "grounding_reason": None,
        "citations": citations,
    }

    turns = prior_turns + [turn]
    save_session(session_id, turns)

    # run the grounding check only when there are chunks and the answer cites a source
    # skip it otherwise (for example, when the answer is "I don't know")
    if chunks and CITATION_MARKER.search(answer):
        background_tasks.add_task(_run_grounding_check, session_id, len(turns) - 1, answer, chunks)
    else:
        # mark as not grounded and save the reason
        turn["grounded"] = False
        turn["grounding_reason"] = "no chunks were retrieved" if not chunks else "answer did not cite any source"
        save_session(session_id, turns)

    return turn
