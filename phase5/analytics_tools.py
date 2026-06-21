"""Data query tools and analytical Q&A engine for Phase 5."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from query_insights import (
    QueryInsight,
    answer_from_insights,
    get_relevant_insights,
    load_combined_query_results,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEANED_CSV = PROJECT_ROOT / "output" / "phase1" / "cleaned_telco_churn.csv"
PREDICTIONS_CSV = PROJECT_ROOT / "output" / "phase3" / "churn_predictions.csv"

SEGMENT_COLUMNS = {
    "contract": "Contract",
    "plan": "Contract",
    "month-to-month": "Contract",
    "internet": "Internet Service",
    "internet service": "Internet Service",
    "fiber": "Internet Service",
    "dsl": "Internet Service",
    "payment risk": "Payment Risk",
    "risk": "Payment Risk",
    "tenure": "Tenure Group",
    "tenure group": "Tenure Group",
    "gender": "Gender",
    "senior": "Senior Citizen",
    "senior citizen": "Senior Citizen",
    "payment method": "Payment Method",
    "payment": "Payment Method",
    "city": "City",
    "state": "State",
    "partner": "Partner",
    "dependents": "Dependents",
    "paperless": "Paperless Billing",
}


@dataclass
class DataContext:
    df: pd.DataFrame
    summary_text: str
    metrics: dict
    query_insights: dict[int, QueryInsight] = field(default_factory=dict)


def _pct(n: float) -> str:
    return f"{n * 100:.1f}%"


def load_merged_data() -> pd.DataFrame:
    if not CLEANED_CSV.exists():
        raise FileNotFoundError(f"Missing Phase 1 output: {CLEANED_CSV}")
    df = pd.read_csv(CLEANED_CSV)
    if PREDICTIONS_CSV.exists():
        preds = pd.read_csv(PREDICTIONS_CSV)
        df = df.merge(
            preds[["CustomerID", "churn_probability", "churn_prediction", "model_used"]],
            on="CustomerID",
            how="left",
        )
    return df


def churn_by_column(df: pd.DataFrame, column: str) -> pd.Series:
    return (
        df.groupby(column, observed=True)["Churn_encoded"]
        .mean()
        .sort_values(ascending=False)
        * 100
    )


def get_overall_kpis(ctx: DataContext) -> str:
    m = ctx.metrics
    retained = ctx.df[ctx.df["Churn_encoded"] == 0]
    high_risk = retained[retained["Payment Risk"] == "High"]
    return (
        f"Total customers: {m['total_customers']:,}\n"
        f"Overall churn rate: {_pct(m['churn_rate'])}\n"
        f"Churned customers: {int(ctx.df['Churn_encoded'].sum()):,}\n"
        f"Retained customers: {int((ctx.df['Churn_encoded'] == 0).sum()):,}\n"
        f"ARPU (avg monthly charges): ${m['arpu']:.2f}\n"
        f"Total lost CLTV (churned): ${m['lost_cltv']:,.0f}\n"
        f"High-risk retained customers: {len(high_risk):,}\n"
        f"Monthly revenue at risk (high-risk retained): ${high_risk['Monthly Charges'].sum():,.2f}"
    )


def get_churn_by_segment(ctx: DataContext, column: str) -> tuple[str, pd.Series]:
    if column not in ctx.df.columns:
        return f"Unknown segment column: {column}", pd.Series(dtype=float)
    series = churn_by_column(ctx.df, column)
    lines = [f"Churn rate by {column}:", *[f"  - {k}: {v:.1f}%" for k, v in series.items()]]
    top = series.index[0]
    lines.append(f"Highest churn segment: {top} ({series.iloc[0]:.1f}%)")
    return "\n".join(lines), series


def get_top_churn_reasons(ctx: DataContext, n: int = 10) -> str:
    reasons = (
        ctx.df.loc[(ctx.df["Churn_encoded"] == 1) & (ctx.df["Churn Reason"] != "Not Applicable"), "Churn Reason"]
        .value_counts()
        .head(n)
    )
    total = int(ctx.df["Churn_encoded"].sum())
    lines = ["Top stated churn reasons:"]
    for reason, count in reasons.items():
        lines.append(f"  - {reason}: {count} ({count / total * 100:.1f}% of churned)")
    return "\n".join(lines)


def get_top_at_risk(ctx: DataContext, n: int = 10) -> str:
    subset = ctx.df[(ctx.df["Churn_encoded"] == 0) & ctx.df["churn_probability"].notna()]
    if subset.empty:
        subset = ctx.df[ctx.df["Churn_encoded"] == 0]
        top = subset.nlargest(n, "Churn Score")[
            ["CustomerID", "Churn Score", "Contract", "Internet Service", "Monthly Charges", "Payment Risk"]
        ].copy()
        return f"Top {n} at-risk retained customers (Churn Score):\n{top.to_string(index=False)}"

    top = subset.nlargest(n, "churn_probability")[
        ["CustomerID", "churn_probability", "Contract", "Internet Service", "Monthly Charges", "Payment Risk"]
    ].copy()
    top["churn_probability"] = (top["churn_probability"] * 100).round(1)
    return f"Top {n} at-risk retained customers (ML probability %):\n{top.to_string(index=False)}"


def get_arpu_breakdown(ctx: DataContext) -> str:
    lines = [f"Overall ARPU: ${ctx.metrics['arpu']:.2f}/month"]
    for col in ["Contract", "Internet Service", "Payment Risk"]:
        grp = ctx.df.groupby(col, observed=True)["Monthly Charges"].mean().sort_values(ascending=False)
        lines.append(f"\nARPU by {col}:")
        lines.extend(f"  - {k}: ${v:.2f}" for k, v in grp.items())
    return "\n".join(lines)


def get_tenure_trend(ctx: DataContext) -> tuple[str, pd.Series]:
    counts = ctx.df.groupby("Tenure Months").size()
    by_month = (
        ctx.df.groupby("Tenure Months")["Churn_encoded"]
        .mean()
        .loc[counts[counts >= 20].index]
        .sort_values(ascending=False)
        .head(12)
        * 100
    )
    lines = [
        "Tenure-month churn rates (min 20 customers per month; no calendar dates in dataset):",
        *[f"  - Month {int(i)}: {v:.1f}%" for i, v in by_month.items()],
    ]
    early = churn_by_column(ctx.df, "Tenure Group")
    lines.append("\nChurn by tenure group:")
    lines.extend(f"  - {k}: {v:.1f}%" for k, v in early.items())
    return "\n".join(lines), by_month


def get_service_count_analysis(ctx: DataContext) -> tuple[str, pd.Series]:
    series = churn_by_column(ctx.df, "Service Count")
    lines = ["Churn rate by number of add-on services:", *[f"  - {int(k)} services: {v:.1f}%" for k, v in series.items()]]
    return "\n".join(lines), series


def get_fiber_vs_dsl(ctx: DataContext) -> str:
    subset = ctx.df[ctx.df["Internet Service"].isin(["Fiber optic", "DSL"])]
    series = churn_by_column(subset, "Internet Service")
    arpu = subset.groupby("Internet Service")["Monthly Charges"].mean()
    lines = ["Fiber optic vs DSL comparison:"]
    for svc in ["Fiber optic", "DSL"]:
        if svc in series.index:
            lines.append(f"  - {svc}: churn {series[svc]:.1f}%, avg monthly charge ${arpu.get(svc, 0):.2f}")
    mtm = ctx.df[ctx.df["Contract"] == "Month-to-month"]["Churn_encoded"].mean() * 100
    lines.append(f"  - Month-to-month contract churn (all services): {mtm:.1f}%")
    return "\n".join(lines)


def get_high_risk_summary(ctx: DataContext) -> str:
    retained = ctx.df[ctx.df["Churn_encoded"] == 0]
    high = retained[retained["Payment Risk"] == "High"]
    high_churn = ctx.df[ctx.df["Payment Risk"] == "High"]["Churn_encoded"].mean() * 100
    rule = ctx.df[
        (ctx.df["Contract"] == "Month-to-month")
        & (ctx.df["Payment Method"] == "Electronic check")
        & (ctx.df["Paperless Billing"] == "Yes")
    ]
    rule_rate = rule["Churn_encoded"].mean() * 100 if len(rule) else 0
    return (
        f"High payment risk segment churn rate: {high_churn:.1f}%\n"
        f"High-risk retained customers: {len(high):,}\n"
        f"Monthly revenue at risk: ${high['Monthly Charges'].sum():,.2f}\n"
        f"High-risk rule (MTM + electronic check + paperless): {rule_rate:.1f}% churn "
        f"({int(rule['Churn_encoded'].sum()):,} churned / {len(rule):,} customers)"
    )


def detect_segment_column(question: str) -> str | None:
    q = question.lower()
    # Prefer longer keys first to avoid "payment" matching before "payment method"
    for key, col in sorted(SEGMENT_COLUMNS.items(), key=lambda x: -len(x[0])):
        if key in q:
            return col
    return None


def build_context(df: pd.DataFrame) -> DataContext:
    insights = load_combined_query_results()
    metrics = {
        "total_customers": len(df),
        "churn_rate": df["Churn_encoded"].mean(),
        "arpu": df["Monthly Charges"].mean(),
        "lost_cltv": df.loc[df["Churn_encoded"] == 1, "CLTV"].sum(),
        "by_contract": churn_by_column(df, "Contract").to_dict(),
        "by_internet": churn_by_column(df, "Internet Service").to_dict(),
        "by_payment_risk": churn_by_column(df, "Payment Risk").to_dict(),
        "by_tenure": churn_by_column(df, "Tenure Group").to_dict(),
        "top_reasons": (
            df.loc[(df["Churn_encoded"] == 1) & (df["Churn Reason"] != "Not Applicable"), "Churn Reason"]
            .value_counts()
            .head(5)
            .to_dict()
        ),
    }
    ctx_stub = DataContext(df, "", metrics, insights)
    summary = "\n\n".join([
        get_overall_kpis(ctx_stub),
        get_churn_by_segment(ctx_stub, "Contract")[0],
        get_churn_by_segment(ctx_stub, "Internet Service")[0],
        get_churn_by_segment(ctx_stub, "Payment Risk")[0],
        get_top_churn_reasons(ctx_stub),
        get_high_risk_summary(ctx_stub),
    ])
    return DataContext(df=df, summary_text=summary, metrics=metrics, query_insights=insights)


def _append_insights(ctx: DataContext, question: str, base_text: str) -> str:
    """Prefer Phase 2 SQL exports when available for the same topic."""
    direct = answer_from_insights(question, ctx.query_insights)
    if direct:
        return direct

    extra = get_relevant_insights(question, ctx.query_insights)
    if extra and extra not in base_text:
        return f"{base_text}\n\n--- Phase 2 SQL results ---\n{extra}"
    return base_text


def answer_question(question: str, ctx: DataContext) -> tuple[str, pd.Series | None]:
    """Rule-based Q&A — always uses real data; Phase 2 CSV when matched."""
    q = question.lower().strip()

    if re.search(r"\b(why|reason|cause)\b.*\b(churn|churning|churned|leave|left)\b", q) or \
       re.search(r"\b(churn|churning)\b.*\b(why|reason|cause)\b", q):
        text = get_top_churn_reasons(ctx, 10)
        contract = churn_by_column(ctx.df, "Contract")
        internet = churn_by_column(ctx.df, "Internet Service")
        risk = churn_by_column(ctx.df, "Payment Risk")
        text += (
            f"\n\nKey drivers from data:\n"
            f"  - Month-to-month contracts: {contract.get('Month-to-month', 0):.1f}% churn\n"
            f"  - Fiber optic: {internet.get('Fiber optic', 0):.1f}% churn\n"
            f"  - High payment risk: {risk.get('High', 0):.1f}% churn\n"
            f"  - Early tenure (0-12 months) is the highest-risk period."
        )
        return _append_insights(ctx, question, text), None

    if re.search(r"\b(top|at[- ]?risk|highest risk|call list|who should)\b", q):
        n = 10
        m = re.search(r"\btop\s+(\d+)\b", q)
        if m:
            n = int(m.group(1))
        return _append_insights(ctx, question, get_top_at_risk(ctx, n)), None

    if re.search(r"\b(high[- ]?risk|revenue at risk)\b.*\b(retained|still|active)\b", q) or \
       re.search(r"\b(how many|count)\b.*\bhigh[- ]?risk\b", q):
        return _append_insights(ctx, question, get_high_risk_summary(ctx)), None

    if "compare" in q and ("fiber" in q or "dsl" in q):
        return _append_insights(ctx, question, get_fiber_vs_dsl(ctx)), churn_by_column(ctx.df, "Internet Service")

    if "fiber" in q and "churn" in q:
        series = churn_by_column(ctx.df, "Internet Service")
        text = (
            f"Fiber optic churn: {series.get('Fiber optic', 0):.1f}%. "
            f"DSL: {series.get('DSL', 0):.1f}%. No internet: {series.get('No', 0):.1f}%."
        )
        return _append_insights(ctx, question, text), series

    if re.search(r"\b(arpu|average revenue|monthly charge|revenue per user)\b", q):
        text = get_arpu_breakdown(ctx)
        if "lost" in q or "cltv" in q:
            text += f"\n\nTotal lost CLTV from churned customers: ${ctx.metrics['lost_cltv']:,.0f}"
        return _append_insights(ctx, question, text), None

    if re.search(r"\b(trend|tenure month|by month|over time)\b", q):
        text, series = get_tenure_trend(ctx)
        return _append_insights(ctx, question, text), series

    if re.search(r"\b(service count|add[- ]?on|services subscribed)\b", q):
        text, series = get_service_count_analysis(ctx)
        return _append_insights(ctx, question, text), series

    if "payment method" in q or ("payment" in q and "churn" in q and "risk" not in q):
        text, series = get_churn_by_segment(ctx, "Payment Method")
        return _append_insights(ctx, question, text), series

    if "senior" in q:
        text, series = get_churn_by_segment(ctx, "Senior Citizen")
        return _append_insights(ctx, question, text), series

    if re.search(r"\b(highest|most|worst|which segment|which group|segment)\b.*\bchurn\b", q) or \
       re.search(r"\bchurn\b.*\b(highest|most|segment|contract|internet|risk|tenure)\b", q):
        col = detect_segment_column(q) or "Contract"
        text, series = get_churn_by_segment(ctx, col)
        return _append_insights(ctx, question, text), series

    if re.search(r"\b(overall|total|how many|summary|kpi)\b", q) or q in {"churn rate", "what is the churn rate"}:
        return _append_insights(ctx, question, get_overall_kpis(ctx)), None

    if "churn rate" in q:
        col = detect_segment_column(q)
        if col:
            text, series = get_churn_by_segment(ctx, col)
            return _append_insights(ctx, question, text), series
        return _append_insights(ctx, question, get_overall_kpis(ctx)), None

    if re.search(r"\b(model|machine learning|ml|prediction|roc|accuracy)\b", q):
        return (
            "Phase 3 ML results:\n"
            "  - Logistic Regression: ROC-AUC 0.848 (best), recall 78%\n"
            "  - Random Forest: accuracy 77.7%\n"
            "  - XGBoost: ROC-AUC 0.838\n"
            "Churn probabilities in output/phase3/churn_predictions.csv. "
            "Churn Score was excluded from features to prevent leakage.",
        ), None

    direct = answer_from_insights(question, ctx.query_insights)
    if direct:
        return direct, None

    return (
        get_overall_kpis(ctx) + "\n\n" +
        get_churn_by_segment(ctx, "Contract")[0] + "\n\n" +
        "Ask about: segments, reasons, at-risk customers, ARPU, tenure trends, fiber vs DSL, payment method.",
        None,
    )


def get_verified_facts(question: str, ctx: DataContext) -> str:
    """Build the full factual payload passed to Gemini (never guess numbers)."""
    analytical, _ = answer_question(question, ctx)
    extra = get_relevant_insights(question, ctx.query_insights)
    parts = [analytical]
    if extra and extra not in analytical:
        parts.append(extra)
    return "\n\n".join(parts)
