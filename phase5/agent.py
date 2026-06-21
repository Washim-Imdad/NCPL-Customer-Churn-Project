"""Gemini-powered synthesis over verified data — no hallucinated statistics."""

from __future__ import annotations

import os

import pandas as pd

from analytics_tools import DataContext, answer_question, get_verified_facts

SYNTHESIZE_SYSTEM = """You are a telecom churn analyst for NCPL.
You receive VERIFIED FACTS computed from customer data and Phase 2 SQL analytics.
Write a clear, professional answer to the user's question.

Rules:
- Use ONLY numbers and facts from the VERIFIED FACTS section
- Do NOT invent, round differently, or add statistics not in the facts
- If facts mention tenure months, do not imply calendar months
- Use bullet points for lists of segments or reasons
- Keep answers concise (under 250 words unless listing many rows)"""


def _gemini_api_key() -> str | None:
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


def _get_gemini_model():
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        temperature=0,
        google_api_key=_gemini_api_key(),
    )


def get_agent_mode() -> str:
    if _gemini_api_key():
        return "gemini"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "data-only"


def _synthesize_with_gemini(question: str, facts: str) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    model = _get_gemini_model()
    response = model.invoke([
        SystemMessage(content=SYNTHESIZE_SYSTEM),
        HumanMessage(content=f"QUESTION:\n{question}\n\nVERIFIED FACTS:\n{facts}"),
    ])
    return response.content


def _synthesize_with_openai(question: str, facts: str) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    response = model.invoke([
        SystemMessage(content=SYNTHESIZE_SYSTEM),
        HumanMessage(content=f"QUESTION:\n{question}\n\nVERIFIED FACTS:\n{facts}"),
    ])
    return response.content


def generate_answer(question: str, ctx: DataContext) -> tuple[str, str, pd.Series | None]:
    """Always compute data first; optionally polish with Gemini."""
    analytical_text, chart = answer_question(question, ctx)
    facts = get_verified_facts(question, ctx)
    mode = get_agent_mode()

    if mode == "gemini":
        try:
            answer = _synthesize_with_gemini(question, facts)
            return answer, "Gemini + verified data", chart
        except Exception as exc:
            return (
                analytical_text,
                f"Verified data (Gemini error: {exc})",
                chart,
            )

    if mode == "openai":
        try:
            answer = _synthesize_with_openai(question, facts)
            return answer, "OpenAI + verified data", chart
        except Exception as exc:
            return analytical_text, f"Verified data (OpenAI error: {exc})", chart

    return analytical_text, "Verified data engine", chart
