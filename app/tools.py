"""Lecture 03: tools for the agent.

Function docstrings and type hints here become the "tool descriptions" presented to the model.
Rewriting descriptions changes whether the model uses a tool and which arguments it supplies.
"""

import json
import random
import re
from datetime import datetime
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOG_DIR = Path(__file__).resolve().parent.parent / "learning_log"
MAX_RESULTS = 3


@cache
def load_glossary() -> list[dict]:
    with open(DATA_DIR / "glossary.json", encoding="utf-8") as f:
        return json.load(f)["terms"]


def _normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("　", "")


def _names(entry: dict) -> list[str]:
    return [_normalize(entry["term"]), _normalize(entry["id"])] + [
        _normalize(a) for a in entry["aliases"]
    ]


def search_glossary(query: str) -> str:
    """Search the course glossary and return definitions and the sessions that cover the terms.

    Use before answering about AI engineering terms or words specific to this course (AIE2026).
    Put only one term to look up in query (for example, "LoRA").
    """
    q = _normalize(query)
    if not q:
        return "The search query is empty. Specify one term to look up."
    glossary = load_glossary()

    exact = [e for e in glossary if q in _names(e)]
    # Exclude short names so aliases such as "r" do not match everything
    partial = [
        e for e in glossary
        if e not in exact and any(q in n or (len(n) >= 3 and n in q) for n in _names(e))
    ]
    in_definition = [
        e for e in glossary
        if e not in exact and e not in partial and q in _normalize(e["definition"])
    ]
    hits = (exact + partial + in_definition)[:MAX_RESULTS]

    if not hits:
        return f"The term '{query}' was not found in the glossary."
    return json.dumps(
        [
            {
                "term": e["term"],
                "lecture": e["lecture"],
                "definition": e["definition"],
                "related": e["related"],
            }
            for e in hits
        ],
        ensure_ascii=False,
    )


def get_lecture_summary(lecture: int) -> str:
    """Return key points from the specified session (an integer starting at 1).

    Use when asked about session content or relationships, such as "What will we learn in Lecture 03?".
    """
    path = DATA_DIR / "lectures" / f"{lecture:02d}.md"
    if not path.exists():
        available = sorted(p.stem for p in (DATA_DIR / "lectures").glob("*.md"))
        return f"Key points for Lecture {lecture:02d} are not available yet. Available sessions: {', '.join(available)}"
    return path.read_text(encoding="utf-8")


def make_quiz(lecture: int) -> str:
    """Pick one glossary term from the given session (an integer starting at 1) and return a review question and its answer.

    Use when the learner asks for a review question or a quiz, such as "Give me a review question for Lecture 2".
    The answer is the glossary definition. Show the question first and let the learner try before giving the answer.
    """
    terms = [t for t in load_glossary() if t["lecture"] == lecture]
    if not terms:
        available = sorted({t["lecture"] for t in load_glossary()})
        return f"There are no glossary terms for Lecture {lecture:02d}. Sessions with terms: {available}"
    term = random.choice(terms)
    return json.dumps(
        {"question": f"What does \"{term['term']}\" mean?", "answer": term["definition"], "lecture": lecture},
        ensure_ascii=False,
    )


def save_learning_log(title: str, content: str) -> str:
    """Save a learning record as a Markdown file in the learning_log/ folder and return the saved path.

    Use only when the learner explicitly asks to save, record, or note down what they learned.
    title is a short title (for example, "LoRA vs QLoRA"); content is the text to save.
        Call it directly when asked: the program itself asks the learner to approve the save, so do not ask for confirmation in your answer.
    """
    LOG_DIR.mkdir(exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()[:40] or "note"
    path = LOG_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}.md"
    path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
    return f"Saved: {path.relative_to(LOG_DIR.parent)}"