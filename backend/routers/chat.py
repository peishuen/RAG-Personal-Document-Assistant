"""
This file handles the chat api.
For one question, it rewrites the question, searches the documents,
generates an answer, adds citations, and saves the turn to the session.
There are two endpoints: one returns the full answer at once, and the stream
one sends the answer word by word, so the user can start reading sooner.
The grounding check runs later in the background, so the answer is not delayed.
Time and token use are logged for both parts (see src/metrics/tracker.py).
"""
import json
import queue
import re
import threading

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.retrieval.cross_document import cross_document_search
from src.generation.query_rewriter import rewrite_query
from src.generation.generator import generate_answer, stream_answer
from src.generation.grounding_check import check_grounding
from src.citation.citation_tracker import build_cited_answer
from src.session.session_store import load_session, append_turn, update_turn
from src.metrics.tracker import start_request, finish_request

router = APIRouter()

# match markers like "[Source 1]" or "[1]" to check if the answer cited anything
CITATION_MARKER = re.compile(r"\[(?:Source )?\d+\]")


# describe the data the frontend sends: the question and the files to search in
class Question(BaseModel):
    question: str
    sources: list[str] = []


def _run_grounding_check(session_id: str, turn_index: int, answer: str, chunks: list[dict]):
    # start a separate record, because this runs after the answer is sent
    start_request("grounding", session_id=session_id, turn_index=turn_index)

    # run after the answer is already sent, so the user does not wait for it
    grounding = check_grounding(answer, chunks)

    # add the result to the saved turn, without touching the other turns
    update_turn(session_id, turn_index, {
        "grounded": grounding["grounded"],
        "grounding_reason": grounding["reason"],
    })

    # write the record to the metrics file
    finish_request()


def _same_scope_history(turns: list[dict], sources: list[str]) -> list[dict]:
    # keep only the latest turns that were asked about the same chosen files
    # so a question about a new document is not mixed up with talk about the old one
    # turns saved before this field existed have no "sources", so treat them as the same scope
    current = set(sources)
    kept = []
    for turn in reversed(turns):
        if "sources" in turn and set(turn["sources"]) != current:
            break
        kept.append(turn)
    return list(reversed(kept))


def _prepare(session_id: str, body: Question):
    # rewrite the question so it makes sense alone, then find the best 5 chunks
    prior_turns = _same_scope_history(load_session(session_id), body.sources)
    standalone_query = rewrite_query(body.question, prior_turns)
    chunks = cross_document_search(standalone_query, top_k=5, sources=body.sources)
    return prior_turns, standalone_query, chunks


def _save_turn(session_id: str, question: str, answer: str, chunks: list[dict], sources: list[str]):
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
        "question": question,
        "sources": sources,
        "answer": cited["answer"],
        "grounded": None,
        "grounding_reason": None,
        "citations": citations,
    }

    # run the grounding check only when there are chunks and the answer cites a source
    # skip it otherwise (for example, when the answer is "I don't know")
    needs_grounding = bool(chunks and CITATION_MARKER.search(answer))
    if not needs_grounding:
        # mark as not grounded and save the reason
        turn["grounded"] = False
        turn["grounding_reason"] = "no chunks were retrieved" if not chunks else "answer did not cite any source"

    # add the turn to the latest saved session, and get its position
    turn_index = append_turn(session_id, turn)

    return turn, needs_grounding, turn_index


@router.post("/{session_id}/messages")
def ask_question(session_id: str, body: Question, background_tasks: BackgroundTasks):
    # start timing this request
    start_request("answer", session_id=session_id, sources_count=len(body.sources))

    # follow these steps: rewrite, search, generate, cite, save
    prior_turns, standalone_query, chunks = _prepare(session_id, body)
    answer = generate_answer(standalone_query, chunks, prior_turns)
    turn, needs_grounding, turn_index = _save_turn(session_id, body.question, answer, chunks, body.sources)

    # run the grounding check afterwards in the background
    if needs_grounding:
        background_tasks.add_task(_run_grounding_check, session_id, turn_index, answer, chunks)

    # write the answer record to the metrics file before replying
    finish_request()

    return turn


def _sse(payload: dict) -> str:
    # format one server-sent event: a "data:" line followed by a blank line
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/{session_id}/messages/stream")
def ask_question_stream(session_id: str, body: Question):
    # do all the work in one worker thread and pass events through a queue
    # use one thread so the metrics for this request stay together
    events = queue.Queue()

    def worker():
        try:
            start_request("answer", session_id=session_id, sources_count=len(body.sources), streamed=True)
            prior_turns, standalone_query, chunks = _prepare(session_id, body)

            # send each piece of the answer as soon as the llm writes it
            pieces = []
            for piece in stream_answer(standalone_query, chunks, prior_turns):
                pieces.append(piece)
                events.put({"type": "token", "text": piece})

            answer = "".join(pieces)
            turn, needs_grounding, turn_index = _save_turn(session_id, body.question, answer, chunks, body.sources)
            finish_request()
        except Exception as e:
            # log the real error here, and send a short message to the browser
            print(f"stream failed: {e}")
            events.put({"type": "error", "message": "something went wrong, please try again"})
            events.put(None)
            return

        # send the finished turn and close the stream, so the browser does not wait for grounding
        events.put({"type": "done", "turn": turn})
        events.put(None)

        # run the grounding check after the stream is closed
        if needs_grounding:
            _run_grounding_check(session_id, turn_index, answer, chunks)

    threading.Thread(target=worker, daemon=True).start()

    def event_stream():
        # pass events to the browser until the worker sends the stop signal
        while True:
            item = events.get()
            if item is None:
                break
            yield _sse(item)

    # tell proxies not to hold the stream back, so the words show up right away
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
