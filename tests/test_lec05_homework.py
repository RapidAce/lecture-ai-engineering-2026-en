"""Offline checks for the Lecture 05 homework changes (no API key needed)."""
import struct

import app.retrieval as R


def stored_vector(page_id: str) -> list[float]:
    with R.open_index(R.RAG_DB) as db:
        blob = db.execute("SELECT embedding FROM chunks WHERE page_id = ?", (page_id,)).fetchone()[0]
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


def test_adjacent_pages_stay_in_document_and_do_not_repeat():
    with R.open_index(R.RAG_DB) as db:
        hits = R.search_by_vector(db, stored_vector("lec03-main-p039"), 5)
    results = R.add_adjacent_pages(hits, 1)
    ids = [r["page_id"] for r in results]
    assert len(ids) == len(set(ids))
    hit_docs = {h["page_id"]: h["document_id"] for h in hits}
    for r in results:
        if "added_as" in r:
            source = r["added_as"].rsplit(" ", 1)[-1]
            assert r["document_id"] == hit_docs[source]


def test_adjacent_off_returns_hits_unchanged():
    hits = [{"page_id": "x", "document_id": "lec01-main", "page": 1}]
    assert R.add_adjacent_pages(hits, 0) == hits


def test_rerank_keeps_closest_candidates(monkeypatch):
    vector = stored_vector("lec03-main-p039")
    monkeypatch.setattr(R, "embed_text", lambda text, task: vector)
    monkeypatch.setattr(R, "GRAPH_RERANK_KEEP", 3)
    result = R.search_graph("memory")
    distances = [e["distance"] for e in result["expanded"]]
    assert result["reranked"] and len(distances) <= 3 and distances == sorted(distances)
