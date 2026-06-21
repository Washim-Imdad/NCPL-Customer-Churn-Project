"""Load and search Phase 2 combined SQL query results for accurate answers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMBINED_CSV = PROJECT_ROOT / "output" / "phase2" / "query_results" / "Combined Query Results.csv"

QUERY_TOPICS: dict[int, tuple[str, tuple[str, ...]]] = {
    1: ("Overall churn rate and customer count", ("overall", "churn rate", "total customer", "how many customer", "kpi", "summary")),
    2: ("Revenue retained vs churned", ("retained vs churned", "total revenue", "revenue by status")),
    3: ("Average revenue per user (ARPU)", ("arpu", "average revenue per user", "avg monthly charge")),
    4: ("Average CLTV by churn status", ("cltv by churn", "cltv churn status", "lifetime value")),
    5: ("Churn rate by payment method", ("payment method", "electronic check", "mailed check", "bank transfer", "credit card")),
    6: ("Churn rate by senior citizen", ("senior citizen", "senior")),
    7: ("Churn by partner and dependents", ("partner", "dependents", "family profile")),
    8: ("Top cities by churn rate", ("city", "cities", "geographic", "location")),
    9: ("ARPU by contract type", ("arpu contract", "contract arpu", "month-to-month arpu")),
    10: ("ARPU by internet service", ("arpu internet", "internet arpu", "fiber arpu", "dsl arpu")),
    11: ("Revenue at risk for high-risk retained customers", ("high-risk", "high risk", "revenue at risk", "retained high risk")),
    12: ("High-value customer churn", ("high value", "high-value", "top 25%", "cltv percentile")),
    13: ("Total lost CLTV", ("lost cltv", "cltv lost", "total lost")),
    14: ("Top stated churn reasons", ("churn reason", "why churn", "why are customer", "why customer leave", "top reason")),
    15: ("Churn reasons by monthly charges", ("reason monthly charge", "reasons ranked")),
    16: ("Churn by service count", ("service count", "add-on", "addon", "services subscribed")),
    17: ("Fiber tech support impact", ("tech support", "technical support")),
    18: ("High-risk rule validation", ("high risk rule", "electronic check paperless", "57.7", "rule match")),
    19: ("Churn by tenure month", ("tenure month", "monthly churn", "by month", "trend")),
    20: ("Top at-risk active customers", ("at-risk", "at risk", "top 20", "call list", "who should we call")),
    21: ("Churn by monthly charge quartile", ("quartile", "charge quartile", "ntile")),
    22: ("Cumulative lost CLTV pareto", ("pareto", "cumulative cltv", "running total cltv")),
    23: ("Cross-segment contract within internet", ("cross-segment", "contract within internet", "fiber month-to-month", "internet and contract")),
}


@dataclass
class QueryInsight:
    number: int
    title: str
    df: pd.DataFrame


def _clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def load_combined_query_results(path: Path | None = None) -> dict[int, QueryInsight]:
    """Parse the combined Phase 2 CSV export into per-query DataFrames."""
    csv_path = path or COMBINED_CSV
    if not csv_path.exists():
        return {}

    lines = csv_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    lines = [line.replace("\ufffd", "").strip() for line in lines]
    insights: dict[int, QueryInsight] = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(r"^QUERY\s+(\d+)\s*:\s*(.+?)\s*,*\s*$", line, re.IGNORECASE)
        if not match:
            i += 1
            continue

        query_num = int(match.group(1))
        title = match.group(2).strip(" ,")
        i += 1

        while i < len(lines) and not _clean_cell(lines[i]):
            i += 1
        if i >= len(lines):
            break

        header = [_clean_cell(c) for c in lines[i].split(",")]
        header = [h for h in header if h]
        i += 1

        rows: list[list[str]] = []
        while i < len(lines):
            row_line = lines[i]
            if not _clean_cell(row_line):
                break
            if re.match(r"^QUERY\s+\d+\s*:", row_line, re.IGNORECASE):
                break
            cells = [_clean_cell(c) for c in row_line.split(",")]
            if cells and any(cells):
                rows.append(cells[: len(header)])
            i += 1

        if header and rows:
            df = pd.DataFrame(rows, columns=header)
            for col in df.columns:
                converted = pd.to_numeric(df[col], errors="coerce")
                if converted.notna().any():
                    df[col] = converted
            insights[query_num] = QueryInsight(number=query_num, title=title, df=df)

    return insights


def _format_dataframe(df: pd.DataFrame, max_rows: int = 15) -> str:
    view = df.head(max_rows)
    return view.to_string(index=False)


def format_query_insight(insight: QueryInsight, max_rows: int = 15) -> str:
    return f"Query {insight.number}: {insight.title}\n{_format_dataframe(insight.df, max_rows=max_rows)}"


def match_query_numbers(question: str) -> list[int]:
    """Return Phase 2 query numbers relevant to a natural-language question."""
    q = question.lower()
    matched: list[tuple[int, int]] = []

    for num, (_, keywords) in QUERY_TOPICS.items():
        score = 0
        for kw in keywords:
            if kw in q:
                score += len(kw)
        if score:
            matched.append((score, num))

    matched.sort(key=lambda x: (-x[0], x[1]))
    return [num for _, num in matched[:3]]


def get_relevant_insights(question: str, insights: dict[int, QueryInsight]) -> str:
    """Format the most relevant precomputed SQL results for a question."""
    if not insights:
        return ""

    numbers = match_query_numbers(question)
    if not numbers:
        return ""

    blocks = [format_query_insight(insights[n]) for n in numbers if n in insights]
    return "\n\n".join(blocks)


def answer_from_insights(question: str, insights: dict[int, QueryInsight]) -> str | None:
    """Direct factual answers for common questions using Phase 2 query exports."""
    if not insights:
        return None

    q = question.lower()

    if any(k in q for k in ("overall", "summary", "kpi")) or q in {"churn rate", "what is the churn rate"}:
        if 1 in insights:
            row = insights[1].df.iloc[0]
            return (
                f"Overall churn rate: {row['churn_rate_pct']:.2f}% "
                f"({int(row['churned_customers']):,} churned / {int(row['total_customers']):,} total). "
                f"Retained: {int(row['retained_customers']):,}."
            )

    if re.search(r"\b(arpu|average revenue)\b", q) and "contract" not in q and "internet" not in q:
        if 3 in insights:
            row = insights[3].df.iloc[0]
            return (
                f"Overall ARPU: ${row['arpu_overall']:.2f}/month "
                f"(range ${row['min_monthly_charge']:.2f}–${row['max_monthly_charge']:.2f})."
            )

    if "payment method" in q or ("payment" in q and "churn" in q):
        if 5 in insights:
            return format_query_insight(insights[5])

    if "high-risk" in q or "high risk" in q or "revenue at risk" in q:
        if 11 in insights:
            high = insights[11].df[insights[11].df["Payment Risk"] == "High"].iloc[0]
            return (
                f"High-risk retained customers: {int(high['retained_customers']):,}. "
                f"Monthly revenue at risk: ${float(high['monthly_revenue_at_risk']):,.2f}. "
                f"Avg monthly charge: ${float(high['avg_monthly_charge']):.2f}."
            )

    if re.search(r"\b(why|reason)\b.*\b(churn|leave|left)\b", q) or "churn reason" in q:
        if 14 in insights:
            return format_query_insight(insights[14])

    if "fiber" in q and "dsl" in q and ("cross-segment" in q or "contract within" in q):
        if 23 in insights:
            return format_query_insight(insights[23], max_rows=8)

    if "service count" in q or "add-on" in q or "addon" in q:
        if 16 in insights:
            return format_query_insight(insights[16])

    if "senior" in q:
        if 6 in insights:
            return format_query_insight(insights[6])

    if "city" in q or "cities" in q:
        if 8 in insights:
            return format_query_insight(insights[8])

    if "tenure" in q and ("month" in q or "trend" in q):
        if 19 in insights:
            return format_query_insight(insights[19], max_rows=12)

    if re.search(r"\b(at[- ]?risk|call list|top \d+)\b", q):
        if 20 in insights:
            n = 10
            m = re.search(r"\btop\s+(\d+)\b", q)
            if m:
                n = int(m.group(1))
            return format_query_insight(insights[20], max_rows=n)

    if "lost cltv" in q or ("cltv" in q and "lost" in q):
        if 13 in insights:
            row = insights[13].df.iloc[0]
            return (
                f"Total lost CLTV from churned customers: ${float(row['total_lost_cltv']):,.0f} "
                f"({int(row['churned_customers']):,} customers, "
                f"avg ${float(row['avg_lost_cltv_per_customer']):,.0f} each)."
            )

    return None
