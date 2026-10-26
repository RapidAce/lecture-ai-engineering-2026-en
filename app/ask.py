"""Lecture 01: a script that asks a bare LLM a question.

Usage:
    uv run python -m app.ask "What is LoRA?"
    uv run python -m app.ask            # Ask a course-specific question if none is supplied
    uv run python -m app.ask --chat     # Follow-up questions with conversation history

Token counts are printed to stderr after each answer.
"""

import argparse
import sys

from google import genai
from google.genai import errors

from app.config import MODEL, api_error_message, get_api_key

# A course-specific question. The correct answer is in homework-levels in data/glossary.json
DEFAULT_QUESTION = "What are the 3 homework levels in the AIE2026 course?"


def print_usage(response) -> None:
    """Show input/output token counts from response.usage_metadata."""
    usage = response.usage_metadata
    if usage is None:
        return
    print(
        f"[tokens] input={usage.prompt_token_count} "
        f"output={usage.candidates_token_count} total={usage.total_token_count}",
        file=sys.stderr,
    )


def ask(question: str) -> str:
    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(model=MODEL, contents=question)
    print_usage(response)
    return response.text


def chat_loop() -> None:
    """Interactive chat that keeps the conversation history between turns."""
    client = genai.Client(api_key=get_api_key())
    session = client.chats.create(model=MODEL)  # the session stores the history
    print("Chat mode (type 'exit' to quit)")
    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question in ("exit", "quit"):
            break
        if not question:
            continue
        response = session.send_message(question)
        print(f"model> {response.text}")
        print_usage(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a bare LLM a question")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--chat", action="store_true", help="follow-up questions with history")
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    try:
        if args.chat:
            chat_loop()
        else:
            print(f"[question] {args.question}\n")
            print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()