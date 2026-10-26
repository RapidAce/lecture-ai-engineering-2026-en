"""Lecture 01 homework: run each question 3 times per condition, record time and tokens."""
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
    ("gemini-3.5-flash", None),
    ("gemini-3.5-flash-lite", 0.0),
]
QUESTIONS = [
    "What is LoRA?",
    "What are the 3 homework levels in the AIE2026 course?",
]
RUNS = 3
PAUSE = 6  # seconds between calls, to stay under free-tier per-minute limits
LEVELS = ("basic", "implementation", "advanced")


def call(client, model, temp, question):
    cfg = types.GenerateContentConfig(temperature=temp) if temp is not None else None
    err = ""
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
                "text": r.text or "",
            }
        except errors.APIError as e:
            err = f"{e.code}: {e.message}"[:200]
            print(f"  error ({err}); waiting 30s then retrying")
            time.sleep(30)
    return {"ok": False, "error": err}


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
                    snippet = res["text"][:90].replace("\n", " ")
                    print(f"{model} t={temp} run{i} {res['seconds']}s in={res['in']} out={res['out']} | {snippet}")
                else:
                    print(f"{model} t={temp} run{i} FAILED {res['error']}")
                time.sleep(PAUSE)

    Path("lectures/01/bench_results.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False)
    )

    print("\n=== SUMMARY (mean over runs) ===")
    for model, temp in CONDITIONS:
        for q in QUESTIONS:
            g = [
                r for r in rows
                if r["model"] == model and r["temperature"] == temp
                and r["question"] == q and r["ok"]
            ]
            distinct = len({r["text"] for r in g})
            line = (
                f"{model} t={temp} | {q[:40]!r} | ok={len(g)}/{RUNS} "
                f"sec={mean([r['seconds'] for r in g])} "
                f"in={mean([r['in'] for r in g])} "
                f"out={mean([r['out'] for r in g])} distinct_answers={distinct}"
            )
            if "homework levels" in q:
                correct = sum(all(l in r["text"].lower() for l in LEVELS) for r in g)
                line += f" mentions_all_3_levels={correct}/{len(g)}"
            print(line)


if __name__ == "__main__":
    main()
    