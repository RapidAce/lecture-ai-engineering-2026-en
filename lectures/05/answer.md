# Lecture 05 Answers

All numbers below come from one run of `scripts/run_lec05.sh`, saved in full in `lectures/05/runs.txt` (13 runs, in the order listed there). Each method and setting was run once.

## Exercises

- Answering model (`[model]` shown during execution): gemini-3.5-flash-lite
- Comparison question: "In Lecture 2, what does LoRA freeze and what does it train? What does QLoRA add?" Expected evidence: Lecture 2 p.52 (LoRA freezes the original weights W and trains only the small matrices A and B; QLoRA also compresses the original weights to 4 bits, about one quarter of the memory).
- Target materials (also record the difference in scope between full context and the other methods): vector search, Tree and Graph search the main materials for Lectures 01–03 (`RAG_DOCUMENT_IDS`). Full context sends everything in `lectures.json`, which is 9 documents (369,490 characters), including the Lecture 05 materials and the exercise documents. So full context had a much wider scope than the other three methods.

### Results by Method

| Method | Key points and correctness of the answer | Cited pages and evidence | Time (seconds) | Input/output tokens | Model responses | Estimated generation API cost (USD) |
|---|---|---|---|---|---|---|
| Full context | Correct: frozen original weights, small added matrices (less than 1% of parameters), 4-bit compression to about one quarter. It also says the adapters stay unquantized, which I could not find on p.52 | Lecture 2 p.51, p.52 (translated p.75), translated p.81 | 3.09 | 95,823 / 276 | 1 | $0.029437 |
| Vector search | Correct: freezes W, trains the product of two thin matrices A and B, QLoRA adds 4-bit compression | Lecture 2 pp.51–52 | 3.51 | 2,756 / 146 | 2 | $0.001192 |
| Tree | Correct and the most detailed: frozen W, A and B less than 1% of parameters, 4-bit compression to about one quarter | Lecture 2 p.52 | 9.41 | 9,437 / 290 | 5 | $0.003556 |
| Graph | Correct, but it cited the internal ID `lec02-main-p052` instead of the citation label | Lecture 2 p.52 | 3.62 | 5,193 / 147 | 2 | $0.001925 |

- Pages found by running search alone, and what their text confirmed: `uv run python -m app.retrieval "LoRA QLoRA difference"` returned Lecture 2 p.52, p.51, p.60, translated p.79 and p.61. The text of p.52 confirms every part of the expected answer: "Freeze the original weights and train only a small change, or delta, with LoRA. QLoRA also compresses the original weights to 4 bits", the trainable part "can be less than 1% of the total", and 4 bits reduces memory "to about one quarter". p.51 says the same in a comparison of Full Fine-Tuning, LoRA and QLoRA. p.60, p.61 and p.79 are about the exercise and about RAG versus FT, so they are related but do not answer the question.
- Tool calls shown by `--trace` (names, arguments, counts, table-of-contents paths followed by Tree, etc.):
  - Vector search: 1 call, `search_materials({'query': 'LoRA freeze train QLoRA'})`, 5 pages returned (p.52, p.51, p.60, translated p.79, p.61).
  - Tree: 4 calls to `browse_tree`, following the path course materials → Fundamentals of Foundation Models (`lec02-main`) → "When and how to adapt the selected model" (`lec02-main-s045`) → p.52 (`lec02-main-p052`, 1,238 characters of full text). It picked the right section from the headings and the right page from the first sentences. 5 model responses, so it was the slowest (9.41 s).
  - Graph: 1 call, `search_graph({'query': 'LoRA freeze train QLoRA add Lecture 2'})`, 10 pages returned: 3 seeds (p.52, p.51, p.60) and 7 expanded pages (p.53, p.50, p.59 and p.61 at 1 hop, translated p.81, p.62 and translated p.79 at 2 hops).
  - Full context: no tools, 1 model response with the whole corpus in the prompt.
- Examples where retrieved information was insufficient, or was retrieved but not used in the answer:
  - Graph retrieved 10 pages but the answer used only p.52. Expanded pages like p.62 ("Next: AI agents") had nothing to do with the question and only added input tokens.
  - Vector search also returned p.60, p.61 and translated p.79, which were not used.
  - On the multi-page memory question (EX5), plain vector search retrieved all the evidence pages (Lecture 3 p.13, p.39, p.40, plus p.38 and p.65), but the answer mostly asked me guiding questions instead of answering, because of the instruction to give hints. So the evidence was there but only partly used.
  - On the question that is not in the materials (EX6, "What are our RAG system's measured average response time and accuracy?"), the agent correctly said the materials contain no such numbers. It mentioned the Lecture 2 p.13 example (asking "What is RAG?" five times) and clearly labeled it as an illustration, not a measurement.
- Method you would adopt for this use case, your reasons, and limitations of the comparison conditions: for a course question bot, I would use vector search as the default. It was correct, cited the right pages, and cost $0.001192, about 25 times less than full context ($0.029437) and 3 times less than Tree, at about the same speed. Tree is attractive when citations must point to one exact page, because it read only p.52, but it needed 5 model responses. Full context is the simplest to build, but it sends about 96,000 tokens for every question, and it covered 9 documents instead of 3, so its result is not a strict comparison. Limitations: one question, one run per method, and full context had a different scope, so these numbers show the size of the differences, not a ranking.
- Observations and questions:
  - Environment: my Codespace was running Python 3.14, whose `sqlite3` module cannot load extensions (`enable_load_extension` is missing). One course test failed and vector search would not have worked at all. The course pins Python 3.12, so I rebuilt the environment with `uv sync --frozen --managed-python --python 3.12`, checked that `enable_load_extension` exists, and then all tests passed.
  - The original `--trace` cut tool results off after 120 characters, so I could not see which pages search returned. I changed `print_trace` in `app/agent.py` to list every returned page with its citation label, and for Graph whether it was a seed or an expanded page with its hop count. Everything above about retrieved pages comes from that output.
  - Question: Graph cited `lec02-main-p052` instead of the citation label even though the instructions ask for the label. Is it better to fix this in the instructions, or to remove the internal ID from what the tool returns?

## Homework

- Level attempted: all three (Basic, Implementation, Advanced). The three changes are switched on only by environment variables (`AIE_RAG_TOP_K`, `AIE_RAG_ADJACENT`, `AIE_GRAPH_RERANK_KEEP`), so the default behavior is unchanged and before/after runs use the same code. I added 3 offline tests in `tests/test_lec05_homework.py`, and `uv run pytest -q` shows 24 passed.
- Comparison question and conditions held fixed (model, target materials, etc.): the main comparison question is the multi-page one from the exercise slides, "What is the difference between compaction and cross-session memory? Do all daily notes become long-term memory?" (expected evidence: Lecture 3 p.13, p.39, p.40). I also reused the LoRA question above. Fixed: model gemini-3.5-flash-lite, the Lecture 01–03 materials and the provided search database, the same question text, one run each.

### Basic: change the result count (RAG_TOP_K 5 → 2)

- **What I did:** `RAG_TOP_K` in `app/config.py` now reads `AIE_RAG_TOP_K` (default 5). I asked the memory question with the default 5 and with `AIE_RAG_TOP_K=2`.

| | top-k 5 | top-k 2 |
|---|---|---|
| Tool calls | 1 search: "compaction cross-session memory daily notes long-term memory" | 2 searches: the same query, then "daily notes long-term memory memory tool" |
| Pages returned | p.65, p.38, p.39, p.40, p.13 | first p.65, p.38; then p.40, p.65 again |
| Evidence pages reached (p.13, p.39, p.40) | all 3 | only p.40 |
| Pages cited | p.39, p.40, p.65 | p.38, p.40, p.65 |
| Time | 6.32 s | 5.70 s |
| Input / output tokens | 2,287 / 256 | 3,172 / 290 |
| Model responses | 2 | 3 |
| Estimated cost | $0.001326 | $0.001677 |

- **Observations:** fewer results did not make the run cheaper. With only 2 pages per search, the model searched a second time (the instructions say to "make separate searches as needed"), so it used 3 model responses and 39% more input tokens. The evidence also got narrower: it never saw p.39 (the Claude example) or p.13, so it explained compaction only from the short supplement on p.65. The answer was still roughly right, and it was a bit more direct than the top-k 5 answer, but that could be normal variation between runs. Lowering top-k traded one bigger search for two smaller ones and lost evidence.

### Implementation: add the adjacent pages to search results

- **What I built:** `add_adjacent_pages()` in `app/retrieval.py`. After each search hit it adds the text of the page before and after it (`AIE_RAG_ADJACENT=1`), only from the same document, never repeating a page that is already in the results, and it marks each added page with `added_as: "adjacent page of <hit>"` so the trace shows where it came from. `search_materials` and `python -m app.retrieval` use it, and Graph does not, so Graph's seeds are unchanged.

| | LoRA question, normal | LoRA question, + adjacent | Memory question, normal | Memory question, + adjacent |
|---|---|---|---|---|
| Pages returned | 5 | 11 (6 added) | 5 | 11 (6 added) |
| Added pages | none | p.53, p.50, p.46, translated p.80, p.59, p.62 | none | p.64, p.66, p.37, p.41, p.12, p.14 |
| Pages cited | pp.51–52 | p.51, p.52 | p.39, p.40, p.65 | p.13, p.39, p.40, p.65 |
| Time | 3.51 s | 4.30 s | 6.32 s | 4.40 s |
| Input / output tokens | 2,756 / 146 | 4,792 / 193 | 2,287 / 256 | 4,182 / 374 |
| Estimated cost | $0.001192 | $0.001920 | $0.001326 | $0.002190 |

- **Improvements:** on the memory question, the run with adjacent pages gave the best answer of all my runs. It answered both parts directly and cited all three evidence pages (p.13, p.39, p.40). But none of the 6 added pages was cited or needed. The evidence pages were already in the normal top 5, so I cannot credit the improvement to the adjacent pages. It looks more like the normal variation in how much the model answers versus only giving hints.
- **Remaining failures and limitations:** in both questions, every added page was noise: the previous section's overview pages, the "Next lecture" page, or unrelated supplements. Input tokens went up by 74% to 83%, and cost by 61% to 65%. Adjacent pages would help when an explanation continues onto the next slide, but on these two questions vector search had already found every evidence page. Page numbers are adjacent, but slides next to each other are not always about the same thing, especially at section boundaries.

### Advanced: re-rank Graph candidates by closeness to the question

- **Data structure:** `data/rag_data/graph.json` has page nodes and term nodes, with two kinds of edges: `next_page` (page to the following page) and `mentions` (term to every page that uses it). `search_graph` takes the top 3 vector-search pages as seeds, walks up to 2 hops (page → page, or page → term → page), and returns at most 10 pages.
- **The problem I targeted:** the original code orders the extra candidates only by graph position: fewer hops first, then rarer terms, then seed rank. Then it cuts the list at 10. So pages that are near the seeds but unrelated to the question fill the slots. In the memory question, 5 of the 7 expanded pages were supplements or the decision-models slide (p.64, p.66, p.63, p.67, p.36), and p.13, one of the expected evidence pages, did not make the cut.
- **What I built:** with `AIE_GRAPH_RERANK_KEEP=4`, `search_graph` collects every candidate the walk finds (before the cut), measures each one's cosine distance to the question with `rerank_by_distance()`, and keeps the 4 closest. Seeds stay as they are. The question is embedded only once and reused, and the page embeddings come from the existing search database, so re-ranking adds one local database query and no API call.
- **Why:** the graph is good at finding candidates the plain search might miss (recall), and the embedding distance is good at saying which candidates are about the question (precision). Using the graph to collect and the distance to choose should keep the useful pages and drop the noise.

| | Vector search (Basic RAG) | Graph, normal | Graph, re-ranked (keep 4) |
|---|---|---|---|
| Memory question: pages returned | 5 | 10 (3 seeds + 7 expanded) | 7 (3 seeds + 4 expanded) |
| Expanded pages | none | p.64, p.66, p.37, p.40, p.63, p.67, p.36 | p.40, p.13, p.41, p.37 |
| Expected evidence reached (p.13, p.39, p.40) | all 3 | p.39, p.40 | all 3 |
| Pages cited | p.39, p.40, p.65 | p.38, p.39, p.40, p.65 | p.13, p.39, p.40, p.65 |
| Time | 6.32 s | 7.20 s | 8.43 s |
| Input / output tokens | 2,287 / 256 | 4,939 / 339 | 3,136 / 286 |
| Estimated cost | $0.001326 | $0.001782 | $0.001656 |
| LoRA question: input tokens / cost | 2,756 / $0.001192 | 5,193 / $0.001925 | 4,059 / $0.001605 |

- **Improved example:** on the memory question, re-ranking pulled p.13 ("Memory") into the results. The normal Graph had cut it off, and the answer then cited all three expected evidence pages. The 5 unrelated supplement pages were gone, and input tokens fell by 37% (4,939 to 3,136). On the LoRA question, input fell by 22%, and the answer was still correct.
- **Failed and open examples:**
  - On the LoRA question, the re-ranked run gave a correct answer but no citations at all, even though the instructions require them. Fewer pages did not fix the citation behavior, and the normal Graph run had cited an internal ID instead.
  - Re-ranking still kept some weak pages, such as p.41 (Skills) and p.37 (the Part 6 title slide) on the memory question, because "close in embedding space" is not the same as "contains the answer".
  - The re-ranked runs were slower in my single runs (8.43 s against 7.20 s, and 6.85 s against 3.62 s). Re-ranking itself is one local query, so I think this is API timing variation, but I did not measure it separately.
- **Compared with Basic RAG on the same questions:** plain vector search found all three evidence pages for the memory question and was still the cheapest (2,287 input tokens). Re-ranked Graph matched its evidence and beat normal Graph on noise and cost, but did not beat vector search on this corpus.
- **Would I adopt it?** I would make re-ranking the default inside Graph mode, because it is cheaper than normal Graph and recovered a missing evidence page at no extra API cost. For this small course corpus I would still use plain vector search as the main method, and keep Graph for questions where the evidence is spread across lectures and the first search misses it. The main limitation is the sample: two questions, one run each.

- **Observations and questions:**
  - One theme across all three levels: retrieving more is not the same as answering better. Adjacent pages and normal Graph added pages that were never used, and lowering top-k made the model search again. The useful changes were the ones that chose better pages, not more pages.
  - The model's tendency to only give hints (from the "guide learners with hints" instruction) changed how complete the answers were more than any retrieval change did. That makes it hard to compare answers, so for retrieval experiments I would look at which pages were returned and cited, not only at the answer text.
  - Question: would a hybrid of keyword and vector search help questions like the memory one, where the exact words ("compaction", "daily notes") appear on the evidence pages?

## Model used and honesty note
gemini-3.5-flash-lite through the Gemini API in GitHub Codespaces (Python 3.12, pinned dependencies). I used Claude to help plan the steps, write the code changes (top-k override, adjacent pages, Graph re-ranking, the trace change and the run script), test them offline, and draft this write-up. I applied the changes, fixed my environment, ran `scripts/run_lec05.sh` myself, and checked the numbers and pages above against `lectures/05/runs.txt`.
