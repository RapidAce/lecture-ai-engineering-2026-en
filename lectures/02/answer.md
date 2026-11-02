# Lecture 02 Exercise and Homework

## Exercise: LoRA format tuning

**Model and settings.** Qwen/Qwen3.5-0.8B, LoRA without quantization, trained in Google Colab on a T4 GPU. Settings: lr 0.0002, lora_r 16, lora_alpha 32, seed 42, warmup_steps 6, 20 epochs (40 steps), max_seq_len 512, max_new_tokens 96, greedy generation (do_sample false). Trainable parameters: 6,389,760 of 758,782,784 (0.84%). Libraries as pinned in the notebook: transformers 5.18.0, peft 0.21.1, trl 1.14.2, torch 2.11.0+cu130.

**executed_training_myself:** True. I ran the notebook myself in Colab and saved result.json, eval_before.json and eval_after.json for every run.

**Results (21 test questions: 15 grounded, 6 ungrounded)**

| | Before training | After training (20 epochs) |
|---|---|---|
| format_rate | 0.952 (20 of 21) | 1.000 (21 of 21) |
| content_rate | 0.381 (8 of 21) | 0.905 (19 of 21) |

**Regressed questions.** None. The regressed list in result.json is empty.

**Remaining failures (first 20 epoch run).** 2 of 21, both grounded questions. The model answered "This FAQ does not contain that information. Confirmation from the course organizers is needed." with needs_review true, although the FAQ contains the answer:
- "Can I submit a format other than PDF?"
- "Tell me how submissions after the deadline are handled"

The type is over-abstention (needs_review true when it should be false). No format errors remain.

**Knowledge questions, before to after.**

| Question | In FAQ | Before | After |
|---|---|---|---|
| When is the final assignment deadline for this course? | no | asserted | asserted |
| What is the instructor's name? | no | needs_review | needs_review |
| What is the topic of the next lecture? | no | needs_review | needs_review |
| When is the assignment deadline? | yes | asserted | asserted |

The first row is a failure that training did not fix. The FAQ gives the assignment deadline (September 30 at 23:59 Japan time), not a final assignment deadline, but the model answers with that date before and after training.

**What training changed.**
- Before training, one answer had a format error: for "Where should I submit my work?" the model pasted five FAQ sentences and left out the needs_review key. Seven grounded questions were wrongly sent to review, and five ungrounded questions got a confident "No", "Yes" or a guess with needs_review false.
- After training, all 21 outputs have the right format, and 13 of the 15 grounded questions are correct. In the first run all 6 ungrounded questions were flagged for review, each with the same sentence. Answers also became full sentences instead of one-word answers.

**What training did not change.**
- It did not add knowledge. The model still asserts a date for the final assignment deadline, which the FAQ does not contain.
- It over-abstains on some grounded questions.
- The ungrounded questions get one identical sentence. The final training loss was 0.0146 on only 14 training examples, so I think the model learned that exact phrase. I did not test other wording, so I cannot say whether it understood when to abstain.

**Same settings, different mistakes.** I ran the 20 epoch configuration a second time to record the loss and training time. The rates were identical (format 1.000, content 0.905, no regressions), but one failure changed. "Tell me how submissions after the deadline are handled" was now correct, and "Do office hours require an appointment?" was now wrong: the model answered with the office hours instead of flagging it for review. The seed was 42 and generation was greedy, so I expected identical answers. My guess is non-deterministic GPU operations during training, but I did not check that. The lesson for me is that the rate was stable while the individual answers were not, so I would not trust a single run to say which questions a model gets right.

## Homework
I did all three levels.

### Basic

I changed only `num_train_epochs`, from 20 to 5, and kept lr, lora_r, lora_alpha, seed and warmup_steps the same. I restarted the Colab session before each new run.

| | 20 epochs (original) | 5 epochs |
|---|---|---|
| steps | 40 | 10 |
| format_rate before to after | 0.952 to 1.000 | 0.952 to 1.000 |
| content_rate before to after | 0.381 to 0.905 | 0.381 to 0.714 |
| final training loss | 0.0146 | 1.7100 |
| training time | 207 seconds | 52 seconds |
| regressed questions | none | When will grades be released? |
| remaining failures | 2 | 6, all ungrounded questions |

The rates for 20 epochs come from my first run, and the loss and time come from my second run with the same settings, because I did not save the training log the first time. Both runs gave the same rates. The "before" numbers were identical in all three runs, so the baseline is reproducible. The eval time for the same "before" test varied (82.0, 56.5 and 64.6 seconds), so I do not compare eval times.

**What 5 epochs did differently.**
- The format was learned just as well (1.000), and all 15 grounded questions were answered correctly.
- It did not learn to abstain. Of the 6 ungrounded questions, 5 got a confident answer with needs_review false: an invented grades date ("the last day of the semester, September 30 at 23:59"), "No, lecture recordings are not made available", "Yes, feedback is provided during office hours", "Please follow APA or your institution's preferred style", and "No" for office-hour appointments.
- The sixth ("Is there a character count limit?") was flagged needs_review true, but the content check still marked it wrong. I did not read how the check works, so I count it as a failure as scored.
- "When will grades be released?" got worse. Before training the model flagged it for review, and after 5 epochs it invented a date.

**Why I think this happened.** The loss log explains most of it. In the 20 epoch run the loss was 1.689 at step 10, then fell to 0.062 at step 20 and 0.0146 at step 40. The 5 epoch run ended at step 10 with a loss of 1.710, about where the longer run was before its loss dropped. So the short run stopped before the model had really learned the training answers. It picked up the output format early but not the refusal behavior. Also, warmup_steps stayed at 6, so 6 of the 10 steps in the short run were warmup. I did not test how much that matters, and I ran only one seed per setting, so I would not claim that 20 epochs is always better.

**Extra observation: 4-bit loading.** The notebook also loads the base model in 4-bit. Weight memory dropped from 3.01 GB to 0.76 GB, but before any training the 4-bit model's content_rate was 0.048 (1 of 21) against 0.381 for the full model, even though its format_rate was 1.000. For this small model, quantization cost a lot of answer quality.



### Implementation: my own topic (gas plant site safety FAQ)

**What I changed.** I replaced `FAQ`, `GROUNDED`, `UNGROUNDED` and the test-only questions with a fictional gas plant site safety FAQ of 5 items: PPE, hot work permits, the muster point, the visitor induction, and mobile phones. I kept the JSON format, the `needs_review` design, the same split (train 14, valid 7, test 21 with 15 grounded and 6 ungrounded) and the original CONFIG (20 epochs). I changed the system prompt from "course FAQ" to "site safety FAQ", changed the abstain answer to "Confirmation from the site HSE office is needed.", and replaced the knowledge questions with site questions. I picked this topic because it is close to my own work in oil and gas, where a confident wrong answer about a safety rule matters much more than in a course FAQ.

**How I prepared the questions without evidence.** I wrote 12 questions a real visitor to a gas plant might ask that none of the 5 FAQ items answers. On purpose, about half are near misses that share words with an FAQ item, to test whether the model reuses the closest item instead of asking for confirmation: "Do I need a permit for working at height?" (the FAQ only covers hot work permits), "Do I need a respirator in the process area?" (the FAQ lists other PPE), "Are visitors allowed to drive inside the fence?" (the FAQ's fence rule is about phones), and "Can I bring a laptop into the plant?" (phones again). The others are plain gaps such as the speed limit or the first aid room. As in the original notebook, 4 of them went to training, 2 to validation and 6 to the test set.

| | Before | After (20 epochs) |
|---|---|---|
| format_rate | 1.000 | 1.000 |
| content_rate | 0.238 (5 of 21) | 0.905 (19 of 21) |
| regressed questions | | none |
| final training loss | | 0.0142 (2.056 at step 10) |
| training time | | 199 seconds |

**Before training.** Unlike the course FAQ, the format was already perfect, but the content was weak. The model gave short answers like "Yes", "No" or "30 minutes" without the FAQ wording, sent several grounded questions to review, and answered near misses with false confidence: "Do I need a permit for working at height?" got "No", and "Where is the nearest fire extinguisher?" got "Muster Point B".

**After training.** All 15 grounded questions were correct, each answered with the exact FAQ sentence. 4 of the 6 ungrounded questions were flagged for review, including the near miss about working at height. The 2 failures were both near misses, and both were the "applying a different FAQ item" type:
- "Are visitors allowed to drive inside the fence?" got the mobile phone rule (shared words: inside the fence).
- "Do I need a respirator in the process area?" got the PPE rule (shared words: process area). A worker could read that as "no respirator needed", which is exactly the kind of answer that would be dangerous on a real site.

**Knowledge questions.** The three questions absent from the FAQ (crane wind speed limit, fire wardens per shift, daily gas production) were already flagged for review before training, and stayed flagged after. Only the wording changed, to the trained sentence. The control question about the muster point was answered correctly before and after.

**Compared with the course FAQ.** The after score was the same (0.905), but the failures were the opposite type. On the course FAQ the model over-abstained on grounded questions. On my topic it asserted answers to ungrounded near misses by matching surface words to the closest FAQ item. So the ungrounded questions you choose decide which failures you can see, and a test set without near misses would make the model look safer than it is.

**4-bit observation.** Loading the base model in 4-bit dropped content_rate before training from 0.238 to 0.000, with format still at 1.000.

### Advanced: training on the course glossary instead of the FAQ

**What I did.** I ran `uv run python scripts/make_sft_dataset.py > glossary_sft.jsonl` in Codespaces (116 records: 58 glossary terms, each asked as "What is X?" and "Briefly explain X."), uploaded the file to Colab, and passed the records directly to `Dataset.from_list`. I trained with the same LoRA settings as section 4 (r 16, alpha 32, lr 0.0002, seed 42) for 4 epochs, which is 60 steps, starting from a fresh copy of the base model in the same session. I did not use the FAQ system prompt, because the glossary data is plain question and answer.

**My evaluation set (17 questions).**
- 6 questions with the exact training wording ("What is Pi?", "What is Default model?", "What is LoRA?" and so on), checked for keywords from the definition, such as "gemini-3.5-flash-lite" or "Basic / Implementation / Advanced".
- 6 paraphrased questions about glossary content in new wording, for example "Which model is the standard model for the AIE2026 exercises?" and "What is the npm package name of the Pi coding agent?".
- 5 questions about things that are not glossary terms: RAG, DPO, a vector database, "the Lecture 04 homework", and "the npm package name of the glossary search agent". The ideal answer is to say it does not know. I chose the last two because they sound like course facts and could tempt the model to invent one.

The keyword check is case-insensitive. For the absent terms I used a small list of hedge phrases ("not sure", "don't know" and similar) and then read every answer myself.

| | Before | After (4 epochs, 60 steps) |
|---|---|---|
| exact training wording, keywords correct | 1 of 6 | 1 of 6 |
| paraphrased questions, keywords correct | 1 of 6 | 0 of 6 |
| absent terms, flagged by my hedge list | 0 of 5 | 0 of 5 |
| training loss | 2.887 at step 10 | 0.471 at step 60 |
| mean token accuracy | 0.48 at step 10 | 0.89 at step 60 |

**Before training.** The base model answered from general knowledge. "What is Pi?" got the mathematical constant, "lecNN-start tag" got an invented protein, and the paraphrased course questions got confident inventions ("Aerospace Industry Engineering 2026", "10 homework levels", an npm package called "pi-code", GOOGLE_API_KEY). Only "What is LoRA?" was right, from pretraining. One paraphrase passed the keyword check while being wrong: it described Low-Rank Adaptation as reducing the dimensionality of a dataset. On the other hand, for "What is 3 homework levels?" and "What is the Lecture 04 homework?" it asked me for more context, which is the honest answer. My hedge list missed those two, so the 0 of 5 in the table understates it.

**After training.** Every answer copied the glossary's style ("A ... In this course, ...") but the facts were mostly invented:
- "What is Pi?" became "a programming language designed for educational purposes ... you will use it as a homework helper".
- "Default model" became "Gemini 3.5 Flashlight", and the paraphrase said "Gemini 3.5 Flash". The glossary says gemini-3.5-flash-lite.
- The homework levels became "Basics, Application, Research and analysis", and the paraphrase said "6 homework levels (HW01 to HW06)".
- The Gemini key variable became "gemini-api-key", followed by "In this course, you do not use the Gemini API".
- The only keyword pass, "Codespaces secret", added a false sentence: "the secret is your course ID".
- The absent terms got invented course facts too: "In this course, Lecture 02 exercises use RAG", "we use DPO to teach reading", a Lecture 04 homework about writing a function that returns a square, and a package called "glossary-search-agent". It no longer asked for context on any question.

**What I take from this.** 60 steps on 116 examples taught the model what a glossary answer looks like, but not what the glossary says. The loss was still 0.47, so it had not memorized the definitions, and more epochs might fix the exact training wording. I did not test that, and the paraphrase result suggests memorizing would not carry over to new wording. Worse, training made the model sound like the course while making things up about it, which is harder to spot than the base model's generic mistakes. This matches the lecture's point that fine-tuning is good for format and behavior and bad for adding knowledge, and it matches my FAQ runs, where training fixed the format but not the judgment.

**Training versus a glossary search agent.** For a glossary, search is the better fit. A search agent like the one we build in Lecture 03 returns the actual definition text, so a paraphrase still finds the right entry when the term matches. It can say "not found" for RAG or DPO instead of inventing, it can show the source, and adding a new term means editing a JSON file instead of retraining. Fine-tuning would only make sense on top of search, for example to teach a fixed answer format, which is what the FAQ runs showed it does well.

## Model used and honesty note
Qwen/Qwen3.5-0.8B with LoRA in Colab. I used Claude to help plan the steps, draft the new FAQ data and the glossary evaluation cell, and draft this write-up. I ran every training run myself (20 epochs, 5 epochs, 20 epochs again, my own FAQ, and the glossary), downloaded the result files, and checked the numbers above against those files and the training logs.