"""Generate answers for my own evaluation set one case at a time, saving after each answer.

Same as `app.judge --generate`, but it waits between calls, retries on 429/503,
and skips cases that already have an answer, so a rerun continues where it stopped.
    uv run python scripts/gen_my_cases.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import agent, build_model
from app.judge import read_jsonl, write_jsonl

CASES = Path("data/eval/my_cases.jsonl")
cases = read_jsonl(CASES)
model = build_model()
for case in cases:
    if case.get("answer"):
        print(f"#{case['id']} already answered, skipping")
        continue
    for attempt in range(1, 6):
        try:
            case["answer"] = str(agent.run_sync(case["question"], model=model).output)
            write_jsonl(CASES, cases)
            print(f"#{case['id']} answered")
            break
        except Exception as e:  # 429 rate limit or 503 high demand
            print(f"#{case['id']} attempt {attempt} failed ({str(e)[:70]}); waiting 30s")
            time.sleep(30)
    time.sleep(8)
print("Done. Unanswered:", [c["id"] for c in cases if not c.get("answer")])