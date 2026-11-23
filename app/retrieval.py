"""Lecture 05: page-level vector search."""

import argparse
import json
import math
import re
import sqlite3
from contextlib import contextmanager
from collections import defaultdict, deque
from pathlib import Path

from google import genai
from google.genai import types
from pydantic_ai.exceptions import ModelHTTPError
import sqlite_vec

from app.config import (
    EMBEDDING_DIMENSIONS, EMBEDDING_MAX_TOKENS, EMBEDDING_MODEL,
    RAG_DB, RAG_DOCUMENT_IDS, RAG_SOURCE, RAG_TOP_K, RAG_TREE, get_api_key,
    RAG_GRAPH, GRAPH_START_K, GRAPH_HOPS, GRAPH_MAX_RESULTS,
    RAG_ADJACENT, GRAPH_RERANK_KEEP,
)


def get_all_materials() -> str:
    """Combine all materials into one string with lecture, section, and page metadata."""
    documents = json.loads(RAG_SOURCE.read_text(encoding="utf-8"))
    return "\n\n".join(
        f"Document: {document['id']} / {document['title']}\n"
        f"Section: {section['section']}\n"
        f"Page: {page.get('citation') or ('PDF p.' + str(page['page']))} / {page['title']}\n{page['content']}"
        for document in documents
        for section in document["content"]
        for page in section["content"]
    )

def load_pages(source: Path = RAG_SOURCE) -> list[dict]:
    """Convert document → section → page JSON into a page list for the selected materials."""
    documents = json.loads(source.read_text(encoding="utf-8"))
    pages = []
    for document in documents:
        if document["id"] not in RAG_DOCUMENT_IDS:
            continue
        for section in document["content"]:
            for page in section["content"]:
                pages.append({"page_id": page["id"], "document_id": document["id"],
                              "lecture": int(document["id"][3:5]), "document_title": document["title"],
                              "section": section["section"], "title": page["title"],
                              "page": page["page"], "content": page["content"]})
                if page.get("citation"):
                    pages[-1]["citation"] = page["citation"]
    return pages


def browse_tree(node_id: str | None = None) -> dict:
    """Return the first sentence for child pages and the full text for the selected page itself."""
    tree = json.loads(RAG_TREE.read_text(encoding="utf-8"))
    tree["children"] = [node for node in tree["children"] if node["id"] in RAG_DOCUMENT_IDS]
    node_id = node_id or tree["id"]
    pages = {page["page_id"]: page for page in load_pages(RAG_SOURCE)}

    def describe(node, full=False):
        info = {key: node[key] for key in ("id", "kind", "title")}
        if node["kind"] == "page":
            info.update({key: value for key, value in pages[node["id"]].items() if key != "page_id"})
            if not full:
                info["content"] = re.split(r"(?<=[。！？।॥])|(?<=[.!?؟])\s+|\n", info["content"].strip(), maxsplit=1)[0]
        return info

    remaining = [tree]
    while remaining:
        node = remaining.pop()
        if node["id"] == node_id:
            return {
                "node": describe(node, full=True),
                "children": [describe(child) for child in node.get("children", [])],
            }
        remaining.extend(node.get("children", []))
    raise ValueError("The requested table-of-contents node was not found.")


def read_page(page_id: str) -> dict:
    """Return text and citation metadata for one specified page from the main materials for Lectures 01–03."""
    for page in load_pages(RAG_SOURCE):
        if page["page_id"] == page_id:
            return page
    raise ValueError("The requested page was not found.")


def normalized_vector(values: list[float]) -> list[float]:
    """Normalize the vector to unit length."""
    norm = math.hypot(*values)
    if norm == 0:
        raise ValueError("The embedding is a zero vector.")
    return [value / norm for value in values]


def embed_text(text: str, task_type: str) -> list[float]:
    """Embed text with Gemini. Stop instead of truncating if the input limit is exceeded."""
    with genai.Client(api_key=get_api_key()) as client:
        count = client.models.count_tokens(model=EMBEDDING_MODEL, contents=text).total_tokens
        if count is None or count > EMBEDDING_MAX_TOKENS:
            raise ValueError(f"Embedding input exceeds the limit or could not be measured: {count} tokens.")
        response = client.models.embed_content(
            model=EMBEDDING_MODEL, contents=text,
            config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBEDDING_DIMENSIONS),
        )
    embedding = response.embeddings[0]
    if embedding.statistics and embedding.statistics.truncated:
        raise ValueError("The embedding API truncated the text.")
    return normalized_vector(embedding.values)


@contextmanager
def open_index(path: Path):
    """Open an existing search database read-only and close it on exit."""
    if not path.is_file():
        raise FileNotFoundError("Search database not found.")
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        db.row_factory = sqlite3.Row
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        yield db
    finally:
        db.close()


def search_by_vector(db, vector: list[float], limit: int) -> list[dict]:
    """Return up to limit pages closest to an already embedded query vector."""
    columns = {column["name"] for column in db.execute("PRAGMA table_info(chunks)")}
    citation = "citation," if "citation" in columns else ""
    rows = db.execute(f"""
        SELECT page_id, document_id, lecture, document_title, section, title, page, content,
               {citation}
               vec_distance_cosine(embedding, ?) AS distance
        FROM chunks ORDER BY distance, page_id LIMIT ?
    """, (sqlite_vec.serialize_float32(vector), limit))
    return [dict(row) for row in rows]


def search(query: str) -> list[dict]:
    """Embed the query and return up to RAG_TOP_K similar pages."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("The search query is empty.")
    with open_index(RAG_DB) as db:
        vector = embed_text(query.strip(), "RETRIEVAL_QUERY")
        return search_by_vector(db, vector, RAG_TOP_K)


def add_adjacent_pages(hits: list[dict], window: int = RAG_ADJACENT) -> list[dict]:
    """Homework (Implementation): after each hit, add the text of `window` pages before and after it.

    Only pages from the same document are added (no crossing into another lecture),
    pages already in the results are not repeated, and each added page records which hit it came from.
    """
    if window <= 0:
        return hits
    by_position = {(page["document_id"], page["page"]): page for page in load_pages(RAG_SOURCE)}
    seen = {hit["page_id"] for hit in hits}
    results = []
    for hit in hits:
        results.append(hit)
        for offset in [o for o in range(-window, window + 1) if o != 0]:
            neighbor = by_position.get((hit["document_id"], hit["page"] + offset))
            if neighbor is None or neighbor["page_id"] in seen:
                continue
            seen.add(neighbor["page_id"])
            results.append({**neighbor, "added_as": f"adjacent page of {hit['page_id']}"})
    return results


def search_with_adjacent(query: str) -> list[dict]:
    """Vector search, plus adjacent pages when RAG_ADJACENT > 0 (used by search_materials and the CLI)."""
    return add_adjacent_pages(search(query))


def rerank_by_distance(db, vector: list[float], candidates: list[dict], keep: int) -> list[dict]:
    """Homework (Advanced): sort graph candidates by embedding distance to the question and keep the closest ones.

    Uses the page embeddings already stored in the index, so it needs no extra API call.
    """
    if not candidates or keep <= 0:
        return candidates
    ids = [candidate["page_id"] for candidate in candidates]
    marks = ",".join("?" for _ in ids)
    rows = db.execute(
        f"SELECT page_id, vec_distance_cosine(embedding, ?) AS distance FROM chunks WHERE page_id IN ({marks})",
        (sqlite_vec.serialize_float32(vector), *ids),
    )
    distance = {row["page_id"]: row["distance"] for row in rows}
    ranked = sorted(candidates, key=lambda c: (distance.get(c["page_id"], 2.0), c["hops"], c["page_id"]))
    return [{**c, "distance": distance.get(c["page_id"])} for c in ranked[:keep]]


def search_graph(query: str) -> dict:
    """Start with vector search, then expand candidates through adjacent pages and shared terms."""
    pages = {page["page_id"]: page for page in load_pages(RAG_SOURCE)}
    graph = json.loads(RAG_GRAPH.read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in graph["nodes"]
             if node["kind"] == "term" or node["id"] in pages}
    adjacent = defaultdict(set)
    for edge in graph["edges"]:
        a, b = edge["source"], edge["target"]
        if edge["relation"] in ("next_page", "mentions") and a in nodes and b in nodes:
            adjacent[a].add(b)
            adjacent[b].add(a)

    if not isinstance(query, str) or not query.strip():
        raise ValueError("The search query is empty.")
    with open_index(RAG_DB) as db:
        vector = embed_text(query.strip(), "RETRIEVAL_QUERY")  # embed once; reused for re-ranking
        hits = search_by_vector(db, vector, RAG_TOP_K)
    seeds = [hit for hit in hits if hit["page_id"] in pages][:min(GRAPH_START_K, GRAPH_MAX_RESULTS)]
    seed_ids = {seed["page_id"] for seed in seeds}
    results, candidates = [], {}
    for rank, seed in enumerate(seeds):
        root = seed["page_id"]
        results.append({**pages[root], "distance": seed["distance"], "hops": 0,
                        "path": [{"id": root, "title": pages[root]["title"]}]})
        queue = deque([(root, [root])])
        visited = {root}
        while queue:
            current, path = queue.popleft()
            if len(path) - 1 >= GRAPH_HOPS:
                continue
            # At the same depth, follow terms with fewer connections first.
            neighbors = sorted(adjacent[current], key=lambda n: (len(adjacent[n]), n))
            for neighbor in neighbors:
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                route = path + [neighbor]
                queue.append((neighbor, route))
                if neighbor not in pages or neighbor in seed_ids:
                    continue
                frequency = max((len(adjacent[n]) for n in route if nodes[n]["kind"] == "term"), default=0)
                priority = (len(route) - 1, frequency, rank, neighbor)
                candidate = {**pages[neighbor], "hops": len(route) - 1,
                             "path": [{"id": n, "title": nodes[n]["title"]} for n in route]}
                if neighbor not in candidates or priority < candidates[neighbor][0]:
                    candidates[neighbor] = (priority, candidate)
    expanded = [candidate for _, candidate in sorted(candidates.values())]
    if GRAPH_RERANK_KEEP > 0:
        # Advanced: rank every graph candidate by closeness to the question instead of by hop order
        with open_index(RAG_DB) as db:
            expanded = rerank_by_distance(db, vector, expanded, GRAPH_RERANK_KEEP)
    return {"seeds": results, "expanded": expanded[:max(0, GRAPH_MAX_RESULTS - len(results))],
            "max_hops": GRAPH_HOPS, "reranked": GRAPH_RERANK_KEEP > 0}



def run_full_context(agent, question: str, model, instructions: str, prompt_template: str):
    """Pass all materials at once and answer without retrieval tools."""
    prompt = prompt_template.format(materials=get_all_materials(), question=question)
    print(f"[full-context] Input: {len(prompt):,} characters")
    try:
        with agent.override(tools=[], instructions=instructions):
            return agent.run_sync(prompt, model=model)
    except ModelHTTPError as e:
        print(f"[full-context] API error HTTP {e.status_code}: {e.body}")
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search the lecture materials without using an agent")
    parser.add_argument("query", help="What to look up")
    args = parser.parse_args()
    for i, result in enumerate(search_with_adjacent(args.query), 1):
        print(f"\n{'=' * 60}\nSearch result {i}\n{'=' * 60}")
        print(f"Lecture: {result['document_title']}")
        print(f"Section: {result['section']}")
        print(f"Title: {result['title']}")
        print(f"Page: {result.get('citation') or result['page']}")
        if result.get("added_as"):
            print(f"Added: {result['added_as']}")
        print(f"\n{result['content']}")
