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

**Level: Basic.** I changed only `num_train_epochs`, from 20 to 5, and kept lr, lora_r, lora_alpha, seed and warmup_steps the same. I restarted the Colab session before each new run.

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

## Model used and honesty note
Qwen/Qwen3.5-0.8B with LoRA in Colab. I used Claude to help plan the steps and draft this write-up. I ran the notebook three times myself (20 epochs, 5 epochs, and 20 epochs again), downloaded the result files, and checked every number above against those JSON files and the training logs.