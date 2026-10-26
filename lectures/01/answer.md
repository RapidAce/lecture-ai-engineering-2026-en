# Lecture 01 Homework

## Level chosen
All three levels: Basic, Implementation, and Advanced.

## What I did

**Basic.** I ran two questions three times each under three conditions:
- gemini-3.5-flash-lite (default temperature)
- gemini-3.5-flash (default temperature)
- gemini-3.5-flash-lite with temperature 0.0

The questions were a general one ("What is LoRA?") and a course-specific one ("What are the 3 homework levels in the AIE2026 course?"). That makes 18 calls in total. The script is `scripts/bench_lec01.py`, and the raw output is in `lectures/01/bench_results.json` and `lectures/01/bench_log.txt`.

**Implementation.** I changed `app/ask.py` so that `--chat` starts a chat session that keeps the conversation history between turns. I also added the token counts from exercise 6, which print after every answer.

**Advanced.** The same benchmark script recorded response time, input tokens, and output tokens for every call, so I could compare models and questions.

## Results

Mean over 3 runs per row:

| Model | Temperature | Question | Seconds | Input tokens | Output tokens | Distinct answers |
|---|---|---|---|---|---|---|
| flash-lite | default | LoRA | 3.01 | 6 | 717.7 | 3 of 3 |
| flash-lite | default | homework levels | 1.18 | 18 | 132.7 | 3 of 3 |
| flash | default | LoRA | 23.61 | 6 | 854.3 | 3 of 3 |
| flash | default | homework levels | 11.86 | 18 | 346.3 | 3 of 3 |
| flash-lite | 0.0 | LoRA | 2.83 | 6 | 669.0 | 3 of 3 |
| flash-lite | 0.0 | homework levels | 0.88 | 18 | 114.0 | 3 of 3 |

**Differences between models and settings**
- Every run produced a different text, even at temperature 0.0. Lowering the temperature did not make the answers identical in my runs.
- For "What is LoRA?", all runs correctly said LoRA means Low-Rank Adaptation, but the wording and length varied. gemini-3.5-flash gave longer answers (about 854 tokens vs 718) and some of its answers began by saying LoRA could refer to two different technologies.
- gemini-3.5-flash was much slower: 23.6 seconds on average for the LoRA question, against 3.0 seconds for flash-lite. That is roughly 8 times slower. On the homework question it was 11.9 seconds against 1.2 seconds, roughly 10 times slower.

**The course-specific question**
- The models have no access to the course material, so this question tests how they behave when they do not know.
- flash-lite behaved inconsistently. In several runs it said it had no access to specific information about the AIE2026 course, and in other runs it gave a confident answer ("Based on the structure of the AIE2026 course...") that it could not have known.
- flash always gave a confident answer, and the answers I could see described other courses (for example, ones mentioning AI Vietnam and AI Makerspace).
- I also ran a loose keyword check that counts an answer if it contains the words "basic", "implementation", and "advanced". Results were 0 of 3 for flash-lite, 1 of 3 for flash, and 1 of 3 for flash-lite at temperature 0.0. This check only looks for words. It does not prove an answer is correct, so I treat it as a rough indicator only.
- The main lesson is that a bare model sounds equally confident whether it knows the answer or not, and that one run is not enough to judge it, because the same question gave different answers on different runs.

**Conversation history (Implementation)**
I asked "What is LoRA?" and then "What does the first letter of that abbreviation stand for?". The model answered "Low" (from Low-Rank Adaptation) without being told what the abbreviation was, so the history works. The token counts show why: the first turn sent 6 input tokens, and the second turn sent 698, because the earlier question and answer were sent again with the new question. Input tokens therefore grow with every turn of a conversation.

**Rate limits (Advanced)**
- All 18 benchmark calls succeeded, with a 6 second pause between calls. I saw no rate-limit errors and no 503 errors.
- Answers to the LoRA question used about 670 to 850 output tokens, while the course question used 80 to 400. Longer answers and longer conversations use more tokens per request, so they would reach token-based limits sooner than short one-shot questions.
- I did not push the calls fast enough to find the real per-minute or daily limit, so I cannot say exactly where the free-tier limit is. I only know that this load stayed under it.
- Because gemini-3.5-flash took 10 to 35 seconds per call, it makes fewer calls per minute on its own, which makes hitting a per-minute request limit less likely but makes each request much slower.

## Model used
gemini-3.5-flash-lite (the default) and gemini-3.5-flash, through the Gemini API from GitHub Codespaces. I used an AI assistant to help write the benchmark script and the chat mode, then ran everything myself: the tests (11 passed), the benchmark, and the chat test.

## What I verified myself
- Ran `uv run pytest -q` and got 11 passed.
- Ran the benchmark and read the printed results and the saved JSON.
- Tested chat mode by hand and confirmed the follow-up question was answered correctly and that input tokens grew from 6 to 698.
- Confirmed the token counts printed by the script come from the API's usage metadata.