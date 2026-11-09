"""Run the ADK glossary agent once and print its tool calls (like app.agent --trace).

    GOOGLE_API_KEY=$GEMINI_API_KEY PYTHONPATH=. uv run --with google-adk python adk_agent/trace_run.py "question"
"""
import asyncio
import sys

from google.adk.runners import InMemoryRunner
from google.genai import types

from adk_agent.glossary_agent.agent import root_agent


async def main(question: str) -> None:
    runner = InMemoryRunner(agent=root_agent, app_name="glossary_trace")
    session = await runner.session_service.create_session(app_name="glossary_trace", user_id="me")
    message = types.Content(role="user", parts=[types.Part(text=question)])
    llm_turns = 0
    async for event in runner.run_async(user_id="me", session_id=session.id, new_message=message):
        calls = event.get_function_calls()
        if calls or event.is_final_response():
            llm_turns += 1  # one model response: either a tool request or the final answer
        for call in calls:
            print(f"[tool call]   {call.name}({call.args})")
        for resp in event.get_function_responses():
            print(f"[tool return] {resp.name} -> {str(resp.response)[:100]}…")
        if event.is_final_response() and event.content and event.content.parts:
            print("\n" + "".join(p.text or "" for p in event.content.parts))
    print(f"\n[model responses] {llm_turns}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))