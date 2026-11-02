# Lecture 01 Homework

## Level chosen
All three levels: Basic, Implementation, and Advanced.

## What I did

**Basic.** I ran two questions three times each under three conditions:
- gemini-3.5-flash-lite (default temperature)
- gemini-3.5-flash (default temperature)
- gemini-3.5-flash-lite with temperature 0.0

The questions were a general one ("What is LoRA?") and a course-specific one ("What are the 3 homework levels in the AIE2026 course?"). That makes 18 calls in the first run. The script is `scripts/bench_lec01.py`, and the raw output of that run is in `lectures/01/bench_results.json` and `lectures/01/bench_log.txt`.

**Implementation.** I changed `app/ask.py` so that `--chat` starts a chat session that keeps the conversation history between turns. I also added the token counts from exercise 6, which print after every answer.

**Advanced.** The benchmark script recorded response time, input tokens, and output tokens for every call, so I could compare models and questions. After the first run I changed the script so that it also records thinking tokens, API error codes, and the model that actually served each call, and I added gemini-3.8-flash. I ran this second version too. Its log is `lectures/01/bench_log_run2.txt`.

## Results

### Run 1 (18 calls, mean over 3 runs per row)

| Model | Temperature | Question | Seconds | Input tokens | Output tokens | Distinct answers |
|---|---|---|---|---|---|---|
| flash-lite | default | LoRA | 3.01 | 6 | 717.7 | 3 of 3 |
| flash-lite | default | homework levels | 1.18 | 18 | 132.7 | 3 of 3 |
| flash | default | LoRA | 23.61 | 6 | 854.3 | 3 of 3 |
| flash | default | homework levels | 11.86 | 18 | 346.3 | 3 of 3 |
| flash-lite | 0.0 | LoRA | 2.83 | 6 | 669.0 | 3 of 3 |
| flash-lite | 0.0 | homework levels | 0.88 | 18 | 114.0 | 3 of 3 |

### Run 2 (12 of 24 planned calls, mean over 3 runs per row, 0 API errors)

| Model asked for | Served by | Question | Seconds | Input tokens | Output tokens | Thinking tokens |
|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | gemini-3.5-flash-lite | LoRA | 3.42 | 6 | 701.7 | none reported |
| gemini-3.5-flash-lite | gemini-3.5-flash-lite | homework levels | 1.18 | 18 | 207.0 | none reported |
| gemini-3.5-flash | gemini-3.6-flash | LoRA | 10.83 | 6 | 828.7 | 1005.7 |
| gemini-3.5-flash | gemini-3.6-flash | homework levels | 6.86 | 18 | 330.0 | 790.3 |

The rest of run 2 (gemini-3.8-flash and the second temperature 0.0 test) did not finish. I explain why in the rate limits section. The run 2 JSON file was never written because the script only saves it at the end, so the log file is the record for run 2.

**Differences between models and settings**
- Every run produced a different text, even at temperature 0.0 on flash-lite (3 of 3 distinct answers for both questions). The Lecture 2 slides say temperature is deprecated and that Gemini 3.6 and later ignore it, so I cannot say what the setting does for the flash rows. I only tested temperature 0.0 on flash-lite 3.5, and there the answers still differed.
- gemini-3.5-flash is not the model that answers. In run 2 the response metadata said every call was served by gemini-3.6-flash, which matches what the Lecture 2 slides say about forwarding. I did not record this in run 1, so for run 1 I only know what I asked for.
- gemini-3.5-flash was slower than flash-lite in both runs, but by different amounts. On the LoRA question it was about 8 times slower in run 1 (23.61 s against 3.01 s) and about 3 times slower in run 2 (10.83 s against 3.42 s). On the homework question it was about 10 times slower in run 1 and about 6 times slower in run 2. So the gap is between 3 and 10 times, and it changes from run to run. I do not know why run 1 was slower.
- A likely reason it is slower is thinking. In run 2 the flash model reported about 800 to 1000 thinking tokens per call, and flash-lite reported none. These are reported separately from the output tokens, so the answer text alone understates the work the model did. I did not test whether thinking tokens count toward the free-tier limits.

**Answer quality: "What is LoRA?"**
- I read the full text of all 18 run 1 answers. All of them correctly said that LoRA means Low-Rank Adaptation.
- Two of the three gemini-3.5-flash answers began with "Depending on the context" and spent a large part of the answer on LoRa, the Long Range wireless technology, which I did not ask about. The third went straight to Low-Rank Adaptation.
- One flash-lite answer at temperature 0.0 contains a garbled phrase: it says LoRA reduces GPU memory requirements by up to "3 pitiful 3x". The answer was otherwise correct, but this shows that a fluent answer can still contain broken text.

**Answer quality: the course-specific question**
- The models have no access to the course material, so this question tests how they behave when they do not know. The real levels are Basic, Implementation, and Advanced. No model gave them as a real answer.
- flash-lite was inconsistent. Across both runs, 3 of its 6 default-setting answers said it had no access to specific information about the course, and the other 3 gave a confident answer ("Based on the structure of the AIE2026 course...") that it could not have known. At temperature 0.0 in run 1 it refused twice and invented once (a "Bronze / Silver / Gold" structure).
- flash gave a confident answer every time, in all 6 calls across both runs. The answers I read in full (run 1) described other courses and bootcamps, for example ones mentioning AI Vietnam and AI Makerspace. For run 2 I only have the first 70 characters in the log, and they also start with confident descriptions of an "AIE" course, so I count them as confident answers but I did not read them in full.
- My first benchmark script ran a loose keyword check that counts an answer if it contains the words "basic", "implementation", and "advanced". It reported 0 of 3 for flash-lite, 1 of 3 for flash, and 1 of 3 for flash-lite at temperature 0.0. When I read the full answers, the three answers that passed were all about a different course (for example "Foundational, Intermediate (Implementation), Advanced" for flash). So every pass was a false positive, and the keyword check would have made the models look better than they are.
- The main lesson is that a bare model sounds equally confident whether it knows the answer or not, that a keyword check is not a correctness check, and that one run is not enough to judge a model, because the same question gave different answers on different runs.

**Conversation history (Implementation)**
I asked "What is LoRA?" and then "What does the first letter of that abbreviation stand for?". The model answered "Low" (from Low-Rank Adaptation) without being told what the abbreviation was, so the history works. The token counts show why: the first turn sent 6 input tokens, and the second turn sent 698, because the earlier question and answer were sent again with the new question. Input tokens therefore grow with every turn of a conversation.

**Rate limits (Advanced)**
- Run 1: all 18 calls succeeded, with a 6 second pause between calls. I saw no 429 and no 503 errors.
- Run 2: the first 12 calls (flash-lite and flash) succeeded with no errors. The script then moved on to gemini-3.8-flash, and its first call returned nothing for about 13 minutes, with no error code and no answer. I stopped the script with Ctrl+C. The Lecture 2 slides say gemini-3.8-flash is limited to about 5 requests per minute and 10 to 20 per day on the free tier, but I did not confirm that this was the cause, so I do not know why the call hung.
- My script only retries when the API returns an error code, and it sets no timeout. A call that hangs is therefore neither counted as an error nor retried. If I ran this again I would set a request timeout.
- Answers to the LoRA question used about 670 to 850 output tokens, while the course question used 45 to 400. Longer answers, thinking tokens, and longer conversations use more tokens per request, so they would reach token-based limits sooner than short one-shot questions.
- Because gemini-3.5-flash took between 6 and 36 seconds per call, it makes fewer calls per minute on its own, which makes hitting a per-minute request limit less likely but makes each request much slower.
- I did not push the calls fast enough to find the real per-minute or daily limit on the models that answered, so I cannot say exactly where those limits are.

## Model used
gemini-3.5-flash-lite (the default) and gemini-3.5-flash (served as gemini-3.6-flash), through the Gemini API from GitHub Codespaces. I also tried gemini-3.8-flash in run 2, but that call did not return. I used an AI assistant to help write the benchmark script, the chat mode, and this write-up, then ran everything myself: the tests (11 passed), both benchmark runs, and the chat test. I checked the numbers in this file against `bench_results.json` and `bench_log_run2.txt`.

## What I verified myself
- Ran `uv run pytest -q` and got 11 passed.
- Ran the benchmark twice and read the printed results, the saved JSON for run 1, and the log for run 2.
- Read the full text of all 18 run 1 answers, which is how I found the "Depending on the context" answers, the garbled phrase, and the false positives in the keyword check.
- Tested chat mode by hand and confirmed the follow-up question was answered correctly and that input tokens grew from 6 to 698.
- Confirmed the token counts printed by the script come from the API's usage metadata, and that the served model name comes from the response metadata.