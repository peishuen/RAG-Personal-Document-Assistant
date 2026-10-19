"""
This file tracks the time and token use of one request, and logs it to a file.
Each request gets one record with the time of every stage (rewrite, retrieve,
generate) and the tokens used by the llm.
When the request ends, the record is added as one line to data/metrics.jsonl.
If no request is active (for example in tests), every function here does nothing.
"""

import json
import os
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

# set the file where the records are saved, one json line per request
METRICS_PATH = "data/metrics.jsonl"

# keep the record of the current request in a context variable, so each request has its own
_current = ContextVar("current_request", default=None)

def start_request(kind: str, **info) -> dict:
    # create a fresh record and remember when the request started
    record = {
        "kind": kind,
        "info": info,
        "stages_ms": {},
        "tokens": {"llm_input": 0, "llm_output": 0},
        "_start": time.perf_counter(),
    }
    _current.set(record)
    return record

@contextmanager
def timed(stage: str):
    # skip timing when no request is active
    record = _current.get()
    if record is None:
        yield
        return

    start = time.perf_counter()
    try:
        yield
    finally:
        # add the time to the stage, because a stage can run more than once
        elapsed_ms = (time.perf_counter() - start) * 1000
        record["stages_ms"][stage] = record["stages_ms"].get(stage, 0) + elapsed_ms

def elapsed_ms() -> float:
    # return the time since the request started, or 0 when no request is active
    record = _current.get()
    if record is None:
        return 0.0
    return (time.perf_counter() - record["_start"]) * 1000

def set_stage(stage: str, ms: float) -> None:
    # save a stage time that was measured outside of timed()
    record = _current.get()
    if record is not None:
        record["stages_ms"][stage] = ms

def record_llm(response) -> None:
    # read the token counts that langchain puts on the llm reply
    record = _current.get()
    if record is None:
        return

    usage = getattr(response, "usage_metadata", None) or {}
    record["tokens"]["llm_input"] += usage.get("input_tokens", 0)
    record["tokens"]["llm_output"] += usage.get("output_tokens", 0)

def finish_request() -> dict | None:
    record = _current.get()
    if record is None:
        return None

    total_ms = (time.perf_counter() - record["_start"]) * 1000

    line = {
        "time": datetime.now(timezone.utc).isoformat(),
        "kind": record["kind"],
        "info": record["info"],
        "total_ms": round(total_ms, 1),
        "stages_ms": {name: round(ms, 1) for name, ms in record["stages_ms"].items()},
        "tokens": record["tokens"],
    }

    # never let logging break a request, so ignore any write error
    try:
        os.makedirs(os.path.dirname(METRICS_PATH), exist_ok=True)
        with open(METRICS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
    except OSError:
        pass

    # clear the record, so the next request starts clean
    _current.set(None)
    return line
