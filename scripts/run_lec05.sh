#!/usr/bin/env bash
# Lecture 05 exercise + homework: run every comparison once and save all output to lectures/05/runs.txt
# Usage (from the repo root):  bash scripts/run_lec05.sh
export PYDANTIC_AI_NO_BANNER=1
OUT=lectures/05/runs.txt
Q1="In Lecture 2, what does LoRA freeze and what does it train? What does QLoRA add?"
Q2="What is the difference between compaction and cross-session memory? Do all daily notes become long-term memory?"
Q3="What are our RAG system's measured average response time and accuracy?"
: > "$OUT"

run() {  # run LABEL ENV_SETTINGS COMMAND...
  local label="$1" envs="$2"; shift 2
  for attempt in 1 2 3; do
    echo "===== $label (attempt $attempt) =====" | tee -a "$OUT"
    output=$(env $envs "$@" 2>&1)
    echo "$output" | tee -a "$OUT"
    if echo "$output" | grep -q -E "Rate limit|429|503|UNAVAILABLE|high demand"; then
      echo "[runner] API limit or overload, waiting 60s and retrying" | tee -a "$OUT"; sleep 60
    else
      break
    fi
  done
  echo | tee -a "$OUT"
  sleep 15
}

# Exercise (default settings)
run "EX0 retrieval only: LoRA QLoRA difference" "" uv run python -m app.retrieval "LoRA QLoRA difference"
run "EX1 full context | Q1" "" uv run python -m app.agent --full-context --trace "$Q1"
run "EX2 vector search | Q1" "" uv run python -m app.agent --trace "$Q1"
run "EX3 tree | Q1" "" uv run python -m app.agent --tree --trace "$Q1"
run "EX4 graph | Q1" "" uv run python -m app.agent --graph --trace "$Q1"
run "EX5 vector search | Q2 multi-page (baseline, top-k 5)" "" uv run python -m app.agent --trace "$Q2"
run "EX6 vector search | Q3 not in materials" "" uv run python -m app.agent --trace "$Q3"
# Basic: change one thing (RAG_TOP_K 5 -> 2)
run "BASIC vector search | Q2 | RAG_TOP_K=2" "AIE_RAG_TOP_K=2" uv run python -m app.agent --trace "$Q2"
# Implementation: add 1 adjacent page before/after each hit
run "IMPL vector search | Q1 | adjacent=1" "AIE_RAG_ADJACENT=1" uv run python -m app.agent --trace "$Q1"
run "IMPL vector search | Q2 | adjacent=1" "AIE_RAG_ADJACENT=1" uv run python -m app.agent --trace "$Q2"
# Advanced: graph candidates re-ranked by closeness to the question
run "ADV graph | Q2 (baseline)" "" uv run python -m app.agent --graph --trace "$Q2"
run "ADV graph | Q2 | re-rank keep 4" "AIE_GRAPH_RERANK_KEEP=4" uv run python -m app.agent --graph --trace "$Q2"
run "ADV graph | Q1 | re-rank keep 4" "AIE_GRAPH_RERANK_KEEP=4" uv run python -m app.agent --graph --trace "$Q1"
echo "Done. Output saved to $OUT"
