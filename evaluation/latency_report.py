"""
This file summarises data/metrics.jsonl into latency and cost numbers.
It prints the median and 95th percentile time, the average time of each stage,
and the average tokens and cost per question, for each kind of request.
Run it like this: python evaluation/latency_report.py
"""

import json
import numpy as np

METRICS_PATH = "data/metrics.jsonl"

def load_records(path: str = METRICS_PATH) -> list[dict]:
    # read one json record per line
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def summarise(records: list[dict]) -> None:
    # group the records by kind (answer or grounding)
    kinds = sorted({r["kind"] for r in records})

    for kind in kinds:
        group = [r for r in records if r["kind"] == kind]
        totals = [r["total_ms"] for r in group]

        print(f"\n{kind}: {len(group)} requests")
        print(f"  total time: median {np.percentile(totals, 50):.0f} ms, p95 {np.percentile(totals, 95):.0f} ms")

        # average the time of each stage over the requests that used it
        stage_names = sorted({s for r in group for s in r["stages_ms"]})
        for stage in stage_names:
            values = [r["stages_ms"][stage] for r in group if stage in r["stages_ms"]]
            print(f"  {stage}: average {np.mean(values):.0f} ms ({len(values)} requests)")

        # average the tokens over all requests of this kind
        for token_name in ("llm_input", "llm_output"):
            average = np.mean([r["tokens"][token_name] for r in group])
            print(f"  {token_name} tokens: average {average:.0f}")

if __name__ == "__main__":
    # stop with a clear message when no questions have been logged yet
    try:
        records = load_records()
    except FileNotFoundError:
        raise SystemExit(f"no log found at {METRICS_PATH}, ask some questions in the app first")

    summarise(records)
