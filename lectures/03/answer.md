# Lecture 03 Answers

## Exercises

- **Differences between the Lecture 01 (bare LLM) and agent answers:** In my Lecture 01 benchmark, the bare model never gave the real homework levels. gemini-3.5-flash-lite refused in 3 of its 6 default runs and invented an answer in the other 3, and gemini-3.5-flash invented an answer in all 6. The Lecture 03 agent searched the glossary and answered correctly: Basic (review lecture content), Implementation (write your own code), Advanced (research and experimentation), with "any one level completes the homework" and "as a rule, it is not graded", which matches the `homework-levels` entry in `data/glossary.json`. It ended with "Lecture 01" as the instructions require.
- **Tool calls shown by `--trace` (tool names and arguments):** For "What is the difference between LoRA and QLoRA?" the trace showed one call, `search_glossary({'query': 'LoRA'})`, not two as in the slide example. The search also matches partial names, so the query "LoRA" returned the QLoRA entry too, and one call covered both terms. In later runs of the same question the model sometimes made two calls (`'LoRA'` and `'QLoRA'`), so the number of searches varies between runs.
- **Number of LLM calls for one question (`requests`):** 2 (one to decide to search, one to write the answer), with `tool_calls=1` and 897 input tokens.
- **Tool added and the description in its docstring:** `make_quiz(lecture: int)`. Docstring: "Pick one glossary term from the given session (an integer starting at 1) and return a review question and its answer. Use when the learner asks for a review question or a quiz, such as 'Give me a review question for Lecture 2'. The answer is the glossary definition. Show the question first and let the learner try before giving the answer." For "Give me one review question from Lecture 02" the trace showed `make_quiz({'lecture': 2})`, the tool returned the term "Rank (LoRA r)", and the model showed only the question and asked me to try first, as the docstring says (`requests=2`, `tool_calls=1`). For a session with no terms, such as lecture 0, the tool returns a clear message instead of failing. `uv run pytest -q`: 15 passed.

One thing I noticed: in the LoRA and QLoRA answer the model said QLoRA keeps "the overall performance intact". The glossary only says that quantization "may decrease accuracy slightly", and in my own Lecture 02 run, loading the model in 4-bit dropped content_rate from 0.381 to 0.048. So even with search, the model can add a claim that is not in the search result.

## Homework

- **Level attempted:** all three. For Advanced I chose option (a), rebuilding the agent with ADK.

### Basic: changing INSTRUCTIONS and docstrings

I changed one place at a time, ran the same question ("What is the difference between LoRA and QLoRA?") with `--trace`, and reverted with `git checkout` before the next change.

| Run | Change | Tool calls | requests | Input tokens | How the answer ended |
|---|---|---|---|---|---|
| Baseline | none | `search_glossary('LoRA')` | 2 | 897 | hint question, then "Lecture 02" |
| B1 | removed "Always check the glossary with search_glossary..." from INSTRUCTIONS | `search_glossary('LoRA')`, `search_glossary('QLoRA')` | 2 | 1083 | hint question, then "Lecture 02" |
| B2 | docstring: "Put only one term" changed to "Put several terms together in query (for example, "LoRA QLoRA")" | `search_glossary('LoRA QLoRA')` | 2 | 836 | "(Lecture 02)" |
| B3 | INSTRUCTIONS: "End your answer by indicating the relevant session" changed to "End your answer with one short review question" | `search_glossary('LoRA')`, `search_glossary('QLoRA')` | 2 | 1127 | a review question, no session line |

- **B1:** removing the instruction did not stop the search. The docstring of `search_glossary` still says "Use before answering about AI engineering terms", so the guidance to search lives in two places, and removing one was not enough. It searched twice this time, but the baseline searched once, and model output varies between runs, so I do not read anything into one versus two.
- **B2:** the model sent exactly the example from the new docstring, `'LoRA QLoRA'`, as one query. It still worked only because the search removes spaces and finds "lora" and "qlora" inside "loraqlora". Terms that do not happen to appear inside the combined string would be missed, so this change makes the agent more fragile even though this run looked fine. It also had the fewest input tokens (836), and the answer opened with "Based on the course glossary".
- **B3:** the separate "Lecture 02" line disappeared, and the answer ended with a review question instead. The session moved into the first sentence ("both are covered in Lecture 02").
- **A fifth, unplanned result:** while building the Implementation level, one sentence in a docstring stopped a tool from being called at all (details below). That was the clearest example of how much the wording matters.

### Implementation: save_learning_log with approval

- **What I did:** I added `save_learning_log(title, content)` to `app/tools.py`. It writes a Markdown file to `learning_log/` and returns the path. I registered it with `agent.tool_plain(requires_approval=True)(tools.save_learning_log)` and added `DeferredToolRequests` to the agent's `output_type`. In the CLI, when the result is `DeferredToolRequests`, the program prints the pending call with its arguments and asks "Allow this? [y/N]". It then resumes with `run_sync(message_history=result.all_messages(), deferred_tool_results=...)`, passing `True` for yes or `ToolDenied("The user declined to save.")` for no.
- **First attempt, a failure worth recording:** my first docstring ended with "Saving writes a file, so the learner is asked to approve it before it runs." With that sentence the model never called the tool. It wrote the note in the chat and asked "Would you like me to save this learning note for you now?" in plain text, so nothing was saved and the approval step never ran. The model read the sentence as "ask first yourself". I changed the line to "Call it directly when asked: the program itself asks the learner to approve the save, so do not ask for confirmation in your answer."
- **Results after the fix** (question: "Please save a short learning note about the difference between LoRA and QLoRA"):
  - **Answered y:** the trace showed `search_glossary('LoRA')`, `search_glossary('QLoRA')`, then the pause `[approval needed] save_learning_log({'title': 'LoRA vs QLoRA', 'content': ...})`. After I typed y, the tool returned `Saved: learning_log/20261109-035246-lora-vs-qlora.md`, and the file contains the glossary definitions of both terms.
  - **Answered n:** same searches and the same pause. The tool did not run, and the model received "The user declined to save." and told me the save was declined. `ls learning_log` shows only the one file from the y run.
- **Observations:**
  - `requires_approval` only protects a tool the model actually calls. If the docstring makes the model ask in chat instead, the safety step is skipped and the work is silently lost.
  - The saved file has the heading "# LoRA vs QLoRA" twice, because my tool adds the title as a heading and the model also put it at the start of `content`. One more docstring line ("content should not repeat the title") would fix it.
  - The `[usage]` line after approval shows `requests=1`, because my CLI prints the usage of the resumed run only. The whole question really took 3 LLM calls: search, request the save, and the answer after approval.
  - Even this one confirmation shows the cost of human-in-the-loop: the agent stops and waits, and in a non-interactive script it would need another way to get the decision.

### Advanced (a): the same agent rebuilt with ADK

- **What I did:** I created `adk_agent/glossary_agent/agent.py`, which imports `INSTRUCTIONS` from `app/agent.py` and the tools from `app/tools.py` unchanged, plus a one-line `__init__.py`. I did not change any files in `app/` for this part. I left out `save_learning_log`, because the slides say tools with approval are not needed. I ran the two exercise questions with `adk run` (google-adk 2.14). `adk run` and its log file do not show tool calls, so I wrote `adk_agent/trace_run.py`, which runs the same agent through `InMemoryRunner` and prints each function call and response.

**How the code differs**

| | Pydantic AI (app/agent.py) | ADK (adk_agent/glossary_agent/agent.py) |
|---|---|---|
| Instructions | `Agent(instructions=INSTRUCTIONS)` | `Agent(instruction=INSTRUCTIONS)` |
| Tools | `agent.tool_plain(fn)` once per tool | `tools=[fn, fn, fn]` in the constructor |
| Model | passed at run time (`GoogleModel`), name from `AIE_MODEL` | a fixed string in the code, `model="gemini-3.5-flash-lite"` |
| API key | `GEMINI_API_KEY` through `get_api_key()` | reads `GOOGLE_API_KEY` ("Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY."), so I passed `GOOGLE_API_KEY=$GEMINI_API_KEY` |
| How it runs | `run_sync` returns one result | `adk run` finds `root_agent`, creates a session and streams events (async) |
| Seeing tool calls | `--trace` reads `result.all_messages()` | not shown by `adk run`; my `trace_run.py` reads them from the event stream |
| Testing without an API | `TestModel` (the 15 tests use it) | not tried |

**How the answers compare**

- **"What are the 3 homework levels in the AIE2026 course?":** ADK gave the same correct levels with the same notes (any one level is enough, not graded) and ended with "(Lecture 01)".
- **"What is the difference between LoRA and QLoRA?":** ADK made the same two calls, `search_glossary({'query': 'LoRA'})` and `search_glossary({'query': 'QLoRA'})`, in 2 model responses, which matches `requests=2` in Pydantic AI. It gave the same glossary-based explanation and hint question and ended with "(Lecture 02)".
- **One visible difference in the plumbing:** ADK wraps a tool's string return value as `{'result': '...'}` before passing it to the model, while Pydantic AI passes the string as is.

**Observations:** with the same instructions, tools and model, the two frameworks behaved the same on these questions. The behavior comes from INSTRUCTIONS and the docstrings, not from the framework. The differences are in the developer experience. Pydantic AI made the tool calls easier to see (`--trace`) and to test without an API key (TestModel). ADK gave a ready-made CLI and sessions, but I had to write my own script to see the tool calls. I ran each question only once per framework, so I cannot say anything about how often the answers would differ.

### Questions

- When I removed the "always search" instruction, the docstring still made the model search. In a bigger agent with many tools, which should own the rule, the system instructions or each tool's description?
- Is there a standard way to stop a model from "asking for confirmation" in chat when the program is supposed to handle the approval itself?

## Model used and honesty note
gemini-3.5-flash-lite through the Gemini API in GitHub Codespaces, with Pydantic AI and google-adk 2.14. I used Claude to help plan the steps, write the code for make_quiz, save_learning_log, the approval loop, the ADK agent and the trace script, and draft this write-up. I ran every command myself, read the traces, chose the y and n answers, and checked the numbers above against my terminal output.