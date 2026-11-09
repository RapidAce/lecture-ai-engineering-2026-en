"""Lecture 03 homework (Advanced a): the same agent rebuilt with Google's ADK.

Reuses INSTRUCTIONS and the tool functions from app/ unchanged; only the agent assembly is new.
Run from the repo root:
    PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent
"""
from google.adk.agents import Agent

from app import tools
from app.agent import INSTRUCTIONS

root_agent = Agent(
    model="gemini-3.5-flash-lite",
    name="glossary_agent",
    instruction=INSTRUCTIONS,
    # Same tools as the exercise agent. save_learning_log is left out: the slides say tools with approval are not needed here
    tools=[tools.search_glossary, tools.get_lecture_summary, tools.make_quiz],
)