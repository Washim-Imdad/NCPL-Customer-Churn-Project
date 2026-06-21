"""Phase 5: GenAI Streamlit App — Gemini + verified data engine."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from agent import generate_answer, get_agent_mode
from analytics_tools import build_context, load_merged_data

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

SUGGESTED_QUESTIONS = [
    "What is the overall churn rate?",
    "Why are customers churning?",
    "Which segment has the highest churn?",
    "Who are the top 10 at-risk customers?",
    "What is our ARPU?",
    "What is the churn trend by tenure month?",
    "How does fiber optic compare to DSL for churn?",
    "What is the churn rate by payment method?",
    "How many high-risk customers are still retained?",
]

st.set_page_config(page_title="Telco Churn GenAI Assistant", page_icon="📊", layout="wide")


@st.cache_data
def get_data_context():
    df = load_merged_data()
    return build_context(df)


def plot_series(series: pd.Series, title: str, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    series.sort_values(ascending=True).plot(kind="barh", ax=ax, color="#4C72B0")
    ax.set_title(title)
    ax.set_xlabel(ylabel)
    st.pyplot(fig)
    plt.close(fig)


def main() -> None:
    st.title("Telco Customer Churn — GenAI Assistant")
    st.caption("Phase 5 · Verified analytics + Google Gemini")

    ctx = get_data_context()
    mode = get_agent_mode()

    with st.sidebar:
        st.header("About")
        st.markdown(
            f"- **Customers:** {ctx.metrics['total_customers']:,}\n"
            f"- **Churn rate:** {ctx.metrics['churn_rate']*100:.1f}%\n"
            f"- **ARPU:** ${ctx.metrics['arpu']:.2f}"
        )
        st.info(f"**Engine:** {mode}")
        st.divider()
        st.subheader("Suggested questions")
        for q in SUGGESTED_QUESTIONS:
            if st.button(q, key=q, use_container_width=True):
                st.session_state["pending_question"] = q
        st.divider()
        st.markdown(
            "**Setup:**\n"
            "- **Gemini (recommended):** `GOOGLE_API_KEY` in `phase5/.env`\n"
            "- OpenAI fallback: `OPENAI_API_KEY`\n"
            "- No API: verified data engine (always accurate)"
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("chart") is not None:
                plot_series(msg["chart"], msg.get("chart_title", ""), "Churn rate (%)")

    question = st.chat_input("Ask about churn, segments, revenue, or at-risk customers...")
    if st.session_state.get("pending_question"):
        question = st.session_state.pop("pending_question")

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Querying data..."):
                answer, engine, chart_series = generate_answer(question, ctx)
                st.caption(f"Powered by: **{engine}**")
                st.markdown(answer)
                chart_payload = None
                chart_title = None
                if chart_series is not None and 0 < len(chart_series) <= 15:
                    chart_title = "Churn rate breakdown"
                    plot_series(chart_series, chart_title, "Churn rate (%)")
                    chart_payload = chart_series

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "chart": chart_payload,
            "chart_title": chart_title,
        })


if __name__ == "__main__":
    main()
