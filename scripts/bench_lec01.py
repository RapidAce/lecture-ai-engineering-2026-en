"""Lecture 01 homework: run each question 3 times per condition.

Records time, input/output/thinking tokens, API errors, and which model actually served the call.
"""
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from google.genai import errors, types

from app.config import get_api_key

CONDITIONS = [  # (model, temperature); None = API default
    ("gemini-3.5-flash-lite", None),
    ("gemini-3.5-flash", None),  # slides say this is forwarded to gemini-3.6-flash
    ("gemini-3.8-flash", None),  # slides: about 5/min and 10-20/day on the free tier
    ("gemini-3.5-flash-lite", 0.0),
]
QUESTIONS = [
    "What is LoRA?",
    "What are the 3 homework levels in the AIE2026 course?",
]
RUNS = 3
PAUSE = {"gemini-3.8-flash": 13}  # seconds between calls; default below
DEFAULT_PAUSE = 6
RETRY_WAIT = 35
LEVELS = ("basic", "implementation", "advanced")
OUT_JSON = "lectures/01/bench_results_run2.json"


def call(client, model, temp, question):
    cfg = types.GenerateContentConfig(temperature=temp) if temp is not None else None
    errs = []  # error codes seen before success (or before giving up)
    for _ in range(3):
        t0 = time.perf_counter()
        try:
            r = client.models.generate_content(model=model, contents=question, config=cfg)
            u = r.usage_metadata
            return {
                "ok": True,
                "seconds": round(time.perf_counter() - t0, 2),
                "in": u.prompt_token_count if u else None,
                "out": u.candidates_token_count if u else None,
                "think": getattr(u, "thoughts_token_count", None) if u else None,
                "served": getattr(r, "model_version", None),
                "text": r.text or "",
                "errors": errs,
            }
        except errors.APIError as e:
            errs.append(e.code)
            print(f"  error {e.code} ({str(e.message)[:80]}); waiting {RETRY_WAIT}s then retrying")
            time.sleep(RETRY_WAIT)
    return {"ok": False, "errors": errs}


def mean(values):
    values = [v for v in values if v is not None]
    return round(statistics.mean(values), 2) if values else None


def main():
    client = genai.Client(api_key=get_api_key())
    rows = []
    for model, temp in CONDITIONS:
        for q in QUESTIONS:
            for i in range(1, RUNS + 1):
                res = call(client, model, temp, q)
                res.update({"model": model, "temperature": temp, "question": q, "run": i})
                rows.append(res)
                if res["ok"]:
                    snippet = res["text"][:70].replace("\n", " ")
                    print(f"{model} t={temp} run{i} {res['seconds']}s in={res['in']} "
                          f"out={res['out']} think={res['think']} served={res['served']} "
                          f"errs={res['errors']} | {snippet}")
                else:
                    print(f"{model} t={temp} run{i} FAILED errs={res['errors']}")
                time.sleep(PAUSE.get(model, DEFAULT_PAUSE))

    Path(OUT_JSON).write_text(json.dumps(rows, indent=2, ensure_ascii=False))

    print("\n=== SUMMARY (mean over successful runs) ===")
    for model, temp in CONDITIONS:
        for q in QUESTIONS:
            allr = [r for r in rows if r["model"] == model and r["temperature"] == temp
                    and r["question"] == q]
            g = [r for r in allr if r["ok"]]
            n_err = sum(len(r["errors"]) for r in allr)
            secs = [r["seconds"] for r in g]
            served = sorted({str(r["served"]) for r in g})
            line = (
                f"{model} t={temp} | {q[:30]!r} | ok={len(g)}/{RUNS} api_errors={n_err} "
                f"sec_mean={mean(secs)} sec_max={max(secs) if secs else None} "
                f"in={mean([r['in'] for r in g])} out={mean([r['out'] for r in g])} "
                f"think={mean([r['think'] for r in g])} "
                f"distinct_answers={len({r['text'] for r in g})} served={served}"
            )
            print(line)


if __name__ == "__main__":
    main()